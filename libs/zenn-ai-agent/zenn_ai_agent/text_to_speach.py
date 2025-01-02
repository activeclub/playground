import subprocess

from google.cloud import texttospeech


def speak(text: str) -> None:
    client = texttospeech.TextToSpeechClient()

    input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )

    request = texttospeech.SynthesizeSpeechRequest(
        input=input,
        voice=voice,
        audio_config=audio_config,
    )

    # Make the request
    response = client.synthesize_speech(request=request)

    audio_file = "output.wav"
    with open(audio_file, "wb") as out:
        # Write the response to the output file.
        out.write(response.audio_content)
        subprocess.call(f"aplay -q {audio_file}", shell=True)


def main() -> None:
    text = "こんにちは！"
    speak(text)


if __name__ == "__main__":
    main()
