import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore

st.set_page_config(page_title="ALINEE Study Hub", page_icon="📚", layout="wide")

SUBJECTS = ["Math", "Science", "History", "English", "Geography"]

QUIZ_BANK = {
    "Math": [
        {"q": "What is 8 × 7?", "options": ["54", "56", "64", "48"], "a": "56"},
        {"q": "Solve: 15 + 27", "options": ["42", "41", "43", "40"], "a": "42"},
        {"q": "What is the square root of 81?", "options": ["7", "8", "9", "10"], "a": "9"},
    ],
    "Science": [
        {"q": "What gas do plants absorb from the air?", "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], "a": "Carbon Dioxide"},
        {"q": "What is H2O commonly called?", "options": ["Salt", "Water", "Hydrogen", "Steam"], "a": "Water"},
        {"q": "Which planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Venus"], "a": "Mars"},
    ],
    "History": [
        {"q": "Who was the first President of the United States?", "options": ["George Washington", "Abraham Lincoln", "John Adams", "Thomas Jefferson"], "a": "George Washington"},
        {"q": "In which year did World War II end?", "options": ["1942", "1945", "1939", "1950"], "a": "1945"},
        {"q": "Which ancient civilization built the pyramids?", "options": ["Romans", "Greeks", "Egyptians", "Mayans"], "a": "Egyptians"},
    ],
    "English": [
        {"q": "Choose the synonym of 'rapid'.", "options": ["Slow", "Quick", "Dull", "Late"], "a": "Quick"},
        {"q": "Which is a proper noun?", "options": ["city", "school", "London", "river"], "a": "London"},
        {"q": "Select the correct form: 'She ___ to school every day.'", "options": ["go", "goes", "gone", "going"], "a": "goes"},
    ],
    "Geography": [
        {"q": "What is the largest continent?", "options": ["Africa", "Europe", "Asia", "Australia"], "a": "Asia"},
        {"q": "Which ocean is the biggest?", "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "a": "Pacific"},
        {"q": "What is the capital of Japan?", "options": ["Seoul", "Tokyo", "Beijing", "Osaka"], "a": "Tokyo"},
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
    st.title("📚 ALINEE Study Hub")
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

    st.sidebar.title("ALINEE Study Hub")
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
        st.title("📊 Dashboard")
        col1, col2, col3 = st.columns(3)
        col1.metric("Subject Flashcards", len(subject_cards))
        col2.metric("Best Quiz Score", scores.get(subject, 0))
        col3.metric("Saved Notes (chars)", len(notes.get(subject, "")))
        st.info("Use the sidebar to study, ask AI, generate flashcards, take quizzes, and track progress.")

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
        st.title("📝 Quizzes")
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
        st.title("🗒️ Notes")
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
import streamlit as st
import random

st.set_page_config(page_title="Offline AI Study App", page_icon="📚")

# ---------------- SUBJECTS ----------------
SUBJECTS = [
    "Math", "Science", "History", "Geography", "English",
    "Computer Science", "Physics", "Biology", "Chemistry", "General Knowledge"
]

# ---------------- QUIZ BANK ----------------
QUIZ_BANK = {
    "Math": [
                {"question": "What is 5 + 7?", "options": ["10", "11", "12", "13"], "answer": "12"},
                {"question": "What is 9 × 8?", "options": ["72", "64", "81", "70"], "answer": "72"},
                {"question": "Square root of 64?", "options": ["6", "7", "8", "9"], "answer": "8"},
                {"question": "Solve: 15 - 9", "options": ["6", "7", "5", "8"], "answer": "6"},
                {"question": "What is 12 ÷ 4?", "options": ["2", "3", "4", "6"], "answer": "3"},
            ] * 6,
    "Science": [
                   {"question": "What planet is known as the Red Planet?",
                    "options": ["Earth", "Mars", "Venus", "Jupiter"], "answer": "Mars"},
                   {"question": "What gas do plants absorb from the air?",
                    "options": ["Oxygen", "Carbon Dioxide", "Nitrogen", "Hydrogen"], "answer": "Carbon Dioxide"},
                   {"question": "Water chemical formula?", "options": ["H2O", "CO2", "O2", "H2"], "answer": "H2O"},
                   {"question": "What is the process of plants making food called?",
                    "options": ["Photosynthesis", "Respiration", "Digestion", "Evaporation"],
                    "answer": "Photosynthesis"},
                   {"question": "What is the boiling point of water?", "options": ["90°C", "100°C", "110°C", "120°C"],
                    "answer": "100°C"},
               ] * 6,
    "History": [
                   {"question": "Who was the first US president?",
                    "options": ["George Washington", "Abraham Lincoln", "John Adams", "Thomas Jefferson"],
                    "answer": "George Washington"},
                   {"question": "In which year did World War II end?", "options": ["1942", "1945", "1939", "1950"],
                    "answer": "1945"},
                   {"question": "Who discovered America?", "options": ["Columbus", "Magellan", "Vespucci", "Cook"],
                    "answer": "Columbus"},
                   {"question": "Which empire built the Colosseum?", "options": ["Roman", "Greek", "Egyptian", "Mayan"],
                    "answer": "Roman"},
                   {"question": "Who was the French Revolution leader?",
                    "options": ["Robespierre", "Napoleon", "Louis XVI", "Voltaire"], "answer": "Robespierre"},
               ] * 6,
    "Geography": [
                     {"question": "Largest continent?", "options": ["Asia", "Africa", "Europe", "Australia"],
                      "answer": "Asia"},
                     {"question": "Largest ocean?", "options": ["Pacific", "Atlantic", "Indian", "Arctic"],
                      "answer": "Pacific"},
                     {"question": "Capital of Japan?", "options": ["Tokyo", "Seoul", "Beijing", "Bangkok"],
                      "answer": "Tokyo"},
                     {"question": "Which country has the Great Barrier Reef?",
                      "options": ["Australia", "USA", "Brazil", "South Africa"], "answer": "Australia"},
                     {"question": "Which river is the longest?",
                      "options": ["Nile", "Amazon", "Yangtze", "Mississippi"], "answer": "Nile"},
                 ] * 6,
    "English": [
                   {"question": "Synonym of 'rapid'?", "options": ["Slow", "Quick", "Dull", "Late"], "answer": "Quick"},
                   {"question": "Select the proper noun", "options": ["city", "school", "London", "river"],
                    "answer": "London"},
                   {"question": "Choose correct: 'She ___ to school.'", "options": ["go", "goes", "gone", "going"],
                    "answer": "goes"},
                   {"question": "Antonym of 'happy'?", "options": ["Sad", "Glad", "Joyful", "Cheerful"],
                    "answer": "Sad"},
                   {"question": "Plural of 'child'?", "options": ["Childs", "Children", "Childes", "Childer"],
                    "answer": "Children"},
               ] * 6,
    "Computer Science": [
                            {"question": "CPU stands for?",
                             "options": ["Central Processing Unit", "Computer Power Unit", "Control Processing Unit",
                                         "Central Program Unit"], "answer": "Central Processing Unit"},
                            {"question": "HTML is used for?",
                             "options": ["Structure web pages", "Styling web pages", "Programming logic", "Database"],
                             "answer": "Structure web pages"},
                            {"question": "Python is a type of?",
                             "options": ["Programming Language", "Database", "Web Server", "OS"],
                             "answer": "Programming Language"},
                            {"question": "RAM is used for?",
                             "options": ["Temporary storage", "Permanent storage", "Processing", "Networking"],
                             "answer": "Temporary storage"},
                            {"question": "Which is not a programming language?",
                             "options": ["Python", "Java", "HTML", "C++"], "answer": "HTML"},
                        ] * 6,
    "Physics": [
                   {"question": "Unit of force?", "options": ["Newton", "Joule", "Watt", "Pascal"], "answer": "Newton"},
                   {"question": "Acceleration due to gravity?", "options": ["9.8 m/s²", "10 m/s²", "8 m/s²", "9 m/s"],
                    "answer": "9.8 m/s²"},
                   {"question": "Speed of light?", "options": ["3×10^8 m/s", "3×10^6 m/s", "3×10^5 m/s", "3×10^7 m/s"],
                    "answer": "3×10^8 m/s"},
                   {"question": "Energy formula?", "options": ["E=mc²", "F=ma", "P=mv", "V=IR"], "answer": "E=mc²"},
                   {"question": "Unit of pressure?", "options": ["Pascal", "Newton", "Joule", "Watt"],
                    "answer": "Pascal"},
               ] * 6,
    "Biology": [
                   {"question": "Basic unit of life?", "options": ["Cell", "Atom", "Organ", "Tissue"],
                    "answer": "Cell"},
                   {"question": "Human body has how many chromosomes?", "options": ["46", "44", "48", "42"],
                    "answer": "46"},
                   {"question": "DNA stands for?",
                    "options": ["Deoxyribonucleic Acid", "Ribonucleic Acid", "Deoxyribose Acid", "Dioxin Acid"],
                    "answer": "Deoxyribonucleic Acid"},
                   {"question": "Which organ pumps blood?", "options": ["Heart", "Lungs", "Liver", "Kidney"],
                    "answer": "Heart"},
                   {"question": "Where does photosynthesis occur?",
                    "options": ["Chloroplast", "Mitochondria", "Nucleus", "Cytoplasm"], "answer": "Chloroplast"},
               ] * 6,
    "Chemistry": [
                     {"question": "H2O is?", "options": ["Water", "Oxygen", "Hydrogen", "Salt"], "answer": "Water"},
                     {"question": "NaCl is?", "options": ["Salt", "Sugar", "Acid", "Base"], "answer": "Salt"},
                     {"question": "pH of neutral solution?", "options": ["7", "0", "14", "1"], "answer": "7"},
                     {"question": "Periodic table has how many elements?", "options": ["118", "100", "120", "115"],
                      "answer": "118"},
                     {"question": "Chemical symbol for gold?", "options": ["Au", "Ag", "G", "Go"], "answer": "Au"},
                 ] * 6,
    "General Knowledge": [
                             {"question": "Who wrote 'Hamlet'?",
                              "options": ["Shakespeare", "Dickens", "Hemingway", "Tolkien"], "answer": "Shakespeare"},
                             {"question": "Olympics held every?",
                              "options": ["2 years", "3 years", "4 years", "5 years"], "answer": "4 years"},
                             {"question": "Who invented the telephone?",
                              "options": ["Bell", "Edison", "Tesla", "Newton"], "answer": "Bell"},
                             {"question": "Smallest country?",
                              "options": ["Vatican City", "Monaco", "Malta", "Liechtenstein"],
                              "answer": "Vatican City"},
                             {"question": "Fastest land animal?", "options": ["Cheetah", "Lion", "Tiger", "Leopard"],
                              "answer": "Cheetah"},
                         ] * 6,
}

# ---------------- SESSION ----------------
if "score" not in st.session_state: st.session_state.score = 0
if "current_subject" not in st.session_state: st.session_state.current_subject = SUBJECTS[0]
if "question_pool" not in st.session_state:
    st.session_state.question_pool = random.sample(QUIZ_BANK[SUBJECTS[0]], len(QUIZ_BANK[SUBJECTS[0]]))

# ---------------- SIDEBAR ----------------
subject = st.sidebar.selectbox("Subject", SUBJECTS)
menu = st.sidebar.radio("Menu", ["Dashboard", "AI Assistant", "Quiz"])

# Switch subject → reset question pool
if subject != st.session_state.current_subject:
    st.session_state.current_subject = subject
    st.session_state.question_pool = random.sample(QUIZ_BANK[subject], len(QUIZ_BANK[subject]))

# ---------------- DASHBOARD ----------------
if menu == "Dashboard":
    st.title("📊 Dashboard")
    st.metric("Score", st.session_state.score)
    st.write("Subjects available:", len(SUBJECTS))
    st.write("Total quiz questions:", sum(len(v) for v in QUIZ_BANK.values()))


# ---------------- OFFLINE AI ASSISTANT ----------------
def simple_ai_answer(question):
    q = question.lower()
    if any(k in q for k in ["math", "+", "-", "×", "÷"]):
        return "Try solving step by step. Example: 5 + 7 = 12"
    elif "planet" in q or "mars" in q:
        return "Mars is the Red Planet. Earth is blue."
    elif "gas" in q or "plants" in q:
        return "Plants absorb carbon dioxide for photosynthesis."
    elif "capital" in q:
        return "Tokyo is the capital of Japan. Paris is the capital of France."
    elif "cpu" in q or "computer" in q:
        return "CPU stands for Central Processing Unit."
    elif "water boiling" in q or "boiling point" in q:
        return "Water boils at 100°C at standard pressure."
    else:
        return "I don't know the exact answer, but keep studying!"


if menu == "AI Assistant":
    st.title("🤖 Offline AI Study Assistant")
    question = st.text_area("Ask a study question")
    if st.button("Ask AI"):
        if not question.strip():
            st.warning("Please type a question.")
        else:
            st.success(simple_ai_answer(question))

# ---------------- QUIZ ----------------
if menu == "Quiz":
    st.title(f"📝 {subject} Quiz")

    # Reset question pool if empty
    if len(st.session_state.question_pool) == 0:
        st.success("All questions answered! Resetting quiz.")
        st.session_state.question_pool = random.sample(QUIZ_BANK[subject], len(QUIZ_BANK[subject]))

    # Get current question
    q = st.session_state.question_pool[0]
    st.write("###", q["question"])
    choice = st.radio("Choose answer", q["options"], key=f"{subject}_{q['question']}")

    if st.button("Submit Answer"):
        if choice == q["answer"]:
            st.success("✅ Correct!")
            st.session_state.score += 1
        else:
            st.error("❌ Wrong!")
            st.info(f"The correct answer is: {q['answer']}")

        # Remove answered question
        st.session_state.question_pool.pop(0)
        st.rerun()
