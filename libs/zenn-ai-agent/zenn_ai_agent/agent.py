import asyncio
import base64
import io
import traceback

import cv2
import numpy as np
import PIL.Image
import pyaudio
from google import genai

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

        self.audio_interface = pyaudio.PyAudio()

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(input, "User> ")
            if text.lower() == "q":
                break
            await self.session.send(text or ".", end_of_turn=True)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(msg)

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
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

            audio_data = np.frombuffer(data, dtype=np.int16)
            if np.abs(audio_data).mean() > 500:
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    def _get_frame(self, cap):
        # Read the frameq
        ret, frame = cap.read()
        # Check if the frame was read successfully
        if not ret:
            return None
        # Fix: Convert BGR to RGB color space
        # OpenCV captures in BGR but PIL expects RGB format
        # This prevents the blue tint in the video feed
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)  # Now using RGB frame
        img.thumbnail([1024, 1024])

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        # This takes about a second, and will block the whole program
        # causing the audio pipeline to overflow if you don't to_thread it.
        cap = await asyncio.to_thread(
            cv2.VideoCapture,
            0,  # 0 represents the default camera
        )

        while True:
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break

            await asyncio.sleep(1.0)

            await self.out_queue.put(frame)

        # Release the VideoCapture object
        cap.release()

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
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

                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.get_frames())
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
            traceback.print_exception(EG)


async def main():
    client = genai.Client(
        api_key=app_config.gemini_api_key, http_options={"api_version": "v1alpha"}
    )
    model_id = "gemini-2.0-flash-exp"
    config = {
        "response_modalities": ["AUDIO"],
        "system_instruction": {"parts": [{"text": "Please answer in Japanese."}]},
    }

    async with client.aio.live.connect(model=model_id, config=config) as session:
        await AudioLoop(session).run()
        # while True:
        #     await text2audio(session)


if __name__ == "__main__":
    asyncio.run(main())
