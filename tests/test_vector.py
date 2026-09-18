"""Tier 5, the TF-IDF vector matcher, and the word-level typo check in the fuzzy tier."""

import pytest

from chatbot import VectorIndex, RuleBasedChatbot


# ---- vector tier through the full matcher ---------------------------------

@pytest.mark.parametrize(
    "text, intent, phrase",
    [
        ("could you tell me what the hour is", "time", "tell me the time"),
        ("who built this bot", "creator", "who built you"),
        ("which city do you live in", "location", "which city are you in"),
        ("tell me something funny please", "joke", "tell me a joke"),
        ("is it going to rain today", "weather", "is it raining"),
        ("i am feeling really down today", "mood_bad", "i feel sad"),
        ("i need some assistance", "help", "i need help"),
        ("are you an artificial intelligence", "about_project", "are you an ai"),
        ("i feel great today", "mood_good", "feeling good"),
    ],
)
def test_vector_tier_matches_paraphrases(bot, text, intent, phrase):
    result = bot.match_intent(bot.sanitize_input(text))
    assert result.intent == intent
    assert result.tier == "vector"
    assert result.matched_phrase == phrase
    assert 0.55 <= result.confidence < 1.0


@pytest.mark.parametrize(
    "text",
    [
        "tell me",                        # filler words only
        "what is it",                     # shares filler with "what time is it"
        "this is a test",                 # "this" and "is" are not evidence
        "how do i address you",           # every shared word is a stopword
        "are you able to remember things",
        "what is your purpose",
        "please forget everything",
        "purple elephants dance",
    ],
)
def test_vector_tier_rejects_filler_overlap(bot, text):
    result = bot.match_intent(bot.sanitize_input(text))
    assert result.intent is None, f"{text!r} matched {result.intent} via {result.tier}"


def test_vector_tier_runs_after_fuzzy(bot):
    # A typo is still handled by the fuzzy tier, not the vector tier.
    assert bot.match_intent("helo").tier == "fuzzy"
    # A paraphrase with no typo and no shared phrase falls through to vector.
    assert bot.match_intent("who built this").tier == "vector"


def test_vector_tier_respects_context(bot, session):
    """Intents with a context list are skipped in the vector tier when the context is wrong."""
    bot.intents["about_project"]["context"] = ["greeting"]
    bot.load_intents(bot.intents_path)  # rebuilds the index from the file, dropping the fake context
    assert bot.match_intent("are you an artificial intelligence", session).intent == "about_project"


# ---- VectorIndex on its own ---------------------------------------------

def test_vector_index_scores_identical_text_as_one():
    index = VectorIndex({"tell me a joke": "joke", "what time is it": "time"}, {}, set())
    phrase, intent, score = index.query("tell me a joke")
    assert (phrase, intent) == ("tell me a joke", "joke")
    assert score == pytest.approx(1.0)


def test_vector_index_applies_synonyms():
    index = VectorIndex({"what time is it": "time"}, {"hour": "time"}, {"what", "is", "it"})
    assert index.query("what hour is it")[1] == "time"
    assert index.query("what year is it") is None


def test_vector_index_needs_a_content_word():
    index = VectorIndex({"tell me a joke": "joke", "tell me the time": "time"}, {}, {"tell", "me", "a", "the"})
    assert index.query("tell me") is None
    # "a joke" shares a content word and covers enough of the phrase's weight.
    assert index.query("a joke")[1] == "joke"


def test_vector_index_empty_query():
    index = VectorIndex({"hello": "greeting"}, {}, set())
    assert index.query("") is None


# ---- fuzzy tier word check ----------------------------------------------

@pytest.mark.parametrize(
    "text, phrase, expected",
    [
        ("helo there", "hello there", True),
        ("whats yor name", "what's your name", True),
        ("thankyou", "thank you", True),
        ("what is it", "that is it", False),           # a different word, not a typo
        ("what are your abilities", "what are your hobbies", False),
    ],
)
def test_is_typo_of(text, phrase, expected):
    assert RuleBasedChatbot._is_typo_of(text, phrase) is expected


def test_fuzzy_tier_no_longer_swaps_whole_words(bot):
    assert bot.match_intent("what are your abilities").intent != "favorite"
    assert bot.match_intent("what is it").intent != "user_thanks_bye"
