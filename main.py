from flask import Flask, request
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os
from flask_cors import CORS
from flask import jsonify
import json
from datetime import datetime
import pytz

app = Flask(__name__)
CORS(app)

# read env variables
openaikey = os.environ['OPENAI_API_KEY']

#mangodb setup
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://ericyu:48nqSONXdVfvrQCf@chat.dtdfazx.mongodb.net/?retryWrites=true&w=majority&appName=Chat"
client = MongoClient(uri, server_api=ServerApi('1'))


#vectordb setup
embeddings = OpenAIEmbeddings()
db = FAISS.load_local("faiss_index",
                      embeddings,
                      allow_dangerous_deserialization=True)

# Build prompt
template = """You are an AI assistant working for MScAC (The Master of Science in Applied Computing) at the University of Toronto, the best CS master program in Canada. This program offers a unique combination of academic research and industry engagement. The program aims to cultivate world-class innovators through rigorous education in state-of-the-art research techniques, culminating in an applied research internship. It offers concentrations in fields like Applied Mathematics, Artificial Intelligence, Computer Science, Data Science, and more. And your name is Claire. Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.
{context}
Question: {question}
Helpful Answer:"""
QA_CHAIN_PROMPT = PromptTemplate.from_template(template)
retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 1})
qa = ConversationalRetrievalChain.from_llm(
    llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0),
    chain_type="stuff",
    combine_docs_chain_kwargs={"prompt": QA_CHAIN_PROMPT},
    retriever=retriever,
    return_source_documents=True,
    return_generated_question=True,
)


@app.route('/')
def index():
  return "This is MScAC chatbot's backend. Please do not share this with anyone. Thank you."


@app.route('/query', methods=['POST'])
def query():
  query = request.form.get('query', 'default_value')
  if query == 'default_value':
    return "Please enter a query."
  result = qa({"question": query, "chat_history": []})
  save_message("User: " + query + ";\nBot: " + result['answer'])
  return jsonify({'response': result['answer']})


def save_message(text_message):
    toronto_time = datetime.now(pytz.timezone("America/Toronto")).strftime("%m/%d/%Y, %H:%M:%S")
    # user_ip = request.remote_addr  # Get user's IP address

    message_document = {
        # 'user_ip': user_ip,
        'datetime': toronto_time, 
        'message': text_message
    }

    # Accessing the 'chat' database and then the 'messages' collection
    messages_collection = client['chat']['messages']
    
    # Insert the message document into the collection
    messages_collection.insert_one(message_document)
    print("Message saved to MongoDB")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

