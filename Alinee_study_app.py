import json
import random
import urllib.error
import urllib.request
from datetime import date
from typing import Any

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore

st.set_page_config(page_title="ALINEE Study App", page_icon="📚", layout="wide")

LANGUAGES = ["Python", "Java", "C++", "JavaScript", "SQL", "Go"]
TOPICS = {
    "Python": ["Functions", "Lists", "Dictionaries", "Loops", "Modules", "Classes", "Exceptions", "Comprehensions", "Typing", "File I/O"],
    "Java": ["Classes", "Objects", "Interfaces", "Inheritance", "Collections", "Exceptions", "Threads", "Generics", "JVM", "Streams"],
    "C++": ["Pointers", "References", "Templates", "STL", "OOP", "Memory", "RAII", "Namespaces", "Vectors", "Algorithms"],
    "JavaScript": ["DOM", "Promises", "Closures", "Arrays", "Objects", "Events", "Async/Await", "Modules", "Scope", "Fetch API"],
    "SQL": ["SELECT", "JOIN", "GROUP BY", "HAVING", "ORDER BY", "INDEX", "PRIMARY KEY", "FOREIGN KEY", "Transactions", "Views"],
    "Go": ["Goroutines", "Channels", "Structs", "Interfaces", "Slices", "Maps", "Error Handling", "Packages", "Testing", "Concurrency"],
}

LANGUAGE_FACTS = {
    "Python": {
        "comment": "#",
        "ext": ".py",
        "runtime": "Interpreted",
        "func": "def",
        "creator": "Guido van Rossum",
        "signature": "def process_data(items: list[str]) -> list[str]:",
        "starter": "Use a virtual environment, install with pip, and run with python main.py.",
        "connect": "Use requests for APIs and sqlite3/SQLAlchemy for databases.",
    },
    "Java": {
        "comment": "//",
        "ext": ".java",
        "runtime": "Compiled to JVM bytecode",
        "func": "public static",
        "creator": "James Gosling",
        "signature": "public static int processData(List<String> items) { ... }",
        "starter": "Use Maven/Gradle, compile with javac, run using java Main.",
        "connect": "Use JDBC for DB connections and HttpClient/Retrofit for APIs.",
    },
    "C++": {
        "comment": "//",
        "ext": ".cpp",
        "runtime": "Compiled",
        "func": "int",
        "creator": "Bjarne Stroustrup",
        "signature": "int processData(const vector<string>& items) { ... }",
        "starter": "Use CMake + g++, then run the compiled binary.",
        "connect": "Use libcurl for APIs and connectors/ODBC for databases.",
    },
    "JavaScript": {
        "comment": "//",
        "ext": ".js",
        "runtime": "Interpreted/JIT",
        "func": "function",
        "creator": "Brendan Eich",
        "signature": "function processData(items) { return items.map(String); }",
        "starter": "Use npm, then run browser scripts or node app.js.",
        "connect": "Use fetch/axios for APIs and drivers like pg/mongoose for databases.",
    },
    "SQL": {
        "comment": "--",
        "ext": ".sql",
        "runtime": "Query language",
        "func": "CREATE PROCEDURE",
        "creator": "Donald Chamberlin and Raymond Boyce",
        "signature": "CREATE PROCEDURE ProcessData AS BEGIN SELECT ... END",
        "starter": "Use a SQL client, connect to DB, and run scripts transactionally.",
        "connect": "Use connection strings + drivers (psql, mysql, sqlcmd) from apps.",
    },
    "Go": {
        "comment": "//",
        "ext": ".go",
        "runtime": "Compiled",
        "func": "func",
        "creator": "Robert Griesemer, Rob Pike, and Ken Thompson",
        "signature": "func processData(items []string) []string { return items }",
        "starter": "Initialize with go mod init, run with go run ., build with go build.",
        "connect": "Use net/http for APIs and database/sql with drivers for DB.",
    },
}

QUESTION_DIMENSIONS = [
    ("comment", "debugging notes"),
    ("ext", "repository structure"),
    ("runtime", "deployment approach"),
    ("func", "function design"),
    ("creator", "technology history"),
    ("signature", "team code standard"),
    ("starter", "project setup"),
    ("connect", "service integration"),
    ("runtime", "production incident"),
    ("func", "code review"),
]


def firebase_ready() -> bool:
    return st.session_state.get("firebase_enabled", False)


def initialize_firebase() -> None:
    if "firebase_enabled" in st.session_state:
        return

    st.session_state.firebase_enabled = False
    st.session_state.firestore_client = None

    config = st.secrets.get("firebase") if "firebase" in st.secrets else None
    if not config:
        return

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(dict(config["service_account"]))
            firebase_admin.initialize_app(cred)
        st.session_state.firestore_client = firestore.client()
        st.session_state.firebase_enabled = True
    except Exception:
        st.session_state.firebase_enabled = False


