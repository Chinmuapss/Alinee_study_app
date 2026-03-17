import sqlite3
import hashlib
import random
from datetime import datetime, timezone, date

import streamlit as st

# ==============================
# CONFIG
# ==============================

st.set_page_config(page_title="CodeMaster Pro", layout="wide")

DB_NAME = "codemaster.db"
LANGUAGES = ["Python", "Java", "C++", "JavaScript", "Go", "Rust"]

# ==============================
# DATABASE SETUP
# ==============================

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        streak INTEGER DEFAULT 0,
        last_login TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        username TEXT,
        language TEXT,
        correct INTEGER DEFAULT 0,
        attempted INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ==============================
# HELPERS
# ==============================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def calculate_xp(correct, attempted):
    return correct * 10

def get_rank(xp):
    if xp < 100:
        return "🥉 Beginner"
    elif xp < 300:
        return "🥈 Intermediate"
    elif xp < 600:
        return "🥇 Advanced"
    else:
        return "💎 Code Master"

# ==============================
# USER FUNCTIONS
# ==============================

def create_user(username, password):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, 0, NULL)",
            (username, hash_password(password))
        )

        for lang in LANGUAGES:
            cursor.execute(
                "INSERT INTO progress VALUES (?, ?, 0, 0)",
                (username, lang)
            )

        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def authenticate(username, password):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return False

    return user["password_hash"] == hash_password(password)

def update_streak(username):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()

    today = date.today()

    if user and user["last_login"]:
        last = datetime.fromisoformat(user["last_login"]).date()

        if (today - last).days == 1:
            streak = user["streak"] + 1
        elif (today - last).days > 1:
            streak = 1
        else:
            streak = user["streak"]
    else:
        streak = 1

    cursor.execute("""
    UPDATE users
    SET streak=?, last_login=?
    WHERE username=?
    """, (streak, datetime.now(timezone.utc).isoformat(), username))

    conn.commit()
    conn.close()

# ==============================
# TECH QUESTIONS
# ==============================

def get_question(language):

    questions = {
        "Python": [
            ("What keyword defines a function?", "def"),
            ("What structure stores key-value pairs?", "dictionary"),
        ],
        "Java": [
            ("What keyword creates an object?", "new"),
            ("What starts a Java program?", "main"),
        ],
        "C++": [
            ("What operator allocates memory?", "new"),
            ("What symbol is used for scope resolution?", "::"),
        ],
        "JavaScript": [
            ("Which keyword declares block variable?", "let"),
            ("What handles async operations?", "promise"),
        ],
        "Go": [
            ("What starts a goroutine?", "go"),
            ("What is used for concurrency?", "channel"),
        ],
        "Rust": [
            ("What ensures memory safety?", "ownership"),
            ("Which macro prints text?", "println"),
        ],
    }

    return random.choice(questions[language])

# ==============================
# SESSION STATE
# ==============================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ==============================
# LOGIN PAGE
# ==============================

if not st.session_state.logged_in:

    st.title("📚 CodeMaster Pro")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                update_streak(username)
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        if st.button("Create Account"):
            if new_pass != confirm:
                st.error("Passwords do not match.")
            else:
                if create_user(new_user, new_pass):
                    st.success("Account created!")
                else:
                    st.error("Username already exists.")

    st.stop()

# ==============================
# LOAD USER SAFELY
# ==============================

conn = get_db()
cursor = conn.cursor()

cursor.execute("SELECT * FROM users WHERE username=?",
               (st.session_state.username,))
user = cursor.fetchone()

if user is None:
    st.error("User not found. Please login again.")
    st.session_state.logged_in = False
    st.stop()

# ==============================
# SIDEBAR INFO
# ==============================

cursor.execute("SELECT * FROM progress WHERE username=?",
               (st.session_state.username,))
progress = cursor.fetchall()

total_correct = sum(p["correct"] for p in progress)
total_attempted = sum(p["attempted"] for p in progress)

xp = calculate_xp(total_correct, total_attempted)

st.sidebar.title("📊 Stats")
st.sidebar.metric("XP", xp)
st.sidebar.write("Rank:", get_rank(xp))
st.sidebar.write("🔥 Streak:", user["streak"])

# ==============================
# QUIZ
# ==============================

st.header("🧠 Tech Quiz")

language = st.selectbox("Choose Language", LANGUAGES)

question, answer = get_question(language)

st.write("###", question)

user_answer = st.text_input("Your Answer")

if st.button("Submit Answer"):

    cursor.execute("""
    SELECT * FROM progress
    WHERE username=? AND language=?
    """, (st.session_state.username, language))

    row = cursor.fetchone()

    correct = row["correct"]
    attempted = row["attempted"] + 1

    if user_answer.lower().strip() == answer.lower():
        correct += 1
        st.success("Correct ✅")
    else:
        st.error(f"Wrong ❌ Answer: {answer}")

    cursor.execute("""
    UPDATE progress
    SET correct=?, attempted=?
    WHERE username=? AND language=?
    """, (correct, attempted,
          st.session_state.username, language))

    conn.commit()
    st.rerun()

# ==============================
# CHEAT SHEETS
# ==============================

st.header("📌 Cheat Sheets")

cheats = {
    "Python": "def, lists, dicts, classes, try/except",
    "Java": "OOP, JVM, new, extends, interfaces",
    "C++": "Pointers, STL, new/delete, ::",
    "JavaScript": "DOM, let, async/await, promises",
    "Go": "Goroutines, channels, modules",
    "Rust": "Ownership, borrowing, match, lifetimes"
}

for lang, content in cheats.items():
    with st.expander(lang):
        st.write(content)

# ==============================
# LOGOUT
# ==============================

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

conn.close()
