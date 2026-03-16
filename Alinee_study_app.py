import hashlib
import random
from datetime import datetime, timezone
from typing import Any

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore

st.set_page_config(page_title="CodeLingo by ALINEE", page_icon="🦜", layout="wide")

SUBJECTS = ["Python", "JavaScript", "Java", "C++", "SQL"]

LESSON_NOTES = {
    "Python": """### Python Quick Notes
- **Syntax first:** indentation defines blocks.
- **Core types:** `str`, `int`, `float`, `list`, `dict`, `set`, `tuple`.
- **Loops:** `for item in items` and `while condition`.
- **Functions:** `def name(args): return value`.
- **Why Python?** Fast prototyping, AI/data work, scripting, backend APIs.
""",
    "JavaScript": """### JavaScript Quick Notes
- Runs in the browser and on servers (Node.js).
- **Variables:** `let`, `const` (prefer `const` by default).
- **Functions:** normal, arrow `() => {}`.
- **Async:** `Promise`, `async/await`.
- **Why JavaScript?** Essential for web interactivity.
""",
    "Java": """### Java Quick Notes
- Strongly typed, object-oriented language.
- **Compile + run** on JVM.
- **Classes/objects** are core building blocks.
- **Collections:** `ArrayList`, `HashMap`.
- **Why Java?** Enterprise systems and Android foundation.
""",
    "C++": """### C++ Quick Notes
- High-performance compiled language.
- Supports procedural + object-oriented + generic programming.
- **Memory:** can use pointers and references.
- **STL:** `vector`, `map`, `string`, algorithms.
- **Why C++?** Games, systems, and performance-critical software.
""",
    "SQL": """### SQL Quick Notes
- Query language for relational databases.
- Core commands: `SELECT`, `INSERT`, `UPDATE`, `DELETE`.
- Filter with `WHERE`, combine with `JOIN`.
- Aggregate with `COUNT`, `AVG`, `SUM`, grouped by `GROUP BY`.
- **Why SQL?** Data retrieval and analytics everywhere.
""",
}

QUIZ_BANK = {
    "Python": [
        {
            "q": "Which keyword is used to define a function in Python?",
            "options": ["function", "def", "fn", "lambda"],
            "a": "def",
        },
        {
            "q": "What data type is `[1, 2, 3]` in Python?",
            "options": ["tuple", "set", "list", "dict"],
            "a": "list",
        },
        {
            "q": "How do you start a for loop over a list called `items`?",
            "options": [
                "for i to items",
                "for i in items:",
                "loop i in items",
                "for(items)",
            ],
            "a": "for i in items:",
        },
    ],
    "JavaScript": [
        {
            "q": "Which keyword cannot be reassigned?",
            "options": ["var", "let", "const", "mutable"],
            "a": "const",
        },
        {
            "q": "Which syntax defines an arrow function?",
            "options": ["function => {}", "() => {}", "->", "fn()"],
            "a": "() => {}",
        },
        {
            "q": "Which feature is used for asynchronous code in modern JavaScript?",
            "options": ["sync/wait", "await/async", "pause/go", "thread.join"],
            "a": "await/async",
        },
    ],
    "Java": [
        {
            "q": "Java source code is compiled into what?",
            "options": ["Machine code", "Bytecode", "Python", "HTML"],
            "a": "Bytecode",
        },
        {
            "q": "Which keyword creates a class instance?",
            "options": ["create", "instance", "new", "init"],
            "a": "new",
        },
        {
            "q": "Which collection allows key-value pairs in Java?",
            "options": ["ArrayList", "HashMap", "Stack", "Queue"],
            "a": "HashMap",
        },
    ],
    "C++": [
        {
            "q": "Which symbol is commonly used for a pointer declaration?",
            "options": ["&", "*", "%", "#"],
            "a": "*",
        },
        {
            "q": "Which container is part of STL?",
            "options": ["vector", "arraylist", "dictionary", "dataset"],
            "a": "vector",
        },
        {
            "q": "Why is C++ often used in game engines?",
            "options": ["Low performance", "High performance", "No compilation", "Only web use"],
            "a": "High performance",
        },
    ],
    "SQL": [
        {
            "q": "Which SQL command retrieves data?",
            "options": ["PULL", "GET", "SELECT", "FETCHROW"],
            "a": "SELECT",
        },
        {
            "q": "Which clause filters rows?",
            "options": ["ORDER BY", "WHERE", "GROUP BY", "LIMIT"],
            "a": "WHERE",
        },
        {
            "q": "Which keyword combines rows from two tables?",
            "options": ["MERGE", "JOIN", "PAIR", "UNION ONLY"],
            "a": "JOIN",
        },
    ],
}


