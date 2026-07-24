import io
import os

from groq import Groq
from scipy.io.wavfile import write as wav_write

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    _client = Groq(api_key=api_key)
    return _client


def transcribe(audio_data, sample_rate=16000):
    """
    Accepts either raw numpy audio arrays from the desktop app or a BytesIO WAV
    file from the Flask app, then sends it to Groq Whisper.
    """
    if isinstance(audio_data, io.BytesIO):
        audio_data.seek(0)
        buffer = audio_data
    else:
        buffer = io.BytesIO()
        wav_write(buffer, sample_rate, audio_data)
        buffer.seek(0)

    buffer.name = "audio.wav"

    response = _get_client().audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=buffer,
        response_format="text",
    )
    return response.strip()
