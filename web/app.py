"""
Flask Web Server for Rule-Based AI Chatbot
--------------------------------------------
DecodeLabs | Industrial Training Kit - Artificial Intelligence | Project 1 (Bonus UI)

This wraps the existing RuleBasedChatbot class (chatbot.py) in a simple web
interface. The core chatbot logic is completely unchanged - this file only
adds HTTP routes so the same logic can be used from a browser instead of
the terminal.

Author: Shaikh Muhammad Zain
"""

from flask import Flask, request, jsonify, render_template
from chatbot import RuleBasedChatbot

app = Flask(__name__)
bot = RuleBasedChatbot(bot_name="Nova")


@app.route("/")
def home():
    """Serve the chat interface."""
    return render_template("index.html", bot_name=bot.bot_name)


@app.route("/chat", methods=["POST"])
def chat():
    """
    Receive a user message, run it through the same chatbot pipeline
    used by the terminal version, and return the response + matched intent.
    """
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")

    clean_input = bot.sanitize_input(user_message)

    # Check for exit commands (handled separately here since the web UI
    # doesn't have a literal loop the way the terminal version does -
    # the "loop" is the user clicking Send repeatedly).
    if clean_input in bot.exit_commands:
        return jsonify({
            "response": "Goodbye! Have a great day. 👋",
            "intent": "exit",
            "session_ended": True
        })

    response_text, intent = bot.get_response_with_intent(user_message)

    return jsonify({
        "response": response_text,
        "intent": intent or "unrecognized",
        "session_ended": False
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
