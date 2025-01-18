import asyncio
import base64
import io
import traceback

import cv2
import numpy as np
import PIL.Image
import pyaudio
from google import genai
from google.cloud import speech
from prisma import Prisma
from prisma.models import Message

from zenn_ai_agent.config import config as app_config
from zenn_ai_agent.speach import speak_from_bytes

FORMAT = pyaudio.paInt16
CHANNELS = 1  # monaural
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024


async def text2text(session: object):
    message = input("User> ")
    await session.send(message, end_of_turn=True)

    async for response in session.receive():
        if response.text is None:
            continue
        print(response.text, end="")


async def text2audio(session: object):
    message = input("User> ")
    await session.send(message, end_of_turn=True)

    audio_data = []
    async for message in session.receive():
        if message.server_content.model_turn:
            for part in message.server_content.model_turn.parts:
                if part.inline_data:
                    audio_data.append(part.inline_data.data)
    if audio_data:
        speak_from_bytes(b"".join(audio_data), sample_rate=24_000)


class AudioLoop:
    def __init__(self, session):
        self.session = session

        self.audio_in_queue = None
        self.out_queue = None
        self.db_queue = None

        self.audio_interface = pyaudio.PyAudio()
        self.audio_stream = None

        self.speach = speech.SpeechClient()

        try:
            from libcamera import controls
            from picamera2 import Picamera2

            self.picam2 = Picamera2()
            sensor_modes = self.picam2.sensor_modes
            print("=== sensor_modes ===")
            print(sensor_modes)
            mode = sensor_modes[0]

            camera_controls = {
                "AfMode": controls.AfModeEnum.Continuous,
            }
            preview_config = self.picam2.create_preview_configuration(
                main={
                    "format": "XRGB8888",
                    "size": (1920, 1080),
                },
                # buffer_count=4,
                controls=camera_controls,
                raw=mode,
            )
            self.picam2.configure(preview_config)
            config = self.picam2.camera_configuration()
            print("=== camera config ===")
            print(config)

            self.picam2.start(config=preview_config)
            self.picam2.set_controls({"ScalerCrop": mode["crop_limits"]})

            metadata = self.picam2.capture_metadata()
            print("=== metadata ===")
            print(metadata)
        except ModuleNotFoundError:
            print("libcamera or picamera2 is not installed.")
            self.picam2 = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(input, "User> ")
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def save_db(self):
        language_code = "ja-JP"  # a BCP-47 language tag
        speach_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SEND_SAMPLE_RATE,
            language_code=language_code,
        )
        while True:
            data = await self.db_queue.get()
            response = self.speach.recognize(speach_config, data["audio"])
            transcript = ""
            for result in response.results:
                transcript += result.alternatives[0].transcript
            transcript = data.get("transcript")
            await Message.prisma().create(
                {
                    "contentAudio": data["data"],
                    "contentTranscript": transcript,
                    "speaker": data["speaker"],
                }
            )

    async def listen_audio(self):
        mic_info = self.audio_interface.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            self.audio_interface.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}

        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)

            # await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

            # FIXME: For some reason, the response stops coming back.
            audio_data = np.frombuffer(data, dtype=np.int16)
            mean_abs_amplitude = np.abs(audio_data).mean()
            if mean_abs_amplitude > 500:
                await self.db_queue.put({"audio": data, "speaker": "USER"})
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    def _get_frame(self, frame_rgb):
        img = PIL.Image.fromarray(frame_rgb)  # Now using RGB frame
        img.thumbnail([1024, 1024])

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        if not self.picam2:
            # This takes about a second, and will block the whole program
            # causing the audio pipeline to overflow if you don't to_thread it.
            cap = await asyncio.to_thread(
                cv2.VideoCapture,
                0,  # 0 represents the default camera
            )
            # Prevent `tryIoctl VIDEOIO(V4L2:/dev/video0): select() timeout.` error
            # ref: https://stackoverflow.com/questions/69575185/raspberry-pi-3-video-error-select-timeout-ubuntu
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))

        while True:
            if self.picam2:
                frame = self.picam2.capture_array()
                # 画像が3チャンネル以外の場合は3チャンネルに変換する
                channels = 1 if len(frame.shape) == 2 else frame.shape[2]
                if channels == 1:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                if channels == 4:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                frame_data = await asyncio.to_thread(self._get_frame, frame_rgb)
            else:
                ret, frame = cap.read()
                if not ret:
                    break
                # Fix: Convert BGR to RGB color space
                # OpenCV captures in BGR but PIL expects RGB format
                # This prevents the blue tint in the video feed
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_data = await asyncio.to_thread(self._get_frame, frame_rgb)

            await asyncio.sleep(2.0)

            await self.out_queue.put(frame_data)

        # Release the VideoCapture object
        cap.release()

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    self.db_queue.put_nowait({"data": data, "speaker": "SYSTEM"})
                    continue
                if text := response.text:
                    print(text, end="")

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            self.audio_interface.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            async with asyncio.TaskGroup() as tg:
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)
                self.db_queue = asyncio.Queue()

                send_text_task = tg.create_task(self.send_text())
                # tg.create_task(self.get_frames())
                tg.create_task(self.listen_audio())
                tg.create_task(self.send_realtime())

                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")
        except asyncio.CancelledError:
            pass
        except ExceptionGroup as EG:
            self.audio_stream.close()
            if self.picam2:
                self.picam2.stop()
            traceback.print_exception(EG)


async def main():
    client = genai.Client(
        api_key=app_config.gemini_api_key, http_options={"api_version": "v1alpha"}
    )
    model_id = "gemini-2.0-flash-exp"
    config = {
        "response_modalities": ["AUDIO"],
        "system_instruction": {"parts": [{"text": "Please answer in Japanese."}]},
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Puck",
            }
        },
    }

    prisma = Prisma(auto_register=True)

    try:
        await prisma.connect()
        async with client.aio.live.connect(model=model_id, config=config) as session:
            await AudioLoop(session).run()
            # while True:
            #     await text2audio(session)
    except Exception as e:
        print(e)
    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
