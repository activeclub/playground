import asyncio

from google import genai

from zenn_ai_agent.config import config as app_config
from zenn_ai_agent.speach import speak_from_bytes


async def text2text(session: object):
    async for response in session.receive():
        if response.text is None:
            continue
        print(response.text, end="")


async def text2audio(session: object):
    audio_data = []
    async for message in session.receive():
        if message.server_content.model_turn:
            for part in message.server_content.model_turn.parts:
                if part.inline_data:
                    audio_data.append(part.inline_data.data)
    if audio_data:
        speak_from_bytes(b"".join(audio_data), sample_rate=24_000)


async def main():
    client = genai.Client(
        api_key=app_config.gemini_api_key, http_options={"api_version": "v1alpha"}
    )
    model_id = "gemini-2.0-flash-exp"
    config = {"response_modalities": ["AUDIO"]}

    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            message = input("User> ")
            if message.lower() == "exit":
                break
            await session.send(message, end_of_turn=True)

            await text2audio(session)


if __name__ == "__main__":
    asyncio.run(main())
