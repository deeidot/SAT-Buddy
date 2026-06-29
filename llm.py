import os
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# This is the "System Prompt". It tells the AI how to behave.
SAT_SYSTEM = """You are an experienced, encouraging SAT study buddy named Tutor.
- The student is preparing for the Digital SAT.
- Explain concepts concisely, give a worked example, then ask one practice question.
- Plain language, no filler, never fabricate scoring rules.
- Keep spoken-style answers under ~120 words so TTS stays snappy.
- When showing math equations, ALWAYS format them using LaTeX (e.g., $$ \frac{1}{2} $$)."""

def ask_llm(user_text, history, user_emotion="neutral"):
    """
    Takes text, history, and emotion. Updates the system prompt dynamically
    based on how the user is feeling, then asks Groq for a reply.
    """
    # Change the system prompt based on emotion!
    dynamic_prompt = SAT_SYSTEM
    if user_emotion in ["sad", "fearful", "angry", "disgusted"]:
        dynamic_prompt += "\n\nIMPORTANT: The user looks frustrated or upset right now. Be extra encouraging, offer a word of support, and perhaps suggest taking a 5-minute break if they are stuck."
    elif user_emotion == "surprised":
        dynamic_prompt += "\n\nThe user looks surprised. Maybe they just learned something new! Ask if that concept makes sense."

    messages = [{"role": "system", "content": dynamic_prompt}] + history + \
               [{"role": "user", "content": user_text}]
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=256,
        temperature=0.6,
    )
    return response.choices[0].message.content

def ask_llm_with_image(user_text, base64_image, history, user_emotion="neutral"):
    """
    Takes text, image, history, and emotion. Asks Groq's Vision model to answer.
    """
    dynamic_prompt = SAT_SYSTEM
    if user_emotion in ["sad", "fearful", "angry", "disgusted"]:
        dynamic_prompt += "\n\nIMPORTANT: The user looks frustrated or upset right now. Be extra encouraging and supportive."

    messages = [{"role": "system", "content": dynamic_prompt}] + history
    
    if not user_text:
        user_text = "Please read the question in this image and solve it step-by-step."

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
    
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct", # Groq's vision model
        messages=messages,
        max_tokens=512,
        temperature=0.6,
    )
    return response.choices[0].message.content

def proactive_checkin(emotion):
    """
    Called automatically when the user is frustrated for a long time.
    Generates a short, spoken-style supportive message.
    """
    prompt = f"The user has been looking {emotion} for a while while studying. Say one short, encouraging sentence to check in on them. Keep it under 20 words. Do not ask a math question, just offer support."
    
    messages = [
        {"role": "system", "content": "You are a supportive SAT tutor."},
        {"role": "user", "content": prompt}
    ]
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=50,
        temperature=0.7,
    )
    
    return response.choices[0].message.content

def proactive_checkin(emotion):
    prompt = f"The user has been looking {emotion} for a while while studying. Say one short, encouraging sentence to check in on them. Keep it under 20 words. Do not ask a math question, just offer support."
    
    messages = [
        {"role": "system", "content": "You are a supportive SAT tutor."},
        {"role": "user", "content": prompt}
    ]
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=50,
        temperature=0.7,
    )
    return response.choices[0].message.content