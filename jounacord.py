import hashlib
import random
import sqlite3
from datetime import datetime, timezone
from typing import Any

import streamlit as st

# ---------------- DATABASE ---------------- #

DB_NAME = "codemaster.db"


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
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        username TEXT,
        language TEXT,
        answered TEXT,
        correct INTEGER,
        attempted INTEGER,
        last_question TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        username TEXT,
        language TEXT,
        content TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------- UTILITIES ---------------- #

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


LANGUAGES = ["Python", "Java", "C++", "JavaScript", "Go", "Rust"]


# ---------------- USER FUNCTIONS ---------------- #

def create_user(username, password):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (username, hash_password(password),
             datetime.now(timezone.utc).isoformat())
        )

        for lang in LANGUAGES:
            cursor.execute("""
            INSERT INTO progress VALUES (?, ?, ?, 0, 0, NULL)
            """, (username, lang, ""))

        conn.commit()
        return True, "Account created!"
    except:
        return False, "Username already exists."
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


# ---------------- QUESTIONS ---------------- #

def generate_question(language):
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])

    if op == "+":
        answer = a + b
    elif op == "-":
        answer = a - b
    else:
        answer = a * b

    return f"{a} {op} {b}", str(answer)


# ---------------- MAIN APP ---------------- #

st.set_page_config(page_title="CodeMaster SQL", layout="wide")
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""


# ---------------- AUTH ---------------- #

if not st.session_state.logged_in:

    st.title("📚 CodeMaster (SQL Version)")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
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
                success, msg = create_user(new_user, new_pass)
                st.success(msg) if success else st.error(msg)

    st.stop()


# ---------------- DASHBOARD ---------------- #

st.title("📊 Dashboard")
st.success(f"Welcome {st.session_state.username}")

conn = get_db()
cursor = conn.cursor()

cursor.execute(
    "SELECT * FROM progress WHERE username=?",
    (st.session_state.username,)
)
rows = cursor.fetchall()

total_attempted = sum(r["attempted"] for r in rows)
total_correct = sum(r["correct"] for r in rows)

st.metric("Total Attempted", total_attempted)
st.metric("Total Correct", total_correct)

# ---------------- QUIZ ---------------- #

st.header("📝 Quiz")

language = st.selectbox("Choose Language", LANGUAGES)

question, correct_answer = generate_question(language)

st.write("Solve:", question)

user_answer = st.text_input("Your Answer")

if st.button("Submit"):

    cursor.execute("""
    SELECT * FROM progress
    WHERE username=? AND language=?
    """, (st.session_state.username, language))

    progress = cursor.fetchone()

    attempted = progress["attempted"] + 1
    correct = progress["correct"]

    if user_answer == correct_answer:
        correct += 1
        st.success("Correct ✅")
    else:
        st.error("Wrong ❌")

    cursor.execute("""
    UPDATE progress
    SET attempted=?, correct=?, last_question=?
    WHERE username=? AND language=?
    """, (
        attempted,
        correct,
        question,
        st.session_state.username,
        language
    ))

    conn.commit()
    st.rerun()


# ---------------- NOTES ---------------- #

st.header("📝 Notes")

note = st.text_area("Write your notes here:")

if st.button("Save Notes"):
    cursor.execute("""
    DELETE FROM notes WHERE username=? AND language=?
    """, (st.session_state.username, language))

    cursor.execute("""
    INSERT INTO notes VALUES (?, ?, ?)
    """, (st.session_state.username, language, note))

    conn.commit()
    st.success("Saved!")


# ---------------- LOGOUT ---------------- #

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

conn.close()
