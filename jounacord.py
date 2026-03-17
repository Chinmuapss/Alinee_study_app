import hashlib
import random
from datetime import datetime, timezone
from typing import Any

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase"])
    firebase_admin.initialize_app(cred)

db = firestore.client()


st.set_page_config(page_title="CodeMaster Study Hub", page_icon="📚", layout="wide")

LANGUAGES = ["Python", "Java", "C++", "JavaScript", "Go", "Rust"]
SPECIAL_FEATURES = ["Daily Challenge", "Debug Sprint", "Interview Prep", "Speed Round"]


@st.cache_resource
def init_firebase() -> firestore.Client:
    if not firebase_admin._apps:
        firebase_config = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def generate_question_bank(language: str, count: int = 100) -> list[dict[str, Any]]:
    core_sets = {
        "Python": [
            ("What is the output type of [] and ()?", "list and tuple"),
            ("Which keyword creates a function?", "def"),
            ("What structure stores key-value pairs?", "dictionary"),
            ("What does PEP 8 describe?", "style guide"),
            ("How do you start a class definition?", "class"),
        ],
        "Java": [
            ("Which keyword defines inheritance?", "extends"),
            ("What is JVM?", "java virtual machine"),
            ("Which method starts a Java app?", "main"),
            ("What keyword creates an object?", "new"),
            ("What does JDK include besides JRE?", "compiler"),
        ],
        "C++": [
            ("Which operator allocates memory dynamically?", "new"),
            ("What is RAII focused on?", "resource management"),
            ("Which STL container is dynamic array-like?", "vector"),
            ("Which keyword prevents inheritance?", "final"),
            ("What symbol is used for namespace scope?", "::"),
        ],
        "JavaScript": [
            ("Which keyword declares a block-scoped variable?", "let"),
            ("What is DOM short for?", "document object model"),
            ("What does JSON stand for?", "javascript object notation"),
            ("Which method converts JSON string to object?", "parse"),
            ("What is used for asynchronous operations?", "promise"),
        ],
        "Go": [
            ("Which keyword starts a goroutine?", "go"),
            ("What command initializes a module?", "go mod init"),
            ("Which type handles buffered concurrency communication?", "channel"),
            ("What is the package entry point called?", "main"),
            ("What keyword defers execution?", "defer"),
        ],
        "Rust": [
            ("Which keyword declares an immutable variable?", "let"),
            ("What ownership action transfers value?", "move"),
            ("Which macro prints output?", "println"),
            ("What enum is used for recoverable errors?", "result"),
            ("Which keyword creates pattern matching branch?", "match"),
        ],
    }

    templates = [
        "{lang} Q{n}: {prompt}",
        "For {lang}, answer this (#{n}): {prompt}",
        "Knowledge check {n} in {lang}: {prompt}",
        "Quiz {n} [{lang}] - {prompt}",
    ]
    base = core_sets[language]
    questions: list[dict[str, Any]] = []

    for i in range(count):
        prompt, answer = base[i % len(base)]
        question_text = random.Random(f"{language}-{i}").choice(templates).format(
            lang=language,
            n=i + 1,
            prompt=prompt,
        )
        questions.append(
            {
                "id": f"{slugify(language)}_{i + 1}",
                "question": question_text,
                "answer": answer,
                "hint": f"Focus on foundational {language} syntax and runtime concepts.",
            }
        )
    return questions


@st.cache_data
def get_all_questions() -> dict[str, list[dict[str, Any]]]:
    return {lang: generate_question_bank(lang, 100) for lang in LANGUAGES}


def create_user(db: firestore.Client, username: str, password: str) -> tuple[bool, str]:
    user_ref = db.collection("users").document(username)
    if user_ref.get().exists:
        return False, "Username already exists."

    user_ref.set(
        {
            "username": username,
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "progress": {
                lang: {
                    "answered": [],
                    "correct": 0,
                    "attempted": 0,
                    "last_question": None,
                }
                for lang in LANGUAGES
            },
            "special_feature_attempts": [],
            "notes": {},
        }
    )
    return True, "Account created. You can now log in."


def authenticate_user(db: firestore.Client, username: str, password: str) -> bool:
    doc = db.collection("users").document(username).get()
    if not doc.exists:
        return False
    data = doc.to_dict() or {}
    return data.get("password_hash") == hash_password(password)


def get_user_data(db: firestore.Client, username: str) -> dict[str, Any]:
    doc = db.collection("users").document(username).get()
    return doc.to_dict() if doc.exists else {}


def save_user_data(db: firestore.Client, username: str, payload: dict[str, Any]):
    db.collection("users").document(username).set(payload, merge=True)


def initialize_session():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")


def render_auth(db: firestore.Client):
    st.title("📚 CodeMaster Study Hub")
    st.caption("Master 6 languages with persistent progress stored in Firebase.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary"):
            if authenticate_user(db, username.strip(), password):
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.success("Login successful.")
                st.rerun()
            st.error("Invalid credentials.")

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
                ok, message = create_user(db, username.strip(), password)
                st.success(message) if ok else st.error(message)


def choose_next_question(question_bank: list[dict[str, Any]], answered: set[str], last_question: str | None):
    remaining = [q for q in question_bank if q["id"] not in answered]
    if not remaining:
        return None

    candidates = [q for q in remaining if q["id"] != last_question]
    pool = candidates if candidates else remaining
    return random.choice(pool)


