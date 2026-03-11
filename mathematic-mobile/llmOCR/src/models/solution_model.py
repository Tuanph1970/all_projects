"""
Solution generation model for mathematical problem solving.
"""
import time
import re
from typing import Any, Dict, List, Optional, Union
import torch
from PIL import Image
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from loguru import logger

from ..infrastructure.ml.base import BaseMLModel
from ..domain.shared.value_objects import ModelType, SolutionResult
from ..utils.math_parser import MathExpressionParser


class SolutionModel(BaseMLModel):
    """Mathematical problem solving model."""

    def __init__(
        self,
        model_name: str = "microsoft/DialoGPT-medium",
        device: str = "cpu",
        confidence_threshold: float = 0.7
    ):
        super().__init__(model_name, device)
        self.confidence_threshold = confidence_threshold
        self.tokenizer: Optional[AutoTokenizer] = None
        self.math_parser = MathExpressionParser()

    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load the solution generation model."""
        try:
            start_time = time.time()
            logger.info(f"Loading solution model: {self.model_name}")

            # For basic implementation, we'll use a simple approach
            # In production, you might want to use specialized math models
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
            self.model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")

            if self.device != "cpu":
                self.model = self.model.to(self.device)

            self.model.eval()

            self._load_time = time.time() - start_time
            self.is_loaded = True

            logger.info(f"Solution model loaded successfully in {self._load_time:.2f}s")

        except Exception as e:
            logger.error(f"Failed to load solution model: {str(e)}")
            raise RuntimeError(f"Solution model loading failed: {str(e)}")

    def predict(self, input_data: Union[str, Dict[str, Any]]) -> SolutionResult:
        """
        Generate solution for mathematical problem.

        Args:
            input_data: Mathematical expression/problem as string or dict with problem info

        Returns:
            SolutionResult containing solution steps and answer
        """
        if not self.is_model_loaded():
            raise RuntimeError("Solution model is not loaded")

        start_time = time.time()

        try:
            # Extract problem text
            if isinstance(input_data, dict):
                problem_text = input_data.get('problem', '')
                context = input_data.get('context', {})
            else:
                problem_text = str(input_data)
                context = {}

            if not problem_text.strip():
                return SolutionResult(
                    success=False,
                    problem_type="unknown",
                    solution="No problem text provided",
                    steps=[],
                    final_answer="",
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    metadata={"error": "Empty problem text"}
                )

            # Try to solve using built-in math parser first
            basic_solution = self._solve_basic_math(problem_text)

            if basic_solution['success']:
                processing_time = time.time() - start_time
                return SolutionResult(
                    success=True,
                    problem_type=basic_solution.get('problem_type', 'unknown'),
                    solution=basic_solution['solution'],
                    steps=basic_solution['steps'],
                    final_answer=basic_solution['answer'],
                    confidence=basic_solution['confidence'],
                    processing_time=processing_time,
                    metadata={
                        "method": "basic_math_parser",
                        "problem_type": basic_solution.get('problem_type', 'arithmetic'),
                        **context
                    }
                )

            # Fallback to NLP model for complex problems
            nlp_solution = self._solve_with_nlp(problem_text)

            processing_time = time.time() - start_time

            return SolutionResult(
                success=nlp_solution['success'],
                problem_type=nlp_solution.get('problem_type', 'unknown'),
                solution=nlp_solution['solution'],
                steps=nlp_solution['steps'],
                final_answer=nlp_solution['answer'],
                confidence=nlp_solution['confidence'],
                processing_time=processing_time,
                metadata={
                    "method": "nlp_model",
                    "model_used": self.model_name,
                    **context
                }
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Solution generation failed: {str(e)}")

            return SolutionResult(
                success=False,
                problem_type="unknown",
                solution="",
                steps=[],
                final_answer="",
                confidence=0.0,
                processing_time=processing_time,
                metadata={"error": str(e)}
            )

    def _solve_basic_math(self, problem_text: str) -> Dict[str, Any]:
        """Solve basic mathematical expressions using built-in parser."""
        try:
            # Clean and normalize the problem text
            normalized_problem = self._normalize_math_expression(problem_text)

            # Try to evaluate simple mathematical expressions
            if self._is_simple_arithmetic(normalized_problem):
                try:
                    # Use safe evaluation for basic arithmetic
                    result = self.math_parser.evaluate_expression(normalized_problem)

                    return {
                        'success': True,
                        'solution': f"Evaluating: {normalized_problem}",
                        'steps': [
                            f"Expression: {normalized_problem}",
                            f"Calculation: {result}",
                            f"Answer: {result}"
                        ],
                        'answer': str(result),
                        'confidence': 0.9,
                        'problem_type': 'arithmetic'
                    }
                except Exception as e:
                    logger.warning(f"Arithmetic evaluation failed: {e}")

            # Handle algebraic expressions
            if self._is_algebraic_expression(normalized_problem):
                return self._solve_algebraic(normalized_problem)

            return {'success': False, 'reason': 'Problem type not supported by basic parser'}

        except Exception as e:
            logger.error(f"Basic math solving failed: {e}")
            return {'success': False, 'reason': str(e)}

    def _solve_with_nlp(self, problem_text: str) -> Dict[str, Any]:
        """Solve problem using NLP model."""
        try:
            # Prepare prompt for the model
            prompt = f"Solve this mathematical problem step by step: {problem_text}"

            # Generate solution using the model
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)

            if self.device != "cpu":
                inputs = inputs.to(self.device)

            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=256,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            # Decode the response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract solution from response
            solution_text = response.replace(prompt, "").strip()

            # Try to extract steps and final answer
            steps = self._extract_solution_steps(solution_text)
            final_answer = self._extract_final_answer(solution_text)

            return {
                'success': len(steps) > 0,
                'solution': solution_text,
                'steps': steps,
                'answer': final_answer,
                'confidence': 0.6  # Lower confidence for NLP-generated solutions
            }

        except Exception as e:
            logger.error(f"NLP solution generation failed: {e}")
            return {
                'success': False,
                'solution': "",
                'steps': [],
                'answer': "",
                'confidence': 0.0,
                'reason': str(e)
            }

    def _normalize_math_expression(self, expression: str) -> str:
        """Normalize mathematical expression for parsing."""
        # Remove extra whitespace
        expression = re.sub(r'\s+', ' ', expression.strip())

        # Replace common mathematical symbols
        replacements = {
            '×': '*',
            '÷': '/',
            '−': '-',
            'x': '*',  # multiplication
        }

        for old, new in replacements.items():
            expression = expression.replace(old, new)

        return expression

    def _is_simple_arithmetic(self, expression: str) -> bool:
        """Check if expression is simple arithmetic."""
        # Allow numbers, basic operators, parentheses, and decimal points
        pattern = r'^[0-9+\-*/().\s]+$'
        return bool(re.match(pattern, expression))

    def _is_algebraic_expression(self, expression: str) -> bool:
        """Check if expression contains algebraic variables."""
        # Look for variables (letters)
        return bool(re.search(r'[a-zA-Z]', expression))

    def _solve_algebraic(self, expression: str) -> Dict[str, Any]:
        """Basic algebraic solving (placeholder for future enhancement)."""
        # This is a simplified implementation
        # In production, you might want to use SymPy or similar libraries

        return {
            'success': False,
            'solution': "Algebraic solving not yet implemented",
            'steps': ["Algebraic expressions require advanced solving capabilities"],
            'answer': "Not solved",
            'confidence': 0.0,
            'problem_type': 'algebraic'
        }

    def _extract_solution_steps(self, solution_text: str) -> List[str]:
        """Extract solution steps from generated text."""
        # Look for numbered steps or line breaks
        lines = solution_text.split('\n')
        steps = []

        for line in lines:
            line = line.strip()
            if line and (line.startswith(('1.', '2.', '3.', 'Step', '-')) or len(line) > 10):
                steps.append(line)

        return steps[:10]  # Limit to 10 steps

    def _extract_final_answer(self, solution_text: str) -> str:
        """Extract final answer from solution text."""
        # Look for patterns like "Answer:", "Result:", "=" followed by number
        patterns = [
            r'[Aa]nswer[:\s]*([0-9.-]+)',
            r'[Rr]esult[:\s]*([0-9.-]+)',
            r'=\s*([0-9.-]+)(?:\s|$)',
            r'([0-9.-]+)(?:\s|$)'
        ]

        for pattern in patterns:
            match = re.search(pattern, solution_text)
            if match:
                return match.group(1)

        return "No answer found"

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the solution model."""
        info = {
            "model_name": self.model_name,
            "model_type": ModelType.SOLUTION.value,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "confidence_threshold": self.confidence_threshold,
            "supported_problems": ["arithmetic", "basic_algebra", "word_problems"]
        }

        if self._load_time is not None:
            info["load_time_seconds"] = self._load_time

        if self.is_loaded and hasattr(self.model, 'parameters'):
            try:
                total_params = sum(p.numel() for p in self.model.parameters())
                info.update({
                    "total_parameters": total_params,
                    "model_size_mb": total_params * 4 / (1024 * 1024)
                })
            except Exception as e:
                logger.warning(f"Could not get model parameter info: {e}")

        info.update(self.get_device_info())

        return info

    def set_confidence_threshold(self, threshold: float) -> None:
        """Set the confidence threshold for solutions."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        self.confidence_threshold = threshold
        logger.info(f"Solution confidence threshold set to {threshold}")

    def validate_result(self, result: SolutionResult) -> bool:
        """Validate solution result against confidence threshold."""
        return result.success and result.confidence >= self.confidence_threshold
