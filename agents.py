import openai
import pandas as pd
from sqlalchemy import create_engine
import os

# Initialize OpenAI client
openaikey = os.environ['OPENAI_API_KEY']  # change this to openaikey="your key" if you are testing it locally on your device
client = openai.OpenAI(api_key=openaikey)

# Path to the SQLite database
db_path = "my_database.db"

# Database schema
schema_info = """
    Table: orders
    Columns:
        - ProductID (INTEGER)
        - ProductName (TEXT)
        - Category (TEXT)
        - CategoryID (INTEGER)
        - OrderID (INTEGER)
        - CustomerID (INTEGER)
        - OrderStatus (TEXT)
        - ReturnEligible (BOOLEAN)
        - ShippingDate (TEXT)

    Table: products
    Columns:
        - ProductID (INTEGER)
        - ProductName (TEXT)
        - MerchantID (INTEGER)
        - ClusterID (INTEGER)
        - ClusterLabel (TEXT)
        - CategoryID (INTEGER)
        - Category (TEXT)
        - Price (REAL)
        - StockQuantity (INTEGER)
        - Description (TEXT)
        - Rating (REAL)
"""

# Sample rows from the database for schema understanding
orders_df = pd.read_excel("database/order_data.xlsx")  # Replace with your actual file path
products_df = pd.read_excel("database/product_data.xlsx")  # Replace with your actual file path
sample_orders = orders_df.groupby('OrderStatus', as_index=False).first()
sample_products = products_df.groupby('Category', as_index=False).first()

# Decide SQL Capability Agent
def decide_sql_capability(chat_history, user_query):
    """
    Determines whether the SQL agent can handle the user's query or if clarification is needed.
    Also checks if the query can be answered directly using the current context.

    Args:
        chat_history (list): Chat history as a list of dictionaries in OpenAI's format.
        user_query (str): The user's current query.

    Returns:
        dict: A JSON object indicating the next step:
            - 'action': ('use_sql_agent', 'ask_clarification', or 'respond_directly')
            - 'reason': Explanation for the decision.
            - 'clarification': Suggested clarification question (if needed).
            - 'response': If 'respond_directly', the response to the user's query.
    """
    system_message = f"""
    You are a smart assistant determining the next action for a user's query. Based on the schema, example rows, and chat history provided, decide the following:
    
    Instructions:
    1. Does this request need to use SQL agent and can the SQL agent handle this query? If both yes, output 'use_sql_agent'.
    2. If the query requires more information to be handled by the SQL agent, output 'ask_clarification' and suggest a clarification question.
    3. If the query can be answered directly using the current context, output 'respond_directly' and provide the response.
    4. Must always return a JSON object with the following keys:
        - 'action': ('use_sql_agent', 'ask_clarification', or 'respond_directly')
        - 'reason': A brief explanation of why this action was chosen.
        - 'clarification': If 'ask_clarification', suggest a follow-up question to ask the user.
        - 'response': If 'respond_directly', include the response to the user's query.

    Schema and Example Rows:
    {schema_info}

    Example rows from the `orders` table:
    {sample_orders.to_string(index=False)}

    Example rows from the `products` table:
    {sample_products.to_string(index=False)}

    Chat History:
    {chat_history}

    User Query:
    {user_query}
    """
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": system_message}],
        max_tokens=300,
        temperature=0.0,
    )
    return eval(response.choices[0].message.content.strip())

# SQL Query Agent
def sql_query_agent(chat_history, user_query):
    """
    Generates and executes an SQL query based on user input, database schema, and sample data.

    Args:
        chat_history (list): Chat history as a list of dictionaries in OpenAI's format.

    Returns:
        pd.DataFrame or str: Query result as a Pandas DataFrame or an error message if query fails.
    """
    # Generate the system message
    system_message = f"""
    You are an SQL generation assistant. Based on the following schema and example data, generate a valid SQL query to retrieve the requested information.

    Schema:
    {schema_info}

    Example rows from the `orders` table:
    {sample_orders.to_string(index=False)}

    Example rows from the `products` table:
    {sample_products.to_string(index=False)}

    User Query:
    {user_query}

    Instructions:
    - Analyze the chat history and user query to understand the user's request.
    - Generate a valid SQL query matching the request and schema.
    - Use case-insensitive matching for text-based filters (e.g., categories or product names) by applying LOWER().
    - Return only the SQL query as output.

    Chat history:
    {chat_history}
    """
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": system_message}],
        max_tokens=500,
        temperature=0.0,
    )

    # Extract the SQL query from the response
    sql_query = response.choices[0].message.content.strip()

    # Execute the SQL query on the SQLite database
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            result_df = pd.read_sql_query(sql_query, connection)
            return result_df
    except Exception as e:
        return f"Error executing query: {str(e)}"

def rag_agent(user_query, chat_history, retrieved_df):
    """
    Generates a natural language response based on the user query, chat history, and retrieved data.

    Args:
        user_query (str): The user's current query.
        chat_history (list): Chat history as a list of dictionaries.
        retrieved_df (pd.DataFrame): Data retrieved from the SQL Query Agent.

    Returns:
        str: A natural language response to the user's query.
    """
    # Limit the number of rows sent to the agent to avoid token overflow
    if len(retrieved_df) > 10:
        retrieved_context = retrieved_df[:10].to_dict(orient='records')  # Send only the first 10 rows
        extra_message = "Note: Only the first 10 rows of retrieved data are shown due to space limitations."
    else:
        retrieved_context = retrieved_df.to_dict(orient='records')
        extra_message = ""

    # Generate the system message
    system_message = f"""
    You are an AI assistant tasked with generating a natural language response based on the user's query, chat history, and retrieved data.

    Instructions:
    - Analyze the chat history to understand what the user is asking for.
    - Use the provided retrieved context to answer the user's question accurately.
    - Only provide a response if the retrieved context includes enough information to answer the user's question.
    - If the context is insufficient, just say you don't know.
    - Format your answer using Markdown

    User Query:
    {user_query}

    Chat History:
    {chat_history}

    Retrieved context:
    {retrieved_context}
    {extra_message}

    Your helpful answer:
    """
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": system_message}],
        max_tokens=500,
        temperature=0.0,
    )

    # Extract and return the natural language response
    return response.choices[0].message.content.strip()