def identity_request(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    api_key = st.secrets.get("firebase", {}).get("web_api_key")
    if not api_key:
        raise RuntimeError("Missing firebase.web_api_key in Streamlit secrets.")

    url = f"https://identitytoolkit.googleapis.com/v1/{endpoint}?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8")
        try:
            error = json.loads(details).get("error", {}).get("message", details)
        except json.JSONDecodeError:
            error = details
        raise RuntimeError(error) from exc


def signup_user(email: str, password: str) -> dict[str, Any]:
    return identity_request("accounts:signUp", {"email": email, "password": password, "returnSecureToken": True})


def login_user(email: str, password: str) -> dict[str, Any]:
    return identity_request("accounts:signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})


def build_cheat_sheet(lang: str) -> str:
    facts = LANGUAGE_FACTS[lang]
    return f"""
### {lang} Advanced Cheat Sheet

**1) Core Parts**
- Creator: **{facts['creator']}**
- File Extension: **{facts['ext']}**
- Runtime Model: **{facts['runtime']}**
- Single-line Comment: **{facts['comment']}**

**2) Function Basics**
```text
{facts['signature']}
```
- Typical declaration keyword/pattern: **{facts['func']}**
- Use functions to isolate logic, improve testing, and simplify reviews.

**3) Setup & Connectivity**
- Project bootstrap: {facts['starter']}
- Connecting services: {facts['connect']}

**4) Production Tips**
- Keep configuration in environment variables.
- Add linting + formatting checks in CI.
- Keep error handling explicit and user-facing messages clear.
"""


def shuffled_options(correct: str, pool: list[str], seed: int) -> list[str]:
    rnd = random.Random(seed)
    options = [correct]
    for item in pool:
        if item != correct and item not in options:
            options.append(item)
        if len(options) == 4:
            break
    while len(options) < 4:
        options.append(f"Option {len(options)+1}")
    rnd.shuffle(options)
    return options


def build_question_bank(lang: str) -> list[dict[str, Any]]:
    facts = LANGUAGE_FACTS[lang]
    questions: list[dict[str, Any]] = []
    qid = 1

    for topic in TOPICS[lang]:
        for variant, (field, scenario) in enumerate(QUESTION_DIMENSIONS):
            answer = facts[field]
            pool = [LANGUAGE_FACTS[l][field] for l in LANGUAGES if l != lang]
            options = shuffled_options(answer, pool, seed=(qid * 17 + variant))

            prompt = (
                f"Q{qid:03d} [{topic}] You are mentoring a junior developer in a {lang}-only codebase. "
                f"During a sprint focused on {scenario}, the team must make a correct language-specific decision "
                f"to avoid technical debt and failed reviews. Which choice best fits {lang} best practice in this context?"
            )
            explanation = (
                f"In this {lang}-exclusive situation, the expected choice is '{answer}' because it aligns with {lang} conventions "
                f"for {topic.lower()} and prevents cross-language confusion in production workflows."
            )
            questions.append({
                "id": f"{lang}-{qid}",
                "question": prompt,
                "options": options,
                "answer": answer,
                "explanation": explanation,
                "topic": topic,
            })
            qid += 1
    return questions


def get_question(lang: str, qid: str) -> dict[str, Any] | None:
    return next((q for q in st.session_state.question_bank[lang] if q["id"] == qid), None)


def init_state() -> None:
    initialize_firebase()

    if "user" not in st.session_state:
        st.session_state.user = None
    if "question_bank" not in st.session_state:
        st.session_state.question_bank = {lang: build_question_bank(lang) for lang in LANGUAGES}
    if "progress" not in st.session_state:
        st.session_state.progress = {
            lang: {
                "remaining": [q["id"] for q in st.session_state.question_bank[lang]],
                "current": None,
                "attempted": 0,
                "correct": 0,
                "history": [],
            }
            for lang in LANGUAGES
        }
    if "daily_challenge" not in st.session_state:
        all_ids = [(lang, q["id"]) for lang in LANGUAGES for q in st.session_state.question_bank[lang]]
        random.shuffle(all_ids)
        st.session_state.daily_challenge = {
            "date": date.today().isoformat(),
            "remaining": all_ids[:36],
            "score": 0,
            "attempted": 0,
            "answered": [],
        }


def sync_progress_to_firebase() -> None:
    if not (firebase_ready() and st.session_state.user):
        return

    payload = {
        "email": st.session_state.user["email"],
        "updated_at": firestore.SERVER_TIMESTAMP,
        "overall": {
            "attempted": sum(st.session_state.progress[lang]["attempted"] for lang in LANGUAGES),
            "correct": sum(st.session_state.progress[lang]["correct"] for lang in LANGUAGES),
        },
        "languages": {
            lang: {
                "attempted": st.session_state.progress[lang]["attempted"],
                "correct": st.session_state.progress[lang]["correct"],
                "remaining": len(st.session_state.progress[lang]["remaining"]),
            }
            for lang in LANGUAGES
        },
    }

    db = st.session_state.firestore_client
    db.collection("alinee_scores").document(st.session_state.user["uid"]).set(payload, merge=True)


def load_progress_from_firebase() -> None:
    if not (firebase_ready() and st.session_state.user):
        return

    db = st.session_state.firestore_client
    doc = db.collection("alinee_scores").document(st.session_state.user["uid"]).get()
    if not doc.exists:
        sync_progress_to_firebase()
        return

    data = doc.to_dict().get("languages", {})
    for lang in LANGUAGES:
        if lang not in data:
            continue
        attempted = int(data[lang].get("attempted", 0))
        correct = int(data[lang].get("correct", 0))
        bank_ids = [q["id"] for q in st.session_state.question_bank[lang]]
        remaining_count = int(data[lang].get("remaining", len(bank_ids)))
        used_count = max(0, min(len(bank_ids), len(bank_ids) - remaining_count))
        st.session_state.progress[lang]["attempted"] = attempted
        st.session_state.progress[lang]["correct"] = correct
        st.session_state.progress[lang]["remaining"] = bank_ids[used_count:]


def next_question(lang: str) -> dict[str, Any] | None:
    if not st.session_state.progress[lang]["remaining"]:
        st.session_state.progress[lang]["current"] = None
        return None
    choice = random.choice(st.session_state.progress[lang]["remaining"])
    st.session_state.progress[lang]["current"] = choice
    return get_question(lang, choice)


def reset_language(lang: str) -> None:
    st.session_state.progress[lang] = {
        "remaining": [q["id"] for q in st.session_state.question_bank[lang]],
        "current": None,
        "attempted": 0,
        "correct": 0,
        "history": [],
    }


def auth_panel() -> None:
    st.sidebar.markdown("### 🔐 Account")
    if st.session_state.user:
        st.sidebar.success(f"Logged in as {st.session_state.user['email']}")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        return

    mode = st.sidebar.radio("Auth", ["Login", "Sign Up"], horizontal=True)
    email = st.sidebar.text_input("Email", key=f"{mode}_email")
    password = st.sidebar.text_input("Password", type="password", key=f"{mode}_pwd")

    if st.sidebar.button(mode):
        try:
            payload = login_user(email, password) if mode == "Login" else signup_user(email, password)
            st.session_state.user = {"uid": payload["localId"], "email": payload["email"], "token": payload["idToken"]}
            load_progress_from_firebase()
            st.sidebar.success(f"{mode} successful")
            st.rerun()
        except Exception as exc:
            st.sidebar.error(str(exc))


def dashboard() -> None:
    st.title("📊 Dashboard")
    total_attempted = sum(st.session_state.progress[l]["attempted"] for l in LANGUAGES)
    total_correct = sum(st.session_state.progress[l]["correct"] for l in LANGUAGES)
    completion = int((total_attempted / (len(LANGUAGES) * 100)) * 100)
    accuracy = int((total_correct / total_attempted) * 100) if total_attempted else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Languages", len(LANGUAGES))
    c2.metric("Attempted", total_attempted)
    c3.metric("Accuracy", f"{accuracy}%")
    c4.metric("Completion", f"{completion}%")

    st.progress(completion, text="Global learning completion")
    st.info("Dashboard = global snapshot. Use Progress Tracker for per-language deep analytics.")


def progress_tracker() -> None:
    st.title("📈 Progress Tracker")
    st.write("Detailed language progress board with independent score lines and sync-aware status.")

    rows = []
    for lang in LANGUAGES:
        attempted = st.session_state.progress[lang]["attempted"]
        correct = st.session_state.progress[lang]["correct"]
        rows.append({
            "Language": lang,
            "Attempted": attempted,
            "Correct": correct,
            "Accuracy %": int((correct / attempted) * 100) if attempted else 0,
            "Remaining": len(st.session_state.progress[lang]["remaining"]),
        })
    st.dataframe(rows, use_container_width=True)

    for row in rows:
        st.markdown(f"**{row['Language']}**")
        st.progress(int((row["Attempted"] / 100) * 100), text=f"{row['Attempted']}/100 questions completed")

    if st.session_state.user:
        st.success("Scores can be persisted to Firebase and displayed in this board.")
        if st.button("Sync now to Firebase"):
            sync_progress_to_firebase()
            st.success("Progress synced.")


def quizzes() -> None:
    st.title("🧠 Situational Quizzes (100 per Language)")
    lang = st.selectbox("Choose a technology", LANGUAGES)
    data = st.session_state.progress[lang]

    st.caption(f"{lang}: {data['attempted']}/100 attempted • {data['correct']} correct • {len(data['remaining'])} left")
    question = next_question(lang) if data["current"] is None else get_question(lang, data["current"])

    if question is None:
        st.success(f"You completed all 100 non-repeating {lang} questions.")
        if st.button("Reset this language"):
            reset_language(lang)
            st.rerun()
        return

    st.markdown(f"### {question['question']}")
    selected = st.radio("Select best answer", question["options"], key=f"answer_{question['id']}")

    if st.button("Submit", type="primary"):
        correct = selected == question["answer"]
        data["attempted"] += 1
        data["correct"] += int(correct)
        data["remaining"].remove(question["id"])
        data["history"].append({
            "Question": question["question"],
            "Chosen": selected,
            "Answer": question["answer"],
            "Result": "✅ Correct" if correct else "❌ Incorrect",
        })
        data["current"] = None
        if st.session_state.user and firebase_ready():
            sync_progress_to_firebase()
        st.success("Great answer!" if correct else f"Correct answer: {question['answer']}")
        st.info(question["explanation"])
        st.rerun()


def cheat_sheets() -> None:
    st.title("📘 Technology Cheat Sheets")
    lang = st.selectbox("Technology", LANGUAGES, key="sheet_lang")
    st.markdown(build_cheat_sheet(lang))


def special_features() -> None:
    st.title("✨ Special Features")
    tab1, tab2 = st.tabs(["🎯 Adaptive Daily Marathon", "⚡ Interview Mode"])

    with tab1:
        st.write("Mixed-language challenge where each item is consumed once with no repeats.")
        dc = st.session_state.daily_challenge
        st.caption(f"Attempted: {dc['attempted']} • Score: {dc['score']} • Remaining: {len(dc['remaining'])}")
        if dc["remaining"]:
            lang, qid = dc["remaining"][0]
            q = get_question(lang, qid)
            st.markdown(f"**{lang}** | {q['question']}")
            response = st.radio("Choose", q["options"], key=f"daily_{qid}")
            if st.button("Submit daily response"):
                dc["attempted"] += 1
                dc["answered"].append({"lang": lang, "qid": qid})
                dc["score"] += int(response == q["answer"])
                dc["remaining"].pop(0)
                st.rerun()
        else:
            st.success("Daily marathon finished.")

    with tab2:
        st.write("Open-response interaction: answer short prompts for language-specific mastery.")
        lang = st.selectbox("Pick language", LANGUAGES, key="interview_lang")
        field = st.selectbox("Prompt", ["comment", "ext", "func", "runtime", "connect"])
        answer = st.text_input("Type your answer")
        if st.button("Evaluate response"):
            expected = LANGUAGE_FACTS[lang][field].lower().strip()
            got = answer.lower().strip()
            if expected in got or got in expected:
                st.success("Strong answer. ✅")
            else:
                st.warning(f"Expected idea: {LANGUAGE_FACTS[lang][field]}")


def main() -> None:
    init_state()

    render_login_gate()

    st.sidebar.title("📚 ALINEE Study App")
    auth_panel()

    if not firebase_ready():
        st.sidebar.warning("Firebase config missing. App runs locally; cloud sync is disabled.")

    page = st.sidebar.radio("Navigate", ["Dashboard", "Progress Tracker", "Cheat Sheets", "Quizzes", "Special Features"])

    st.sidebar.markdown("---")
    if st.sidebar.button("Reset all progress"):
        for lang in LANGUAGES:
            reset_language(lang)
        all_ids = [(l, q["id"]) for l in LANGUAGES for q in st.session_state.question_bank[l]]
        random.shuffle(all_ids)
        st.session_state.daily_challenge = {
            "date": date.today().isoformat(),
            "remaining": all_ids[:36],
            "score": 0,
            "attempted": 0,
            "answered": [],
        }
        if st.session_state.user and firebase_ready():
            sync_progress_to_firebase()
        st.rerun()

    if page == "Dashboard":
        dashboard()
    elif page == "Progress Tracker":
        progress_tracker()
    elif page == "Cheat Sheets":
        cheat_sheets()
    elif page == "Quizzes":
        quizzes()
    else:
        special_features()


if __name__ == "__main__":
    main()
