"""
Data validator for Vietnamese Grade 12 Math Tutor.

Validates dataset structure, content, and quality.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import get_config
from utils.logger import get_logger

logger = get_logger("data_validator")


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    message: str
    problem_id: Optional[str] = None
    field: Optional[str] = None


class DataValidator:
    """
    Validates math problem datasets.

    Checks:
    - Required fields presence
    - Field types and values
    - Content quality (minimum lengths)
    - Consistency (grade, language, topic values)
    """

    REQUIRED_FIELDS = [
        "id", "question", "solution", "answer", "grade",
        "topic", "subtopic", "difficulty", "language"
    ]

    VALID_TOPICS = [
        "calculus", "spatial_geometry", "coordinate_geometry_3d", "probability_statistics"
    ]

    VALID_DIFFICULTIES = ["de", "trung binh", "kho", "easy", "medium", "hard"]

    VALID_LANGUAGES = ["vi", "en"]

    MIN_QUESTION_LENGTH = 10
    MIN_SOLUTION_LENGTH = 50

    def __init__(self):
        """Initialize the validator."""
        self.config = get_config()
        self.errors: List[ValidationResult] = []
        self.warnings: List[ValidationResult] = []

    def validate_file(self, file_path: Path) -> Tuple[bool, List[ValidationResult]]:
        """
        Validate a dataset JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Tuple of (is_valid, list of validation results)
        """
        self.errors = []
        self.warnings = []

        # Check file exists
        if not file_path.exists():
            self.errors.append(ValidationResult(
                is_valid=False,
                message=f"File not found: {file_path}"
            ))
            return False, self.errors

        # Load and parse JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(ValidationResult(
                is_valid=False,
                message=f"Invalid JSON: {str(e)}"
            ))
            return False, self.errors

        # Validate structure
        self._validate_structure(data)

        # Validate metadata
        if "metadata" in data:
            self._validate_metadata(data["metadata"])

        # Validate each problem
        for i, problem in enumerate(data.get("problems", [])):
            self._validate_problem(problem, i)

        is_valid = len(self.errors) == 0

        all_results = self.errors + self.warnings
        return is_valid, all_results

    def _validate_structure(self, data: Dict) -> None:
        """Validate overall dataset structure."""
        if "problems" not in data:
            self.errors.append(ValidationResult(
                is_valid=False,
                message="Missing 'problems' array in dataset"
            ))
            return

        if not isinstance(data["problems"], list):
            self.errors.append(ValidationResult(
                is_valid=False,
                message="'problems' must be an array"
            ))
            return

        if len(data["problems"]) == 0:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message="Dataset is empty (0 problems)"
            ))

    def _validate_metadata(self, metadata: Dict) -> None:
        """Validate dataset metadata."""
        if "version" not in metadata:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message="Missing 'version' in metadata"
            ))

        if "grade" in metadata and metadata["grade"] != 12:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message=f"Unexpected grade in metadata: {metadata['grade']} (expected 12)"
            ))

    def _validate_problem(self, problem: Dict, index: int) -> None:
        """Validate a single problem."""
        problem_id = problem.get("id", f"problem_{index}")

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in problem:
                self.errors.append(ValidationResult(
                    is_valid=False,
                    message=f"Missing required field: {field}",
                    problem_id=problem_id,
                    field=field
                ))

        # Validate field values
        self._validate_field_values(problem, problem_id)

        # Validate content quality
        self._validate_content_quality(problem, problem_id)

    def _validate_field_values(self, problem: Dict, problem_id: str) -> None:
        """Validate field values are valid."""
        # Topic
        topic = problem.get("topic", "")
        if topic and topic not in self.VALID_TOPICS:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message=f"Unknown topic: {topic}",
                problem_id=problem_id,
                field="topic"
            ))

        # Difficulty
        difficulty = problem.get("difficulty", "")
        if difficulty and difficulty not in self.VALID_DIFFICULTIES:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message=f"Unknown difficulty: {difficulty}",
                problem_id=problem_id,
                field="difficulty"
            ))

        # Language
        language = problem.get("language", "")
        if language and language not in self.VALID_LANGUAGES:
            self.errors.append(ValidationResult(
                is_valid=False,
                message=f"Invalid language: {language}",
                problem_id=problem_id,
                field="language"
            ))

        # Grade
        grade = problem.get("grade", 0)
        if grade != 12:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message=f"Unexpected grade: {grade} (expected 12)",
                problem_id=problem_id,
                field="grade"
            ))

    def _validate_content_quality(self, problem: Dict, problem_id: str) -> None:
        """Validate content meets quality standards."""
        # Question length
        question = problem.get("question", "")
        if len(question) < self.MIN_QUESTION_LENGTH:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message=f"Question too short ({len(question)} chars)",
                problem_id=problem_id,
                field="question"
            ))

        # Solution length
        solution = problem.get("solution", "")
        if len(solution) < self.MIN_SOLUTION_LENGTH:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message=f"Solution too short ({len(solution)} chars)",
                problem_id=problem_id,
                field="solution"
            ))

        # Answer presence
        answer = problem.get("answer", "")
        if not answer:
            self.warnings.append(ValidationResult(
                is_valid=True,
                message="Empty answer field",
                problem_id=problem_id,
                field="answer"
            ))

    def print_report(self) -> None:
        """Print validation report to console."""
        print("\n" + "=" * 60)
        print("VALIDATION REPORT")
        print("=" * 60)

        if self.errors:
            print(f"\nERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ❌ [{error.problem_id or 'global'}] {error.message}")

        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠️  [{warning.problem_id or 'global'}] {warning.message}")

        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")

        print("=" * 60)


def validate_problem(problem: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a single problem dictionary.

    Args:
        problem: Problem dictionary to validate

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    validator = DataValidator()
    validator._validate_problem(problem, 0)

    errors = [r.message for r in validator.errors]
    return len(errors) == 0, errors


if __name__ == "__main__":
    # Test validation
    config = get_config()
    validator = DataValidator()

    dataset_path = config.DATA_DIR / "grade12_math_dataset.json"
    is_valid, results = validator.validate_file(dataset_path)

    validator.print_report()

    print(f"\nDataset is {'valid' if is_valid else 'INVALID'}")
    print(f"Errors: {len(validator.errors)}, Warnings: {len(validator.warnings)}")
