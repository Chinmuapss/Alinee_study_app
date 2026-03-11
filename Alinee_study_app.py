import hashlib
import json
import re
import time
import json
import re
from datetime import datetime, timezone
from typing import Any

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore
from openai import APIConnectionError, APIError, OpenAI, OpenAIError, RateLimitError
from openai import OpenAI

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


def init_openai() -> OpenAI | None:
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.warning("OpenAI key not found. AI assistant features are disabled until OPENAI_API_KEY is set.")
        return None
    st.session_state.ai_ready = True
    return OpenAI(api_key=api_key)




def request_ai_completion(client: OpenAI, messages: list[dict[str, str]], temperature: float = 0.5) -> str | None:
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except RateLimitError:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            st.error("OpenAI rate limit reached. Please wait a moment and try again.")
            return None
        except APIConnectionError:
            st.error("OpenAI connection failed. Please check your network and try again.")
            return None
        except APIError as exc:
            st.error(f"OpenAI API error: {exc}")
            return None
        except OpenAIError as exc:
            st.error(f"OpenAI error: {exc}")
            return None
        except Exception as exc:
            st.error(f"Unexpected AI error: {exc}")
            return None
    return None

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
    doc = db.collection("users").document(username).get()
    if not doc.exists:
        return None
    return safe_user_payload(doc.to_dict())


def create_user(db: firestore.Client, username: str, password: str) -> bool:
    ref = db.collection("users").document(username)
    if ref.get().exists:
        return False
    ref.set(safe_user_payload({"password": password}))
    return True


def update_user(db: firestore.Client, username: str, data: dict[str, Any]) -> None:
    db.collection("users").document(username).set(data, merge=True)


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
            if user and user.get("password") == password:
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.rerun()
            st.error("Invalid username or password.")


def main() -> None:
    init_state()
    db = init_firebase()
    ai_client = init_openai()

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
        st.title("🤖 AI Study Assistant")
        st.caption("Ask questions and generate custom flashcards from your requested topic.")

        if not ai_client:
            st.warning("AI features are disabled until OPENAI_API_KEY is configured.")
        else:
            topic = st.text_input("Topic for flashcard generation", placeholder="e.g. Cell Biology")
            count = st.slider("Number of flashcards", min_value=1, max_value=12, value=5)

            if st.button("Generate AI Flashcards"):
                if not topic.strip():
                    st.error("Please enter a topic.")
                else:
                    with st.spinner("Generating flashcards..."):
                        content = request_ai_completion(
                            ai_client,
                        response = ai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Return concise study flashcards as JSON list with keys question and answer.",
                                },
                                {
                                    "role": "user",
                                    "content": f"Create {count} flashcards about {topic} for students.",
                                },
                            ],
                            temperature=0.4,
                        )

                    if content is not None:
                        cards = parse_ai_flashcards(content)
                        if cards:
                            subject_cards.extend(cards)
                            flashcards[subject] = subject_cards
                            update_user(db, username, {"flashcards": flashcards})
                            update_progress_stats(db, username, user, "ai_generations")
                            st.success(f"Saved {len(cards)} flashcards to {subject}.")
                        else:
                            st.warning("AI response could not be parsed. Please try again.")
                    content = response.choices[0].message.content or ""
                    cards = parse_ai_flashcards(content)

                    if cards:
                        subject_cards.extend(cards)
                        flashcards[subject] = subject_cards
                        update_user(db, username, {"flashcards": flashcards})
                        update_progress_stats(db, username, user, "ai_generations")
                        st.success(f"Saved {len(cards)} flashcards to {subject}.")
                    else:
                        st.warning("AI response could not be parsed. Please try again.")

            question = st.text_area("Ask any study question")
            if st.button("Ask AI"):
                if not question.strip():
                    st.error("Please enter a question.")
                else:
                    with st.spinner("Thinking..."):
                        answer = request_ai_completion(
                            ai_client,
                        answer = ai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a helpful study tutor."},
                                {"role": "user", "content": question},
                            ],
                            temperature=0.5,
                        )
                    if answer is not None:
                        st.success(answer)
                        update_progress_stats(db, username, user, "ai_questions")
                    st.success(answer.choices[0].message.content)
                    update_progress_stats(db, username, user, "ai_questions")

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
