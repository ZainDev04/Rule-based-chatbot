# Contributing

This is a personal internship project, but suggestions and fixes are welcome.

## Setup

```bash
git clone https://github.com/ZainDev04/Rule-based-chatbot.git
cd Rule-based-chatbot
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS and Linux
pip install -r requirements.txt
pytest -q
```

## Making changes

- New intents go in `intents.json`, not in `chatbot.py`. Add at least one test in `tests/test_matching.py` that proves the intent is reached, and one negative case if the phrase is short enough to appear inside other sentences.
- Engine changes must keep `get_response()` and `get_response_with_intent()` working, since the original terminal contract depends on them.
- Interface changes must follow `docs/DESIGN_SYSTEM.md`: tokens only, all seven component states, and the accessibility checks in section 4 re-run at 320px and 1280px.
- Run `pytest -q` before opening a pull request. CI runs the same suite on Python 3.10 to 3.13.

## Commit messages

Short imperative subject line, a blank line, then the reasoning if the change is not obvious. Example:

```
Add reciprocal intent for "and you?"

Users often turn "how are you" back on the bot. Without this the
message fell through to the fuzzy tier and matched "thank you".
```
