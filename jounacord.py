import hashlib
import json
import random
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="CodeMaster Study Hub", page_icon="📚", layout="wide")

DB_PATH = Path("codemaster.db")
LANGUAGES = ["Python", "Java", "C++", "JavaScript", "Go", "Rust"]
SPECIAL_FEATURES = ["Daily Challenge", "Debug Sprint", "Interview Prep", "Speed Round"]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS progress (
            username TEXT NOT NULL,
            language TEXT NOT NULL,
            answered_json TEXT NOT NULL DEFAULT '[]',
            correct INTEGER NOT NULL DEFAULT 0,
            attempted INTEGER NOT NULL DEFAULT 0,
            last_question TEXT,
            PRIMARY KEY (username, language),
            FOREIGN KEY (username) REFERENCES users(username)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS special_feature_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            feature TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            username TEXT NOT NULL,
            language TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (username, language),
            FOREIGN KEY (username) REFERENCES users(username)
        )
        """
    )
    conn.commit()


def ensure_user_language_rows(conn: sqlite3.Connection, username: str):
    for lang in LANGUAGES:
        conn.execute(
            """
            INSERT OR IGNORE INTO progress(username, language, answered_json, correct, attempted, last_question)
            VALUES (?, ?, '[]', 0, 0, NULL)
            """,
            (username, lang),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO notes(username, language, content, updated_at)
            VALUES (?, ?, '', ?)
            """,
            (username, lang, utc_now()),
        )
    conn.commit()


def generate_question_bank(language: str, count: int = 100) -> list[dict[str, Any]]:
    concepts = {
        "Python": ["lists", "tuples", "dictionaries", "functions", "classes", "decorators", "PEP 8", "generators", "exceptions", "context managers"],
        "Java": ["JVM", "JDK", "inheritance", "interfaces", "collections", "streams", "exceptions", "generics", "threads", "garbage collection"],
        "C++": ["pointers", "references", "RAII", "STL", "templates", "smart pointers", "virtual functions", "move semantics", "namespaces", "const correctness"],
        "JavaScript": ["closures", "promises", "async/await", "DOM", "event loop", "hoisting", "modules", "JSON", "array methods", "fetch API"],
        "Go": ["goroutines", "channels", "interfaces", "slices", "maps", "defer", "error handling", "modules", "pointers", "structs"],
        "Rust": ["ownership", "borrowing", "lifetimes", "traits", "enums", "pattern matching", "Result", "Option", "macros", "crates"],
    }
    templates = [
        "{lang} Question #{n}: Explain or identify the role of {topic}.",
        "In {lang}, what is the purpose of {topic}? (Q{n})",
        "{lang} quiz item {n}: Give one key point about {topic}.",
        "Q{n} [{lang}] - When do you use {topic}?",
    ]
    rows: list[dict[str, Any]] = []
    topic_list = concepts[language]
    for i in range(count):
        topic = topic_list[i % len(topic_list)]
        text = random.Random(f"{language}-{i}").choice(templates).format(lang=language, n=i + 1, topic=topic)
        rows.append(
            {
                "id": f"{slugify(language)}_{i + 1}",
                "question": text,
                "answer": topic.lower(),
                "hint": f"Think about practical use of {topic} in {language}.",
            }
        )
    return rows


@st.cache_data
def get_all_questions() -> dict[str, list[dict[str, Any]]]:
    return {language: generate_question_bank(language, 100) for language in LANGUAGES}


def create_user(conn: sqlite3.Connection, username: str, password: str) -> tuple[bool, str]:
    exists = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if exists:
        return False, "Username already exists."

    conn.execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, hash_password(password), utc_now()),
    )
    conn.commit()
    ensure_user_language_rows(conn, username)
    return True, "Account created. You can now log in."


def authenticate_user(conn: sqlite3.Connection, username: str, password: str) -> bool:
    row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    return bool(row and row["password_hash"] == hash_password(password))


