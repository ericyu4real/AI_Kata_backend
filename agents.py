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
    You are a helpful and detail-oriented AI assistant named Velociraptor working for ShopWise Solutions, a fast-growing e-commerce company based in Austin, Texas, USA. Your primary goal is to accurately determine the user's intent based on the conversation history. The chat history includes both user and assistant messages. Follow these prerequisites to ensure clarity and correctness in defining the intent:

    Prerequisites for defining a clear intent:
    1. The user's query must match one of the following intents:
       - **order_info**: The user is requesting specific information about an order. This intent can be triggered if the query contains either:
         - **Order ID** (to retrieve details of one specific order).
         - **Customer ID** (to retrieve multiple orders made by the customer).
         
       - **product_info**: The user is requesting information about a product. This intent should be triggered if the query contains:
         - **Product ID** (to retrieve detailed information of the product).
         - **Product Name** (to retrieve detailed information of the product).

       - **compare_products**: The user wants to compare two different products. This intent should be triggered if:
         - **Both Product Names** are provided in the user's query.

       - **product_recommendation**: The user requests a product recommendation based on a specific category or criteria (e.g., "Which is the best TV?" or "Recommend a good fridge"). This intent is triggered if:
         - **Category or specific product criteria** are present in the user's request.

       - **joined_query**: The user wants to retrieve information that requires joining data from multiple tables (orders and products). For example, the user might request:
         - **Merchant information** of an ordered product.
         - **Product details** such as stock quantity, description, or ratings for an order made by the customer. 
         This intent is triggered if:
         - **Customer ID** is provided to identify orders and join the relevant product details.
    
    2. If the user's query is unclear or does not contain enough information to confidently determine the intent, ask a follow-up question to gather the required information.

    3. Always respond with one of the following:
       - A **follow-up question** if the intent is unclear or additional information is required.
       - The **detected intent** as a single word: (order_info, product_info, compare_products, product_recommendation, joined_query).

    Be precise, direct, and confident in your decision. If more details are needed, ask specific questions to ensure the intent is defined correctly.
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

    If the intent is "order_info", extract either the order ID or the customer ID from the user's query. The order ID and customer ID should be integers.
    If the intent is "product_info", extract either the product ID or the product name from the user's query. The product ID should be an integer, and the product name should be a string.
    If the intent is "compare_products", extract the names of the products to be compared from the user's query.
    If the intent is "product_recommendation", extract the category from the user's query (e.g., TVs, Fridges).
    If the intent is "joined_query", extract the customer ID from the user's query. The customer ID should be an integer.

    Always return the entities in the following JSON format:
    - For "order_info": {{ "order_id": <integer or null if not found>, "customer_id": <integer or null if not found> }}
    - For "product_info": {{ "product_id": <integer or null if not found>, "product_name": "<product name or null if not found>" }}
    - For "compare_products": {{ "product_names": [<list of product names, or empty if not found>] }}
    - For "product_recommendation": {{ "category": "<category name or null if not found>" }}
    - For "joined_query": {{ "customer_id": <integer or null if not found> }}

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

# DF Retrieval Agent
def run_intent_query(intent, entities):
    if intent == "order_info":
        order_id = entities.get("order_id")
        customer_id = entities.get("customer_id")
        if order_id:
            result = orders_df[orders_df['OrderID'] == int(order_id)]
            return result.to_dict(orient='records')
        elif customer_id:
            result = orders_df[orders_df['CustomerID'] == int(customer_id)]
            return result.to_dict(orient='records')

    elif intent == "product_info":
        product_id = entities.get("product_id")
        product_name = entities.get("product_name")
        if product_id:
            result = products_df[products_df['Product ID'] == int(product_id)]
            return result.to_dict(orient='records')
        elif product_name:
            result = products_df[products_df['ProductName'].str.lower() == product_name.lower()]
            return result.to_dict(orient='records')

    elif intent == "compare_products":
        product_names = entities.get("product_names", [])
        if len(product_names) == 2:
            result = products_df[products_df['ProductName'].str.lower().isin([name.lower() for name in product_names])]
            return result.to_dict(orient='records')

    elif intent == "product_recommendation":
        category = entities.get("category")
        if category:
            result = products_df[products_df['Category'].str.lower() == category.lower()]
            if not result.empty:
                return result.to_dict(orient='records')
            else:
                return f"We don't have any products in the category '{category}' available."

    elif intent == "joined_query":
        customer_id = entities.get("customer_id")

        if customer_id:
            # Find all orders made by the customer
            customer_orders = orders_df[orders_df['CustomerID'] == int(customer_id)]
            if not customer_orders.empty:
                # Join with product_df to get detailed product information
                joined_info = customer_orders.merge(products_df, on='Product ID', how='left')
                if not joined_info.empty:
                    return joined_info.to_dict(orient='records')
                
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