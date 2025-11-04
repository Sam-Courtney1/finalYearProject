from flask import Flask, render_template, request, redirect, session , url_for , flash
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

application = Flask(__name__)

application.secret_key = 'test'

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

@application.route('/')
def index():
    return render_template('login.html')

@application.route('/register')
def register():
    return render_template('register.html')

@application.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')

@application.route('/homepage')
def homepage():
    if 'username' in session:
        return render_template('homepage.html', username=session['username'])
    else:
        return redirect(url_for('index'))

@application.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@application.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    if conn is None:
        return "Database connection failed."

    try:
        cur = conn.cursor()
        """Error: not all arguments converted during string formatting
        comma is needed below, if removed it is treated as a string """
        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,)) 
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and user[1] == password:
            session['user_id'] = user[0]
            session['username'] = username
            print(f"Logged in user: {username} (ID: {user[0]})")
            return redirect(url_for('homepage'))
        else:
            return redirect(url_for('index'))
    except Exception as e:
        print("Login error:", e)
        return f"Error: {e}"

@application.route('/register_user', methods=['POST'])
def submit():
    username = request.form['username']
    password = request.form['password']
    print(f"Received: {username}, {password}")

    conn = get_db_connection()
    if conn is None:
        return "Database connection failed."

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))

        existing_user = cur.fetchone()
        if existing_user:
            flash("Username already exists. Please choose another.")
            cur.close()
            conn.close()
            return redirect(url_for('register'))

        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        session['username'] = username

        """
        Below is needed to assign user_id for the seesion, the only other place you have it is in
        Login functoin above, was getting errors in the db with no user id in the questionnare table
        Look into return function when you insert the record, probably a way to get it without a second query
        """

        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        session['user_id'] = user[0]


        cur.close()
        conn.close()
        print("Data inserted successfully")
        return redirect(url_for('homepage'))
    except Exception as e:
        print("Insert error:", e)
        return f"Error: {e}"
    

@application.route('/questionnaire', methods=['POST'])
def submitQuestionnaire():
    user_id = session.get('user_id')
    blood_type = request.form['blood_type']
    organ = request.form['organ']
    address = request.form['address']
    consent = 'consent' in request.form
    
    conn = get_db_connection()
    if conn is None:
        return "Database connection failed."
    
    try:
        cur = conn.cursor()
        cur.execute("""
                        INSERT INTO questionnaire (user_id, blood_type, organ, address, consent)
                        VALUES (%s, %s, %s, %s, %s)
                     """
                        ,(user_id, blood_type, organ, address, consent))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('homepage'))
    except Exception as e:
        print("Error submitting questionnare form", e)
        return f"Error {e}"
    

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=80)
