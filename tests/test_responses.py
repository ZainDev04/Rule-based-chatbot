"""respond(): the full pipeline, dynamic handlers, session memory and fallbacks."""

import re

import pytest

from chatbot import Session, safe_eval, format_number


def test_every_intent_has_at_least_one_response(bot):
    for name, spec in bot.intents.items():
        assert spec.get("responses"), f"{name} has no responses"


def test_every_intent_is_reachable(bot):
    """Each intent must be triggered by at least one of its own examples."""
    for item in bot.intents_summary():
        for example in item["examples"]:
            result = bot.match_intent(bot.sanitize_input(example))
            assert result.intent == item["name"], f"{example!r} matched {result.intent}, expected {item['name']}"


def test_fallback_for_unknown_input(bot, session):
    reply = bot.respond("purple elephants dance", session)
    assert reply.intent == "fallback"
    assert reply.text in bot.fallback_responses


def test_empty_input(bot, session):
    reply = bot.respond("   ", session)
    assert reply.intent == "empty"
    assert reply.text == bot.empty_input_response


@pytest.mark.parametrize("word", ["exit", "quit", "bye", "goodbye", "BYE!", "see you"])
def test_exit_commands_end_session(bot, session, word):
    reply = bot.respond(word, session)
    assert reply.intent == "exit"
    assert reply.session_ended is True


def test_time_reply_has_clock_format(bot, session):
    reply = bot.respond("what time is it", session)
    assert re.search(r"\d{1,2}:\d{2} (AM|PM)", reply.text)


def test_date_reply_mentions_a_year(bot, session):
    reply = bot.respond("what is the date", session)
    assert re.search(r"20\d\d", reply.text)


def test_math_reply(bot, session):
    reply = bot.respond("what is 12 * 7", session)
    assert "84" in reply.text
    reply = bot.respond("100 divided by 8", session)
    assert "12.5" in reply.text


def test_math_division_by_zero_uses_alt_response(bot, session):
    reply = bot.respond("10 / 0", session)
    assert reply.intent == "math"
    assert reply.text in bot.intents["math"]["alt_responses"]


def test_coin_flip_and_dice(bot, session):
    assert re.search(r"heads|tails", bot.respond("flip a coin", session).text)
    assert re.search(r"[1-6]", bot.respond("roll a dice", session).text)


def test_help_reports_intent_count(bot, session):
    reply = bot.respond("help", session)
    assert str(len(bot.intents)) in reply.text


# ---- session memory ---------------------------------------------------------

def test_remembers_name_across_turns(bot, session):
    bot.respond("my name is zain", session)
    assert session.user_name == "Zain"
    reply = bot.respond("what is my name", session)
    assert "Zain" in reply.text


def test_recall_name_before_it_is_known(bot, session):
    reply = bot.respond("what is my name", session)
    assert reply.intent == "recall_name"
    assert reply.text in bot.intents["recall_name"]["alt_responses"]


def test_templates_needing_a_name_are_skipped_until_known(bot):
    """Run many greetings with no name set: no template may contain an empty placeholder."""
    for _ in range(50):
        reply = bot.respond("hello", Session())
        assert "{user_name}" not in reply.text
        assert "  " not in reply.text and ", !" not in reply.text


def test_repeat_echoes_previous_reply(bot, session):
    first = bot.respond("tell me a joke", session)
    reply = bot.respond("say that again", session)
    assert first.text in reply.text


def test_repeat_with_nothing_to_repeat(bot, session):
    reply = bot.respond("say that again", session)
    assert reply.text in bot.intents["repeat"]["alt_responses"]


def test_session_tracks_turns_and_last_intent(bot, session):
    bot.respond("hello", session)
    bot.respond("what time is it", session)
    assert session.turn_count == 2
    assert session.last_intent == "time"
    assert len(session.history) == 2


def test_sessions_are_isolated(bot):
    a, b = Session(), Session()
    bot.respond("my name is ali", a)
    assert a.user_name == "Ali"
    assert b.user_name is None


def test_seeded_bot_is_deterministic():
    from chatbot import RuleBasedChatbot

    first = [RuleBasedChatbot(seed=7).respond("hello").text for _ in range(3)]
    assert len(set(first)) == 1


# ---- legacy helpers ----------------------------------------------------------

def test_get_response_returns_text(bot):
    assert isinstance(bot.get_response("hello"), str)


def test_get_response_with_intent(bot):
    text, intent = bot.get_response_with_intent("hello")
    assert intent == "greeting"
    assert text


# ---- safe_eval ---------------------------------------------------------------

@pytest.mark.parametrize(
    "expr, expected",
    [
        ("2 + 2", 4),
        ("12 * 7", 84),
        ("(8 + 2) / 5", 2),
        ("2 ^ 10", 1024),
        ("7 mod 3", 1),
        ("3 squared", 9),
        ("-5 + 2", -3),
        ("5 x 5", 25),
    ],
)
def test_safe_eval(expr, expected):
    assert safe_eval(expr) == expected


@pytest.mark.parametrize("expr", ["__import__('os')", "print(1)", "a + 1", "2 ** 1000", "[1,2]", "1 if 2 else 3"])
def test_safe_eval_rejects_non_arithmetic(expr):
    with pytest.raises(ValueError):
        safe_eval(expr)


def test_format_number():
    assert format_number(4.0) == "4"
    assert format_number(12.5) == "12.5"
    assert format_number(1 / 3) == "0.3333"
