"""
Flask API and web interface for the rule-based chatbot
-------------------------------------------------------
DecodeLabs | Industrial Training Kit - Artificial Intelligence | Project 1

This file only adds HTTP on top of chatbot.py. The engine is imported from
the repository root so there is one copy of the logic for the terminal and
the browser.

Routes
    GET  /               chat interface
    POST /api/chat       {"message": str, "session_id": str, "session_state": {...}?}
                         -> reply plus match trace and the updated session state
    POST /api/reset      {"session_id": str}                  -> forget that session
    GET  /api/intents    list of loaded intents
    GET  /api/health     uptime and counters, used by monitoring

Run locally:
    cd web
    python app.py

Author: Shaikh Muhammad Zain
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# Make the repository root importable so `chatbot` resolves to ../chatbot.py.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chatbot import RuleBasedChatbot, Session  # noqa: E402

MAX_MESSAGE_LENGTH = 500
SESSION_TTL_SECONDS = 60 * 60          # forget a browser session after an hour idle
MAX_SESSIONS = 500                     # hard cap so memory cannot grow without bound
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60           # per client per window


def create_app(bot: RuleBasedChatbot | None = None) -> Flask:
    """Application factory. Tests pass their own bot; production uses the default."""
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.bot = bot or RuleBasedChatbot(bot_name="Nova")
    app.started_at = datetime.now(timezone.utc)

    # ---- in-memory state --------------------------------------------------
    # One process serves all users on PythonAnywhere's free tier, so a dict
    # is enough. A real deployment would move this to Redis.
    sessions: dict[str, Session] = {}
    sessions_lock = threading.Lock()
    rate_buckets: dict[str, deque] = {}
    counters = {"requests": 0, "fallbacks": 0}

    def get_session(session_id: str) -> Session:
        with sessions_lock:
            now = time.time()
            # Drop idle sessions, then oldest ones if still over the cap.
            for key in [k for k, s in sessions.items() if now - s.last_active.timestamp() > SESSION_TTL_SECONDS]:
                del sessions[key]
            if session_id not in sessions and len(sessions) >= MAX_SESSIONS:
                oldest = min(sessions, key=lambda k: sessions[k].last_active)
                del sessions[oldest]
            return sessions.setdefault(session_id, Session())

    def rate_limited(client_key: str) -> bool:
        now = time.time()
        bucket = rate_buckets.setdefault(client_key, deque())
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            return True
        bucket.append(now)
        return False

    def client_key() -> str:
        forwarded = request.headers.get("X-Forwarded-For", "")
        return forwarded.split(",")[0].strip() or request.remote_addr or "unknown"

    def error(status: int, code: str, message: str):
        return jsonify({"error": {"code": code, "message": message}}), status

    # ---- pages ------------------------------------------------------------

    @app.get("/")
    def home():
        return render_template(
            "index.html",
            bot_name=app.bot.bot_name,
            intent_count=len(app.bot.intents),
            max_length=MAX_MESSAGE_LENGTH,
        )

    # ---- api --------------------------------------------------------------

    @app.post("/api/chat")
    def chat():
        if rate_limited(client_key()):
            return error(429, "rate_limited", "Too many messages. Wait a minute and try again.")

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error(400, "invalid_json", "Request body must be a JSON object.")

        message = data.get("message")
        if not isinstance(message, str):
            return error(400, "invalid_message", "'message' must be a string.")
        if len(message) > MAX_MESSAGE_LENGTH:
            return error(413, "message_too_long", f"Messages are limited to {MAX_MESSAGE_LENGTH} characters.")

        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not (8 <= len(session_id) <= 64):
            session_id = uuid.uuid4().hex

        session = get_session(session_id)

        # Serverless hosts (Vercel) may serve consecutive requests from
        # different processes, so the browser sends back the state it was
        # given last time. The newer copy wins.
        client_state = data.get("session_state")
        if isinstance(client_state, dict) and client_state.get("turn_count", 0) > session.turn_count:
            session.restore(client_state)

        started = time.perf_counter()
        reply = app.bot.respond(message, session)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

        counters["requests"] += 1
        if reply.intent == "fallback":
            counters["fallbacks"] += 1

        if reply.session_ended:
            with sessions_lock:
                sessions.pop(session_id, None)

        payload = reply.to_dict()
        payload.update({
            "session_id": session_id,
            "session": session.to_dict(),
            "processing_ms": elapsed_ms,
            "bot_name": app.bot.bot_name,
        })
        return jsonify(payload)

    @app.post("/api/reset")
    def reset():
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        with sessions_lock:
            existed = sessions.pop(session_id, None) is not None if isinstance(session_id, str) else False
        return jsonify({"reset": True, "existed": existed})

    @app.get("/api/intents")
    def intents():
        return jsonify({"count": len(app.bot.intents), "intents": app.bot.intents_summary()})

    @app.get("/api/health")
    def health():
        uptime = (datetime.now(timezone.utc) - app.started_at).total_seconds()
        return jsonify({
            "status": "ok",
            "bot": app.bot.bot_name,
            "intents": len(app.bot.intents),
            "uptime_seconds": round(uptime),
            "active_sessions": len(sessions),
            "requests_served": counters["requests"],
            "fallback_rate": round(counters["fallbacks"] / counters["requests"], 3) if counters["requests"] else 0.0,
        })

    # ---- errors -----------------------------------------------------------

    @app.errorhandler(404)
    def not_found(_exc):
        if request.path.startswith("/api/"):
            return error(404, "not_found", "No such endpoint.")
        return render_template("index.html", bot_name=app.bot.bot_name,
                               intent_count=len(app.bot.intents), max_length=MAX_MESSAGE_LENGTH), 404

    @app.errorhandler(405)
    def wrong_method(_exc):
        return error(405, "method_not_allowed", "That method is not allowed on this endpoint.")

    @app.errorhandler(500)
    def server_error(_exc):
        return error(500, "server_error", "Something went wrong on the server.")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
