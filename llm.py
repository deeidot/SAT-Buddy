import os
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# This is the "System Prompt". It tells the AI how to behave.
SAT_SYSTEM = """You are an experienced, encouraging SAT study buddy named Tutor.
- The student is preparing for the Digital SAT.
- Explain concepts concisely, give a worked example, then ask one practice question.
- Plain language, no filler, never fabricate scoring rules.
- Keep spoken-style answers under ~120 words so TTS stays snappy.
- NEW: When showing math equations, ALWAYS format them using LaTeX (e.g., $$ \frac{1}{2} $$)."""

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

def ask_llm_with_image(user_text, base64_image, history):
    """
    This function takes text AND an image, and asks Groq's Vision model to answer.
    """
    messages = [{"role": "system", "content": SAT_SYSTEM}] + history
    
    # If the user didn't type anything, provide a default prompt
    if not user_text:
        user_text = "Please read the question in this image and solve it step-by-step."

    # This is the special format Groq requires to accept an image
    user_message = {
        "role": "user",
        "content": [
            {"type": "text", "text": user_text},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        ]
    }
    messages.append(user_message)
    
    # Call Groq's Vision-capable model
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct", # Groq's vision model
        messages=messages,
        max_tokens=512,
        temperature=0.6,
    )
    return response.choices[0].message.content