"""
Rule-Based AI Chatbot
DecodeLabs | Industrial Training Kit - Artificial Intelligence | Project 1

A deterministic, dictionary-driven chatbot that demonstrates the core
building blocks of conversational AI before introducing probabilistic
(LLM-based) systems: control flow, input sanitization, intent matching,
and graceful fallback handling.

Author: Shaikh Muhammad Zain
"""

import random
from datetime import datetime


class RuleBasedChatbot:
    """A simple rule-based chatbot using dictionary lookups (O(1) intent matching)."""

    def __init__(self, bot_name="Nova"):
        self.bot_name = bot_name
        self.user_name = None
        self.exit_commands = {"exit", "quit", "bye", "goodbye", "stop"}

        # Knowledge base: maps intents -> possible responses.
        # A list of responses (instead of a single string) lets the bot feel
        # less robotic, since it can pick a random variation each time.
        self.knowledge_base = {
            "greeting": [
                "Hello! How can I help you today?",
                "Hi there! What can I do for you?",
                "Hey! Good to see you."
            ],
            "how_are_you": [
                "I'm just a set of rules, but I'm running smoothly! How about you?",
                "Doing great, thanks for asking! How can I assist you?"
            ],
            "name": [
                f"I'm {self.bot_name}, your friendly rule-based assistant.",
                f"You can call me {self.bot_name}!"
            ],
            "time": [
                "lambda"  # handled dynamically, see _handle_dynamic_intents()
            ],
            "thanks": [
                "You're welcome!",
                "Anytime! Happy to help.",
                "No problem at all."
            ],
            "help": [
                "I can chat about greetings, my name, the time, or just keep you company. "
                "Try saying 'hello', 'what's your name', or 'what time is it'."
            ],
            "creator": [
                "I was built as part of the DecodeLabs AI Internship, Project 1.",
                "A DecodeLabs AI intern brought me to life!"
            ],
            "mood_good": [
                "That's wonderful to hear!",
                "Glad you're doing well!"
            ],
            "mood_bad": [
                "I'm sorry to hear that. I hope things get better soon.",
                "That's tough. Take it easy on yourself."
            ],
        }

        # Maps multiple possible user phrasings -> a single canonical intent key.
        # This is what gives the dictionary approach its power: any number of
        # inputs can resolve to the same O(1) lookup.
        self.intent_map = {
            "hello": "greeting", "hi": "greeting", "hey": "greeting",
            "good morning": "greeting", "good evening": "greeting",

            "how are you": "how_are_you", "how are you doing": "how_are_you",

            "what is your name": "name", "what's your name": "name",
            "who are you": "name",

            "what time is it": "time", "current time": "time", "time": "time",

            "thank you": "thanks", "thanks": "thanks", "thank you so much": "thanks",

            "help": "help", "what can you do": "help", "options": "help",

            "who made you": "creator", "who created you": "creator",
            "who built you": "creator",

            "i am good": "mood_good", "i'm good": "mood_good",
            "i am fine": "mood_good", "doing great": "mood_good",

            "i am sad": "mood_bad", "i'm sad": "mood_bad",
            "not good": "mood_bad", "i am tired": "mood_bad",
        }

        self.fallback_responses = [
            "I do not understand. Could you rephrase that?",
            "I'm not quite sure what you mean. Try asking something else.",
            "Hmm, that's outside what I currently know. Type 'help' to see what I can do."
        ]

    def sanitize_input(self, raw_input: str) -> str:
        """Normalize user input: lowercase, strip whitespace, remove trailing punctuation."""
        cleaned = raw_input.lower().strip()
        cleaned = cleaned.rstrip("!?.")
        return cleaned

    def match_intent(self, clean_input: str):
        """Look up the cleaned input directly, then fall back to whole-word/phrase matching."""
        # 1. Exact match (fastest path - O(1) dictionary lookup)
        if clean_input in self.intent_map:
            return self.intent_map[clean_input]

        # 2. Word-boundary match (catches phrases like "hello there" -> "greeting",
        #    without false-positives like "this" containing "hi").
        words = set(clean_input.split())
        for phrase, intent in self.intent_map.items():
            if " " in phrase:
                # Multi-word phrase: check it appears as a contiguous substring
                if phrase in clean_input:
                    return intent
            else:
                # Single-word phrase: must match a whole word, not a substring
                if phrase in words:
                    return intent

        return None

    def _handle_dynamic_intents(self, intent: str) -> str:
        """Some intents need a computed answer rather than a static string."""
        if intent == "time":
            return f"The current time is {datetime.now().strftime('%I:%M %p')}."
        return random.choice(self.knowledge_base[intent])

    def get_response(self, raw_input: str) -> str:
        """Full pipeline: sanitize -> match -> respond (with fallback)."""
        clean_input = self.sanitize_input(raw_input)

        if not clean_input:
            return "Please type something so I can help you."

        intent = self.match_intent(clean_input)

        if intent:
            return self._handle_dynamic_intents(intent)

        return random.choice(self.fallback_responses)

    def get_response_with_intent(self, raw_input: str):
        
        """
        Same pipeline as get_response(), but also returns which intent matched.
        Used by the web UI to show traceability (input -> matched intent -> output),
        without changing the behavior of get_response() used by the terminal version.
        Returns a tuple: (response_text, intent_name_or_None).
        """
        
        clean_input = self.sanitize_input(raw_input)

        if not clean_input:
            return "Please type something so I can help you.", None

        intent = self.match_intent(clean_input)

        if intent:
            return self._handle_dynamic_intents(intent), intent

        return random.choice(self.fallback_responses), "fallback"

    def run(self):
        """Main conversation loop. Runs until the user issues an exit command."""
        print(f"{self.bot_name}: Hello! I'm {self.bot_name}, a rule-based chatbot.")
        print(f"{self.bot_name}: Type 'exit', 'quit', or 'bye' anytime to end our chat.\n")

        while True:
            raw_input_text = input("You: ")
            clean_input = self.sanitize_input(raw_input_text)

            if clean_input in self.exit_commands:
                print(f"{self.bot_name}: Goodbye! Have a great day. 👋")
                break

            response = self.get_response(raw_input_text)
            print(f"{self.bot_name}: {response}")


if __name__ == "__main__":
    bot = RuleBasedChatbot(bot_name="Nova")
    bot.run()