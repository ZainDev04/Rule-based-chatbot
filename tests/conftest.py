"""Shared fixtures. Adds the repo root and web/ to sys.path so tests import the real modules."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "web"))

from chatbot import RuleBasedChatbot, Session  # noqa: E402


@pytest.fixture
def bot() -> RuleBasedChatbot:
    """A bot with a fixed random seed so response choice is repeatable."""
    return RuleBasedChatbot(bot_name="Nova", seed=42)


@pytest.fixture
def session() -> Session:
    return Session()
