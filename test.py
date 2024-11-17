from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import json
import pandas as pd
import os
from agents import detect_intent, retrieve_entities_with_llm, run_intent_query, generate_rag_response

# Initialize Flask app
app = Flask(__name__)
CORS(app) 

# Load user info from a JSON file
user_info_path = 'user_info.json'
intent_options = [
    "order_retrieval",
    "product_retrieval",
    "personal_order_status",
    "compare_products"
]

def load_user_info():
    try:
        with open(user_info_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_user_info(data):
    with open(user_info_path, 'w') as file:
        json.dump(data, file)

# Endpoint to handle chat interactions
@app.route('/chat', methods=['POST'])
def chat():
    username = request.form.get('username')
    user_message = request.form.get('message')

    # Load user chat history from user_info.json
    user_data = load_user_info()

    # Initialize chat history if user is new
    if username not in user_data or not user_data[username]:
        user_data[username] = [{"role": "assistant", "content": "Chatbot: Hello! How can I assist you today?"}]
    user_data[username].append({"role": "user", "content": user_message})
    save_user_info(user_data)

    chat_history = user_data[username]

    # Step 1: Intent Detection
    intent = detect_intent(chat_history)

    # If intent is unknown, loop back to ask for clarification
    if intent not in intent_options:
        response = intent
        chat_history.append({"role": "assistant", "content": response})
        user_data[username] = chat_history
        save_user_info(user_data)
        return jsonify({"response": response})

    # Step 2: Entity Retrieval
    entities = retrieve_entities_with_llm(intent, chat_history)
    try:
        entities = json.loads(entities)
    except json.JSONDecodeError:
        response = "Json transform went wrong!"
        chat_history.append({"role": "assistant", "content": response})
        user_data[username] = chat_history
        save_user_info(user_data)
        return jsonify({"response": response})

    # Step 3: Run Query Based on Intent
    retrieved_context = run_intent_query(intent, entities)
    if not retrieved_context:
        response = "I don't have the knowledge about the request you made given the information you provided."
        chat_history.append({"role": "assistant", "content": response})
        user_data[username] = chat_history
        save_user_info(user_data)
        return jsonify({"response": response})

    # Step 4: Response Generation
    final_response = generate_rag_response(retrieved_context, chat_history)
    chat_history.append({"role": "assistant", "content": final_response})
    user_data[username] = chat_history
    save_user_info(user_data)

    return jsonify({"response": final_response})

# Endpoint to handle ending the session
@app.route('/end_session', methods=['POST'])
def end_session():
    username = request.form.get('username')

    user_data = load_user_info()
    if username in user_data:
        user_data[username] = []

    save_user_info(user_data)
    return jsonify({"message": "Session ended and chat history cleared."})

# Endpoint to handle getting chat history
@app.route('/get_chat_history', methods=['POST'])
def get_chat_history():
    username = request.form.get('username')

    user_data = load_user_info()
    chat_history = user_data.get(username, [])

    return jsonify({"chat_history": chat_history})

@app.route('/')
def index():
  return "This is Velociraptor chatbot's backend. Please do not share this with anyone."

# Run the Flask server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# Include your existing functions here for detect_intent, retrieve_entities_with_llm, run_intent_query, and generate_rag_response
