import json
import os
import re

from groq import Groq

_client = None


SAT_SYSTEM = """You are an experienced, encouraging SAT study buddy named Buddy.
- The student is preparing for the Digital SAT.
- Prioritize wellbeing: protect the student's energy, reduce burnout, and suggest breaks when focus is fading.
- Explain concepts concisely, give a worked example when useful, then ask one practice question when it fits.
- Plain language, no filler, never fabricate scoring rules.
- Keep spoken-style answers under about 120 words so TTS stays snappy.
- When showing math equations, ALWAYS format them using LaTeX, for example $$ \\frac{1}{2} $$."""


def _get_client():
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    _client = Groq(api_key=api_key)
    return _client


def _chat(messages, max_tokens=256, temperature=0.6, model="llama-3.1-8b-instant"):
    client = _get_client()
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not set.")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _fallback_plan(prompt):
    total_minutes = 60
    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|hr|h)\b", prompt, re.I)
    minute_match = re.search(r"(\d+)\s*(minutes?|mins?|min|m)\b", prompt, re.I)

    if hour_match:
        total_minutes = max(10, int(float(hour_match.group(1)) * 60))
    elif minute_match:
        total_minutes = max(10, int(minute_match.group(1)))

    focus = prompt.strip().rstrip(".") or "the requested SAT topic"
    focus = re.sub(r"^i want to study\s+", "", focus, flags=re.I)
    focus = re.sub(r"\s+for\s+\d+.*$", "", focus, flags=re.I).strip() or "the requested SAT topic"

    def fmt(minutes):
        hours, mins = divmod(minutes, 60)
        return f"{hours:02d}:{mins:02d}"

    blocks = []
    elapsed = 0
    remaining = total_minutes
    while remaining > 0:
        study_minutes = min(25, remaining)
        blocks.append(
            {
                "time": f"{fmt(elapsed)}-{fmt(elapsed + study_minutes)}",
                "task": f"Study {focus}",
                "type": "study",
            }
        )
        elapsed += study_minutes
        remaining -= study_minutes

        if remaining > 0:
            break_minutes = min(5, remaining)
            blocks.append(
                {
                    "time": f"{fmt(elapsed)}-{fmt(elapsed + break_minutes)}",
                    "task": "Break",
                    "type": "break",
                }
            )
            elapsed += break_minutes
            remaining -= break_minutes

    return json.dumps(blocks)


def _extract_json_array(raw_text):
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Planner response must be a JSON array.")

    normalized = []
    for block in parsed:
        if not isinstance(block, dict):
            raise ValueError("Each planner block must be an object.")
        normalized.append(
            {
                "time": str(block.get("time", "")).strip(),
                "task": str(block.get("task", "")).strip(),
                "type": str(block.get("type", "study")).strip().lower(),
            }
        )
    return json.dumps(normalized)


def ask_llm(user_text, history, user_emotion="neutral"):
    dynamic_prompt = SAT_SYSTEM
    if user_emotion in ["sad", "fearful", "angry", "disgusted"]:
        dynamic_prompt += (
            "\n\nIMPORTANT: The user looks frustrated or upset right now. Be extra "
            "encouraging, offer support, and suggest a 5-minute break if they seem stuck."
        )
    elif user_emotion == "surprised":
        dynamic_prompt += "\n\nThe user looks surprised. Ask if the concept makes sense."

    messages = [{"role": "system", "content": dynamic_prompt}] + history + [
        {"role": "user", "content": user_text}
    ]

    try:
        return _chat(messages)
    except Exception as exc:
        return (
            "Buddy is ready, but I could not reach the Groq tutor service right now. "
            f"Backend detail: {exc}"
        )