def init_state() -> None:
    defaults = {
        "logged_in": False,
        "username": "",
        "firebase_ready": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def init_firebase() -> firestore.Client | None:
    try:
        firebase_cfg = dict(st.secrets["firebase"])
    except Exception:
        st.error("Firebase config missing. Add [firebase] credentials in `.streamlit/secrets.toml`.")
        return None

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_cfg)
            firebase_admin.initialize_app(cred)
        st.session_state.firebase_ready = True
        return firestore.client()
    except Exception as exc:
        st.error(f"Failed to initialize Firebase: {exc}")
        return None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(raw_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    return stored_password == raw_password or stored_password == hash_password(raw_password)


def safe_user_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    base = {
        "password": "",
        "notes": {},
        "scores": {},
        "stats": {},
        "answered_quizzes": {},
    }
    if not payload:
        return base

    base.update(payload)
    for key in ["notes", "scores", "stats", "answered_quizzes"]:
        if not isinstance(base.get(key), dict):
            base[key] = {}

    for subject in SUBJECTS:
        answered_ids = base["answered_quizzes"].get(subject, [])
        if not isinstance(answered_ids, list):
            base["answered_quizzes"][subject] = []
    return base


def get_user(db: firestore.Client, username: str) -> dict[str, Any] | None:
    try:
        doc = db.collection("users").document(username).get()
        if not doc.exists:
            return None
        return safe_user_payload(doc.to_dict())
    except Exception as exc:
        st.error(f"Database read error: {exc}")
        return None


def create_user(db: firestore.Client, username: str, password: str) -> bool:
    try:
        ref = db.collection("users").document(username)
        if ref.get().exists:
            return False
        ref.set(safe_user_payload({"password": hash_password(password)}))
        return True
    except Exception as exc:
        st.error(f"Database write error: {exc}")
        return False


def update_user(db: firestore.Client, username: str, data: dict[str, Any]) -> None:
    try:
        db.collection("users").document(username).set(data, merge=True)
    except Exception as exc:
        st.error(f"Database update error: {exc}")


def update_progress_stats(db: firestore.Client, username: str, user_data: dict[str, Any], action: str) -> None:
    stats = user_data.get("stats", {})
    stats[action] = int(stats.get(action, 0)) + 1
    stats["last_activity_utc"] = datetime.now(timezone.utc).isoformat()
    update_user(db, username, {"stats": stats})


def login_signup(db: firestore.Client) -> None:
    st.title("🦜 CodeLingo by ALINEE")
    st.subheader("Login or create your account")

    mode = st.radio("Account", ["Login", "Sign Up"], horizontal=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Sign Up":
        confirm = st.text_input("Confirm Password", type="password")
        if st.button("Create Account", use_container_width=True):
            if not username.strip() or not password:
                st.error("Username and password are required.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif create_user(db, username.strip(), password):
                st.success("Account created successfully. Please log in.")
            else:
                st.error("Username already exists.")
    else:
        if st.button("Login", use_container_width=True):
            user = get_user(db, username.strip())
            if user and verify_password(password, user.get("password", "")):
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.rerun()
            else:
                st.error("Invalid username or password.")


def build_quiz_bank() -> dict[str, list[dict[str, Any]]]:
    templates: dict[str, list[dict[str, Any]]] = {
        "Python": [
            {"q": "Which keyword defines a function in Python?", "a": "def", "wrong": ["function", "fn", "lambda"]},
            {"q": "Which data type stores key-value pairs?", "a": "dict", "wrong": ["list", "tuple", "set"]},
            {"q": "How do you start a loop over items?", "a": "for item in items:", "wrong": ["for(item)", "loop item items", "foreach items"]},
            {"q": "Which keyword handles exceptions?", "a": "except", "wrong": ["catch", "rescue", "error"]},
            {"q": "What value represents nothing?", "a": "None", "wrong": ["null", "nil", "empty"]},
        ],
        "JavaScript": [
            {"q": "Which declaration cannot be reassigned?", "a": "const", "wrong": ["var", "let", "mutable"]},
            {"q": "What syntax defines an arrow function?", "a": "() => {}", "wrong": ["function => {}", "->", "fn()"]},
            {"q": "Which pair is used for async flows?", "a": "async/await", "wrong": ["wait/run", "pause/go", "sync/await"]},
            {"q": "Which value means strict equality operator?", "a": "===", "wrong": ["==", "=", "=>"]},
            {"q": "Which object usually logs to browser console?", "a": "console", "wrong": ["window", "screen", "document"]},
        ],
        "Java": [
            {"q": "Java code compiles to what?", "a": "Bytecode", "wrong": ["Machine code", "Python", "HTML"]},
            {"q": "Which keyword creates an object instance?", "a": "new", "wrong": ["create", "instance", "init"]},
            {"q": "Which keyword defines inheritance?", "a": "extends", "wrong": ["inherits", "implements", "super"]},
            {"q": "Which type stores true/false?", "a": "boolean", "wrong": ["bool", "bit", "binary"]},
            {"q": "Which collection stores key-value pairs?", "a": "HashMap", "wrong": ["ArrayList", "Stack", "Queue"]},
        ],
        "C++": [
            {"q": "Which symbol marks pointer declaration?", "a": "*", "wrong": ["&", "%", "#"]},
            {"q": "Which namespace is standard library?", "a": "std", "wrong": ["cpp", "core", "lib"]},
            {"q": "Which STL container is dynamic array?", "a": "vector", "wrong": ["map", "set", "queue"]},
            {"q": "Which file extension is C++ header?", "a": ".hpp", "wrong": [".java", ".py", ".sql"]},
            {"q": "What is C++ mainly known for?", "a": "High performance", "wrong": ["No compilation", "Only web", "Low speed"]},
        ],
        "SQL": [
            {"q": "Which command retrieves records?", "a": "SELECT", "wrong": ["GET", "PULL", "READ"]},
            {"q": "Which clause filters rows?", "a": "WHERE", "wrong": ["GROUP BY", "ORDER BY", "LIMIT"]},
            {"q": "Which keyword combines tables?", "a": "JOIN", "wrong": ["PAIR", "MERGE", "LINK"]},
            {"q": "Which function counts rows?", "a": "COUNT", "wrong": ["SUM", "AVG", "TOTAL"]},
            {"q": "Which statement adds new row?", "a": "INSERT", "wrong": ["PUT", "CREATE", "APPEND"]},
        ],
    }

    bank: dict[str, list[dict[str, Any]]] = {}
    for subject, subject_templates in templates.items():
        questions: list[dict[str, Any]] = []
        for i in range(QUIZZES_PER_SUBJECT):
            template = subject_templates[i % len(subject_templates)]
            distractors = template["wrong"][:]
            random.shuffle(distractors)
            options = [template["a"], *distractors]
            random.shuffle(options)
            questions.append(
                {
                    "id": f"{subject}-{i + 1}",
                    "q": f"[{subject} #{i + 1}] {template['q']}",
                    "options": options,
                    "a": template["a"],
                }
            )
        bank[subject] = questions
    return bank


QUIZ_BANK = build_quiz_bank()


def main() -> None:
    init_state()
    db = init_firebase()

    if not db:
        st.stop()

    if not st.session_state.logged_in:
        login_signup(db)
        st.stop()

    username = st.session_state.username
    user = get_user(db, username)
    if not user:
        st.error("Unable to load your account data.")
        st.stop()

    st.sidebar.title("🦜 CodeLingo Path")
    subject = st.sidebar.selectbox("Subject", SUBJECTS)
    menu = st.sidebar.radio(
        "Menu",
        ["Dashboard", "AI Assistant", "Flashcards", "Quizzes", "Notes", "Progress"],
    )

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    notes = user.get("notes", {})
    scores = user.get("scores", {})
    answered_quizzes = user.get("answered_quizzes", {})
    answered_ids = set(answered_quizzes.get(subject, []))

    if menu == "Dashboard":
        st.title("🏆 Duolingo-Style Coding Dashboard")

        flashcard_total = sum(len(flashcards.get(s, [])) for s in SUBJECTS)
        best_scores_total = sum(int(scores.get(s, 0)) for s in SUBJECTS)
        notes_nonempty = sum(1 for s in SUBJECTS if notes.get(s, "").strip())
        xp_points = flashcard_total * 8 + best_scores_total * 15 + notes_nonempty * 20
        streak = min(30, notes_nonempty + int(user.get("stats", {}).get("quizzes_taken", 0)))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Subject Flashcards", len(subject_cards))
        col2.metric("Best Quiz Score", scores.get(subject, 0))
        col3.metric("XP", xp_points)
        col4.metric("Current Streak", f"🔥 {streak} days")

        path_completion = min(100, int((xp_points / 400) * 100))
        st.progress(path_completion, text=f"Learning path completion: {path_completion}%")

        st.subheader(f"{subject} Mission")
        st.markdown(LESSON_NOTES.get(subject, ""))
        st.info("Follow the path: Read notes ➜ Practice flashcards ➜ Take quiz ➜ Save your own notes.")

    elif menu == "AI Assistant":
        render_ai_assistant(db, ai_ready, username, user, subject, flashcards, notes)

    elif menu == "Flashcards":
        st.title("📇 Flashcards")
        with st.expander("Create a flashcard", expanded=True):
            q_input = st.text_input("Question")
            a_input = st.text_input("Answer")
            if st.button("Save Flashcard"):
                if not q_input.strip() or not a_input.strip():
                    st.error("Both question and answer are required.")
                else:
                    subject_cards.append({"q": q_input.strip(), "a": a_input.strip()})
                    flashcards[subject] = subject_cards
                    update_user(db, username, {"flashcards": flashcards})
                    update_progress_stats(db, username, user, "flashcards_created")
                    st.success("Flashcard saved.")
                    st.rerun()

        st.subheader(f"Review {subject} flashcards")
        if not subject_cards:
            st.info("No flashcards yet for this subject.")
        else:
            for idx, card in enumerate(subject_cards, start=1):
                with st.container(border=True):
                    st.markdown(f"**Q{idx}:** {card['q']}")
                    st.caption(card["a"])

    elif menu == "Quizzes":
        st.title("🎯 Quizzes")
        questions = QUIZ_BANK.get(subject, [])
        if not questions:
            st.info("No quiz questions available.")
        else:
            current_batch = remaining[:QUIZ_BATCH_SIZE]
            answers: dict[str, str] = {}
            for idx, item in enumerate(current_batch, start=1):
                st.markdown(f"**Q{idx}. {item['q']}**")
                answers[item["id"]] = st.radio(
                    f"Answer {idx}",
                    item["options"],
                    key=f"quiz_{subject}_{item['id']}",
                )

            if st.button("Submit Quiz Batch"):
                score = 0
                newly_answered = list(answered_ids)
                for item in current_batch:
                    if answers[item["id"]] == item["a"]:
                        score += 1
                    newly_answered.append(item["id"])

                answered_quizzes[subject] = sorted(set(newly_answered))
                scores[subject] = max(score, int(scores.get(subject, 0)))
                update_user(
                    db,
                    username,
                    {
                        "answered_quizzes": answered_quizzes,
                        "scores": scores,
                    },
                )
                update_progress_stats(db, username, user, "quizzes_taken")
                st.success(f"Batch score: {score}/{len(current_batch)}")
                st.rerun()

    elif menu == "Notes":
        st.title("🗒️ Notes + Cheat Sheet")
        st.markdown("#### Starter notes")
        st.markdown(LESSON_NOTES.get(subject, ""))

        current_notes = notes.get(subject, "")
        new_notes = st.text_area("Write your notes", value=current_notes, height=280)
        if st.button("Save Notes"):
            notes[subject] = new_notes
            update_user(db, username, {"notes": notes})
            update_progress_stats(db, username, user, "notes_saved")
            st.success("Notes saved successfully.")

    elif menu == "Progress":
        st.title("📈 Progress Tracker")
        stats = user.get("stats", {})

        answered_total = sum(len(answered_quizzes.get(s, [])) for s in SUBJECTS)
        notes_nonempty = sum(1 for s in SUBJECTS if notes.get(s, "").strip())
        total_possible = QUIZZES_PER_SUBJECT * len(SUBJECTS)

        completion = min(int((answered_total / total_possible) * 100) + notes_nonempty * 2, 100)
        st.progress(completion, text=f"Overall completion: {completion}%")

        c1, c2, c3 = st.columns(3)
        c1.metric("Answered Quizzes", f"{answered_total}/{total_possible}")
        c2.metric("Subjects With Notes", f"{notes_nonempty}/{len(SUBJECTS)}")
        c3.metric("Total Quiz Attempts", stats.get("quizzes_taken", 0))

        st.subheader("Per-language completion")
        for lang in SUBJECTS:
            done = len(answered_quizzes.get(lang, []))
            st.write(f"{lang}: {done}/{QUIZZES_PER_SUBJECT}")

        st.subheader("Activity")
        st.write(f"Quizzes taken: {stats.get('quizzes_taken', 0)}")
        st.write(f"Notes saved: {stats.get('notes_saved', 0)}")
        if stats.get("last_activity_utc"):
            st.caption(f"Last activity (UTC): {stats['last_activity_utc']}")


if __name__ == "__main__":
    main()
