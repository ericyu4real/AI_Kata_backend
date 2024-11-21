from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import pandas as pd
import os
from agents import decide_sql_capability, sql_query_agent, rag_agent

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# User info path for storing chat history
user_info_path = 'user_info.json'

# Load and save user chat history
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

    # Load chat history
    user_data = load_user_info()

    # Initialize chat history for a new user
    if username not in user_data or not user_data[username]:
        user_data[username] = [{"role": "assistant", "content": "Chatbot: Hello! How can I assist you today?"}]
    chat_history = user_data[username]

    # Append the user's message to chat history
    chat_history.append({"role": "user", "content": user_message})
    save_user_info(user_data)

    # Step 1: Decide capability of SQL agent or alternative action
    decision = decide_sql_capability(chat_history, user_message)

    # Handle the decision
    if decision['action'] == 'use_sql_agent':
        # Call the SQL Query Agent
        sql_result = sql_query_agent(chat_history, user_message)
        if isinstance(sql_result, pd.DataFrame):
            # Call the Third Agent for response generation
            response = rag_agent(user_message, chat_history, sql_result)
        else:
            response = sql_result  # Handle error messages
    elif decision['action'] == 'ask_clarification':
        response = decision['clarification']
    elif decision['action'] == 'respond_directly':
        response = decision['response']
    else:
        response = "I'm not sure how to handle your request. Could you clarify?"

    # Append the assistant's response to chat history
    chat_history.append({"role": "assistant", "content": response})
    user_data[username] = chat_history
    save_user_info(user_data)

    return jsonify({"response": response})

# Endpoint to handle ending the session
@app.route('/end_session', methods=['POST'])
def end_session():
    username = request.form.get('username')

    user_data = load_user_info()
    if username in user_data:
        user_data[username] = []

    save_user_info(user_data)
    return jsonify({"message": f"Session ended and chat history for {username} is cleared."})

# Endpoint to handle getting chat history
@app.route('/get_chat_history', methods=['POST'])
def get_chat_history():
    username = request.form.get('username')

    user_data = load_user_info()
    chat_history = user_data.get(username, [])

    return jsonify({"chat_history": chat_history})

@app.route('/')
def index():
    return "This is the updated Velociraptor chatbot backend with enhanced agent workflows."

# Run the Flask server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
