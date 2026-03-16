import random
from datetime import date
from typing import Any

import streamlit as st

st.set_page_config(page_title="ALINEE Study App", page_icon="📚", layout="wide")

LANGUAGES = ["Python", "Java", "C++", "JavaScript", "SQL", "Go"]

CHEAT_SHEETS = {
    "Python": """
### Python Cheat Sheet
```python
# variables
name = "ALINEE"

def greet(user: str) -> str:
    return f"Hello, {user}!"

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
    "Python": {
        "func": "def",
        "comment": "#",
        "runtime": "Interpreted",
        "ext": ".py",
        "creator": "Guido van Rossum",
    },
    "Java": {
        "func": "public static",
        "comment": "//",
        "runtime": "Compiled to bytecode",
        "ext": ".java",
        "creator": "James Gosling",
    },
    "C++": {
        "func": "int",
        "comment": "//",
        "runtime": "Compiled",
        "ext": ".cpp",
        "creator": "Bjarne Stroustrup",
    },
    "JavaScript": {
        "func": "function",
        "comment": "//",
        "runtime": "Interpreted/JIT",
        "ext": ".js",
        "creator": "Brendan Eich",
    },
    "SQL": {
        "func": "CREATE PROCEDURE",
        "comment": "--",
        "runtime": "Query language",
        "ext": ".sql",
        "creator": "Donald Chamberlin and Raymond Boyce",
    },
    "Go": {
        "func": "func",
        "comment": "//",
        "runtime": "Compiled",
        "ext": ".go",
        "creator": "Robert Griesemer, Rob Pike, and Ken Thompson",
    },
}

TOPICS = {
    "Python": ["Functions", "Lists", "Dictionaries", "Loops", "Modules", "Classes", "Exceptions", "Comprehensions", "Typing", "File I/O"],
    "Java": ["Classes", "Objects", "Interfaces", "Inheritance", "Collections", "Exceptions", "Threads", "Generics", "JVM", "Streams"],
    "C++": ["Pointers", "References", "Templates", "STL", "OOP", "Memory", "RAII", "Namespaces", "Vectors", "Algorithms"],
    "JavaScript": ["DOM", "Promises", "Closures", "Arrays", "Objects", "Events", "Async/Await", "Modules", "Scope", "Fetch API"],
    "SQL": ["SELECT", "JOIN", "GROUP BY", "HAVING", "ORDER BY", "INDEX", "PRIMARY KEY", "FOREIGN KEY", "Transactions", "Views"],
    "Go": ["Goroutines", "Channels", "Structs", "Interfaces", "Slices", "Maps", "Error Handling", "Packages", "Testing", "Concurrency"],
}


def shuffled_options(correct: str, pool: list[str], seed: int) -> list[str]:
    rnd = random.Random(seed)
    options = [correct]
    for choice in pool:
        if choice != correct and choice not in options:
            options.append(choice)
        if len(options) == 4:
            break
    while len(options) < 4:
        options.append(f"Option {len(options)+1}")
    rnd.shuffle(options)
    return options


def build_question_bank(lang: str) -> list[dict[str, Any]]:
    facts = LANGUAGE_FACTS[lang]
    other_comments = [LANGUAGE_FACTS[l]["comment"] for l in LANGUAGES if l != lang]
    other_exts = [LANGUAGE_FACTS[l]["ext"] for l in LANGUAGES if l != lang]
    other_runtime = [LANGUAGE_FACTS[l]["runtime"] for l in LANGUAGES if l != lang]
    other_func = [LANGUAGE_FACTS[l]["func"] for l in LANGUAGES if l != lang]
    topics = TOPICS[lang]

    questions: list[dict[str, Any]] = []
    qid = 1
    for topic in topics:
        for variant in range(10):
            mode = variant % 5
            if mode == 0:
                answer = facts["comment"]
                options = shuffled_options(answer, other_comments, qid)
                question = f"[{topic}] In {lang}, what symbol starts a single-line comment?"
                explanation = f"{lang} uses `{answer}` for single-line comments."
            elif mode == 1:
                answer = facts["ext"]
                options = shuffled_options(answer, other_exts, qid)
                question = f"[{topic}] Which file extension is standard for {lang} source files?"
                explanation = f"The standard source file extension for {lang} is `{answer}`."
            elif mode == 2:
                answer = facts["runtime"]
                options = shuffled_options(answer, other_runtime, qid)
                question = f"[{topic}] How is {lang} generally executed?"
                explanation = f"{lang} is generally described as: {answer}."
            elif mode == 3:
                answer = facts["func"]
                options = shuffled_options(answer, other_func, qid)
                question = f"[{topic}] Which keyword/pattern is commonly used to declare functions in {lang}?"
                explanation = f"A common function declaration keyword/pattern in {lang} is `{answer}`."
            else:
                answer = facts["creator"]
                creator_pool = [LANGUAGE_FACTS[l]["creator"] for l in LANGUAGES if l != lang]
                options = shuffled_options(answer, creator_pool, qid)
                question = f"[{topic}] Who is most associated with creating {lang}?"
                explanation = f"{lang} is most associated with {answer}."

            questions.append(
                {
                    "id": f"{lang}-{qid}",
                    "question": f"Q{qid:03d} {question}",
                    "options": options,
                    "answer": answer,
                    "explanation": explanation,
                }
            )
            qid += 1
    return questions


def get_question(lang: str, qid: str) -> dict[str, Any] | None:
    return next((q for q in st.session_state.question_bank[lang] if q["id"] == qid), None)


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

    if "daily_challenge" not in st.session_state:
        all_ids = [(lang, q["id"]) for lang in LANGUAGES for q in st.session_state.question_bank[lang]]
        random.shuffle(all_ids)
        st.session_state.daily_challenge = {
            "date": date.today().isoformat(),
            "remaining": all_ids[:30],
            "score": 0,
            "attempted": 0,
        }


def next_question(lang: str) -> dict[str, Any] | None:
    data = st.session_state.progress[lang]
    if not data["remaining"]:
        data["current"] = None
        return None

    chosen = random.choice(data["remaining"])
    data["current"] = chosen
    return get_question(lang, chosen)


def reset_language(lang: str) -> None:
    st.session_state.progress[lang] = {
        "remaining": [q["id"] for q in st.session_state.question_bank[lang]],
        "current": None,
        "attempted": 0,
        "correct": 0,
        "history": [],
    }


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

    st.caption(f"{lang}: {data['attempted']}/100 attempted • {data['correct']} correct • {len(data['remaining'])} left")

    question = next_question(lang) if data["current"] is None else get_question(lang, data["current"])

    if question is None:
        st.success("Amazing! You completed all 100 questions for this language with no repeats.")
        if st.button("Reset this language quiz"):
            reset_language(lang)
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
        st.rerun()

    if data["history"]:
        with st.expander("Recent answers"):
            st.dataframe(data["history"][-8:], use_container_width=True)


def cheat_sheets() -> None:
    st.title("📘 Code Cheat Sheets")
    lang = st.selectbox("Pick a language", LANGUAGES, key="cheat_sheet_lang")
    st.markdown(CHEAT_SHEETS[lang])


def special_features() -> None:
    st.title("✨ Special Features")

    tab1, tab2 = st.tabs(["🎯 Daily Mixed Challenge", "🧪 Code Recall Challenge"])

    with tab1:
        st.write("Answer mixed questions from all technologies. Questions are not repeated once answered.")
        dc = st.session_state.daily_challenge
        st.caption(f"Date: {dc['date']} • Attempted: {dc['attempted']} • Score: {dc['score']} • Remaining: {len(dc['remaining'])}")

        if dc["remaining"]:
            lang, qid = dc["remaining"][0]
            q = get_question(lang, qid)
            st.markdown(f"**{lang}** — {q['question']}")
            pick = st.radio("Your answer", q["options"], key=f"daily_{qid}")
            if st.button("Submit daily answer"):
                dc["attempted"] += 1
                if pick == q["answer"]:
                    dc["score"] += 1
                    st.success("Great! Correct answer.")
                else:
                    st.error(f"Incorrect. Correct answer: {q['answer']}")
                dc["remaining"].pop(0)
                st.rerun()
        else:
            st.success("Daily challenge complete! Come back tomorrow for a refreshed set.")

    with tab2:
        st.write("Type your answer for quick recall drills.")
        lang = st.selectbox("Language", LANGUAGES, key="recall_lang")
        prompts = {
            "comment": f"Type the single-line comment symbol for {lang}.",
            "ext": f"Type the standard file extension for {lang} source files.",
            "func": f"Type the common function keyword/pattern in {lang}.",
        }
        recall_type = st.radio("Prompt type", list(prompts.keys()), format_func=lambda x: x.upper())
        st.info(prompts[recall_type])
        user_input = st.text_input("Your answer")
        if st.button("Check recall answer"):
            expected = LANGUAGE_FACTS[lang][recall_type].strip().lower()
            if user_input.strip().lower() == expected:
                st.success("Excellent memory! ✅")
            else:
                st.warning(f"Almost there. Expected answer: {LANGUAGE_FACTS[lang][recall_type]}")


def main() -> None:
    init_state()

    st.sidebar.title("📚 ALINEE Study App")
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Progress Tracker", "Cheat Sheets", "Quizzes", "Special Features"],
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("Reset all progress"):
        for lang in LANGUAGES:
            reset_language(lang)
        st.session_state.daily_challenge = {
            "date": date.today().isoformat(),
            "remaining": random.sample(
                [(l, q["id"]) for l in LANGUAGES for q in st.session_state.question_bank[l]],
                k=30,
            ),
            "score": 0,
            "attempted": 0,
        }
        st.sidebar.success("All progress reset.")
        st.rerun()

    if page == "Dashboard":
        dashboard()
    elif page == "Progress Tracker":
        dashboard()
    elif page == "Cheat Sheets":
        cheat_sheets()
    elif page == "Quizzes":
        quizzes()
    else:
        special_features()


if __name__ == "__main__":
    main()