def get_user_data(conn: sqlite3.Connection, username: str) -> dict[str, Any]:
    ensure_user_language_rows(conn, username)

    progress_rows = conn.execute(
        "SELECT language, answered_json, correct, attempted, last_question FROM progress WHERE username = ?",
        (username,),
    ).fetchall()
    progress = {
        row["language"]: {
            "answered": json.loads(row["answered_json"]),
            "correct": row["correct"],
            "attempted": row["attempted"],
            "last_question": row["last_question"],
        }
        for row in progress_rows
    }

    note_rows = conn.execute("SELECT language, content FROM notes WHERE username = ?", (username,)).fetchall()
    notes = {row["language"]: row["content"] for row in note_rows}

    attempts = conn.execute(
        "SELECT feature, response, created_at FROM special_feature_attempts WHERE username = ? ORDER BY id DESC LIMIT 20",
        (username,),
    ).fetchall()

    return {
        "progress": progress,
        "notes": notes,
        "special_feature_attempts": [dict(row) for row in attempts],
    }


def update_progress(conn: sqlite3.Connection, username: str, language: str, state: dict[str, Any]):
    conn.execute(
        """
        UPDATE progress
        SET answered_json = ?, correct = ?, attempted = ?, last_question = ?
        WHERE username = ? AND language = ?
        """,
        (
            json.dumps(state.get("answered", [])),
            state.get("correct", 0),
            state.get("attempted", 0),
            state.get("last_question"),
            username,
            language,
        ),
    )
    conn.commit()


def save_special_response(conn: sqlite3.Connection, username: str, feature: str, response: str):
    conn.execute(
        "INSERT INTO special_feature_attempts(username, feature, response, created_at) VALUES (?, ?, ?, ?)",
        (username, feature, response, utc_now()),
    )
    conn.commit()


def save_note(conn: sqlite3.Connection, username: str, language: str, note: str):
    conn.execute(
        "UPDATE notes SET content = ?, updated_at = ? WHERE username = ? AND language = ?",
        (note, utc_now(), username, language),
    )
    conn.commit()


def initialize_session():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")


