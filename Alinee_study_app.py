import random
from datetime import date

import streamlit as st

st.set_page_config(page_title="ALINEE Study App", page_icon="📚", layout="wide")

LANGUAGES = ["Python", "Java", "C++", "JavaScript", "SQL", "Go"]

CHEAT_SHEETS = {
    "Python": """
### Python Cheat Sheet
```python
# variables
name = "ALINEE"

# function
def greet(user: str) -> str:
    return f"Hello, {user}!"

# loop
for i in range(3):
    print(i)
```
- Uses indentation for blocks.
- Dynamic typing and clean syntax.
""",
    "Java": """
### Java Cheat Sheet
```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello Java");
    }
}
```
- Class-based and statically typed.
- Compile to JVM bytecode.
""",
    "C++": """
### C++ Cheat Sheet
```cpp
#include <iostream>
using namespace std;

int main() {
    cout << "Hello C++" << endl;
    return 0;
}
```
- Compiled, high performance.
- STL includes `vector`, `map`, `string`.
""",
    "JavaScript": """
### JavaScript Cheat Sheet
```javascript
const greet = (user) => {
  console.log(`Hello ${user}`);
};
```
- Runs in browser and Node.js.
- `let` and `const` are preferred over `var`.
""",
    "SQL": """
### SQL Cheat Sheet
```sql
SELECT name, score
FROM students
WHERE score >= 80
ORDER BY score DESC;
```
- `SELECT` reads rows.
- `JOIN` combines tables.
- `GROUP BY` aggregates data.
""",
    "Go": """
### Go Cheat Sheet
```go
package main
import "fmt"

func main() {
    fmt.Println("Hello Go")
}
```
- Simple syntax and fast compilation.
- Great for backend services and concurrency.
""",
}

LANGUAGE_FACTS = {
    "Python": {"func": "def", "comment": "#", "runtime": "Interpreted", "ext": ".py"},
    "Java": {"func": "public static", "comment": "//", "runtime": "Compiled to bytecode", "ext": ".java"},
    "C++": {"func": "int", "comment": "//", "runtime": "Compiled", "ext": ".cpp"},
    "JavaScript": {"func": "function", "comment": "//", "runtime": "Interpreted/JIT", "ext": ".js"},
    "SQL": {"func": "CREATE PROCEDURE", "comment": "--", "runtime": "Query language", "ext": ".sql"},
    "Go": {"func": "func", "comment": "//", "runtime": "Compiled", "ext": ".go"},
}
def build_question_bank(lang):


def init_state() -> None:
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



def get_questions():
    questions = []

    return questions


def next_question(lang: str) -> dict | None:
    data = st.session_state.progress[lang]
    if not data["remaining"]:
        data["current"] = None
        return None
    chosen = random.choice(data["remaining"])
    data["current"] = chosen
    return get_question(lang, chosen)


def dashboard() -> None:
    st.title("📊 Learning Dashboard")
    total_attempted = sum(st.session_state.progress[l]["attempted"] for l in LANGUAGES)
    total_correct = sum(st.session_state.progress[l]["correct"] for l in LANGUAGES)
    total_questions = len(LANGUAGES) * 100
    completion = int((total_attempted / total_questions) * 100) if total_questions else 0
    accuracy = int((total_correct / total_attempted) * 100) if total_attempted else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Languages", len(LANGUAGES))
    c2.metric("Questions Attempted", total_attempted)
    c3.metric("Accuracy", f"{accuracy}%")
    c4.metric("Overall Completion", f"{completion}%")

    st.progress(completion, text=f"Course completion: {completion}%")

    st.subheader("Per-language status")
    for lang in LANGUAGES:
        stats = st.session_state.progress[lang]
        lang_completion = int((stats["attempted"] / 100) * 100)
        lang_accuracy = int((stats["correct"] / stats["attempted"]) * 100) if stats["attempted"] else 0
        st.write(f"**{lang}** — completion: {lang_completion}%, accuracy: {lang_accuracy}%")
        st.progress(lang_completion)


