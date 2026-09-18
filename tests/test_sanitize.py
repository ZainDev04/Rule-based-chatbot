"""sanitize_input(): many spellings must collapse to one lookup key."""

import pytest


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Hello", "hello"),
        ("  HELLO!!!  ", "hello"),
        ("What's your name?", "what's your name"),
        ("what’s your name", "what's your name"),      # curly apostrophe
        ("hi,   there", "hi there"),
        ("thx", "thanks"),
        ("whats ur name", "what's your name"),
        ("hi nova", "hi"),                                  # bot name is filler
        ("help please", "help"),
        ("please help", "help"),
        ("12 * 7", "12 * 7"),                               # arithmetic symbols survive
        ("1.5 + 2.", "1.5 + 2"),
        ("", ""),
        ("   ", ""),
        ("???", ""),
    ],
)
def test_sanitize(bot, raw, expected):
    assert bot.sanitize_input(raw) == expected


def test_sanitize_keeps_hyphen_and_apostrophe(bot):
    assert bot.sanitize_input("well-known, isn't it?") == "well-known isn't it"
