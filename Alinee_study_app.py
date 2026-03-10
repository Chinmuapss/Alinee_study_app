import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import openai
import random

# import os  # Removed as we use st.secrets instead

# ---------------- CONFIG ----------------
st.set_page_config(page_title="ALINEE Study Hub", layout="wide")

# ---------------- FIREBASE ----------------
if not firebase_admin._apps:
    # Initialize Firebase using Streamlit secrets
    try:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except KeyError:
        st.error("Firebase secrets not found! Please configure 'firebase' in Streamlit Secrets.")
        st.stop()

# ---------------- OPENAI ----------------
# Use st.secrets instead of os.getenv for consistency with Streamlit
openai.api_key = st.secrets.get("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OpenAI API key not found! Please set 'OPENAI_API_KEY' in Streamlit Secrets.")
    st.stop()

# ---------------- SESSION ----------------
for key in ["logged_in", "username", "quiz_score", "subject_cards", "flashcard_index", "quiz_answers"]:
    if key not in st.session_state:
        if key == "logged_in":
            st.session_state[key] = False
        elif key == "username":
            st.session_state[key] = ""
        elif key == "quiz_score":
            st.session_state[key] = 0
        elif key == "subject_cards":
            st.session_state[key] = []
        elif key == "flashcard_index":
            st.session_state[key] = 0
        elif key == "quiz_answers":
            st.session_state[key] = {}


# ---------------- USER FUNCTIONS ----------------
def get_user(username):
    try:
        doc = db.collection("users").document(username).get()
        if doc.exists:
            data = doc.to_dict()
            # Ensure all fields are dictionaries
            for key in ["flashcards", "notes", "scores"]:
                if key not in data or not isinstance(data[key], dict):
                    data[key] = {}
            return data
        return None
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None


def create_user(username, password):
    try:
        ref = db.collection("users").document(username)
        if ref.get().exists:
            return False
        ref.set({"password": password, "flashcards": {}, "notes": {}, "scores": {}})
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False


def update_user(username, data):
    try:
        db.collection("users").document(username).update(data)
    except Exception as e:
        st.error(f"Database Error: {e}")


# ---------------- LOGIN / SIGNUP ----------------
if not st.session_state.logged_in:
    st.title("📚 ALINEE Study Hub")
    mode = st.radio("Login / Sign Up", ["Login", "Sign Up"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Sign Up":
        confirm = st.text_input("Confirm Password", type="password")
        if st.button("Create Account"):
            if password != confirm:
                st.error("Passwords do not match")
            else:
                if create_user(username, password):
                    st.success("Account created! Please login")
                else:
                    st.error("Username exists")
    else:
        if st.button("Login"):
            user = get_user(username)
            if user and user["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid login")
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.title("ALINEE Study Hub")
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Create Flashcard", "Review Flashcards",
                                     "Study Notes", "Quiz", "Progress", "AI Study Assistant"])
subjects = ["Math", "Science", "History", "English", "Geography"]
subject = st.sidebar.selectbox("Subject", subjects)
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ---------------- LOAD USER DATA ----------------
user = get_user(st.session_state.username)
if not user:
    st.error("User data not found. Please try logging in again.")
    st.stop()

flashcards = user.get("flashcards", {})
notes = user.get("notes", {})
scores = user.get("scores", {})
subject_cards = flashcards.get(subject, [])

# ---------------- DASHBOARD ----------------
if menu == "Dashboard":
    st.title("📊 Dashboard")
    st.metric("Flashcards", len(subject_cards))
    st.metric("Quiz Score", scores.get(subject, 0))
    st.info("Use the sidebar to navigate study tools")

# ---------------- CREATE FLASHCARD ----------------
if menu == "Create Flashcard":
    st.title("➕ Create Flashcard")
    q_input = st.text_input("Question")
    a_input = st.text_input("Answer")
    if st.button("Save Flashcard"):
        if q_input and a_input:
            subject_cards.append({"q": q_input, "a": a_input})
            flashcards[subject] = subject_cards
            update_user(st.session_state.username, {"flashcards": flashcards})
            st.success("Flashcard saved!")
            st.rerun()