def quizzes() -> None:
    st.title("🧠 Smart Quiz Arena")
    lang = st.selectbox("Choose language", LANGUAGES)
    data = st.session_state.progress[lang]

    st.caption(
        f"{lang}: {data['attempted']}/100 attempted • {data['correct']} correct • {len(data['remaining'])} left"
    )

    if data["current"] is None:
        question = next_question(lang)
    else:
        question = get_question(lang, data["current"])

    if question is None:
        st.success("Amazing! You completed all 100 questions for this language with no repeats.")
        if st.button("Reset this language quiz"):
            st.session_state.progress[lang] = {
                "remaining": [q["id"] for q in st.session_state.question_bank[lang]],
                "current": None,
                "attempted": 0,
                "correct": 0,
                "history": [],
            }
            st.rerun()
        return

    st.markdown(f"### {question['question']}")
    selected = st.radio("Pick your answer", question["options"], key=f"answer_{question['id']}")

    if st.button("Submit answer", type="primary"):
        correct = selected == question["answer"]
        data["attempted"] += 1
        data["correct"] += int(correct)
        data["remaining"].remove(question["id"])
        data["history"].append(
            {
                "question": question["question"],
                "selected": selected,
                "correct_answer": question["answer"],
                "result": "✅ Correct" if correct else "❌ Incorrect",
            }
        )
        data["current"] = None

        if correct:
            st.success("Correct! Great job.")
        else:
            st.error(f"Not quite. Correct answer: {question['answer']}")
        st.info(question["explanation"])

        if st.button("Next question"):
            st.rerun()


def cheat_sheets() -> None:
    st.title("📘 Code Cheat Sheets")
    tabs = st.tabs(LANGUAGES)
    for idx, lang in enumerate(LANGUAGES):
        with tabs[idx]:
            st.markdown(CHEAT_SHEETS[lang])


def progress_tracker() -> None:
    st.title("📈 Progress Tracker")
    rows = []
    for lang in LANGUAGES:
        stats = st.session_state.progress[lang]
        completion = int((stats["attempted"] / 100) * 100)
        accuracy = int((stats["correct"] / stats["attempted"]) * 100) if stats["attempted"] else 0
        rows.append(
            {
                "Language": lang,
                "Attempted": stats["attempted"],
                "Correct": stats["correct"],
                "Remaining": len(stats["remaining"]),
                "Completion %": completion,
                "Accuracy %": accuracy,
            }
        )

    st.dataframe(rows, use_container_width=True)

    st.subheader("Recent quiz activity")
    recent = []
    for lang in LANGUAGES:
        for item in st.session_state.progress[lang]["history"][-3:]:
            recent.append({"Language": lang, **item})
    if recent:
        st.dataframe(recent[::-1], use_container_width=True)
    else:
        st.info("No quiz activity yet. Start answering questions to build your history.")


def special_features() -> None:
    st.title("✨ Special Features")

    st.subheader("Daily Challenge")
    challenge_lang = LANGUAGES[date.today().toordinal() % len(LANGUAGES)]
    challenge_q = st.session_state.question_bank[challenge_lang][date.today().toordinal() % 100]
    st.write(f"Today's language: **{challenge_lang}**")
    st.write(challenge_q["question"])

    user_answer = st.text_input(
        "Type your daily challenge answer",
        key=f"daily_answer_{challenge_q['id']}",
        placeholder="Enter your answer here...",
    )
    if st.button("Check Daily Challenge Answer"):
        if not user_answer.strip():
            st.warning("Please type an answer before checking.")
        elif user_answer.strip() == challenge_q["answer"]:
            st.success("✅ Correct! Great job on today's challenge.")
        else:
            st.error(f"❌ Incorrect. Correct answer: {challenge_q['answer']}")

    st.subheader("Adaptive Recommendation")
    weakest = None
    weakest_acc = 101
    for lang in LANGUAGES:
        stats = st.session_state.progress[lang]
        if stats["attempted"] == 0:
            continue
        acc = int((stats["correct"] / stats["attempted"]) * 100)
        if acc < weakest_acc:
            weakest_acc = acc
            weakest = lang

    if weakest:
        st.warning(f"Focus suggestion: Review **{weakest}** (current accuracy: {weakest_acc}%).")
    else:
        st.info("Once you answer some questions, we will recommend your best next focus area.")

    st.subheader("Achievement Badges")
    total_correct = sum(st.session_state.progress[l]["correct"] for l in LANGUAGES)
    badges = []
    if total_correct >= 25:
        badges.append("🥉 Bronze Solver")
    if total_correct >= 75:
        badges.append("🥈 Silver Solver")
    if total_correct >= 150:
        badges.append("🥇 Gold Solver")
    if all(st.session_state.progress[l]["attempted"] >= 100 for l in LANGUAGES):
        badges.append("🏆 Polyglot Master")

    st.write(", ".join(badges) if badges else "No badges yet — start quizzing to unlock achievements!")


def main() -> None:
    init_state()

    st.sidebar.title("ALINEE Study App")
    st.sidebar.caption("User-friendly coding learning dashboard")
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Quizzes", "Cheat Sheets", "Progress Tracker", "Special Features"],
    )

    if page == "Dashboard":
        dashboard()
    elif page == "Quizzes":
        quizzes()
    elif page == "Cheat Sheets":
        cheat_sheets()
    elif page == "Progress Tracker":
        progress_tracker()
    else:
        special_features()


if __name__ == "__main__":
    main()
