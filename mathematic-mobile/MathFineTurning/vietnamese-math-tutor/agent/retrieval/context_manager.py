"""
Conversation Context Manager for KG-RAG system.

Tracks conversation state for context-aware retrieval and personalization.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class FormulaInteraction:
    """Record of interaction with a formula."""

    formula_id: str
    timestamp: datetime
    interaction_type: str  # "viewed", "explained", "calculated", "practiced"
    context: str = ""  # Query or problem context
    success: bool = True  # Was the interaction successful/understood


@dataclass
class ProblemAttempt:
    """Record of a problem attempt."""

    problem_id: str
    problem_text: str
    topic: str
    timestamp: datetime
    correct: bool
    formulas_used: List[str] = field(default_factory=list)
    time_spent_seconds: int = 0


@dataclass
class StudentKnowledgeState:
    """Representation of student's knowledge state."""

    known_formulas: Set[str] = field(default_factory=set)
    weak_formulas: Set[str] = field(default_factory=set)  # Struggled with
    mastered_formulas: Set[str] = field(default_factory=set)  # High confidence
    topic_proficiency: Dict[str, float] = field(default_factory=dict)  # 0-1 scores

    def to_dict(self) -> Dict[str, Any]:
        return {
            "known_formulas": list(self.known_formulas),
            "weak_formulas": list(self.weak_formulas),
            "mastered_formulas": list(self.mastered_formulas),
            "topic_proficiency": self.topic_proficiency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentKnowledgeState":
        return cls(
            known_formulas=set(data.get("known_formulas", [])),
            weak_formulas=set(data.get("weak_formulas", [])),
            mastered_formulas=set(data.get("mastered_formulas", [])),
            topic_proficiency=data.get("topic_proficiency", {}),
        )


class ConversationContextManager:
    """
    Tracks conversation state for context-aware retrieval.

    Features:
    - Formula interaction history
    - Student knowledge state tracking
    - Learning gap detection
    - Personalized retrieval context
    - Session persistence
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        max_history: int = 50,
        persist_dir: Optional[str] = None,
    ):
        """
        Initialize context manager.

        Args:
            session_id: Unique session identifier
            max_history: Maximum interaction history to keep
            persist_dir: Directory for session persistence
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.max_history = max_history
        self.persist_dir = Path(persist_dir) if persist_dir else None

        # Conversation state
        self.formula_history: List[str] = []
        self.topic_history: List[str] = []
        self.query_history: List[str] = []
        self.interactions: List[FormulaInteraction] = []
        self.problem_attempts: List[ProblemAttempt] = []

        # Student knowledge state
        self.knowledge_state = StudentKnowledgeState()

        # Current problem context
        self.current_problem: Optional[str] = None
        self.current_topic: Optional[str] = None

        # Load persisted state if available
        if self.persist_dir:
            self._load_state()

        logger.info(f"Context manager initialized for session: {self.session_id}")

    def add_formula_interaction(
        self,
        formula_id: str,
        interaction_type: str = "viewed",
        context: str = "",
        success: bool = True,
    ):
        """
        Record a formula interaction.

        Args:
            formula_id: Formula ID
            interaction_type: Type of interaction
            context: Query or problem context
            success: Whether interaction was successful
        """
        interaction = FormulaInteraction(
            formula_id=formula_id,
            timestamp=datetime.now(),
            interaction_type=interaction_type,
            context=context,
            success=success,
        )

        self.interactions.append(interaction)
        self._trim_history(self.interactions)

        # Update formula history
        self.formula_history.append(formula_id)
        self._trim_history(self.formula_history)

        # Update knowledge state
        self._update_knowledge_state(formula_id, interaction_type, success)

        logger.debug(f"Recorded {interaction_type} interaction with {formula_id}")

    def add_query(self, query: str, topic: Optional[str] = None):
        """
        Record a search query.

        Args:
            query: Search query
            topic: Detected topic (optional)
        """
        self.query_history.append(query)
        self._trim_history(self.query_history)

        if topic:
            self.topic_history.append(topic)
            self._trim_history(self.topic_history)
            self.current_topic = topic

    def add_problem_attempt(
        self,
        problem_id: str,
        problem_text: str,
        topic: str,
        correct: bool,
        formulas_used: List[str],
        time_spent_seconds: int = 0,
    ):
        """
        Record a problem attempt.

        Args:
            problem_id: Problem identifier
            problem_text: Problem statement
            topic: Problem topic
            correct: Whether answer was correct
            formulas_used: Formulas used in solution
            time_spent_seconds: Time spent on problem
        """
        attempt = ProblemAttempt(
            problem_id=problem_id,
            problem_text=problem_text,
            topic=topic,
            timestamp=datetime.now(),
            correct=correct,
            formulas_used=formulas_used,
            time_spent_seconds=time_spent_seconds,
        )

        self.problem_attempts.append(attempt)
        self._trim_history(self.problem_attempts)

        # Update knowledge state
        for formula_id in formulas_used:
            self._update_knowledge_state(
                formula_id,
                "practiced",
                correct,
            )

        # Update topic proficiency
        self._update_topic_proficiency(topic, correct)

        logger.debug(f"Recorded problem attempt: {problem_id}, correct={correct}")

    def _update_knowledge_state(
        self,
        formula_id: str,
        interaction_type: str,
        success: bool,
    ):
        """Update student knowledge state based on interaction."""
        if success:
            self.knowledge_state.known_formulas.add(formula_id)
            self.knowledge_state.weak_formulas.discard(formula_id)

            # Track mastery
            if interaction_type == "practiced":
                # Count successful uses
                successful_uses = sum(
                    1
                    for i in self.interactions
                    if i.formula_id == formula_id
                    and i.interaction_type == "practiced"
                    and i.success
                )
                if successful_uses >= 3:
                    self.knowledge_state.mastered_formulas.add(formula_id)
        else:
            self.knowledge_state.weak_formulas.add(formula_id)
            self.knowledge_state.mastered_formulas.discard(formula_id)

    def _update_topic_proficiency(self, topic: str, success: bool):
        """Update topic proficiency based on problem attempt."""
        current = self.knowledge_state.topic_proficiency.get(topic, 0.5)

        # Simple exponential moving average
        alpha = 0.3
        new_value = 1.0 if success else 0.0
        updated = alpha * new_value + (1 - alpha) * current

        self.knowledge_state.topic_proficiency[topic] = updated

    def get_context_formulas(self, n: int = 5) -> List[str]:
        """
        Get recent formulas for retrieval context.

        Args:
            n: Number of recent formulas

        Returns:
            List of recent formula IDs
        """
        # Deduplicate while preserving recency order
        seen = set()
        result = []

        for formula_id in reversed(self.formula_history):
            if formula_id not in seen:
                seen.add(formula_id)
                result.append(formula_id)
            if len(result) >= n:
                break

        return result

    def get_recent_topics(self, n: int = 3) -> List[str]:
        """Get recent topics for context."""
        seen = set()
        result = []

        for topic in reversed(self.topic_history):
            if topic not in seen:
                seen.add(topic)
                result.append(topic)
            if len(result) >= n:
                break

        return result

    def get_learning_gaps(
        self,
        target_formula: str,
        knowledge_graph,  # FormulaKnowledgeGraph
    ) -> List[str]:
        """
        Find prerequisite formulas student hasn't learned.

        Args:
            target_formula: Formula student wants to learn
            knowledge_graph: KG instance

        Returns:
            List of formula IDs student needs to learn first
        """
        prereq_paths = knowledge_graph.find_prerequisites(target_formula, max_depth=3)

        gaps = []
        for path in prereq_paths:
            for node_id in path.nodes:
                if (
                    node_id != target_formula
                    and not node_id.startswith("concept_")
                    and node_id not in self.knowledge_state.known_formulas
                ):
                    gaps.append(node_id)

        # Remove duplicates while preserving order
        seen = set()
        unique_gaps = []
        for gap in gaps:
            if gap not in seen:
                seen.add(gap)
                unique_gaps.append(gap)

        return unique_gaps

    def get_weak_areas(self) -> Dict[str, Any]:
        """
        Identify areas where student needs improvement.

        Returns:
            Dictionary of weak areas with details
        """
        weak_areas = {
            "formulas": list(self.knowledge_state.weak_formulas),
            "topics": [],
        }

        # Find low-proficiency topics
        for topic, proficiency in self.knowledge_state.topic_proficiency.items():
            if proficiency < 0.6:
                weak_areas["topics"].append({
                    "topic": topic,
                    "proficiency": round(proficiency, 2),
                })

        # Sort topics by proficiency
        weak_areas["topics"].sort(key=lambda x: x["proficiency"])

        return weak_areas

    def get_recommended_review(self, knowledge_graph) -> List[str]:
        """
        Get recommended formulas for review.

        Args:
            knowledge_graph: KG instance

        Returns:
            List of formula IDs to review
        """
        recommendations = []

        # Add weak formulas
        recommendations.extend(self.knowledge_state.weak_formulas)

        # Add prerequisites of weak formulas
        for weak_id in self.knowledge_state.weak_formulas:
            prereqs = knowledge_graph.find_prerequisites(weak_id, max_depth=1)
            for path in prereqs:
                for node_id in path.nodes:
                    if (
                        not node_id.startswith("concept_")
                        and node_id not in self.knowledge_state.mastered_formulas
                    ):
                        recommendations.append(node_id)

        # Remove duplicates
        seen = set()
        unique = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique.append(rec)

        return unique[:10]  # Limit to 10 recommendations

    def get_retrieval_context(self) -> Dict[str, Any]:
        """
        Get context dictionary for retrieval system.

        Returns:
            Context for hybrid retriever
        """
        return {
            "recent_formulas": self.get_context_formulas(5),
            "recent_topics": self.get_recent_topics(3),
            "current_topic": self.current_topic,
            "known_formulas": list(self.knowledge_state.known_formulas),
            "weak_formulas": list(self.knowledge_state.weak_formulas),
            "topic_proficiency": self.knowledge_state.topic_proficiency,
        }

    def _trim_history(self, history_list: list):
        """Trim history to max length."""
        while len(history_list) > self.max_history:
            history_list.pop(0)

    def _load_state(self):
        """Load persisted state from disk."""
        if not self.persist_dir:
            return

        state_file = self.persist_dir / f"session_{self.session_id}.json"
        if not state_file.exists():
            return

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.formula_history = data.get("formula_history", [])
            self.topic_history = data.get("topic_history", [])
            self.query_history = data.get("query_history", [])
            self.knowledge_state = StudentKnowledgeState.from_dict(
                data.get("knowledge_state", {})
            )

            logger.info(f"Loaded state for session {self.session_id}")

        except Exception as e:
            logger.warning(f"Failed to load session state: {e}")

    def save_state(self):
        """Save state to disk."""
        if not self.persist_dir:
            return

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.persist_dir / f"session_{self.session_id}.json"

        try:
            data = {
                "session_id": self.session_id,
                "formula_history": self.formula_history,
                "topic_history": self.topic_history,
                "query_history": self.query_history,
                "knowledge_state": self.knowledge_state.to_dict(),
                "saved_at": datetime.now().isoformat(),
            }

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved state for session {self.session_id}")

        except Exception as e:
            logger.warning(f"Failed to save session state: {e}")

    def reset(self):
        """Reset conversation state."""
        self.formula_history.clear()
        self.topic_history.clear()
        self.query_history.clear()
        self.interactions.clear()
        self.problem_attempts.clear()
        self.current_problem = None
        self.current_topic = None
        # Keep knowledge state for continuity

        logger.info(f"Reset context for session {self.session_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        total_attempts = len(self.problem_attempts)
        correct_attempts = sum(1 for a in self.problem_attempts if a.correct)

        return {
            "session_id": self.session_id,
            "total_interactions": len(self.interactions),
            "unique_formulas_viewed": len(set(self.formula_history)),
            "total_problems_attempted": total_attempts,
            "problems_correct": correct_attempts,
            "accuracy": correct_attempts / total_attempts if total_attempts > 0 else 0,
            "formulas_known": len(self.knowledge_state.known_formulas),
            "formulas_mastered": len(self.knowledge_state.mastered_formulas),
            "formulas_weak": len(self.knowledge_state.weak_formulas),
            "topics_practiced": len(self.knowledge_state.topic_proficiency),
        }

    @property
    def info(self) -> Dict[str, Any]:
        """Get context manager info."""
        return {
            "session_id": self.session_id,
            "max_history": self.max_history,
            "persist_enabled": self.persist_dir is not None,
            "statistics": self.get_statistics(),
        }