def render_dashboard(user_data: dict[str, Any]):
    st.subheader("📈 Dashboard")
    progress = user_data.get("progress", {})
    cols = st.columns(3)

    total_attempted = sum(progress.get(lang, {}).get("attempted", 0) for lang in LANGUAGES)
    total_correct = sum(progress.get(lang, {}).get("correct", 0) for lang in LANGUAGES)
    total_questions = len(LANGUAGES) * 100

    cols[0].metric("Total Attempted", total_attempted)
    cols[1].metric("Total Correct", total_correct)
    cols[2].metric("Completion", f"{(total_attempted / total_questions) * 100:.1f}%")

    for lang in LANGUAGES:
        lang_data = progress.get(lang, {"attempted": 0, "correct": 0})
        attempted = lang_data.get("attempted", 0)
        correct = lang_data.get("correct", 0)
        score = (correct / attempted) * 100 if attempted else 0
        st.progress(min(attempted / 100, 1.0), text=f"{lang}: {attempted}/100 answered | Accuracy {score:.1f}%")


def render_cheat_sheets():
    st.subheader("📌 Code Cheat Sheets")
    cheats = {
        "Python": "Lists, dicts, comprehensions, classes, decorators, context managers.",
        "Java": "OOP, interfaces, exception handling, collections, streams, JVM memory model.",
        "C++": "Pointers/references, RAII, STL containers, templates, smart pointers.",
        "JavaScript": "Closures, async/await, promises, array methods, DOM manipulation.",
        "Go": "Goroutines/channels, interfaces, error handling, modules, slices/maps.",
        "Rust": "Ownership, borrowing, lifetimes, traits, enums/match, Result/Option.",
    }
    for lang, cheat in cheats.items():
        with st.expander(lang):
            st.write(cheat)


def render_quiz(db: firestore.Client, username: str, user_data: dict[str, Any], questions: dict[str, list[dict[str, Any]]]):
    st.subheader("📝 Adaptive Quiz")
    language = st.selectbox("Choose language", LANGUAGES)

    progress = user_data.setdefault("progress", {})
    lang_state = progress.setdefault(language, {"answered": [], "correct": 0, "attempted": 0, "last_question": None})
    answered = set(lang_state.get("answered", []))

    current_key = f"current_question_{language}"
    if current_key not in st.session_state:
        st.session_state[current_key] = choose_next_question(
            questions[language],
            answered,
            lang_state.get("last_question"),
        )

    current_q = st.session_state[current_key]
    if not current_q:
        st.success(f"You completed all 100 {language} questions. Great job!")
        if st.button(f"Restart {language} quiz set"):
            progress[language] = {"answered": [], "correct": 0, "attempted": 0, "last_question": None}
            save_user_data(db, username, {"progress": progress})
            st.session_state.pop(current_key, None)
            st.rerun()
        return

    st.write(current_q["question"])
    st.caption(f"Hint: {current_q['hint']}")
    answer = st.text_input("Your answer", key=f"ans_{language}_{current_q['id']}")

    if st.button("Submit answer", key=f"submit_{language}"):
        is_correct = current_q["answer"].lower() in answer.strip().lower()
        st.success("Correct ✅") if is_correct else st.error(f"Not quite. Expected concept: {current_q['answer']}")

        lang_state["attempted"] = lang_state.get("attempted", 0) + 1
        if is_correct:
            lang_state["correct"] = lang_state.get("correct", 0) + 1
        lang_state["answered"] = list(answered | {current_q["id"]})
        lang_state["last_question"] = current_q["id"]
        progress[language] = lang_state

        save_user_data(db, username, {"progress": progress})

        st.session_state.pop(current_key, None)
        st.rerun()


def render_special_features(db: firestore.Client, username: str, user_data: dict[str, Any]):
    st.subheader("✨ Special Features")
    feature = st.selectbox("Pick a special mode", SPECIAL_FEATURES)

    prompt_map = {
        "Daily Challenge": "Explain one optimization technique you used recently.",
        "Debug Sprint": "Share a bug scenario and your fix strategy.",
        "Interview Prep": "How would you explain polymorphism to a beginner?",
        "Speed Round": "Write one tip for writing cleaner functions.",
    }

    response = st.text_area("Your response", placeholder=prompt_map[feature], height=130)
    if st.button("Save special feature response"):
        attempts = user_data.get("special_feature_attempts", [])
        attempts.append(
            {
                "feature": feature,
                "response": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        save_user_data(db, username, {"special_feature_attempts": attempts})
        st.success("Saved. Your interactive response is now part of your learning record.")

    st.markdown("#### Personal Notes")
    selected_lang = st.selectbox("Language for notes", LANGUAGES, key="note_lang")
    existing_notes = (user_data.get("notes", {}) or {}).get(selected_lang, "")
    notes = st.text_area("Write your notes", value=existing_notes, key="notes_input")
    if st.button("Save notes"):
        all_notes = user_data.get("notes", {})
        all_notes[selected_lang] = notes
        save_user_data(db, username, {"notes": all_notes})
        st.success("Notes saved.")


def render_app(db: firestore.Client):
    username = st.session_state.username
    user_data = get_user_data(db, username)
    questions = get_all_questions()

    st.title("📚 CodeMaster Study Hub")
    st.success(f"Welcome, {username}")
    st.caption("Progress is saved in Firebase and remains available when you leave and come back.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    dashboard_tab, quiz_tab, cheats_tab, special_tab = st.tabs(
        ["Dashboard", "Quiz", "Cheat Sheets", "Special Features"]
    )

    with dashboard_tab:
        render_dashboard(user_data)

    with quiz_tab:
        render_quiz(db, username, user_data, questions)

    with cheats_tab:
        render_cheat_sheets()

    with special_tab:
        render_special_features(db, username, user_data)


def main():
    initialize_session()
    try:
        db = init_firebase()
    except Exception as exc:
        st.error(f"Firebase initialization failed. Add valid firebase secrets to run the app: {exc}")
        st.stop()

    if not st.session_state.logged_in:
        render_auth(db)
        st.stop()

    render_app(db)


if __name__ == "__main__":
    main()