def render_auth(conn: sqlite3.Connection):
    st.title("📚 CodeMaster Study Hub")
    st.caption("Learn 6 coding languages with persistent SQL-backed progress.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    with login_tab:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary"):
            if authenticate_user(conn, username.strip(), password):
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.success("Logged in successfully.")
                st.rerun()
            st.error("Invalid username or password.")

    with signup_tab:
        username = st.text_input("Create Username", key="signup_username")
        password = st.text_input("Create Password", type="password", key="signup_password")
        confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
        if st.button("Create Account"):
            if not username.strip() or not password:
                st.error("Username and password are required.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = create_user(conn, username.strip(), password)
                st.success(message) if ok else st.error(message)


def choose_next_question(question_bank: list[dict[str, Any]], answered: set[str], last_question: str | None):
    remaining = [q for q in question_bank if q["id"] not in answered]
    if not remaining:
        return None
    candidates = [q for q in remaining if q["id"] != last_question]
    return random.choice(candidates if candidates else remaining)


def render_dashboard(user_data: dict[str, Any]):
    st.subheader("📈 Dashboard")
    progress = user_data.get("progress", {})

    total_attempted = sum(progress.get(lang, {}).get("attempted", 0) for lang in LANGUAGES)
    total_correct = sum(progress.get(lang, {}).get("correct", 0) for lang in LANGUAGES)
    total_questions = len(LANGUAGES) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Attempted", total_attempted)
    c2.metric("Total Correct", total_correct)
    c3.metric("Completion", f"{(total_attempted / total_questions) * 100:.1f}%")

    for lang in LANGUAGES:
        lang_data = progress.get(lang, {"attempted": 0, "correct": 0})
        attempted = lang_data.get("attempted", 0)
        correct = lang_data.get("correct", 0)
        acc = (correct / attempted) * 100 if attempted else 0
        st.progress(min(attempted / 100, 1.0), text=f"{lang}: {attempted}/100 answered | Accuracy {acc:.1f}%")


def render_cheat_sheets():
    st.subheader("📌 Code Cheat Sheets")
    sheets = {
        "Python": ["list/dict/set comprehensions", "functions + decorators", "exceptions + context managers"],
        "Java": ["classes/interfaces", "collections + streams", "checked vs unchecked exceptions"],
        "C++": ["RAII + smart pointers", "STL containers", "templates + move semantics"],
        "JavaScript": ["scope + closures", "promises + async/await", "DOM + event handling"],
        "Go": ["goroutines + channels", "interfaces", "error handling idioms"],
        "Rust": ["ownership + borrowing", "traits + enums", "Result/Option + pattern matching"],
    }
    for lang, tips in sheets.items():
        with st.expander(lang):
            for tip in tips:
                st.write(f"- {tip}")


def render_quiz(conn: sqlite3.Connection, username: str, user_data: dict[str, Any], questions: dict[str, list[dict[str, Any]]]):
    st.subheader("📝 Adaptive Quiz")
    language = st.selectbox("Choose language", LANGUAGES)

    progress = user_data.get("progress", {})
    lang_state = progress.get(language, {"answered": [], "correct": 0, "attempted": 0, "last_question": None})
    answered = set(lang_state.get("answered", []))

    q_key = f"current_question_{language}"
    if q_key not in st.session_state:
        st.session_state[q_key] = choose_next_question(questions[language], answered, lang_state.get("last_question"))

    q = st.session_state[q_key]
    if not q:
        st.success(f"You completed all 100 {language} questions.")
        if st.button(f"Restart {language} set"):
            reset_state = {"answered": [], "correct": 0, "attempted": 0, "last_question": None}
            update_progress(conn, username, language, reset_state)
            st.session_state.pop(q_key, None)
            st.rerun()
        return

    st.write(q["question"])
    st.caption(f"Hint: {q['hint']}")
    user_answer = st.text_input("Your answer", key=f"ans_{language}_{q['id']}")

    if st.button("Submit Answer", key=f"submit_{language}"):
        correct = q["answer"] in user_answer.strip().lower()
        st.success("Correct ✅") if correct else st.error(f"Expected concept: {q['answer']}")

        new_state = {
            "answered": list(answered | {q["id"]}),
            "correct": lang_state.get("correct", 0) + (1 if correct else 0),
            "attempted": lang_state.get("attempted", 0) + 1,
            "last_question": q["id"],
        }
        update_progress(conn, username, language, new_state)
        st.session_state.pop(q_key, None)
        st.rerun()


def render_special_features(conn: sqlite3.Connection, username: str, user_data: dict[str, Any]):
    st.subheader("✨ Special Features")
    feature = st.selectbox("Pick a special mode", SPECIAL_FEATURES)
    prompts = {
        "Daily Challenge": "Share one performance improvement trick.",
        "Debug Sprint": "Describe a bug and how you fixed it.",
        "Interview Prep": "Explain polymorphism in simple terms.",
        "Speed Round": "Write one best practice for clean code.",
    }

    response = st.text_area("Your response", placeholder=prompts[feature], height=130)
    if st.button("Save Response"):
        if response.strip():
            save_special_response(conn, username, feature, response.strip())
            st.success("Response saved to your profile.")
        else:
            st.warning("Please enter a response first.")

    st.markdown("#### Personal Notes")
    note_lang = st.selectbox("Language for notes", LANGUAGES, key="note_lang")
    existing = (user_data.get("notes", {}) or {}).get(note_lang, "")
    note_value = st.text_area("Write your notes", value=existing, key="notes_input")
    if st.button("Save Notes"):
        save_note(conn, username, note_lang, note_value)
        st.success("Notes saved.")

    st.markdown("#### Recent Special Responses")
    for row in user_data.get("special_feature_attempts", [])[:5]:
        with st.expander(f"{row['feature']} • {row['created_at'][:19]}"):
            st.write(row["response"])


def render_app(conn: sqlite3.Connection):
    username = st.session_state.username
    user_data = get_user_data(conn, username)
    all_questions = get_all_questions()

    st.title("📚 CodeMaster Study Hub")
    st.success(f"Welcome, {username}")
    st.caption("Your progress is stored in SQL and remains after you leave and come back.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Quiz", "Cheat Sheets", "Special Features"])
    with tab1:
        render_dashboard(user_data)
    with tab2:
        render_quiz(conn, username, user_data, all_questions)
    with tab3:
        render_cheat_sheets()
    with tab4:
        render_special_features(conn, username, user_data)


def main():
    initialize_session()
    with closing(get_connection()) as conn:
        init_db(conn)
        if not st.session_state.logged_in:
            render_auth(conn)
            st.stop()
        render_app(conn)


if __name__ == "__main__":
    main()
