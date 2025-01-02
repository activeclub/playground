import pyttsx3
import speech_recognition as sr
from google import genai
from google.cloud import texttospeech

from zenn_ai_agent.config import config

client = genai.Client(
    api_key=config.gemini_api_key, http_options={"api_version": "v1alpha"}
)
model_id = "gemini-2.0-flash-exp"
config = {"response_modalities": ["TEXT"]}

r = sr.Recognizer()

engine = pyttsx3.init()
# for voice in engine.getProperty('voices'):
#     print(voice)
# engine.setProperty('voice', 'com.apple.eloquence.ja-JP.Sandy')
engine.setProperty('voice', 'Japanese')
# engine.setProperty('rate', 150)  # 読み上げ速度

client = texttospeech.TextToSpeechClient()

async def main():
    print("Hello from zenn-ai-agent!")
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


def speak(text: str):
    # engine.say(text)
    # engine.runAndWait()

    input = texttospeech.SynthesisInput()
    input.text = "text_value"

    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    request = texttospeech.SynthesizeSpeechRequest(
        input=input,
        voice=voice,
        audio_config=audio_config,
    )

    # Make the request
    response = client.synthesize_speech(request=request)
    print(response)

def speech_test():
    with sr.Microphone() as source:
        speak("こんにちは")
        # speak("Say something!")
        print("Say something!")
        audio = r.listen(source)

    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        text = r.recognize_google(audio)
        print("Google Speech Recognition thinks you said " + text)
        speak(text)
    except sr.UnknownValueError as e:
        print(f"Google Speech Recognition could not understand audio; {e}")
    except sr.RequestError as e:
        print(
            "Could not request results from Google Speech Recognition service; {0}".format(
                e
            )
        )


if __name__ == "__main__":
    # asyncio.run(main())
    speech_test()