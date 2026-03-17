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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def calculate_xp(correct):
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
# USER SYSTEM
# ==============================

def create_user(username, password):
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute(
            "INSERT INTO users VALUES (?, ?, 0, NULL)",
            (username, hash_password(password))
        )

        for lang in LANGUAGES:
            c.execute(
                "INSERT INTO progress VALUES (?, ?, 0, 0, '')",
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
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()

    if not user:
        return False

    return user["password_hash"] == hash_password(password)


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
    UPDATE users
    SET streak=?, last_login=?
    WHERE username=?
    """, (streak, datetime.now(timezone.utc).isoformat(), username))

    conn.commit()
    conn.close()

# ==============================
# QUESTION GENERATOR (100+)
# ==============================

def generate_questions(language):

    base_questions = {
        "Python": [
            ("Keyword to define function?", "def"),
            ("Data structure for key-value pairs?", "dictionary"),
            ("Loop keyword?", "for"),
            ("Exception handling keyword?", "try"),
            ("OOP keyword?", "class"),
        ],
        "Java": [
            ("Create object keyword?", "new"),
            ("Main method name?", "main"),
            ("Inheritance keyword?", "extends"),
            ("Interface keyword?", "implements"),
            ("Java runs on?", "jvm"),
        ],
        "C++": [
            ("Allocate memory?", "new"),
            ("Free memory?", "delete"),
            ("Scope operator?", "::"),
            ("Library for containers?", "stl"),
            ("Destructor symbol?", "~"),
        ],
        "JavaScript": [
            ("Block variable keyword?", "let"),
            ("Constant keyword?", "const"),
            ("Async handling object?", "promise"),
            ("DOM stands for?", "document object model"),
            ("Delay function?", "settimeout"),
        ],
        "Go": [
            ("Start goroutine?", "go"),
            ("Concurrency tool?", "channel"),
            ("Module command?", "go mod"),
            ("Main package name?", "main"),
            ("Delay keyword?", "defer"),
        ],
        "Rust": [
            ("Memory safety system?", "ownership"),
            ("Error handling type?", "result"),
            ("Print macro?", "println"),
            ("Pattern matching keyword?", "match"),
            ("Borrowing uses?", "references"),
        ]
    }

    # Expand to 100 by repetition with unique IDs
    expanded = []
    for i in range(20):  # 5 base × 20 = 100
        for q, a in base_questions[language]:
            expanded.append((f"{q} #{i+1}", a))

    return expanded

# ==============================
# SESSION STATE
# ==============================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ==============================
# AUTH PAGE
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
                st.error("Username already exists.")

    st.stop()

# ==============================
# LOAD USER SAFELY
# ==============================

conn = get_db()
c = conn.cursor()

c.execute("SELECT * FROM users WHERE username=?",
          (st.session_state.username,))
user = c.fetchone()

if user is None:
    st.error("User data missing. Please login again.")
    st.stop()

# ==============================
# SIDEBAR STATS
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

language = st.selectbox("Choose Language", LANGUAGES)

questions = generate_questions(language)

c.execute("""
SELECT * FROM progress
WHERE username=? AND language=?
""", (st.session_state.username, language))

row = c.fetchone()

if row is None:
    st.error("Progress data missing.")
    st.stop()

answered_ids = row["answered"].split(",") if row["answered"] else []

available = [
    (i, q) for i, q in enumerate(questions)
    if str(i) not in answered_ids
]

if not available:
    st.success("🎉 You completed all questions for this language!")
else:
    idx, (question, answer) = random.choice(available)

    st.write("###", question)

    user_answer = st.text_input("Your Answer")

    if st.button("Submit"):
        correct = row["correct"]
        attempted = row["attempted"] + 1

        if user_answer.lower().strip() == answer.lower():
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
# ELABORATED CHEAT SHEETS
# ==============================

# ==============================
# ELABORATED CHEAT SHEETS (FULL CODE FORMAT)
# ==============================

st.header("📘 Advanced Cheat Sheets")

cheats = {

"Python": """
PYTHON OVERVIEW:
Python is a high-level, interpreted programming language designed for readability and simplicity. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.

It uses indentation to define code blocks instead of braces. Python has dynamic typing and automatic memory management through garbage collection.

CORE FEATURES:
- Easy syntax
- Large standard library
- Cross-platform
- Strong community support

EXAMPLE:
def greet(name):
    return "Hello " + name

print(greet("World"))

OBJECT-ORIENTED PROGRAMMING:
Python supports classes, inheritance, encapsulation, and polymorphism.

ADVANCED TOPICS:
- Decorators
- Generators (yield)
- Async programming
- Multithreading
- Multiprocessing
""",

"Java": """
JAVA OVERVIEW:
Java is a strongly typed, object-oriented language that runs on the Java Virtual Machine (JVM). It follows the principle of "Write Once, Run Anywhere".

Java compiles source code into bytecode, which can run on any system with a JVM installed.

CORE FEATURES:
- Platform independence
- Garbage collection
- Strict OOP structure
- Strong type system

EXAMPLE:
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}

ADVANCED TOPICS:
- Streams API
- Lambda expressions
- Generics
- Multithreading
- Exception handling
""",

"C++": """
C++ OVERVIEW:
C++ is a high-performance compiled language that supports procedural, object-oriented, and generic programming. It provides low-level memory control.

It is commonly used in systems programming, game development, and performance-critical applications.

CORE FEATURES:
- Manual memory management
- Pointers and references
- Classes and inheritance
- Templates

EXAMPLE:
#include <iostream>
using namespace std;

int main() {
    cout << "Hello World";
    return 0;
}

ADVANCED TOPICS:
- Smart pointers
- Move semantics
- STL (Standard Template Library)
- Multithreading
""",

"JavaScript": """
JAVASCRIPT OVERVIEW:
JavaScript is a dynamic scripting language mainly used for web development. It runs in browsers and also on servers using Node.js.

It is event-driven and supports asynchronous programming.

CORE FEATURES:
- DOM manipulation
- Prototype-based objects
- Event loop
- Dynamic typing

EXAMPLE:
function greet(name) {
    return "Hello " + name;
}

console.log(greet("World"));

MODERN FEATURES:
- Arrow functions
- Promises
- async/await
- Modules
- Destructuring
""",

"Go": """
GO OVERVIEW:
Go (Golang) is a compiled language designed for simplicity and concurrency. It was developed for scalable backend systems.

It includes built-in support for concurrency using goroutines.

CORE FEATURES:
- Static typing
- Fast compilation
- Simple syntax
- Garbage collection

EXAMPLE:
package main
import "fmt"

func main() {
    fmt.Println("Hello World")
}

CONCURRENCY:
- Goroutines
- Channels
""",

"Rust": """
RUST OVERVIEW:
Rust is a systems programming language focused on memory safety without using a garbage collector.

It uses an ownership system to prevent memory errors at compile time.

CORE FEATURES:
- Ownership model
- Borrowing rules
- Zero-cost abstractions
- High performance

EXAMPLE:
fn main() {
    println!("Hello World");
}

ADVANCED TOPICS:
- Pattern matching
- Traits
- Enums
- Result and Option types
- Safe concurrency
"""
}

for lang, content in cheats.items():
    with st.expander(lang):
        st.code(content)

# ==============================
# LOGOUT
# ==============================

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

conn.close()
