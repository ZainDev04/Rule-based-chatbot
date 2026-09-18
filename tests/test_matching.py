"""match_intent(): each tier, in the order the engine tries them."""

import pytest


# ---- tier 1: exact -------------------------------------------------------

@pytest.mark.parametrize(
    "text, intent",
    [
        ("hello", "greeting"),
        ("what's your name", "name"),
        ("what time is it", "time"),
        ("thank you", "thanks"),
        ("help", "help"),
        ("who made you", "creator"),
        ("i am good", "mood_good"),
        ("i am sad", "mood_bad"),
        ("tell me a joke", "joke"),
        ("flip a coin", "coin_flip"),
        ("what day is it", "day"),
    ],
)
def test_exact_tier(bot, text, intent):
    result = bot.match_intent(text)
    assert result.intent == intent
    assert result.tier == "exact"
    assert result.confidence == 1.0


def test_exact_only_phrases_do_not_leak_into_keyword_tier(bot):
    # "good" alone means mood_good, but inside a sentence it must not.
    assert bot.match_intent("good").intent == "mood_good"
    assert bot.match_intent("good luck with the project").intent is None


# ---- tier 2: pattern (regex + entities) ------------------------------------

def test_pattern_tier_extracts_name(bot):
    result = bot.match_intent("my name is zain")
    assert result.intent == "remember_name"
    assert result.tier == "pattern"
    assert result.entities == {"name": "zain"}


def test_pattern_tier_rejects_adjectives_as_names(bot):
    # "i am tired" must be a mood, never a person called Tired.
    result = bot.match_intent("i am tired")
    assert result.intent == "mood_bad"
    result = bot.match_intent("i am busy")
    assert result.intent != "remember_name"


@pytest.mark.parametrize(
    "text, expr",
    [
        ("what is 12 * 7", "12 * 7"),
        ("12 * 7", "12 * 7"),
        ("8 plus 2", "8 plus 2"),
        ("calculate (8 + 2) / 5", "(8 + 2) / 5"),
    ],
)
def test_pattern_tier_extracts_math_expression(bot, text, expr):
    result = bot.match_intent(text)
    assert result.intent == "math"
    assert result.entities["expr"] == expr


def test_bare_number_is_not_math(bot):
    # A validator turns the regex hit down: no operator, no arithmetic.
    assert bot.match_intent("42").intent is None


# ---- tier 3: keyword -------------------------------------------------------

def test_keyword_tier_finds_phrase_inside_sentence(bot):
    result = bot.match_intent("hey nova what time is it right now")
    assert result.intent == "time"
    assert result.tier == "keyword"
    assert result.matched_phrase == "what time is it"


def test_keyword_tier_prefers_longest_phrase(bot):
    # "hi" and "what is your name" both appear; the longer one is more specific.
    result = bot.match_intent("hi what is your name")
    assert result.intent == "name"


def test_keyword_tier_requires_whole_words(bot):
    # "this" contains "hi" but is not a greeting.
    assert bot.match_intent("this is a test").intent is None


def test_keyword_confidence_is_below_exact(bot):
    result = bot.match_intent("so anyway tell me a joke now")
    assert result.tier == "keyword"
    assert 0.5 <= result.confidence < 1.0


# ---- tier 4: fuzzy ---------------------------------------------------------

@pytest.mark.parametrize(
    "text, intent",
    [
        ("helo", "greeting"),
        ("whats yor name", "name"),
        ("thankyou", "thanks"),
        ("tell me a jok", "joke"),
    ],
)
def test_fuzzy_tier_forgives_typos(bot, text, intent):
    result = bot.match_intent(text)
    assert result.intent == intent
    assert result.tier == "fuzzy"
    assert result.confidence < 1.0


def test_fuzzy_tier_ignores_short_words(bot):
    # Two-letter words are never fuzzy matched, so "hs" is not "hi".
    assert bot.match_intent("hs").intent is None


# ---- no match --------------------------------------------------------------

@pytest.mark.parametrize("text", ["asdkjh qwe", "purple elephants dance", "x"])
def test_no_match_returns_none(bot, text):
    result = bot.match_intent(text)
    assert result.intent is None
    assert result.tier == "none"
    assert result.confidence == 0.0
