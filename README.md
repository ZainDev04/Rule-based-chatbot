# 🤖 Rule-Based AI Chatbot

> **DecodeLabs Industrial Training Kit — Artificial Intelligence | Project 1**

🔗 **Live Demo:** [zaindev04.pythonanywhere.com](https://zaindev04.pythonanywhere.com)
📂 **Repository:** [github.com/ZainDev04/Rule-based-chatbot](https://github.com/ZainDev04/Rule-based-chatbot)

A deterministic, dictionary-driven chatbot built in Python. This project demonstrates the foundational logic that underpins every conversational AI system — control flow, input sanitization, intent matching, and graceful fallback handling — before introducing probabilistic, LLM-based approaches in later projects.

---

## 📌 Overview

Before a system can *learn* to respond intelligently, it must first be taught to respond *predictably*. This project implements a rule-based chatbot that maps user inputs to responses using explicit logic — no machine learning involved. It's the "white box" foundation referenced in modern AI guardrail systems (like NVIDIA NeMo and Llama Guard), where traceability and zero hallucination risk matter more than flexibility.

## ✨ Features

- **Continuous conversation loop** — runs indefinitely until an exit command is given
- **Input sanitization** — handles inconsistent casing, whitespace, and trailing punctuation
- **Dictionary-based intent matching** — O(1) lookups instead of long if-elif chains (see [Design Notes](#-design-notes))
- **9 intents supported** — exceeds the 5-intent minimum requirement
- **Dynamic responses** — randomized phrasing per intent so the bot doesn't sound robotic
- **Real-time responses** — e.g., correctly answers "what time is it"
- **Graceful fallback** — clear, varied responses when input isn't recognized
- **Clean exit handling** — multiple exit keywords (`exit`, `quit`, `bye`, `goodbye`, `stop`)

## 🧠 Supported Intents

| Intent | Example Triggers |
|---|---|
| Greeting | "hello", "hi", "good morning" |
| Wellbeing | "how are you" |
| Identity | "what is your name", "who are you" |
| Time | "what time is it" |
| Gratitude | "thank you", "thanks" |
| Help | "help", "what can you do" |
| Creator | "who made you" |
| Mood (positive) | "i am good", "doing great" |
| Mood (negative) | "i am sad", "i am tired" |

## 🛠 Tech Stack

- **Language:** Python 3
- **Libraries:** `random`, `datetime` (both from the standard library — no external dependencies)

## 🚀 Getting Started

### Prerequisites
- Python 3.7 or higher

### Run it locally

```bash
git clone https://github.com/ZainDev04/Rule-based-chatbot.git
cd Rule-based-chatbot
python chatbot.py
```

### Example session

```
Nova: Hello! I'm Nova, a rule-based chatbot.
Nova: Type 'exit', 'quit', or 'bye' anytime to end our chat.

You: hello
Nova: Hey! Good to see you.

You: what's your name
Nova: I'm Nova, your friendly rule-based assistant.

You: what time is it
Nova: The current time is 02:45 PM.

You: thanks
Nova: Anytime! Happy to help.

You: exit
Nova: Goodbye! Have a great day. 👋
```

## 🏗 Design Notes

A naive implementation of this problem reaches for a long `if/elif` ladder. That approach has two problems: **O(n) lookup time** (every check is compared sequentially) and **high technical debt** (every new intent adds another fragile branch).

This implementation instead uses a **dictionary as the knowledge base**, giving:

- **O(1) intent lookups** regardless of how many intents are added
- A single `intent_map` that lets multiple phrasings ("hi", "hello", "hey") resolve to one canonical intent, keeping the knowledge base itself clean
- `dict.get()`-style fallback handling, combining lookup and default-response logic in one atomic step

```python
reply = responses.get(user_input, "I do not understand.")
```

This mirrors the architecture used in real-world AI guardrail systems, where a deterministic rule layer sits in front of a probabilistic model to filter, validate, or short-circuit responses before they ever reach the LLM.

## 📂 Project Structure

```
rule-based-chatbot/
├── chatbot.py              # Main chatbot implementation (terminal version - the core submission)
├── README.md                # Project documentation
└── web/                      # Bonus: browser-based UI for the same chatbot
    ├── app.py                 # Flask server wrapping RuleBasedChatbot
    ├── requirements.txt
    ├── templates/
    │   └── index.html
    └── static/
        ├── style.css
        └── script.js
```

## 🖥 Bonus: Web UI

The core requirement for this project is the terminal chatbot in `chatbot.py`. As an extension, a browser-based interface is included in the `web/` folder, and deployed live at **[zaindev04.pythonanywhere.com](https://zaindev04.pythonanywhere.com)**. It reuses the exact same `RuleBasedChatbot` class — no logic is duplicated — and adds a small Flask layer on top so the chatbot can be used from a browser.

A nice side effect: each bot reply in the UI shows which intent was matched (e.g. `[greeting]`, `[time]`, `[fallback]`), making the dictionary-lookup logic visible and easy to explain.

**To run the web version locally:**

```bash
cd web
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## 🔮 Possible Extensions

- Expand the knowledge base with more intents and synonyms
- Add nested conditions for multi-turn context (e.g., remembering the user's name)
- Layer this rule-based system in front of an LLM as a guardrail/router (rule match → instant response; no match → pass to LLM)
- Add unit tests for `sanitize_input()` and `match_intent()`

## 👤 Author

**Shaikh Muhammad Zain**
AI Intern, DecodeLabs (June 2026 Batch)
Third-year Computer Science (AI Specialization), NED University of Engineering & Technology

---

*This project was completed as part of the DecodeLabs Industrial Training Kit — Artificial Intelligence Internship Program.*