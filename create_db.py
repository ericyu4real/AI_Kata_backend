import pandas as pd
from sqlalchemy import create_engine

# File paths for your Excel files
orders_file = "database/order_data.xlsx"
products_file = "database/product_data.xlsx"

# Load the Excel files into DataFrames
orders_df = pd.read_excel(orders_file)
products_df = pd.read_excel(products_file)

# Create a SQLite database (or connect to an existing one)
engine = create_engine("sqlite:///my_database.db")

# Write DataFrames to the database
orders_df.to_sql("orders", engine, if_exists="replace", index=False)
products_df.to_sql("products", engine, if_exists="replace", index=False)


# Define your SQL query
query = """
SELECT 
    products.ProductName,
    products.Price,
    products.Description,
    products.Rating
FROM
    products
WHERE
    products.ProductName = 'bosch serie 4 kil22vf30g integrated fridge';
"""

# Execute the query and fetch the results into a DataFrame
with engine.connect() as connection:
    try:
        result_df = pd.read_sql_query(query, connection)
        print(result_df)
    except Exception as e:
        print("Error executing query:", str(e))
