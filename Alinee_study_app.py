import streamlit as st
import firebase_admin
import hashlib
import json
from datetime import datetime
from firebase_admin import credentials, firestore
from openai import OpenAI

st.set_page_config(page_title="ALINEE Study Hub", page_icon="📚", layout="wide")

SUBJECTS = ["Math", "Science", "History", "English", "Geography"]

# ---------------- SESSION ---------------- #

def init_state():
    defaults = {
        "logged_in": False,
        "username": "",
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------- FIREBASE ---------------- #

def init_firebase():

    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)

    return firestore.client()


# ---------------- OPENAI ---------------- #

def init_openai():

    key = st.secrets.get("OPENAI_API_KEY")

    if not key:
        return None

    return OpenAI(api_key=key)


def ai_chat(ai, messages):

    res = ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return res.choices[0].message.content


# ---------------- SECURITY ---------------- #

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(raw, stored):
    return stored == hash_password(raw)


# ---------------- DATABASE ---------------- #

def get_user(db, username):

    doc = db.collection("users").document(username).get()

    if doc.exists:
        return doc.to_dict()

    return None


def create_user(db, username, password):

    ref = db.collection("users").document(username)

    if ref.get().exists:
        return False

    ref.set({
        "password": hash_password(password),
        "flashcards": {},
        "notes": {},
        "scores": {},
        "stats": {
            "study_streak": 0
        }
    })

    return True


def update_user(db, username, data):

    db.collection("users").document(username).set(data, merge=True)


# ---------------- LOGIN ---------------- #

def login_signup(db):

    st.title("📚 ALINEE Study Hub")

    mode = st.radio("Account", ["Login", "Sign Up"])

    username = st.text_input("Username")

    password = st.text_input("Password", type="password")

    if mode == "Sign Up":

        if st.button("Create Account"):

            if create_user(db, username, password):

                st.success("Account created")

            else:

                st.error("Username exists")

    else:

        if st.button("Login"):

            user = get_user(db, username)

            if user and verify_password(password, user["password"]):

                st.session_state.logged_in = True
                st.session_state.username = username

                st.rerun()

            else:

                st.error("Invalid login")


# ---------------- AI FLASHCARDS ---------------- #

def generate_ai_flashcards(ai, topic, count):

    prompt = f"""
Create {count} flashcards about {topic}.

Return JSON like:
[
{{"question":"...","answer":"..."}}
]
"""

    res = ai_chat(ai, [
        {"role":"system","content":"You are a study assistant."},
        {"role":"user","content":prompt}
    ])

    try:
        return json.loads(res)
    except:
        return []


# ---------------- AI QUIZ ---------------- #

def generate_ai_quiz(ai, topic, count):

    prompt = f"""
Create {count} quiz questions about {topic}.

Return JSON:

[
{{
"question":"...",
"options":["A","B","C","D"],
"answer":"..."
}}
]
"""

    res = ai_chat(ai, [
        {"role":"system","content":"You generate study quizzes"},
        {"role":"user","content":prompt}
    ])

    try:
        return json.loads(res)
    except:
        return []


# ---------------- PROGRESS ---------------- #

def update_streak(user):

    stats = user.get("stats", {})

    today = datetime.now().date()

    last = stats.get("last_study")

    if last:

        last = datetime.fromisoformat(last).date()

        if (today - last).days == 1:

            stats["study_streak"] += 1

    stats["last_study"] = today.isoformat()

    return stats


# ---------------- MAIN ---------------- #

def main():

    init_state()

    db = init_firebase()

    ai = init_openai()

    if not st.session_state.logged_in:

        login_signup(db)

        st.stop()

    username = st.session_state.username

    user = get_user(db, username)

    st.sidebar.title("ALINEE Study Hub")

    subject = st.sidebar.selectbox("Subject", SUBJECTS)

    menu = st.sidebar.radio(
        "Menu",
        [
            "Dashboard",
            "AI Assistant",
            "Flashcards",
            "AI Quiz",
            "Notes",
            "Progress"
        ]
    )

    if st.sidebar.button("Logout"):

        st.session_state.logged_in = False
        st.rerun()

    flashcards = user.get("flashcards", {})
    notes = user.get("notes", {})
    scores = user.get("scores", {})

    subject_cards = flashcards.get(subject, [])

    # ---------------- DASHBOARD ---------------- #

    if menu == "Dashboard":

        st.title("📊 Dashboard")

        st.metric("Flashcards", len(subject_cards))

        st.metric("Best Score", scores.get(subject, 0))

    # ---------------- AI ASSISTANT ---------------- #

    if menu == "AI Assistant":

        st.title("🤖 AI Tutor")

        question = st.text_area("Ask a question")

        if st.button("Ask AI"):

            answer = ai_chat(ai, [
                {"role":"system","content":"You are a helpful tutor"},
                {"role":"user","content":question}
            ])

            st.success(answer)

    # ---------------- FLASHCARDS ---------------- #

    if menu == "Flashcards":

        st.title("📇 Flashcards")

        q = st.text_input("Question")

        a = st.text_input("Answer")

        if st.button("Save Flashcard"):

            subject_cards.append({"q":q,"a":a})

            flashcards[subject] = subject_cards

            update_user(db, username, {"flashcards":flashcards})

            st.success("Saved")

            st.rerun()

        for c in subject_cards:

            st.write("Q:", c["q"])
            st.write("A:", c["a"])

            st.divider()

    # ---------------- AI FLASHCARDS ---------------- #

    if menu == "AI Quiz":

        st.title("📝 AI Quiz Generator")

        topic = st.text_input("Quiz topic")

        if st.button("Generate Quiz"):

            quiz = generate_ai_quiz(ai, topic, 5)

            score = 0

            answers = {}

            for i, q in enumerate(quiz):

                answers[i] = st.radio(q["question"], q["options"], key=i)

            if st.button("Submit Quiz"):

                for i, q in enumerate(quiz):

                    if answers[i] == q["answer"]:
                        score += 1

                scores[subject] = max(score, scores.get(subject,0))

                update_user(db, username, {"scores":scores})

                st.success(f"Score {score}/{len(quiz)}")

    # ---------------- NOTES ---------------- #

    if menu == "Notes":

        st.title("🗒️ Notes")

        txt = st.text_area("Notes", value=notes.get(subject,""))

        if st.button("Save Notes"):

            notes[subject] = txt

            update_user(db, username, {"notes":notes})

            st.success("Saved")

    # ---------------- PROGRESS ---------------- #

    if menu == "Progress":

        st.title("📈 Progress")

        stats = update_streak(user)

        st.metric("Study Streak 🔥", stats.get("study_streak",0))

        st.write("Flashcards:", sum(len(flashcards.get(s,[])) for s in SUBJECTS))

        st.write("Notes subjects:", len([n for n in notes.values() if n]))


if __name__ == "__main__":
    main()
