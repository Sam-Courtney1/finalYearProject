import psycopg2
import os

"""
This file connects to the database using pyscog2
The variables are stored in a .env file rather then being hardcoded
This ensures they are not pushed to GitHub and leaked
They are also stored in AWS under secrets manager
In this configuration the database can be connected to securly
without leaking any sensitive information
"""

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        print("Connected to RDS successfully")
        return conn
    except Exception as e:
        print("Database connection error:", e)
        return None




