import os
import io
from flask import Flask, request, jsonify, render_template
from pydub import AudioSegment
from dotenv import load_dotenv
import sqlite3
from datetime import datetime

# Load our employees (reusing your exact code!)
load_dotenv()
from stt import transcribe
from llm import ask_llm
from database import DB_NAME

app = Flask(__name__)

# Route 1: Serve the website
@app.route('/')
def index():
    return render_template('index.html')

# Route 2: Get conversation history for the sidebar
@app.route('/api/conversations')
def get_conversations():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conversations = conn.execute('SELECT * FROM conversations ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(conv) for conv in conversations])

# Route 3: Get messages for a specific conversation
@app.route('/api/conversations/<int:conv_id>/messages')
def get_messages(conv_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    messages = conn.execute('SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC', (conv_id,)).fetchall()
    conn.close()
    return jsonify([dict(msg) for msg in messages])

# Route 4: Receive audio, process it, return answer
@app.route('/api/chat', methods=['POST'])
def chat():
    # 1. Get the audio file from the website
    audio_file = request.files.get('audio')
    conv_id = request.form.get('conversation_id')

    # 2. Convert webm (browser format) to wav (Groq format)
    audio = AudioSegment.from_file(audio_file, format="webm")
    audio = audio.set_frame_rate(16000).set_channels(1)
    
    # Export to a virtual WAV file in memory
    wav_buffer = io.BytesIO()
    audio.export(wav_buffer, format="wav")
    wav_buffer.seek(0)
    wav_buffer.name = "audio.wav"

    # 3. Transcribe (using your stt.py)
    user_text = transcribe(wav_buffer)
    if not user_text:
        return jsonify({"error": "Could not transcribe audio"}), 400

    # 4. Load conversation history from database for the LLM
    history = []
    if conv_id and conv_id != 'null':
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        msgs = conn.execute('SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC', (conv_id,)).fetchall()
        history = [{"role": m['role'], "content": m['content']} for m in msgs]
        conn.close()

    # 5. Ask the Tutor (using your llm.py)
    reply = ask_llm(user_text, history)

    # 6. Save everything to the database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # If it's a new conversation, create one using the user's first words as the title
    if not conv_id or conv_id == 'null':
        cursor.execute('INSERT INTO conversations (title) VALUES (?)', (user_text[:30] + "...",))
        conv_id = cursor.lastrowid
    else:
        conv_id = int(conv_id)

    # Save the user message and tutor message
    cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)', 
                   (conv_id, "user", user_text))
    cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)', 
                   (conv_id, "assistant", reply))
    conn.commit()
    conn.close()

    # 7. Send the text back to the website
    return jsonify({
        "conversation_id": conv_id,
        "user_text": user_text,
        "tutor_reply": reply
    })

if __name__ == '__main__':
    # Run the server on port 5000
    app.run(debug=True, port=5000)