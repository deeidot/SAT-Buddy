import os
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# This is the "System Prompt". It tells the AI how to behave.
SAT_SYSTEM = """You are an experienced, encouraging SAT study buddy named Tutor.
- The student is preparing for the Digital SAT.
- Explain concepts concisely, give a worked example, then ask one practice question.
- Plain language, no filler, never fabricate scoring rules.
- Keep spoken-style answers under ~120 words so TTS stays snappy."""

def ask_llm(user_text, history):
    """
    This function takes the user's text and the conversation history,
    and asks Groq's Llama model to generate a reply.
    """
    # We build the "messages" array. LLMs read this like a script.
    # [System] = the rules. [History] = what we said before. [User] = what you just said.
    messages = [{"role": "system", "content": SAT_SYSTEM}] + history + \
               [{"role": "user", "content": user_text}]
    
    # We send the script to Groq
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", # Fast, free, and smart enough
        messages=messages,
        max_tokens=256, # Limits how long the answer can be
        temperature=0.6, # A little creative, but mostly factual
    )
    
    # Extract just the text from the response
    return response.choices[0].message.content