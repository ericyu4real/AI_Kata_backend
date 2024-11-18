import openai
import pandas as pd
import os

# Initialize OpenAI client
openaikey = os.environ['OPENAI_API_KEY']  # change this to openaikey="your key" if you are testing it locally on your device
client = openai.OpenAI(api_key=openaikey)

# Load data into DataFrames
orders_df = pd.read_excel("database/order_data.xlsx")
products_df = pd.read_excel("database/product_data.xlsx")

# Intent Detection Agent
def detect_intent(chat_history):
    system_message = """
    You are a helpful AI assistant working for ShopWise Solutions, an innovative and fast-growing e-commerce company based in Austin, Texas, USA. You are tasked with detecting the user's intent. The chat history includes both user and assistant messages.
    Prerequisites for defining a clear intent:
    1. The user's query must match one of the following intents:
    - order_retrieval: The user wants specific information about an order (must include an Order ID).
    - product_retrieval: The user wants specific information about a product (must include a Product ID).
    - personal_order_status: The user wants to know about their orders (must include a Customer ID).
    - compare_products: The user wants to compare two products (must include names of both products).
    2. If the intent is unclear or required information is missing, ask a follow-up question to clarify the user's query.
    3. Always respond with one of the following:
      - A follow-up question (if clarification is needed).
      - The detected intent name in one word (order_retrieval, product_retrieval, personal_order_status, compare_products).
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": system_message}] + chat_history,
        max_tokens=50,
        temperature=0.0
    )
    return response.choices[0].message.content.strip().lower()

# Entity Retrieval Agent
def retrieve_entities_with_llm(intent, chat_history):
    system_message = f"""
    You are an assistant that extracts key information (entities) from user queries based on detected intent.

    User's Intent: {intent}

    If the intent is "order_retrieval", extract the order ID from the user's query. The order ID should be an integer.
    If the intent is "product_retrieval", extract the product ID from the user's query. The product ID should be an integer.
    If the intent is "personal_order_status", extract the customer ID from the user's query. The customer ID should be an integer.
    If the intent is "compare_products", extract the names of the products to be compared from the user's query.

    Always return the entities in the following JSON format:
    - For "order_retrieval": {{ "order_id": <integer or null if not found> }}
    - For "product_retrieval": {{ "product_id": <integer or null if not found> }}
    - For "personal_order_status": {{ "customer_id": <integer or null if not found> }}
    - For "compare_products": {{ "product_names": [<list of product names, or empty if not found>] }}

    Chat History so far:
    {chat_history}
    """
    messages = [
        {"role": "system", "content": system_message}
    ]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=500,
        temperature=0.0
    )

    entities = response.choices[0].message.content.strip()
    return entities

# df retrieval agent
def run_intent_query(intent, entities):
    if intent == "order_retrieval":
        order_id = entities.get("order_id")
        if order_id:
            result = orders_df[orders_df['OrderID'] == int(order_id)]
            return result.to_dict(orient='records')

    elif intent == "product_retrieval":
        product_id = entities.get("product_id")
        if product_id:
            result = products_df[products_df['Product ID'] == int(product_id)]
            return result.to_dict(orient='records')

    elif intent == "personal_order_status":
        customer_id = entities.get("customer_id")
        if customer_id:
            result = orders_df[orders_df['CustomerID'] == int(customer_id)]
            return result.to_dict(orient='records')

    elif intent == "compare_products":
        product_names = entities.get("product_names", [])
        if len(product_names) == 2:
            result = products_df[products_df['ProductName'].str.lower().isin([name.lower() for name in product_names])]
            return result.to_dict(orient='records')

    return None

# RAG Agent
def generate_rag_response(retrieved_context, chat_history):
    system_message = f"""
    You are a helpful AI assistant working for ShopWise Solutions, tasked with providing helpful and accurate responses to user queries.

    The following context has been retrieved to help you answer the user's question:
    {retrieved_context}

    Chat History:
    {chat_history}

    Instructions:
    - Analyze the chat history to understand what the user is asking for.
    - Use the provided retrieved context to answer the user's question accurately.
    - Only provide a response if the retrieved context includes enough information to answer the user's question.
    - If the context is insufficient, respond with "I don't have the knowledge about the request you made given the information you provided".

    Your helpful answer:
    """

    messages = [
        {"role": "system", "content": system_message}
    ]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=500,
        temperature=0.0
    )

    assistant_response = response.choices[0].message.content.strip()
    return assistant_response