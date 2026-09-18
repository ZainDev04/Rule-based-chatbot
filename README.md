# Nova, a rule-based chatbot

DecodeLabs Industrial Training Kit, Artificial Intelligence, Project 1.

Live demo: [zaindev04.pythonanywhere.com](https://zaindev04.pythonanywhere.com)

Nova is a chatbot that answers with rules instead of a model. Every reply can be traced to a line in `intents.json`, which is the point of the project: before building systems that learn, build one you can fully explain. The terminal version is the graded deliverable. The web version wraps the same class in a small Flask API and shows the matching trace next to every reply.

![tests](https://github.com/ZainDev04/Rule-based-chatbot/actions/workflows/tests.yml/badge.svg)

## What it does

- Understands 34 intents: greetings, small talk, the time and date, arithmetic, jokes, coin flips, remembering your name, and an honest fallback when nothing matches.
- Matches input in four tiers, cheapest first: exact dictionary lookup, regex patterns with entity extraction, keyword search inside longer sentences, and fuzzy matching for typos.
- Keeps per-session memory: your name, the last reply (so "say that again" works), and the turn count.
- Normalises chat shorthand before matching, so "whats ur name" and "What's your name?" hit the same rule.
- Returns a confidence score and the tier that matched, which the web interface displays on every message.
- Has no dependencies outside the Python standard library. Flask is only needed for the web version.

## How a message is handled

```
"Hey Nova, whats ur name??"
        |
        v
  sanitize_input()      -> "hey what's your name"
        |                  lowercase, strip punctuation, expand shorthand,
        |                  drop filler words such as the bot's own name
        v
  match_intent()
    1. exact    intent_map["hey what's your name"]      -> miss
    2. pattern  regexes for names and arithmetic         -> miss
    3. keyword  longest known phrase inside the text     -> "what's your name"  (intent: name, 0.82)
    4. fuzzy    difflib against every phrase             -> (not reached)
        |
        v
  handler (if the intent needs one: time, date, math, memory)
        |
        v
  pick a response template, fill {bot_name}, {user_name}, {time} ...
        |
        v
  "I'm Nova, a rule-based chatbot."
```

Each tier costs more than the one before it, and each is tried only if the previous one missed. The exact tier is a single dictionary lookup, so the common case stays O(1) no matter how many intents are loaded. Pattern-tier regexes carry named groups that become entities (`{"name": "zain"}`, `{"expr": "12 * 7"}`). The keyword tier prefers the longest phrase it finds, so "hi what time is it" resolves to `time` and not `greeting`. The fuzzy tier uses `difflib` with a 0.8 cutoff and never looks at words shorter than four letters, because "hi" is one edit away from too many things.

Arithmetic is evaluated by walking a Python AST with a whitelist of number and operator nodes. `eval()` is never called.

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/ZainDev04/Rule-based-chatbot.git
cd Rule-based-chatbot
python chatbot.py
```

Useful flags:

```bash
python chatbot.py --debug             # print the match trace after every reply
python chatbot.py --log chat.jsonl    # append every turn to a JSON lines file
python chatbot.py --list-intents      # print the loaded intents and exit
python chatbot.py --name Ada          # rename the bot
```

A session with `--debug`:

```
Nova: Hello! I'm Nova, a rule-based chatbot with 34 intents.
Nova: Type 'help' to see what I can do, or 'exit' to leave.

You: helo there
  [trace] cleaned='helo there' tier=fuzzy intent=greeting confidence=0.95 phrase='hello there' entities={}
Nova: Hi there! What can I do for you?
You: my name is zain
  [trace] cleaned='my name is zain' tier=pattern intent=remember_name confidence=0.95 phrase='my name is zain' entities={'name': 'zain'}
Nova: Nice to meet you, Zain! I'll remember that.
You: what is 2 to the power of 10
  [trace] cleaned='what is 2 to the power of 10' tier=pattern intent=math confidence=0.95 phrase='what is 2 to the power of 10' entities={'expr': '2 to the power of 10'}
Nova: 2 to the power of 10 = 1024
You: bye
Nova: Goodbye! Have a great day.
```

## Web interface

```bash
pip install -r requirements.txt
cd web
python app.py
```

Open `http://127.0.0.1:5000`. The page shows the chat on the left and a match trace on the right (a bottom sheet on phones): raw and cleaned input, the tier that matched, the intent, the matched phrase, a confidence meter, extracted entities and server processing time. The pipeline diagram lights up the step that produced the answer.

The interface follows the Renovast design tokens (Helvetica Neue, 16px base, 4px radius, green accent, black header and footer) and is documented in [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md). It works from 320px wide upwards, supports light and dark themes, and every control is reachable with the keyboard.

### API

| Method | Route | Body | Returns |
|---|---|---|---|
| POST | `/api/chat` | `{"message": "hello", "session_id": "..."}` | reply, intent, tier, confidence, cleaned input, entities, session state, processing time |
| POST | `/api/reset` | `{"session_id": "..."}` | `{"reset": true, "existed": bool}` |
| GET | `/api/intents` | | count and a summary of every intent |
| GET | `/api/health` | | uptime, sessions, requests served, fallback rate |

Messages over 500 characters return 413, malformed bodies return 400, and more than 60 requests a minute from one client return 429. Errors are JSON with a `code` and a `message`. Sessions live in memory, expire after an hour idle, and are capped at 500.

```bash
curl -s -X POST http://127.0.0.1:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hey what time is it", "session_id": "demo0001"}'
```

## Project structure

```
rule-based-chatbot/
├── chatbot.py              engine and terminal runner
├── intents.json            knowledge base: 34 intents, patterns, responses, normalisations
├── requirements.txt        Flask and pytest
├── tests/
│   ├── test_sanitize.py    input normalisation
│   ├── test_matching.py    each matching tier
│   ├── test_responses.py   handlers, memory, safe arithmetic, legacy helpers
│   └── test_api.py         Flask routes, validation, sessions
├── web/
│   ├── app.py              Flask application factory and API
│   ├── wsgi.py             entry point for PythonAnywhere
│   ├── templates/index.html
│   └── static/style.css, script.js
├── docs/DESIGN_SYSTEM.md   tokens, component states, accessibility criteria
└── .github/workflows/tests.yml
```

## Tests

```bash
pytest -q
```

101 tests run in under a second. They cover sanitisation, every tier with positive and negative cases, the safe evaluator (including inputs that try to escape it), session isolation, template filtering when the user's name is unknown, and every API route. One test walks every intent and checks that each of its own examples still reaches it, so a typo in `intents.json` fails CI.

## Adding an intent

Edit `intents.json`. A static intent needs a name, a description, patterns and responses:

```json
{
  "name": "farewell_soon",
  "description": "The user says they will leave shortly.",
  "patterns": ["i will go soon", "leaving in a bit"],
  "exact_only": ["soon"],
  "responses": ["No rush. I'll be here."]
}
```

`patterns` take part in every tier. `exact_only` phrases match only when they are the whole message, which is how short words such as "good" avoid matching inside unrelated sentences. Responses may use `{bot_name}` and `{user_name}`; templates that need a name are skipped until the user has given one.

An intent that needs computed data adds a `handler` name and a method on `RuleBasedChatbot` that returns the placeholder values. Pattern-tier intents add `regex` entries with named groups and, optionally, a `reject` list and a validator, which is how "i am tired" stays a mood instead of becoming a person called Tired.

## Design decisions

Why a JSON file instead of Python dictionaries: the graded version kept intents in code, so adding one meant editing logic. Moving them to data made the engine generic, made the file testable on its own, and let the web interface list intents without importing anything private.

Why four tiers instead of one big fuzzy match: fuzzy matching everything is slow and produces surprising hits. Trying the exact lookup first keeps the common path at one dictionary read, and each later tier only runs when the earlier ones fail. The tier name is returned with every reply, so the trade-off is visible instead of hidden.

Why an AST walker for arithmetic: `eval()` on user text is a remote code execution bug, even in a demo. Parsing to an AST and accepting only numbers and six operators gives the same result with no risk, and `test_safe_eval_rejects_non_arithmetic` makes sure it stays that way.

Why sessions in a dictionary: the demo runs as a single process on PythonAnywhere's free tier. A dictionary with idle expiry and a hard cap is enough. The session store is isolated behind two functions in `app.py`, so moving it to Redis is a local change.

Why the trace panel: in an interview, the interesting part of a rule-based bot is the matching, not the replies. Showing the tier and confidence on every message turns the demo into an explanation.

## Deploying to PythonAnywhere

1. Clone the repository into your home directory.
2. Create a virtualenv and run `pip install -r requirements.txt`.
3. In the Web tab, set the source directory to `Rule-based-chatbot/web` and point the WSGI file at `wsgi.py` (see the comment in that file for the three lines to paste).
4. Reload the app. `/api/health` should return `"status": "ok"`.

Time replies use Pakistan Standard Time (UTC+5) explicitly because the server runs in UTC.

## Limitations and next steps

- Matching is still lexical. "Could you tell me what the hour is" will fall back, because no pattern contains those words. A next step is a small embedding model in front of the fuzzy tier, used only when confidence is low.
- Context is one turn deep. Multi-turn slot filling ("book a table", "for when?") would need a state machine on top of the session.
- The knowledge base is English only. The normalisation map is the natural place to add transliterated Urdu shorthand.
- Sessions are lost on restart. Fine for a demo, not for a product.

## Author

Shaikh Muhammad Zain
AI intern, DecodeLabs (June 2026 batch)
Third-year Computer Science (AI specialisation), NED University of Engineering and Technology

MIT licence. See [LICENSE](LICENSE).
