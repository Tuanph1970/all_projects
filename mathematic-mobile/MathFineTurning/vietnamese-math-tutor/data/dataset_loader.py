"""
Dataset loader for Vietnamese Grade 12 Math Tutor.

Handles loading, formatting, and splitting the math problem dataset.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Generator
from dataclasses import dataclass
import random

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import get_config
from utils.logger import get_logger

logger = get_logger("dataset_loader")


@dataclass
class MathProblem:
    """Represents a single math problem."""
    id: str
    question: str
    solution: str
    answer: str
    grade: int
    topic: str
    subtopic: str
    difficulty: str
    language: str
    requires_computation: bool
    requires_graph: bool
    keywords: List[str]

    def to_training_format(self, include_answer: bool = True) -> Dict[str, str]:
        """
        Convert to format suitable for fine-tuning.

        Returns:
            Dict with 'instruction' and 'output' keys
        """
        instruction = self.question
        output = self.solution
        if include_answer and self.answer:
            output += f"\n\n**Dap an:** {self.answer}"

        return {
            "instruction": instruction,
            "output": output,
            "input": "",  # Empty for direct Q&A format
        }

    def to_chat_format(self) -> List[Dict[str, str]]:
        """
        Convert to chat format for instruction tuning.

        Returns:
            List of message dicts with 'role' and 'content'
        """
        return [
            {"role": "user", "content": self.question},
            {"role": "assistant", "content": self.solution},
        ]


class DatasetLoader:
    """
    Loads and processes the Grade 12 math dataset.

    Features:
    - Load from JSON file
    - Filter by topic, difficulty, language
    - Split into train/validation sets
    - Convert to various training formats
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize the dataset loader.

        Args:
            data_path: Path to dataset JSON file. Uses default if not provided.
        """
        self.config = get_config()

        if data_path is None:
            data_path = self.config.DATA_DIR / "grade12_math_dataset.json"

        self.data_path = Path(data_path)
        self.problems: List[MathProblem] = []
        self.metadata: Dict = {}

        self._load_dataset()

    def _load_dataset(self) -> None:
        """Load dataset from JSON file."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")

        logger.info(f"Loading dataset from {self.data_path}")

        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.metadata = data.get("metadata", {})

        for problem_data in data.get("problems", []):
            problem = MathProblem(
                id=problem_data.get("id", ""),
                question=problem_data.get("question", ""),
                solution=problem_data.get("solution", ""),
                answer=problem_data.get("answer", ""),
                grade=problem_data.get("grade", 12),
                topic=problem_data.get("topic", ""),
                subtopic=problem_data.get("subtopic", ""),
                difficulty=problem_data.get("difficulty", ""),
                language=problem_data.get("language", "vi"),
                requires_computation=problem_data.get("requires_computation", False),
                requires_graph=problem_data.get("requires_graph", False),
                keywords=problem_data.get("keywords", []),
            )
            self.problems.append(problem)

        logger.info(f"Loaded {len(self.problems)} problems")

    def filter(
        self,
        topic: Optional[str] = None,
        subtopic: Optional[str] = None,
        difficulty: Optional[str] = None,
        language: Optional[str] = None,
        requires_computation: Optional[bool] = None,
    ) -> List[MathProblem]:
        """
        Filter problems by criteria.

        Args:
            topic: Filter by topic (e.g., "calculus")
            subtopic: Filter by subtopic (e.g., "derivative")
            difficulty: Filter by difficulty ("de", "trung binh", "kho")
            language: Filter by language ("vi", "en")
            requires_computation: Filter by computation requirement

        Returns:
            List of filtered MathProblem objects
        """
        filtered = self.problems

        if topic:
            filtered = [p for p in filtered if p.topic == topic]
        if subtopic:
            filtered = [p for p in filtered if p.subtopic == subtopic]
        if difficulty:
            filtered = [p for p in filtered if p.difficulty == difficulty]
        if language:
            filtered = [p for p in filtered if p.language == language]
        if requires_computation is not None:
            filtered = [p for p in filtered if p.requires_computation == requires_computation]

        return filtered

    def split(
        self,
        train_ratio: float = 0.85,
        seed: int = 42,
        stratify_by: Optional[str] = "topic",
    ) -> Tuple[List[MathProblem], List[MathProblem]]:
        """
        Split dataset into training and validation sets.

        Args:
            train_ratio: Ratio of training data (default: 0.85)
            seed: Random seed for reproducibility
            stratify_by: Field to stratify by ("topic", "difficulty", None)

        Returns:
            Tuple of (train_problems, val_problems)
        """
        random.seed(seed)

        if stratify_by is None:
            # Simple random split
            problems = self.problems.copy()
            random.shuffle(problems)
            split_idx = int(len(problems) * train_ratio)
            return problems[:split_idx], problems[split_idx:]

        # Stratified split
        groups: Dict[str, List[MathProblem]] = {}
        for problem in self.problems:
            key = getattr(problem, stratify_by, "unknown")
            if key not in groups:
                groups[key] = []
            groups[key].append(problem)

        train_problems = []
        val_problems = []

        for key, group in groups.items():
            random.shuffle(group)
            split_idx = max(1, int(len(group) * train_ratio))
            train_problems.extend(group[:split_idx])
            val_problems.extend(group[split_idx:])

        random.shuffle(train_problems)
        random.shuffle(val_problems)

        logger.info(f"Split: {len(train_problems)} train, {len(val_problems)} val")
        return train_problems, val_problems

    def to_training_dataset(
        self,
        problems: Optional[List[MathProblem]] = None,
        format: str = "instruction",
    ) -> List[Dict]:
        """
        Convert problems to training format.

        Args:
            problems: List of problems to convert (uses all if None)
            format: Output format ("instruction", "chat", "raw")

        Returns:
            List of training examples
        """
        if problems is None:
            problems = self.problems

        if format == "instruction":
            return [p.to_training_format() for p in problems]
        elif format == "chat":
            return [p.to_chat_format() for p in problems]
        elif format == "raw":
            return [{"question": p.question, "solution": p.solution, "answer": p.answer}
                    for p in problems]
        else:
            raise ValueError(f"Unknown format: {format}")

    def get_by_id(self, problem_id: str) -> Optional[MathProblem]:
        """Get a specific problem by ID."""
        for problem in self.problems:
            if problem.id == problem_id:
                return problem
        return None

    def get_topics(self) -> List[str]:
        """Get list of unique topics."""
        return list(set(p.topic for p in self.problems))

    def get_subtopics(self, topic: Optional[str] = None) -> List[str]:
        """Get list of unique subtopics, optionally filtered by topic."""
        problems = self.filter(topic=topic) if topic else self.problems
        return list(set(p.subtopic for p in problems))

    def get_statistics(self) -> Dict:
        """Get dataset statistics."""
        stats = {
            "total_problems": len(self.problems),
            "by_topic": {},
            "by_difficulty": {},
            "by_language": {},
            "requires_computation": sum(1 for p in self.problems if p.requires_computation),
            "requires_graph": sum(1 for p in self.problems if p.requires_graph),
        }

        for problem in self.problems:
            # By topic
            if problem.topic not in stats["by_topic"]:
                stats["by_topic"][problem.topic] = 0
            stats["by_topic"][problem.topic] += 1

            # By difficulty
            if problem.difficulty not in stats["by_difficulty"]:
                stats["by_difficulty"][problem.difficulty] = 0
            stats["by_difficulty"][problem.difficulty] += 1

            # By language
            if problem.language not in stats["by_language"]:
                stats["by_language"][problem.language] = 0
            stats["by_language"][problem.language] += 1

        return stats

    def __len__(self) -> int:
        return len(self.problems)

    def __iter__(self) -> Generator[MathProblem, None, None]:
        yield from self.problems

    def __getitem__(self, idx: int) -> MathProblem:
        return self.problems[idx]


def load_dataset(data_path: Optional[Path] = None) -> DatasetLoader:
    """
    Convenience function to load the dataset.

    Args:
        data_path: Optional path to dataset file

    Returns:
        DatasetLoader instance
    """
    return DatasetLoader(data_path)


if __name__ == "__main__":
    # Test dataset loading
    loader = load_dataset()

    print(f"Loaded {len(loader)} problems")
    print(f"Topics: {loader.get_topics()}")
    print(f"\nStatistics:")
    stats = loader.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test split
    train, val = loader.split()
    print(f"\nSplit: {len(train)} train, {len(val)} val")

    # Test filtering
    calculus = loader.filter(topic="calculus")
    print(f"\nCalculus problems: {len(calculus)}")

    # Test training format
    training_data = loader.to_training_dataset(calculus[:2])
    print(f"\nSample training data:")
    for item in training_data:
        print(f"  Instruction: {item['instruction'][:50]}...")
