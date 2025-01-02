import asyncio
import re

from google import genai

from zenn_ai_agent.config import config as app_config
from zenn_ai_agent.speach_to_text import GoogleSpeach, MicrophoneStream
from zenn_ai_agent.text_to_speach import speak

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


async def listen_loop(responses: object, session: object) -> str:
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = " " * (num_chars_printed - len(transcript))

        if not result.is_final:
            await session.send(transcript, end_of_turn=True)
            async for res in session.receive():
                if res.text is None:
                    continue
                speak(res.text)

            num_chars_printed = len(transcript)

        else:
            print(transcript + overwrite_chars)

            # Exit recognition if any of the transcribed phrases could be
            # one of our keywords.
            if re.search(r"\b(exit|quit)\b", transcript, re.I):
                print("Exiting..")
                break

            num_chars_printed = 0

    return transcript


async def main() -> None:
    client = genai.Client(
        api_key=app_config.gemini_api_key, http_options={"api_version": "v1alpha"}
    )
    model_id = "gemini-2.0-flash-exp"
    config = {"response_modalities": ["TEXT"]}

    speach = GoogleSpeach()

    async with client.aio.live.connect(model=model_id, config=config) as session:
        with MicrophoneStream(RATE, CHUNK) as stream:
            audio_generator = stream.generator()
            responses = speach.recognize(audio_generator)
            await listen_loop(responses, session)


if __name__ == "__main__":
    asyncio.run(main())