def ask_llm_with_page_context(user_text, history, page_context=None, user_emotion="neutral"):
    page_context = page_context or {}
    mode = page_context.get("mode", "ai_tutor")
    dynamic_prompt = SAT_SYSTEM

    if user_emotion in ["sad", "fearful", "angry", "disgusted"]:
        dynamic_prompt += (
            "\n\nThe student may be frustrated. Be warm, concrete, and consider suggesting "
            "a short reset before more problem solving."
        )

    if mode == "question":
        question = page_context.get("question") or {}
        answers = question.get("answers") or []
        correct_index = question.get("correct_index")
        correct_answer = ""
        if isinstance(correct_index, int) and 0 <= correct_index < len(answers):
            correct_answer = answers[correct_index]

        dynamic_prompt += (
            "\n\nThe student is on the Search by ID question-bank page. Answer using the "
            "current SAT question context below. Keep the reply friendly, TTS-friendly, "
            "and focused on helping the student understand this exact question.\n"
            f"Question ID: {question.get('id', 'unknown')}\n"
            f"Domain: {question.get('domain', 'SAT')}\n"
            f"Skill: {question.get('skill', 'Practice')}\n"
            f"Passage: {question.get('passage', '')}\n"
            f"Answer choices: {json.dumps(answers)}\n"
            f"Correct answer: {correct_answer}\n"
            f"Official explanation: {question.get('explanation', '')}"
        )
    elif mode == "planner":
        dynamic_prompt += (
            "\n\nThe student is on the Study Planner page. Help them structure today's "
            "study time into realistic focus blocks with breaks, and keep the advice "
            "supportive rather than intense."
        )
    else:
        dynamic_prompt += (
            "\n\nThe student is in the AI Tutor chat. Use the visible chat history as the "
            "main context and answer like a normal SAT tutoring conversation."
        )

    messages = [{"role": "system", "content": dynamic_prompt}] + history + [
        {"role": "user", "content": user_text}
    ]

    try:
        return _chat(messages)
    except Exception as exc:
        return (
            "Buddy is ready, but I could not reach the Groq tutor service right now. "
            f"Backend detail: {exc}"
        )


def ask_llm_with_image(user_text, base64_image, history, user_emotion="neutral"):
    dynamic_prompt = SAT_SYSTEM
    if user_emotion in ["sad", "fearful", "angry", "disgusted"]:
        dynamic_prompt += "\n\nIMPORTANT: The user looks frustrated or upset. Be encouraging."

    if not user_text:
        user_text = "Please read the question in this image and solve it step by step."

    messages = [{"role": "system", "content": dynamic_prompt}] + history
    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }
    )

    try:
        return _chat(
            messages,
            max_tokens=512,
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
    except Exception as exc:
        return (
            "I could not process that image with the Groq vision service right now. "
            f"Backend detail: {exc}"
        )


def summarize_explanation(explanation):
    messages = [
        {
            "role": "system",
            "content": (
                "You are Buddy, a friendly SAT tutor. Summarize official SAT answer "
                "explanations in 2-3 short sentences that are easy to understand and "
                "good for text-to-speech. Do not add new facts."
            ),
        },
        {"role": "user", "content": explanation},
    ]

    try:
        return _chat(messages, max_tokens=120, temperature=0.4)
    except Exception:
        sentences = re.split(r"(?<=[.!?])\s+", explanation.strip())
        return " ".join(sentences[:3]) or "The explanation points to the answer supported by the passage."


def generate_study_plan_json(prompt):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a wellbeing-focused SAT study planner. Break the requested "
                "study time into Pomodoro blocks using 25-minute study intervals and "
                "5-minute breaks, shortening the final block if needed. Return ONLY a "
                'strict JSON array of objects with keys "time", "task", and "type". '
                'The "type" value must be either "study" or "break". Use relative '
                'ranges like "00:00-00:25". No markdown, no prose.'
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        return _extract_json_array(_chat(messages, max_tokens=500, temperature=0.2))
    except Exception:
        return _fallback_plan(prompt)


def proactive_checkin(emotion):
    prompt = (
        f"The user has been looking {emotion} for a while while studying. Say one short, "
        "encouraging sentence to check in on them. Keep it under 20 words. Do not ask a "
        "math question, just offer support."
    )
    messages = [
        {"role": "system", "content": "You are a supportive SAT tutor."},
        {"role": "user", "content": prompt},
    ]

    try:
        return _chat(messages, max_tokens=50, temperature=0.7)
    except Exception:
        return "You are doing meaningful work. Take one calm breath, then keep going at your pace."
