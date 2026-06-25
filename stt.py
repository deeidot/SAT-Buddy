import os
import io
from groq import Groq
from scipy.io.wavfile import write as wav_write

client = Groq(api_key=os.environ["GROQ_API_KEY"])

def transcribe(audio_data, sample_rate=16000):
    """
    This function can accept either:
    1. Raw numpy audio arrays (from main.py microphone)
    2. A BytesIO file object (from app.py web server)
    """
    # Check if it's a file object coming from the web server
    if isinstance(audio_data, io.BytesIO):
        audio_data.seek(0)
        buffer = audio_data
    else:
        # It's raw numpy data, so we need to convert it to a wav file first
        buffer = io.BytesIO()
        wav_write(buffer, sample_rate, audio_data)
        buffer.seek(0)
    
    # Groq needs a filename to know it's a wav file
    buffer.name = "audio.wav"

    # Send to Groq Whisper
    response = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=buffer,
        response_format="text",
    )
    return response.strip()