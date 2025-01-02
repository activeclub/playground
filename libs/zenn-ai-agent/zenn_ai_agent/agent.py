import asyncio

from google import genai

from zenn_ai_agent.config import config as app_config


async def main():
    client = genai.Client(
        api_key=app_config.gemini_api_key, http_options={"api_version": "v1alpha"}
    )
    model_id = "gemini-2.0-flash-exp"
    config = {"response_modalities": ["TEXT"]}

    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            message = input("User> ")
            if message.lower() == "exit":
                break
            await session.send(message, end_of_turn=True)

            async for response in session.receive():
                if response.text is None:
                    continue
                print(response.text, end="")


if __name__ == "__main__":
    asyncio.run(main())
