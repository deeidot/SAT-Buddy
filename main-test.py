# import os
# import numpy as np
# import sounddevice as sd
# from dotenv import load_dotenv

# # 1. Load the .env file FIRST
# load_dotenv()

# # 2. Import our employees
# from stt import transcribe
# from llm import ask_llm

# # --- Microphone Code (Paused for now) ---
# # def record_until_silence(threshold=0.012, silence_limit=1.2, max_len=12.0):
# #     ... (we can leave this here, we just won't call it)

# def main():
#     print("SAT buddy ready (Text Mode). Type 'quit' to exit.")
#     print("-" * 40)
    
#     # Move history inside main()
#     history = []
    
#     while True:
#         # 1. Get input from the keyboard instead of the microphone
#         user_text = input("Student: ")
        
#         # Allow a way to exit the loop
#         if user_text.lower() in ['quit', 'exit']:
#             print("Goodbye!")
#             break
            
#         # Ignore empty inputs
#         if not user_text.strip():
#             continue
            
#         # 2. Send text to Groq Llama to get an answer
#         print("🧠 Tutor is thinking...")
#         reply = ask_llm(user_text, history)
#         print(f"\nTutor: {reply}\n")
#         print("-" * 40)
        
#         # 3. Save this exchange so the AI has memory next time
#         history.append({"role": "user", "content": user_text})
#         history.append({"role": "assistant", "content": reply})
#         # Keep the history from getting too long
#         history = history[-8:]

# if __name__ == "__main__":
#     main()
    