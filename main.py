import os
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

# 1. Load the .env file FIRST
load_dotenv()

# 2. Import our employees
from stt import transcribe
from llm import ask_llm

def record_until_silence(threshold=0.012, silence_limit=1.2, max_len=12.0):
    """
    This uses your Mac's microphone. It listens for sound.
    If the sound drops below 'threshold' for 'silence_limit' seconds, 
    it assumes you finished speaking and stops recording.
    """
    frames, silence_count, total = [], 0.0, 0.0
    chunk = 0.5 # Read audio in half-second chunks
    
    with sd.InputStream(samplerate=16000, channels=1, dtype='float32') as stream:
        print("🎤 Listening... (speak now)")
        while total < max_len:
            data, _ = stream.read(int(16000 * chunk))
            frames.append(data)
            total += chunk
            
            # Calculate how loud the current chunk is
            volume = np.linalg.norm(data) / len(data)
            
            if volume < threshold:
                silence_count += chunk
                if silence_count >= silence_limit:
                    break # You stopped talking, end the recording
            else:
                silence_count = 0 # You are still talking, reset the silence timer
                
    # Convert the audio from decimal numbers (-1.0 to 1.0) to 16-bit integers 
    audio = (np.concatenate(frames) * 32767).astype(np.int16)
    return audio

def main():
    print("SAT buddy ready (laptop MVP). Press Ctrl+C to quit.")
    
    # Move history inside main() so Python doesn't get confused about scope
    history = []
    
    while True:
        # 1. Record audio from mic
        pcm = record_until_silence()
        if len(pcm) < 4000: # Ignore tiny clicks
            continue
            
        # 2. Send audio to Groq Whisper to get text
        print("⏳ Transcribing...")
        user_text = transcribe(pcm)
        
        # 3. Ignore empty transcriptions or hallucinations like "."
        if not user_text or len(user_text) < 2:
            print("Didn't catch that, please try again.\n")
            continue
            
        print(f"\nStudent: {user_text}")
        
        # 4. Send text to Groq Llama to get an answer
        print("🧠 Tutor is thinking...")
        reply = ask_llm(user_text, history)
        print(f"Tutor: {reply}\n")
        
        # 5. Save this exchange so the AI has memory next time
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        # Keep the history from getting too long
        history = history[-8:]

if __name__ == "__main__":
    main()