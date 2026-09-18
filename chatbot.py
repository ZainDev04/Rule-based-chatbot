"""
Rule-Based AI Chatbot
---------------------
DecodeLabs | Industrial Training Kit - Artificial Intelligence | Project 1

A deterministic chatbot. Every reply can be traced back to a rule in
intents.json, which makes the whole thing explainable: no model weights,
no network calls, no guessing.

Pipeline for each message:

    raw text -> sanitize -> match (exact, pattern, keyword, fuzzy) -> handler -> reply

Run it in the terminal:

    python chatbot.py
    python chatbot.py --debug          # print the match trace for each turn
    python chatbot.py --log chat.jsonl # append every turn to a JSON lines file

Author: Shaikh Muhammad Zain
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import operator
import random
import re
import string
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

# Pakistan Standard Time is UTC+5 with no daylight saving, so a fixed offset
# is correct and avoids pulling in a timezone library. Servers such as
# PythonAnywhere run in UTC, so "what time is it" would otherwise be wrong.
PKT = timezone(timedelta(hours=5))

DEFAULT_INTENTS_PATH = Path(__file__).with_name("intents.json")

# Words shorter than this are never fuzzy-matched. "hi" is too close to "his".
FUZZY_MIN_WORD_LENGTH = 4


# --------------------------------------------------------------------------
# Data containers
# --------------------------------------------------------------------------

@dataclass
class MatchResult:
    """What the matcher found for one cleaned message."""

    intent: Optional[str]
    tier: str                      # exact | pattern | keyword | fuzzy | none
    confidence: float              # 0.0 to 1.0
    matched_phrase: Optional[str] = None
    entities: dict = field(default_factory=dict)


@dataclass
class BotReply:
    """Everything the engine knows about one turn. The web API returns this as JSON."""

    text: str
    intent: str
    tier: str
    confidence: float
    raw_input: str
    cleaned_input: str
    matched_phrase: Optional[str] = None
    entities: dict = field(default_factory=dict)
    session_ended: bool = False

    def to_dict(self) -> dict:
        return {
            "response": self.text,
            "intent": self.intent,
            "tier": self.tier,
            "confidence": self.confidence,
            "raw_input": self.raw_input,
            "cleaned_input": self.cleaned_input,
            "matched_phrase": self.matched_phrase,
            "entities": self.entities,
            "session_ended": self.session_ended,
        }


class Session:
    """Per-conversation memory. The terminal uses one; the web app keeps one per browser."""

    MAX_HISTORY = 100

    def __init__(self) -> None:
        self.user_name: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.last_reply: Optional[str] = None
        self.turn_count = 0
        self.started_at = datetime.now(PKT)
        self.last_active = self.started_at
        self.history: list[dict] = []

    def record(self, reply: BotReply) -> None:
        self.turn_count += 1
        self.last_active = datetime.now(PKT)
        # "repeat" should echo the reply before it, so only real replies are stored.
        if reply.intent not in ("repeat", "empty"):
            self.last_reply = reply.text
        self.last_intent = reply.intent
        self.history.append({"user": reply.raw_input, "bot": reply.text, "intent": reply.intent})
        if len(self.history) > self.MAX_HISTORY:
            self.history.pop(0)

    def to_dict(self) -> dict:
        return {
            "user_name": self.user_name,
            "last_intent": self.last_intent,
            "last_reply": self.last_reply,
            "turn_count": self.turn_count,
            "started_at": self.started_at.isoformat(),
        }

    def restore(self, data: dict) -> None:
        """Load state that a client sent back. Used on hosts where each request
        may hit a different process, so the browser carries its own memory."""
        if not isinstance(data, dict):
            return
        name = data.get("user_name")
        self.user_name = name[:40] if isinstance(name, str) and name.strip() else None
        intent = data.get("last_intent")
        self.last_intent = intent if isinstance(intent, str) and len(intent) <= 40 else None
        reply = data.get("last_reply")
        self.last_reply = reply[:1000] if isinstance(reply, str) and reply else None
        turns = data.get("turn_count")
        self.turn_count = turns if isinstance(turns, int) and 0 <= turns <= 100000 else 0


# --------------------------------------------------------------------------
# Safe arithmetic (used by the "math" handler)
# --------------------------------------------------------------------------

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}

_MATH_WORDS = [
    (r"\bto the power of\b", "**"),
    (r"\bmultiplied by\b", "*"),
    (r"\bdivided by\b", "/"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\btimes\b", "*"),
    (r"\bover\b", "/"),
    (r"\binto\b", "*"),
    (r"\bmod\b", "%"),
    (r"(?<=\d)\s*x\s*(?=\d)", "*"),
    (r"\^", "**"),
]


def safe_eval(expression: str) -> float:
    """Evaluate + - * / % ** on numbers only. Anything else raises ValueError.

    Python's eval() would run arbitrary code, so the expression is parsed into
    an AST and only whitelisted node types are walked.
    """
    text = expression.lower()
    for pattern, replacement in _MATH_WORDS:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"(\d+)\s*squared", r"(\1**2)", text)

    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError("invalid expression") from exc

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 64:
                raise ValueError("exponent too large")
            return _BINARY_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](walk(node.operand))
        raise ValueError(f"unsupported syntax: {type(node).__name__}")

    return walk(tree)


def format_number(value: float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


# --------------------------------------------------------------------------
# The chatbot
# --------------------------------------------------------------------------

class RuleBasedChatbot:
    """Dictionary-driven chatbot with tiered matching and per-session memory."""

    def __init__(
        self,
        bot_name: str = "Nova",
        intents_path: Optional[Path | str] = None,
        fuzzy_threshold: float = 0.8,
        seed: Optional[int] = None,
    ) -> None:
        self.bot_name = bot_name
        self.fuzzy_threshold = fuzzy_threshold
        self.random = random.Random(seed)
        self.intents_path = Path(intents_path) if intents_path else DEFAULT_INTENTS_PATH

        # Validators run in the pattern tier, after a regex matched but before
        # the match is accepted. Returning False sends the matcher on to the
        # next tier, which is how "42" avoids being treated as arithmetic.
        self.validators: dict[str, Callable[[dict], bool]] = {
            "math": self._validate_math,
            "remember_name": self._validate_name,
        }

        # Handlers compute values for placeholders such as {time}. A handler
        # may return {"alt": True} to ask for the intent's alt_responses.
        self.handlers: dict[str, Callable[[Session, dict], dict]] = {
            "time": self._handle_time,
            "date": self._handle_date,
            "day": self._handle_day,
            "math": self._handle_math,
            "remember_name": self._handle_remember_name,
            "recall_name": self._handle_recall_name,
            "coin_flip": self._handle_coin_flip,
            "dice_roll": self._handle_dice_roll,
            "help": self._handle_help,
            "list_intents": self._handle_list_intents,
            "repeat": self._handle_repeat,
        }

        self.default_session = Session()
        self.load_intents(self.intents_path)

    # ---------------------------------------------------------------- loading

    def load_intents(self, path: Path | str) -> None:
        """Read intents.json and build the lookup tables the matcher uses."""
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        self.intents: dict[str, dict] = {item["name"]: item for item in data["intents"]}
        self.normalizations: dict[str, str] = data.get("normalizations", {})
        self.exit_commands: set[str] = set(data.get("exit_commands", ["exit", "quit", "bye"]))
        self.goodbye_responses: list[str] = data.get("goodbye_responses", ["Goodbye!"])
        self.empty_input_response: str = data.get("empty_input_response", "Please type something.")
        self.fallback_responses: list[str] = data.get("fallback", {}).get("responses", ["I do not understand."])

        # phrase -> intent for the exact tier. Includes exact_only phrases.
        self.exact_lookup: dict[str, str] = {}
        # phrase -> intent for keyword and fuzzy tiers. Excludes exact_only phrases.
        self.phrase_lookup: dict[str, str] = {}
        # compiled regexes for the pattern tier, in file order.
        self.regex_intents: list[tuple[str, re.Pattern]] = []

        for name, spec in self.intents.items():
            for phrase in spec.get("patterns", []):
                self.exact_lookup[phrase] = name
                self.phrase_lookup[phrase] = name
            for phrase in spec.get("exact_only", []):
                self.exact_lookup[phrase] = name
            for pattern in spec.get("regex", []):
                self.regex_intents.append((name, re.compile(pattern)))

        # Multi-word normalizations must run before single-word ones.
        self.phrase_normalizations = {k: v for k, v in self.normalizations.items() if " " in k}
        self.word_normalizations = {k: v for k, v in self.normalizations.items() if " " not in k}

    # -------------------------------------------------------------- sanitize

    _PUNCT_TO_STRIP = ",!?;:\"" + "".join(c for c in string.punctuation if c in "[]{}<>|~`")

    def sanitize_input(self, raw_input: str) -> str:
        """Normalise a message so that many spellings collapse to one lookup key.

        Steps: lowercase, straighten curly quotes, drop noise punctuation,
        expand chat shorthand (u -> you), remove filler words, squeeze spaces.
        Apostrophes, hyphens, dots and arithmetic symbols are kept because
        "what's", "well-known" and "3.5 * 2" need them.
        """
        text = raw_input.lower().strip()
        text = text.replace("’", "'").replace("‘", "'")
        text = text.translate(str.maketrans("", "", self._PUNCT_TO_STRIP))
        text = text.strip(". ")

        for phrase, replacement in self.phrase_normalizations.items():
            text = re.sub(rf"\b{re.escape(phrase)}\b", replacement, text)

        words = []
        for word in text.split():
            replacement = self.word_normalizations.get(word, word)
            if replacement:
                words.append(replacement)
        return " ".join(words)

    # --------------------------------------------------------------- matching

    def _context_ok(self, intent_name: str, last_intent: Optional[str]) -> bool:
        allowed = self.intents[intent_name].get("context")
        return not allowed or last_intent in allowed

    def match_intent(self, clean_input: str, session: Optional[Session] = None) -> MatchResult:
        """Find the best intent for an already-sanitized message.

        Tiers, cheapest first:
          1. exact    - the whole message is a known phrase (dict lookup, O(1))
          2. pattern  - a regex with named groups matched, giving entities
          3. keyword  - a known phrase appears inside a longer message
          4. fuzzy    - close enough to a known phrase to forgive typos
        """
        if not clean_input:
            return MatchResult(None, "none", 0.0)

        last_intent = session.last_intent if session else None

        # 1. exact
        intent = self.exact_lookup.get(clean_input)
        if intent and self._context_ok(intent, last_intent):
            return MatchResult(intent, "exact", 1.0, clean_input)

        # 2. pattern (regex with entities)
        for intent_name, regex in self.regex_intents:
            if not self._context_ok(intent_name, last_intent):
                continue
            found = regex.match(clean_input)
            if not found:
                continue
            entities = {k: v.strip() for k, v in found.groupdict().items() if v}
            reject = set(self.intents[intent_name].get("reject", []))
            if any(value in reject for value in entities.values()):
                continue
            validator = self.validators.get(self.intents[intent_name].get("handler", ""))
            if validator and not validator(entities):
                continue
            return MatchResult(intent_name, "pattern", 0.95, found.group(0), entities)

        # 3. keyword: longest known phrase contained in the message wins,
        #    so "what time is it" beats "hi" in "hi what time is it".
        words = clean_input.split()
        word_set = set(words)
        padded = f" {clean_input} "
        best_phrase, best_intent = None, None
        for phrase, intent_name in self.phrase_lookup.items():
            if not self._context_ok(intent_name, last_intent):
                continue
            if " " in phrase:
                hit = f" {phrase} " in padded
            else:
                hit = phrase in word_set
            if hit and (best_phrase is None or len(phrase) > len(best_phrase)):
                best_phrase, best_intent = phrase, intent_name
        if best_phrase:
            coverage = len(best_phrase.split()) / max(len(words), 1)
            confidence = round(min(0.9, 0.5 + 0.4 * coverage), 2)
            return MatchResult(best_intent, "keyword", confidence, best_phrase)

        # 4a. fuzzy on the whole message ("whats yor name" -> "what's your name")
        candidates = [p for p, i in self.phrase_lookup.items() if self._context_ok(i, last_intent)]
        close = difflib.get_close_matches(clean_input, candidates, n=1, cutoff=self.fuzzy_threshold)
        if close:
            ratio = difflib.SequenceMatcher(None, clean_input, close[0]).ratio()
            return MatchResult(self.phrase_lookup[close[0]], "fuzzy", round(ratio, 2), close[0])

        # 4b. fuzzy per word, single-word phrases only ("helo there" -> "hello")
        single_word_phrases = [p for p in candidates if " " not in p and len(p) >= FUZZY_MIN_WORD_LENGTH]
        for word in words:
            if len(word) < FUZZY_MIN_WORD_LENGTH:
                continue
            close = difflib.get_close_matches(word, single_word_phrases, n=1, cutoff=self.fuzzy_threshold)
            if close:
                ratio = difflib.SequenceMatcher(None, word, close[0]).ratio()
                # A single corrected word inside a longer message is weaker evidence.
                confidence = round(ratio * (0.9 if len(words) == 1 else 0.75), 2)
                return MatchResult(self.phrase_lookup[close[0]], "fuzzy", confidence, close[0])

        return MatchResult(None, "none", 0.0)

    # ------------------------------------------------------------- validators

    _MATH_OPERATOR_RE = re.compile(r"[+\-*/%^]|\b(?:plus|minus|times|divided|over|into|power|squared|mod)\b|(?<=\d)\s*x\s*(?=\d)")

    def _validate_math(self, entities: dict) -> bool:
        """Needs a digit and an operator, otherwise "42" or "x" would count as arithmetic."""
        expr = entities.get("expr", "")
        return bool(re.search(r"\d", expr)) and bool(self._MATH_OPERATOR_RE.search(expr))

    def _validate_name(self, entities: dict) -> bool:
        return bool(entities.get("name", "").strip("'-"))

    # --------------------------------------------------------------- handlers

    def _handle_time(self, session: Session, entities: dict) -> dict:
        return {"time": datetime.now(PKT).strftime("%I:%M %p").lstrip("0")}

    def _handle_date(self, session: Session, entities: dict) -> dict:
        now = datetime.now(PKT)
        return {"date": f"{now.strftime('%A')}, {now.day} {now.strftime('%B %Y')}"}

    def _handle_day(self, session: Session, entities: dict) -> dict:
        return {"day": datetime.now(PKT).strftime("%A")}

    def _handle_math(self, session: Session, entities: dict) -> dict:
        expr = entities.get("expr", "").strip()
        try:
            result = safe_eval(expr)
        except ZeroDivisionError:
            return {"alt": True, "expr": expr}
        except (ValueError, OverflowError, RecursionError):
            return {"alt": True, "expr": expr}
        return {"expr": expr, "result": format_number(result)}

    def _handle_remember_name(self, session: Session, entities: dict) -> dict:
        session.user_name = entities["name"].strip("'-").capitalize()
        return {}

    def _handle_recall_name(self, session: Session, entities: dict) -> dict:
        return {} if session.user_name else {"alt": True}

    def _handle_coin_flip(self, session: Session, entities: dict) -> dict:
        return {"coin": self.random.choice(["heads", "tails"])}

    def _handle_dice_roll(self, session: Session, entities: dict) -> dict:
        return {"dice": self.random.randint(1, 6)}

    def _handle_help(self, session: Session, entities: dict) -> dict:
        return {"intent_count": len(self.intents)}

    def _handle_list_intents(self, session: Session, entities: dict) -> dict:
        return {"intent_count": len(self.intents), "intent_list": ", ".join(sorted(self.intents))}

    def _handle_repeat(self, session: Session, entities: dict) -> dict:
        if not session.last_reply:
            return {"alt": True}
        return {"last_reply": session.last_reply}

    # ------------------------------------------------------------- rendering

    _FIELD_RE = re.compile(r"\{(\w+)\}")

    def _render(self, match: MatchResult, session: Session) -> str:
        """Run the intent's handler (if any) and fill a response template."""
        spec = self.intents[match.intent]
        values = {"bot_name": self.bot_name, "user_name": session.user_name}
        values.update(match.entities)

        handler_name = spec.get("handler")
        use_alt = False
        if handler_name:
            produced = self.handlers[handler_name](session, match.entities)
            use_alt = bool(produced.pop("alt", False))
            values.update(produced)
            # A handler may have set the name during this turn.
            values["user_name"] = session.user_name

        templates = spec.get("alt_responses" if use_alt else "responses", [])
        usable = [t for t in templates if all(values.get(f) is not None for f in self._FIELD_RE.findall(t))]
        if not usable:
            usable = [t for t in templates if "{user_name}" not in t] or templates
        template = self.random.choice(usable)
        return template.format(**{k: ("" if v is None else v) for k, v in values.items()})

    # --------------------------------------------------------------- public

    def respond(self, raw_input: str, session: Optional[Session] = None) -> BotReply:
        """Full pipeline for one turn. This is the one method every interface calls."""
        session = session or self.default_session
        clean = self.sanitize_input(raw_input)

        if not clean:
            reply = BotReply(self.empty_input_response, "empty", "none", 0.0, raw_input, clean)
        elif clean in self.exit_commands:
            reply = BotReply(
                self.random.choice(self.goodbye_responses), "exit", "exact", 1.0,
                raw_input, clean, matched_phrase=clean, session_ended=True,
            )
        else:
            match = self.match_intent(clean, session)
            if match.intent is None:
                reply = BotReply(self.random.choice(self.fallback_responses), "fallback", "none", 0.0, raw_input, clean)
            else:
                text = self._render(match, session)
                reply = BotReply(
                    text, match.intent, match.tier, match.confidence, raw_input, clean,
                    matched_phrase=match.matched_phrase, entities=match.entities,
                )

        session.record(reply)
        return reply

    def get_response(self, raw_input: str) -> str:
        """Plain-text reply using the default session. Kept for the original terminal contract."""
        return self.respond(raw_input).text

    def get_response_with_intent(self, raw_input: str) -> tuple[str, str]:
        """(reply text, intent name) using the default session."""
        reply = self.respond(raw_input)
        return reply.text, reply.intent

    def intents_summary(self) -> list[dict]:
        """Compact description of every intent, used by the web UI and the CLI."""
        summary = []
        for name, spec in self.intents.items():
            examples = spec.get("patterns", [])[:3] or spec.get("exact_only", [])[:3]
            if not examples and spec.get("regex"):
                examples = {"remember_name": ["my name is zain"], "math": ["12 * 7", "what is 8 plus 2"]}.get(name, [])
            summary.append({
                "name": name,
                "description": spec.get("description", ""),
                "examples": examples,
                "dynamic": bool(spec.get("handler")),
                "pattern_count": len(spec.get("patterns", [])) + len(spec.get("exact_only", [])) + len(spec.get("regex", [])),
            })
        return summary

    # ------------------------------------------------------------- terminal

    def run(self, debug: bool = False, log_path: Optional[str] = None) -> None:
        """Interactive loop. Ends on an exit command or Ctrl+C / Ctrl+D."""
        session = Session()
        print(f"{self.bot_name}: Hello! I'm {self.bot_name}, a rule-based chatbot with {len(self.intents)} intents.")
        print(f"{self.bot_name}: Type 'help' to see what I can do, or 'exit' to leave.\n")

        log_file = open(log_path, "a", encoding="utf-8") if log_path else None
        try:
            while True:
                try:
                    raw = input("You: ")
                except (EOFError, KeyboardInterrupt):
                    print(f"\n{self.bot_name}: Goodbye!")
                    break

                reply = self.respond(raw, session)
                if debug:
                    print(f"  [trace] cleaned='{reply.cleaned_input}' tier={reply.tier} "
                          f"intent={reply.intent} confidence={reply.confidence:.2f} "
                          f"phrase={reply.matched_phrase!r} entities={reply.entities}")
                print(f"{self.bot_name}: {reply.text}")

                if log_file:
                    entry = {"at": datetime.now(PKT).isoformat(timespec="seconds"), **reply.to_dict()}
                    log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    log_file.flush()

                if reply.session_ended:
                    break
        finally:
            if log_file:
                log_file.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nova, a rule-based chatbot.")
    parser.add_argument("--name", default="Nova", help="bot display name (default: Nova)")
    parser.add_argument("--intents", default=None, help="path to an intents JSON file")
    parser.add_argument("--debug", action="store_true", help="print the match trace after every turn")
    parser.add_argument("--log", metavar="FILE", help="append each turn as JSON lines to FILE")
    parser.add_argument("--list-intents", action="store_true", help="print the loaded intents and exit")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    bot = RuleBasedChatbot(bot_name=args.name, intents_path=args.intents)

    if args.list_intents:
        for item in bot.intents_summary():
            kind = "dynamic" if item["dynamic"] else "static"
            print(f"{item['name']:<18} {kind:<8} {item['description']}")
        print(f"\n{len(bot.intents)} intents loaded from {bot.intents_path}")
        return 0

    bot.run(debug=args.debug, log_path=args.log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
