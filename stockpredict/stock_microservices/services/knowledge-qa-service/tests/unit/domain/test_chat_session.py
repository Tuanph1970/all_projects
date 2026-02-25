"""Tests for ChatSession aggregate root."""
import pytest
from app.domain.entities.chat_session import ChatSession
from app.domain.events.domain_events import (
    SessionCreatedEvent,
    SessionClearedEvent,
    QuestionAskedEvent,
    AnswerGeneratedEvent,
)


class TestChatSession:
    def test_creation_emits_event(self):
        session = ChatSession(id="test-1")
        events = session.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SessionCreatedEvent)
        assert events[0].session_id == "test-1"

    def test_add_user_message(self):
        session = ChatSession(id="test-1")
        session.collect_events()  # clear creation event

        msg = session.add_user_message("Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert session.message_count == 1

        events = session.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], QuestionAskedEvent)

    def test_add_assistant_message(self):
        session = ChatSession(id="test-1")
        session.collect_events()

        msg = session.add_assistant_message(
            content="Hi there!",
            sources=[{"note_id": "n1", "title": "Test"}],
            tokens_used=10,
            model="llama3.1",
        )
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"
        assert msg.tokens_used == 10
        assert len(msg.sources) == 1

        events = session.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], AnswerGeneratedEvent)

    def test_clear_session(self):
        session = ChatSession(id="test-1")
        session.add_user_message("q1")
        session.add_assistant_message(content="a1")
        session.collect_events()

        session.clear()
        assert session.message_count == 0

        events = session.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SessionClearedEvent)

    def test_get_history_for_llm(self):
        session = ChatSession(id="test-1")
        session.add_user_message("q1")
        session.add_assistant_message(content="a1")
        session.add_user_message("q2")

        history = session.get_history_for_llm(max_turns=5)
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"

    def test_history_truncation(self):
        session = ChatSession(id="test-1")
        for i in range(20):
            session.add_user_message(f"q{i}")
            session.add_assistant_message(content=f"a{i}")

        history = session.get_history_for_llm(max_turns=3)
        assert len(history) == 6  # 3 turns * 2 messages
