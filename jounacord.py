import hashlib
import random
import sqlite3
from datetime import datetime, timezone, date

import streamlit as st

# ==============================
# CONFIG
# ==============================

st.set_page_config(page_title="CodeMaster Pro", layout="wide")

DB_NAME = "codemaster.db"
LANGUAGES = ["Python", "Java", "C++", "JavaScript", "Go", "Rust"]

# ==============================
# DATABASE
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
        created_at TEXT,
        streak INTEGER DEFAULT 0,
        last_login TEXT
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


init_db()

# ==============================
# UTILITIES
# ==============================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def calculate_xp(correct, attempted):
    if attempted == 0:
        return 0
    accuracy = correct / attempted
    base = correct * 10
    bonus = 100 if accuracy >= 0.9 else 50 if accuracy >= 0.75 else 20
    return base + bonus


def get_rank(xp):
    if xp < 200:
        return "🥉 Beginner"
    elif xp < 500:
        return "🥈 Intermediate"
    elif xp < 1000:
        return "🥇 Advanced"
    else:
        return "💎 Code Master"


# ==============================
# AUTH FUNCTIONS
# ==============================

def create_user(username, password):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?, 0, NULL)",
            (username, hash_password(password),
             datetime.now(timezone.utc).isoformat())
        )

        for lang in LANGUAGES:
            cursor.execute("""
            INSERT INTO progress VALUES (?, ?, '', 0, 0, NULL)
            """, (username, lang))

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


def update_streak(username):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT streak, last_login FROM users WHERE username=?", (username,))
    user = cursor.fetchone()

    today = date.today()

    if user["last_login"]:
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

def generate_question(language):
    questions = {
        "Python": [
            ("What keyword defines a function?", "def"),
            ("What structure stores key-value pairs?", "dictionary"),
            ("What is used for loops?", "for"),
        ],
        "Java": [
            ("What keyword creates an object?", "new"),
            ("What starts a Java program?", "main"),
            ("What does JVM stand for?", "java virtual machine"),
        ],
        "C++": [
            ("What operator allocates memory?", "new"),
            ("What is used for scope resolution?", "::"),
            ("What is STL?", "standard template library"),
        ],
        "JavaScript": [
            ("Which keyword declares block variable?", "let"),
            ("What handles async operations?", "promise"),
            ("What does DOM stand for?", "document object model"),
        ],
        "Go": [
            ("What starts a goroutine?", "go"),
            ("What initializes modules?", "go mod"),
            ("What is used for concurrency?", "channel"),
        ],
        "Rust": [
            ("What ensures memory safety?", "ownership"),
            ("Which macro prints text?", "println"),
            ("What handles recoverable errors?", "result"),
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
# AUTH UI
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
                success, msg = create_user(new_user, new_pass)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    st.stop()


# ==============================
# DASHBOARD
# ==============================

st.sidebar.title("📊 Dashboard")

conn = get_db()
cursor = conn.cursor()

cursor.execute("SELECT * FROM users WHERE username=?",
               (st.session_state.username,))
user = cursor.fetchone()

cursor.execute("SELECT * FROM progress WHERE username=?",
               (st.session_state.username,))
progress_rows = cursor.fetchall()

total_attempted = sum(r["attempted"] for r in progress_rows)
total_correct = sum(r["correct"] for r in progress_rows)

xp = calculate_xp(total_correct, total_attempted)

st.sidebar.metric("XP", xp)
st.sidebar.write("Rank:", get_rank(xp))
st.sidebar.write("🔥 Streak:", user["streak"])


# ==============================
# QUIZ SECTION
# ==============================

st.header("🧠 Tech Quiz")

language = st.selectbox("Choose Language", LANGUAGES)

question, answer = generate_question(language)

st.write("###", question)

user_answer = st.text_input("Your Answer")

if st.button("Submit"):
    cursor.execute("""
    SELECT * FROM progress
    WHERE username=? AND language=?
    """, (st.session_state.username, language))

    row = cursor.fetchone()

    attempted = row["attempted"] + 1
    correct = row["correct"]

    if user_answer.lower().strip() == answer.lower():
        correct += 1
        st.success("Correct ✅")
    else:
        st.error(f"Wrong ❌ (Answer: {answer})")

    cursor.execute("""
    UPDATE progress
    SET attempted=?, correct=?
    WHERE username=? AND language=?
    """, (attempted, correct,
          st.session_state.username, language))

    conn.commit()
    st.rerun()


# ==============================
# CHEAT SHEETS
# ==============================

st.header("📌 Cheat Sheets")

cheats = {
    "Python": "Functions, lists, dicts, classes, exceptions, imports.",
    "Java": "OOP, JVM, inheritance, interfaces, collections.",
    "C++": "Pointers, RAII, STL, memory control.",
    "JavaScript": "DOM, async/await, promises, events.",
    "Go": "Goroutines, channels, modules.",
    "Rust": "Ownership, borrowing, lifetimes, match."
}

for lang, content in cheats.items():
    with st.expander(lang):
        st.write(content)


# ==============================
# NOTES
# ==============================

st.header("📝 Notes")

note = st.text_area("Write notes for this language:")

if st.button("Save Notes"):
    cursor.execute("""
    DELETE FROM notes
    WHERE username=? AND language=?
    """, (st.session_state.username, language))

    cursor.execute("""
    INSERT INTO notes VALUES (?, ?, ?)
    """, (st.session_state.username, language, note))

    conn.commit()
    st.success("Saved!")


# ==============================
# LOGOUT
# ==============================

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

conn.close()