# ---------------- REVIEW FLASHCARDS ----------------
if menu == "Review Flashcards":
    st.title("📇 Flashcards")
    if not subject_cards:
        st.warning("No flashcards for this subject")
    else:
        # Ensure index is within bounds
        if st.session_state.flashcard_index >= len(subject_cards):
            st.session_state.flashcard_index = 0

        card = subject_cards[st.session_state.flashcard_index]
        st.subheader(card["q"])

        if st.button("Show Answer", key="show_answer"):
            st.success(card["a"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Previous Card"):
                st.session_state.flashcard_index = max(0, st.session_state.flashcard_index - 1)
                st.rerun()
        with col2:
            if st.button("Next Card"):
                st.session_state.flashcard_index = min(len(subject_cards) - 1, st.session_state.flashcard_index + 1)
                st.rerun()

# ---------------- STUDY NOTES ----------------
if menu == "Study Notes":
    st.title("📝 Study Notes")
    current_notes = notes.get(subject, "")
    new_notes = st.text_area("Write your notes here", value=current_notes, height=300)
    if st.button("Save Notes"):
        notes[subject] = new_notes
        update_user(st.session_state.username, {"notes": notes})
        st.success("Notes saved!")

# ---------------- QUIZ ----------------
quiz_data = {
    "Math": [{"q": "5 + 7 =", "options": ["10", "11", "12", "13"], "a": "12"}],
    "Science": [{"q": "H2O is", "options": ["Water", "Oxygen", "Hydrogen", "Carbon"], "a": "Water"}],
    "History": [
        {"q": "First US President", "options": ["Lincoln", "Washington", "Adams", "Jefferson"], "a": "Washington"}],
    "English": [{"q": "Synonym of BIG", "options": ["Large", "Tiny", "Small", "Weak"], "a": "Large"}],
    "Geography": [{"q": "Largest continent", "options": ["Asia", "Europe", "Africa", "Australia"], "a": "Asia"}]
}

if menu == "Quiz":
    st.title("📝 Quiz")
    questions = quiz_data.get(subject, [])

    if not questions:
        st.warning("No quiz questions available for this subject.")
    else:
        # Render all questions first
        for i, q in enumerate(questions):
            st.subheader(f"Q{i + 1}: {q['q']}")
            ans = st.radio("Choose", q["options"], key=f"quiz_{i}", label_visibility="collapsed")
            if ans:
                st.session_state.quiz_answers[i] = ans

        if st.button("Finish Quiz"):
            score = 0
            for i, q in enumerate(questions):
                user_ans = st.session_state.quiz_answers.get(i)
                if user_ans == q["a"]:
                    score += 1
                else:
                    st.error(f"Q{i + 1}: Correct answer was {q['a']}")

            scores[subject] = score
            update_user(st.session_state.username, {"scores": scores})
            st.success(f"Your score: {score}/{len(questions)}")
            st.session_state.quiz_answers = {}  # Reset answers

# ---------------- PROGRESS ----------------
if menu == "Progress":
    st.title("📈 Progress")
    progress_val = min(len(subject_cards) * 10, 100)
    st.progress(progress_val)
    st.write(f"Flashcards: {len(subject_cards)}")
    st.write(f"Quiz score: {scores.get(subject, 0)}")

# ---------------- AI STUDY ASSISTANT ----------------
if menu == "AI Study Assistant":
    st.title("🤖 AI Study Assistant")
    topic = st.text_input("Topic to study")
    num_questions = st.slider("Number of AI flashcards", 1, 100, 5)

    if st.button("Generate AI Flashcards"):
        if topic.strip():
            try:
                prompt = f"Generate {num_questions} study flashcards for '{topic}'. Format: Q: ... A: ..."
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                text = response.choices[0].message.content
                ai_flashcards = []
                # Improved parsing logic
                lines = text.split("\n")
                for line in lines:
                    if "Q:" in line and "A:" in line:
                        try:
                            parts = line.split("A:")
                            if len(parts) >= 2:
                                q = parts[0].replace("Q:", "").strip()
                                a = parts[1].strip()
                                ai_flashcards.append({"q": q, "a": a})
                        except:
                            continue

                if ai_flashcards:
                    subject_cards.extend(ai_flashcards)
                    flashcards[subject] = subject_cards
                    update_user(st.session_state.username, {"flashcards": flashcards})
                    st.success(f"{len(ai_flashcards)} AI flashcards generated and saved!")
                else:
                    st.warning("Could not parse AI response format.")
            except Exception as e:
                st.error(f"AI Error: {e}")

    question = st.text_area("Ask AI a question:")
    if st.button("Ask AI"):
        if question.strip():
            try:
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": question}],
                    temperature=0.7
                )
                answer = response.choices[0].message.content
                st.info(answer)
            except Exception as e:
                st.error(f"AI Error: {e}")