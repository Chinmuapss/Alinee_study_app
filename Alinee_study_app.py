import hashlib
import json
import re
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
        "quiz_answers": {},
        "firebase_ready": False,
        "ai_ready": False,
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


def init_openai() -> bool:
    # New AI engine is local and does not require external API keys.
    st.session_state.ai_ready = True
    return True


def generate_offline_flashcards(topic: str, count: int) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    clean_topic = topic.strip().title()
    for idx in range(1, count + 1):
        cards.append(
            {
                "q": f"[{clean_topic}] Key concept #{idx}: what does it mean?",
                "a": f"Concept #{idx} in {clean_topic} is a core idea. Define it, explain why it matters, and give one simple example.",
            }
        )
    return cards


def request_ai_completion(question: str, subject: str, notes_text: str) -> str:
    q = question.strip().lower()

    if "summary" in q and notes_text.strip():
        preview = notes_text.strip()[:500]
        return f"Here is a quick summary from your saved {subject} notes\n\n{preview}"

    if "quiz" in q or "question" in q:
        return (
            f"Try this {subject} practice question:\n"
            f"- Explain one important {subject} concept in 3 sentences and provide one real-life example."
        )

    if "flashcard" in q:
        return (
            f"For {subject}, strong flashcards are short and specific.\n"
            "Template: Q: What is ___? A: ___ is ___ because ___."
        )

    return (
        "Study tip: Use active recall + spaced repetition.\n"
        f"For {subject}, do this now:\n"
        "1) Review notes for 10 minutes\n"
        "2) Answer 5 self-test questions\n"
        "3) Teach the topic out loud in 2 minutes"
    )


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(raw_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    # Backward compatible with legacy plain-text passwords.
    return stored_password == raw_password or stored_password == hash_password(raw_password)


def safe_user_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    base = {"password": "", "flashcards": {}, "notes": {}, "scores": {}, "stats": {}}
    if not payload:
        return base
    base.update(payload)
    for key in ["flashcards", "notes", "scores", "stats"]:
        if not isinstance(base.get(key), dict):
            base[key] = {}
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


def parse_ai_flashcards(raw_text: str) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []

    try:
        decoded = json.loads(raw_text)
        if isinstance(decoded, list):
            for item in decoded:
                if isinstance(item, dict) and item.get("question") and item.get("answer"):
                    cards.append({"q": str(item["question"]).strip(), "a": str(item["answer"]).strip()})
    except json.JSONDecodeError:
        pass

    if cards:
        return cards

    pattern = r"Q\s*:\s*(.+?)\s*A\s*:\s*(.+?)(?=\nQ\s*:|$)"
    for match in re.finditer(pattern, raw_text, flags=re.DOTALL | re.IGNORECASE):
        q = match.group(1).strip()
        a = match.group(2).strip()
        if q and a:
            cards.append({"q": q, "a": a})
    return cards


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




def render_ai_assistant(
    db: firestore.Client,
    ai_ready: bool,
    username: str,
    user: dict[str, Any],
    subject: str,
    flashcards: dict[str, list[dict[str, str]]],
    notes: dict[str, str],
) -> None:
    st.title("🤖 AI Study Assistant")
    st.caption("Ask questions and generate custom flashcards from your requested topic.")

    if not ai_ready:
        st.warning("AI assistant is temporarily unavailable.")
        return

    subject_cards = flashcards.get(subject, [])
    topic = st.text_input("Topic for flashcard generation", placeholder="e.g. Cell Biology")
    count = st.slider("Number of flashcards", min_value=1, max_value=12, value=5)

    if st.button("Generate AI Flashcards"):
        if not topic.strip():
            st.error("Please enter a topic.")
        else:
            with st.spinner("Generating flashcards..."):
                cards = generate_offline_flashcards(topic, count)

            subject_cards.extend(cards)
            flashcards[subject] = subject_cards
            update_user(db, username, {"flashcards": flashcards})
            update_progress_stats(db, username, user, "ai_generations")
            st.success(f"Saved {len(cards)} flashcards to {subject}.")

    question = st.text_area("Ask any study question")
    if st.button("Ask AI"):
        if not question.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner("Thinking..."):
                answer = request_ai_completion(
                    question=question,
                    subject=subject,
                    notes_text=notes.get(subject, ""),
                )
            st.success(answer)
            update_progress_stats(db, username, user, "ai_questions")

def main() -> None:
    init_state()
    db = init_firebase()
    ai_ready = init_openai()

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

    flashcards = user.get("flashcards", {})
    notes = user.get("notes", {})
    scores = user.get("scores", {})
    subject_cards = flashcards.get(subject, [])

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
            answers: dict[int, str] = {}
            for idx, item in enumerate(questions):
                st.markdown(f"**Q{idx + 1}. {item['q']}**")
                answers[idx] = st.radio(
                    f"Answer {idx + 1}",
                    item["options"],
                    key=f"quiz_{subject}_{idx}",
                )

            if st.button("Submit Quiz"):
                score = sum(1 for idx, item in enumerate(questions) if answers[idx] == item["a"])
                scores[subject] = max(score, int(scores.get(subject, 0)))
                update_user(db, username, {"scores": scores})
                update_progress_stats(db, username, user, "quizzes_taken")
                st.success(f"Score: {score}/{len(questions)}")
                for idx, item in enumerate(questions):
                    if answers[idx] != item["a"]:
                        st.error(f"Q{idx + 1} correct answer: {item['a']}")

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

        flashcard_total = sum(len(flashcards.get(s, [])) for s in SUBJECTS)
        best_scores_total = sum(int(scores.get(s, 0)) for s in SUBJECTS)
        quizzes_total_questions = sum(len(QUIZ_BANK.get(s, [])) for s in SUBJECTS)
        notes_nonempty = sum(1 for s in SUBJECTS if notes.get(s, "").strip())

        completion = min(
            int((flashcard_total * 2 + best_scores_total * 5 + notes_nonempty * 10) / 5),
            100,
        )
        st.progress(completion, text=f"Overall study completion: {completion}%")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Flashcards", flashcard_total)
        c2.metric("Best Quiz Points", f"{best_scores_total}/{quizzes_total_questions}")
        c3.metric("Subjects With Notes", f"{notes_nonempty}/{len(SUBJECTS)}")

        st.subheader("Activity")
        st.write(f"AI questions asked: {stats.get('ai_questions', 0)}")
        st.write(f"AI generations: {stats.get('ai_generations', 0)}")
        st.write(f"Flashcards created: {stats.get('flashcards_created', 0)}")
        st.write(f"Quizzes taken: {stats.get('quizzes_taken', 0)}")
        st.write(f"Notes saved: {stats.get('notes_saved', 0)}")
        if stats.get("last_activity_utc"):
            st.caption(f"Last activity (UTC): {stats['last_activity_utc']}")


if __name__ == "__main__":
    main()
