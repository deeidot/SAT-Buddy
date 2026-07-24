import base64
import io
import json
import sqlite3

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pydub import AudioSegment

load_dotenv()

from database import DB_NAME, init_db
from llm import (
    ask_llm,
    ask_llm_with_page_context,
    ask_llm_with_image,
    generate_study_plan_json,
    proactive_checkin,
    summarize_explanation,
)
from stt import transcribe

app = Flask(__name__)
init_db()

current_emotion = "neutral"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_conversation_id(raw_id):
    if raw_id in (None, "", "null", "undefined"):
        return None
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        return None


def get_history(conv_id):
    if not conv_id:
        return []

    conn = get_db()
    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
        """,
        (conv_id,),
    ).fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def parse_json_field(raw_value, fallback):
    if not raw_value:
        return fallback
    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def save_exchange(user_text, reply, conv_id=None, title=None):
    conn = get_db()
    cursor = conn.cursor()

    if not conv_id:
        conversation_title = title or (user_text[:30] + "..." if len(user_text) > 30 else user_text)
        cursor.execute("INSERT INTO conversations (title) VALUES (?)", (conversation_title,))
        conv_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conv_id, "user", user_text),
    )
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conv_id, "assistant", reply),
    )
    conn.commit()
    conn.close()
    return conv_id


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/question/<question_id>")
def get_question(question_id):
    conn = get_db()
    row = conn.execute(
        """
        SELECT id, domain, skill, passage, answers_json, correct_index, explanation
        FROM questions
        WHERE id = ?
        """,
        (question_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Question not found."}), 404

    return jsonify(
        {
            "id": row["id"],
            "domain": row["domain"],
            "skill": row["skill"],
            "passage": row["passage"],
            "answers": json.loads(row["answers_json"]),
            "correct_index": row["correct_index"],
            "explanation": row["explanation"],
        }
    )


@app.route("/api/buddy_explain", methods=["POST"])
def buddy_explain():
    data = request.get_json(silent=True) or {}
    explanation = data.get("explanation", "").strip()

    if not explanation:
        return jsonify({"error": "No explanation provided."}), 400

    return jsonify({"summary": summarize_explanation(explanation)})


@app.route("/api/generate_plan", methods=["POST"])
def generate_plan():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "No prompt provided."}), 400

    return jsonify({"plan": generate_study_plan_json(prompt)})


@app.route("/api/chat", methods=["POST"])
def chat():
    audio_file = request.files.get("audio")
    conv_id = normalize_conversation_id(request.form.get("conversation_id"))
    context_mode = request.form.get("context_mode", "ai_tutor")
    page_context = parse_json_field(request.form.get("page_context"), {})
    page_context["mode"] = context_mode

    if not audio_file:
        return jsonify({"error": "No audio provided."}), 400

    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({"error": "Audio was empty. Please try speaking again."}), 400

    try:
        source = io.BytesIO(audio_bytes)
        source.name = audio_file.filename or "audio.webm"
        try:
            audio = AudioSegment.from_file(source, format="webm")
        except Exception:
            source.seek(0)
            audio = AudioSegment.from_file(source)

        audio = audio.set_frame_rate(16000).set_channels(1)
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"
    except Exception as exc:
        return jsonify({"error": f"Could not process audio: {exc}"}), 400

    try:
        user_text = transcribe(wav_buffer)
    except Exception as exc:
        return jsonify({"error": f"Could not transcribe audio: {exc}"}), 500

    if not user_text:
        return jsonify({"error": "Could not transcribe audio."}), 400

    if context_mode == "question":
        history = parse_json_field(request.form.get("buddy_history"), [])[-8:]
        reply = ask_llm_with_page_context(user_text, history, page_context, current_emotion)
    elif context_mode == "planner":
        history = parse_json_field(request.form.get("buddy_history"), [])[-8:]
        reply = ask_llm_with_page_context(user_text, history, page_context, current_emotion)
    else:
        history = get_history(conv_id)
        reply = ask_llm_with_page_context(user_text, history, page_context, current_emotion)
        conv_id = save_exchange(user_text, reply, conv_id)

    return jsonify(
        {
            "conversation_id": conv_id,
            "user_text": user_text,
            "tutor_reply": reply,
        }
    )


@app.route("/api/chat_text", methods=["POST"])
def chat_text():
    data = request.get_json(silent=True) or {}
    user_text = data.get("text", "").strip()
    conv_id = normalize_conversation_id(data.get("conversation_id"))

    if not user_text:
        return jsonify({"error": "No text provided."}), 400

    history = get_history(conv_id)
    reply = ask_llm(user_text, history, current_emotion)
    conv_id = save_exchange(user_text, reply, conv_id)

    return jsonify(
        {
            "conversation_id": conv_id,
            "user_text": user_text,
            "tutor_reply": reply,
        }
    )


@app.route("/api/chat_image", methods=["POST"])
def chat_image():
    image_file = request.files.get("image")
    user_text = request.form.get("text", "")
    conv_id = normalize_conversation_id(request.form.get("conversation_id"))

    if not image_file:
        return jsonify({"error": "No image provided."}), 400

    image_bytes = image_file.read()
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    history = get_history(conv_id)
    reply = ask_llm_with_image(user_text, base64_image, history, current_emotion)
    conv_id = save_exchange(f"[Image Uploaded] {user_text}".strip(), reply, conv_id, "Image Question...")

    return jsonify(
        {
            "conversation_id": conv_id,
            "user_text": f"[Image Uploaded] {user_text}".strip(),
            "tutor_reply": reply,
        }
    )


@app.route("/api/conversations")
def get_conversations():
    conn = get_db()
    rows = conn.execute("SELECT * FROM conversations ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/conversations/<int:conv_id>/messages")
def get_messages(conv_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT *
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
        """,
        (conv_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/conversations/<int:conv_id>/delete", methods=["DELETE"])
def delete_conversation(conv_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/emotion", methods=["POST"])
def update_emotion():
    global current_emotion
    data = request.get_json(silent=True) or {}
    current_emotion = data.get("emotion", "neutral")
    return jsonify({"success": True})


@app.route("/api/proactive_checkin")
def run_proactive_checkin():
    return jsonify({"message": proactive_checkin(current_emotion)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
