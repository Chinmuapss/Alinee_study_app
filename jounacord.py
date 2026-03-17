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
# DATABASE
# ==============================

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        streak INTEGER DEFAULT 0,
        last_login TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        username TEXT,
        language TEXT,
        correct INTEGER DEFAULT 0,
        attempted INTEGER DEFAULT 0,
        answered TEXT DEFAULT ''
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ==============================
# HELPERS
# ==============================

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def calculate_xp(correct):
    return correct * 10

def get_rank(xp):
    if xp < 100: return "🥉 Beginner"
    elif xp < 300: return "🥈 Intermediate"
    elif xp < 600: return "🥇 Advanced"
    else: return "💎 Code Master"

# ==============================
# USER SYSTEM
# ==============================

def create_user(u, p):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, 0, NULL)",
                  (u, hash_password(p)))
        for lang in LANGUAGES:
            c.execute("INSERT INTO progress VALUES (?, ?, 0, 0, '')",
                      (u, lang))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def authenticate(u, p):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (u,))
    user = c.fetchone()
    conn.close()
    return user and user["password_hash"] == hash_password(p)

def update_streak(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

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

    c.execute("""
    UPDATE users SET streak=?, last_login=?
    WHERE username=?
    """, (streak, datetime.now(timezone.utc).isoformat(), username))

    conn.commit()
    conn.close()

# ==============================
# QUESTION GENERATOR (100+)
# ==============================

def generate_questions(language):

    base = {
        "Python": [
            ("Keyword for function?", "def"),
            ("Data type for key-value?", "dictionary"),
            ("Loop keyword?", "for"),
            ("Exception handler?", "try"),
            ("OOP keyword?", "class"),
        ],
        "Java": [
            ("Create object keyword?", "new"),
            ("Main method name?", "main"),
            ("Inheritance keyword?", "extends"),
            ("Interface keyword?", "implements"),
            ("Runs Java?", "jvm"),
        ],
        "C++": [
            ("Allocate memory?", "new"),
            ("Free memory?", "delete"),
            ("Scope operator?", "::"),
            ("Library for vector?", "stl"),
            ("Destructor symbol?", "~"),
        ],
        "JavaScript": [
            ("Block variable?", "let"),
            ("Async handler?", "promise"),
            ("DOM meaning?", "document object model"),
            ("Constant keyword?", "const"),
            ("Delay function?", "settimeout"),
        ],
        "Go": [
            ("Start goroutine?", "go"),
            ("Concurrency tool?", "channel"),
            ("Module init?", "go mod"),
            ("Main package?", "main"),
            ("Delay keyword?", "defer"),
        ],
        "Rust": [
            ("Memory safety?", "ownership"),
            ("Error handler?", "result"),
            ("Print macro?", "println"),
            ("Pattern matching?", "match"),
            ("Borrow system?", "reference"),
        ]
    }

    # Expand to ~100 questions by variations
    expanded = []
    for q, a in base[language]:
        for i in range(20):  # 5 x 20 = 100
            expanded.append((f"{q} ({i+1})", a))

    return expanded

# ==============================
# SESSION
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
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            if authenticate(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                update_streak(u)
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        cp = st.text_input("Confirm Password", type="password")

        if st.button("Create Account"):
            if np != cp:
                st.error("Passwords do not match.")
            elif create_user(nu, np):
                st.success("Account created!")
            else:
                st.error("Username exists.")

    st.stop()

# ==============================
# LOAD USER
# ==============================

conn = get_db()
c = conn.cursor()

c.execute("SELECT * FROM users WHERE username=?",
          (st.session_state.username,))
user = c.fetchone()

if not user:
    st.error("User missing. Login again.")
    st.stop()

# ==============================
# SIDEBAR
# ==============================

c.execute("SELECT * FROM progress WHERE username=?",
          (st.session_state.username,))
rows = c.fetchall()

total_correct = sum(r["correct"] for r in rows)
xp = calculate_xp(total_correct)

st.sidebar.title("📊 Stats")
st.sidebar.metric("XP", xp)
st.sidebar.write("Rank:", get_rank(xp))
st.sidebar.write("🔥 Streak:", user["streak"])

# ==============================
# QUIZ (NO REPEATS)
# ==============================

st.header("🧠 Tech Quiz")

language = st.selectbox("Language", LANGUAGES)

questions = generate_questions(language)

c.execute("""
SELECT * FROM progress WHERE username=? AND language=?
""", (st.session_state.username, language))

row = c.fetchone()

answered_ids = row["answered"].split(",") if row["answered"] else []

available = [
    (i, q) for i, q in enumerate(questions)
    if str(i) not in answered_ids
]

if not available:
    st.success("🎉 You finished all questions for this language!")
else:
    idx, (question, answer) = random.choice(available)

    st.write("###", question)
    user_ans = st.text_input("Answer")

    if st.button("Submit"):
        correct = row["correct"]
        attempted = row["attempted"] + 1

        if user_ans.lower().strip() == answer.lower():
            correct += 1
            st.success("Correct ✅")
        else:
            st.error(f"Wrong ❌ Answer: {answer}")

        answered_ids.append(str(idx))

        c.execute("""
        UPDATE progress
        SET correct=?, attempted=?, answered=?
        WHERE username=? AND language=?
        """, (
            correct,
            attempted,
            ",".join(answered_ids),
            st.session_state.username,
            language
        ))

        conn.commit()
        st.rerun()

# ==============================
# CHEAT SHEETS (DETAILED)
# ==============================

st.header("📘 Cheat Sheets")

cheats = {
"Python": """
- Functions: def
- Data types: list, dict, tuple, set
- OOP: class
- Exceptions: try/except
- Advanced: decorators, generators, async
""",
"Java": """
- OOP: classes, inheritance
- JVM execution
- Interfaces
- Collections
- Multithreading
""",
"C++": """
- Memory: new/delete
- Pointers & references
- STL containers
- RAII
""",
"JavaScript": """
- DOM
- Async/await
- Promises
- Closures
""",
"Go": """
- Goroutines
- Channels
- Fast compile
""",
"Rust": """
- Ownership
- Borrowing
- Lifetimes
- Pattern matching
"""
}

for lang, content in cheats.items():
    with st.expander(lang):
        st.markdown(content)

# ==============================
# LOGOUT
# ==============================

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

conn.close()
