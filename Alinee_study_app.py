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
