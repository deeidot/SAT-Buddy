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
from llm import ask_llm, ask_llm_with_image
from database import DB_NAME

app = Flask(__name__)

# NEW: Store the user's current emotion globally
current_emotion = "neutral"

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
    reply = ask_llm(user_text, history, current_emotion)

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

# Route 5: Receive image, process it, return answer
@app.route('/api/chat_image', methods=['POST'])
def chat_image():
    # 1. Get the image file and text from the website
    image_file = request.files.get('image')
    user_text = request.form.get('text', '')
    conv_id = request.form.get('conversation_id')

    if not image_file:
        return jsonify({"error": "No image provided"}), 400

    # 2. Convert the image to a Base64 string
    import base64
    image_bytes = image_file.read()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    # 3. Load conversation history from database
    history = []
    if conv_id and conv_id != 'null':
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        msgs = conn.execute('SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC', (conv_id,)).fetchall()
        history = [{"role": m['role'], "content": m['content']} for m in msgs]
        conn.close()

    # 4. Ask the Vision Tutor (Passing the base64_image and current_emotion)
    reply = ask_llm_with_image(user_text, base64_image, history, current_emotion)

    # 5. Save to database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if not conv_id or conv_id == 'null':
        cursor.execute('INSERT INTO conversations (title) VALUES (?)', ("Image Question...",))
        conv_id = cursor.lastrowid
    else:
        conv_id = int(conv_id)

    # Save user message (we note that it was an image)
    cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)', 
                   (conv_id, "user", f"[Image Uploaded] {user_text}"))
    cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)', 
                   (conv_id, "assistant", reply))
    conn.commit()
    conn.close()

    # 6. Send the answer back to the website
    return jsonify({
        "conversation_id": conv_id,
        "user_text": f"[Image Uploaded] {user_text}",
        "tutor_reply": reply
    })
# Route 6: Receive plain text, process it, return answer
@app.route('/api/chat_text', methods=['POST'])
def chat_text():
    # 1. Get the text from the website
    data = request.get_json()
    user_text = data.get('text', '').strip()
    conv_id = data.get('conversation_id')

    if not user_text:
        return jsonify({"error": "No text provided"}), 400

    # 2. Load conversation history
    history = []
    if conv_id and conv_id != 'null':
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        msgs = conn.execute('SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC', (conv_id,)).fetchall()
        history = [{"role": m['role'], "content": m['content']} for m in msgs]
        conn.close()

    # 3. Ask the Tutor
    reply = ask_llm(user_text, history, current_emotion)

    # 4. Save to database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if not conv_id or conv_id == 'null':
        cursor.execute('INSERT INTO conversations (title) VALUES (?)', (user_text[:30] + "...",))
        conv_id = cursor.lastrowid
    else:
        conv_id = int(conv_id)

    cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)', 
                   (conv_id, "user", user_text))
    cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)', 
                   (conv_id, "assistant", reply))
    conn.commit()
    conn.close()

    # 5. Send the answer back
    return jsonify({
        "conversation_id": conv_id,
        "user_text": user_text,
        "tutor_reply": reply
    })

# Route 6.5: Receive emotion from the webcam
@app.route('/api/emotion', methods=['POST'])
def update_emotion():
    global current_emotion
    data = request.get_json()
    current_emotion = data.get('emotion', 'neutral')
    # print(f"User emotion updated to: {current_emotion}") # Uncomment to see it in terminal
    return jsonify({"success": True})

# Route 7: Delete a specific conversation
@app.route('/api/conversations/<int:conv_id>/delete', methods=['DELETE'])
def delete_conversation(conv_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Delete the messages belonging to this conversation
    cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conv_id,))
    # Delete the conversation itself
    cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

# Route 8: Proactive emotional check-in
@app.route('/api/proactive_checkin')
def proactive_checkin():
    emotion = current_emotion
    print(f"Triggering proactive check-in. User seems: {emotion}")
    reply = proactive_checkin(emotion)
    return jsonify({"message": reply})

if __name__ == '__main__':
    # Run the server on port 5000
    app.run(debug=True, port=5000)