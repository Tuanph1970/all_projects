"""Builder pattern for constructing LLM prompts."""
from app.domain.value_objects.graph_context import GraphContext


SYSTEM_PROMPT = """You are a knowledge base assistant. Your role is to answer questions based on the provided knowledge base context.

Rules:
1. Answer based ONLY on the provided context from the knowledge base.
2. If the context contains relevant information, provide a clear, comprehensive answer.
3. Cite your sources by mentioning the note titles you referenced.
4. If no relevant information is found in the context, clearly state that.
5. Be concise but thorough. Use bullet points or numbered lists when appropriate.
6. Respond in the same language as the question.
7. If the context contains code snippets, format them properly."""


class PromptBuilder:
    """Builder pattern for constructing LLM prompt messages step by step."""

    def __init__(self):
        self._messages: list[dict] = []
        self._system_added = False

    def with_system_role(self, system_prompt: str = None) -> "PromptBuilder":
        """Add the system role message."""
        self._messages.append({
            "role": "system",
            "content": system_prompt or SYSTEM_PROMPT,
        })
        self._system_added = True
        return self

    def with_context(self, graph_context: GraphContext) -> "PromptBuilder":
        """Inject retrieved notes as context."""
        context_str = graph_context.to_context_string()
        self._messages.append({
            "role": "system",
            "content": f"Knowledge Base Context:\n\n{context_str}",
        })
        return self

    def with_chat_history(self, history: list[dict]) -> "PromptBuilder":
        """Add previous conversation turns (excluding the latest user message)."""
        # Skip the last message as it will be added by with_user_question
        for msg in history[:-1] if history else []:
            self._messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        return self

    def with_user_question(self, question: str) -> "PromptBuilder":
        """Add the current user question."""
        self._messages.append({
            "role": "user",
            "content": question,
        })
        return self

    def with_source_instruction(self) -> "PromptBuilder":
        """Add instruction to cite sources (appended to last system message)."""
        # Already included in the system prompt
        return self

    def build(self) -> list[dict]:
        """Build and return the final messages array."""
        messages = self._messages.copy()
        self._messages.clear()
        self._system_added = False
        return messages
