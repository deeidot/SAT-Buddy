import os
import io
from groq import Groq
from scipy.io.wavfile import write as wav_write

# We initialize the Groq client. It automatically looks for the GROQ_API_KEY 
# in your environment variables (which python-dotenv loaded from your .env file).
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def transcribe(pcm_audio, sample_rate=16000):
    """
    This function takes raw audio data (pcm_audio) and sends it to Groq.
    """
    # Groq expects a .wav file, not just raw numbers. So we use scipy to 
    # convert our numpy array of numbers into a virtual .wav file in memory.
    buffer = io.BytesIO()
    wav_write(buffer, sample_rate, pcm_audio)
    buffer.seek(0) # Rewind the buffer to the beginning
    buffer.name = "audio.wav" # Groq needs to see a filename ending in .wav

    # We ask Groq to transcribe the audio using their fastest Whisper model
    response = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=buffer,
        response_format="text", # We just want the text back, no extra formatting
    )
    return response.strip()