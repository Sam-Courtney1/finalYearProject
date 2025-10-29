from flask import Flask, render_template, request
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

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
        print("Database connection error", e)
        return None

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form['username']
    password = request.form['password']
    print(f"Received: {username}, {password}")

    conn = get_db_connection()
    if conn is None:
        return "Database connection failed."

    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        cur.close()
        conn.close()
        print("Data inserted successfully")
        return "Data saved successfully to RDS"
    except Exception as e:
        print("Insert error:", e)
        return f"Error: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
