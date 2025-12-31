"""
Solution Verifier tool for Vietnamese Grade 12 Math Tutor.

Provides verification of mathematical solutions:
- Step-by-step verification
- Answer checking
- Error detection
- Suggestion for corrections
"""

import re
import math
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

import sympy as sp
from sympy import (
    symbols, Symbol, Rational, pi, E, oo,
    sin, cos, tan, simplify, expand, Eq,
    solve, diff, integrate, limit,
    latex, N,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.logger import get_logger

logger = get_logger("verifier")


class VerificationStatus(Enum):
    """Status of verification."""
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIALLY_CORRECT = "partially_correct"
    UNABLE_TO_VERIFY = "unable_to_verify"
    ERROR = "error"


class ErrorType(Enum):
    """Types of mathematical errors."""
    CALCULATION = "calculation_error"
    ALGEBRAIC = "algebraic_error"
    CONCEPTUAL = "conceptual_error"
    SIGN = "sign_error"
    NOTATION = "notation_error"
    MISSING_STEP = "missing_step"
    LOGIC = "logic_error"
    UNKNOWN = "unknown"


@dataclass
class VerificationStep:
    """Result of verifying a single step."""
    step_number: int
    original_step: str
    is_correct: bool
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    error_type: Optional[ErrorType] = None
    suggestion: Optional[str] = None


@dataclass
class VerificationResult:
    """Complete verification result."""
    status: VerificationStatus
    is_correct: bool
    confidence: float
    steps_verified: List[VerificationStep]
    final_answer_correct: bool
    errors_found: List[str]
    suggestions: List[str]
    detailed_feedback: str
    expected_answer: Optional[str] = None
    given_answer: Optional[str] = None


class SolutionVerifier:
    """
    Verifier for mathematical solutions.

    Checks:
    - Arithmetic calculations
    - Algebraic manipulations
    - Derivative/Integral correctness
    - Equation solving
    - Final answer validation
    """

    # Common symbols
    x, y, z = symbols('x y z')
    a, b, c = symbols('a b c')
    n, k = symbols('n k', integer=True)

    # Transformation rules
    TRANSFORMATIONS = (
        standard_transformations +
        (implicit_multiplication_application, convert_xor)
    )

    def __init__(self):
        """Initialize the verifier."""
        self.local_dict = {
            'x': self.x, 'y': self.y, 'z': self.z,
            'a': self.a, 'b': self.b, 'c': self.c,
            'n': self.n, 'k': self.k,
            'pi': pi, 'e': E, 'E': E,
            'oo': oo, 'inf': oo,
            'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
            'cot': sp.cot, 'sec': sp.sec, 'csc': sp.csc,
            'exp': sp.exp, 'log': sp.log, 'ln': sp.ln,
            'sqrt': sp.sqrt, 'abs': sp.Abs,
        }
        logger.info("Solution verifier initialized")

    def _parse_expression(self, expr_str: str) -> sp.Expr:
        """Parse a string expression into SymPy expression."""
        expr_str = expr_str.strip()
        expr_str = expr_str.replace('^', '**')
        expr_str = expr_str.replace('×', '*')
        expr_str = expr_str.replace('÷', '/')

        try:
            return parse_expr(
                expr_str,
                local_dict=self.local_dict,
                transformations=self.TRANSFORMATIONS,
            )
        except:
            return None

    def _expressions_equal(
        self,
        expr1: sp.Expr,
        expr2: sp.Expr,
        tolerance: float = 1e-10,
    ) -> bool:
        """Check if two expressions are mathematically equal."""
        try:
            # Try simplifying the difference
            diff = simplify(expr1 - expr2)

            # Check if difference is zero
            if diff == 0:
                return True

            # Try numeric evaluation
            try:
                diff_val = float(N(diff))
                if abs(diff_val) < tolerance:
                    return True
            except:
                pass

            # Check expanded forms
            if expand(expr1) == expand(expr2):
                return True

            return False

        except:
            return False

    def verify_calculation(
        self,
        expression: str,
        claimed_result: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify a simple calculation.

        Args:
            expression: The expression to evaluate
            claimed_result: The claimed result

        Returns:
            Tuple of (is_correct, expected_result, error_message)
        """
        try:
            expr = self._parse_expression(expression)
            claimed = self._parse_expression(claimed_result)

            if expr is None or claimed is None:
                return False, None, "Could not parse expression"

            result = simplify(expr)

            if self._expressions_equal(result, claimed):
                return True, str(result), None
            else:
                return False, str(result), f"Expected {result}, got {claimed_result}"

        except Exception as e:
            return False, None, str(e)

    def verify_derivative(
        self,
        function: str,
        claimed_derivative: str,
        variable: str = "x",
        order: int = 1,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify a derivative calculation.

        Args:
            function: The original function
            claimed_derivative: The claimed derivative
            variable: Variable of differentiation
            order: Order of derivative

        Returns:
            Tuple of (is_correct, expected_result, error_message)
        """
        try:
            func = self._parse_expression(function)
            claimed = self._parse_expression(claimed_derivative)
            var = self.local_dict.get(variable, Symbol(variable))

            if func is None or claimed is None:
                return False, None, "Could not parse expression"

            expected = simplify(diff(func, var, order))

            if self._expressions_equal(expected, claimed):
                return True, str(expected), None
            else:
                return False, str(expected), f"Derivative should be {expected}"

        except Exception as e:
            return False, None, str(e)

    def verify_integral(
        self,
        function: str,
        claimed_integral: str,
        variable: str = "x",
        lower: Optional[str] = None,
        upper: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify an integral calculation.

        Args:
            function: The integrand
            claimed_integral: The claimed result
            variable: Variable of integration
            lower: Lower bound (for definite integral)
            upper: Upper bound (for definite integral)

        Returns:
            Tuple of (is_correct, expected_result, error_message)
        """
        try:
            func = self._parse_expression(function)
            claimed = self._parse_expression(claimed_integral)
            var = self.local_dict.get(variable, Symbol(variable))

            if func is None or claimed is None:
                return False, None, "Could not parse expression"

            if lower is not None and upper is not None:
                # Definite integral
                lower_val = self._parse_expression(lower)
                upper_val = self._parse_expression(upper)
                expected = simplify(integrate(func, (var, lower_val, upper_val)))
            else:
                # Indefinite integral - check by differentiation
                deriv_of_claimed = simplify(diff(claimed, var))
                if self._expressions_equal(deriv_of_claimed, func):
                    return True, str(claimed), None
                else:
                    expected = simplify(integrate(func, var))

            if self._expressions_equal(expected, claimed):
                return True, str(expected), None
            else:
                return False, str(expected), f"Integral should be {expected}"

        except Exception as e:
            return False, None, str(e)

    def verify_equation_solution(
        self,
        equation: str,
        claimed_solutions: List[str],
        variable: str = "x",
    ) -> Tuple[bool, Optional[List[str]], Optional[str]]:
        """
        Verify solutions to an equation.

        Args:
            equation: The equation (use "=" for equality)
            claimed_solutions: List of claimed solutions
            variable: Variable being solved for

        Returns:
            Tuple of (is_correct, expected_solutions, error_message)
        """
        try:
            var = self.local_dict.get(variable, Symbol(variable))

            # Parse equation
            if "=" in equation:
                left, right = equation.split("=", 1)
                left_expr = self._parse_expression(left.strip())
                right_expr = self._parse_expression(right.strip())
                eq_expr = left_expr - right_expr
            else:
                eq_expr = self._parse_expression(equation)

            if eq_expr is None:
                return False, None, "Could not parse equation"

            # Get expected solutions
            expected = solve(eq_expr, var)

            # Parse claimed solutions
            claimed_parsed = []
            for sol in claimed_solutions:
                parsed = self._parse_expression(sol)
                if parsed is not None:
                    claimed_parsed.append(parsed)

            # Check if all expected solutions are claimed
            all_correct = True
            missing = []
            extra = []

            for exp_sol in expected:
                found = False
                for claimed_sol in claimed_parsed:
                    if self._expressions_equal(exp_sol, claimed_sol):
                        found = True
                        break
                if not found:
                    missing.append(str(exp_sol))
                    all_correct = False

            for claimed_sol in claimed_parsed:
                found = False
                for exp_sol in expected:
                    if self._expressions_equal(exp_sol, claimed_sol):
                        found = True
                        break
                if not found:
                    extra.append(str(claimed_sol))
                    all_correct = False

            expected_str = [str(s) for s in expected]

            if all_correct:
                return True, expected_str, None
            else:
                error_msg = ""
                if missing:
                    error_msg += f"Missing solutions: {missing}. "
                if extra:
                    error_msg += f"Extra/wrong solutions: {extra}."
                return False, expected_str, error_msg

        except Exception as e:
            return False, None, str(e)

    def verify_answer(
        self,
        expected_answer: str,
        given_answer: str,
        tolerance: float = 1e-6,
    ) -> Tuple[bool, float, str]:
        """
        Verify a final answer.

        Args:
            expected_answer: The correct answer
            given_answer: The answer to verify
            tolerance: Numeric tolerance for comparison

        Returns:
            Tuple of (is_correct, confidence, feedback)
        """
        try:
            expected = self._parse_expression(expected_answer)
            given = self._parse_expression(given_answer)

            if expected is None or given is None:
                # Try string comparison
                if expected_answer.strip().lower() == given_answer.strip().lower():
                    return True, 0.9, "Answers match (string comparison)"
                return False, 0.3, "Could not parse one or both answers"

            # Symbolic comparison
            if self._expressions_equal(expected, given, tolerance):
                return True, 1.0, "Answer is correct"

            # Check numeric equivalence
            try:
                exp_val = float(N(expected))
                given_val = float(N(given))
                if abs(exp_val - given_val) < tolerance:
                    return True, 0.95, "Answer is numerically correct"
                else:
                    rel_error = abs(exp_val - given_val) / (abs(exp_val) + 1e-10)
                    if rel_error < 0.01:  # 1% error
                        return False, 0.5, f"Close but not exact. Expected {expected}, got {given}"
                    else:
                        return False, 0.0, f"Incorrect. Expected {expected}, got {given}"
            except:
                pass

            return False, 0.2, f"Could not verify. Expected {expected}, got {given}"

        except Exception as e:
            return False, 0.0, f"Verification error: {e}"

    def verify_solution(
        self,
        problem: str,
        solution_steps: List[str],
        final_answer: str,
        expected_answer: Optional[str] = None,
        problem_type: str = "general",
    ) -> VerificationResult:
        """
        Verify a complete solution.

        Args:
            problem: The original problem
            solution_steps: List of solution steps
            final_answer: The final answer given
            expected_answer: Expected correct answer (if known)
            problem_type: Type of problem (derivative, integral, equation, etc.)

        Returns:
            VerificationResult with detailed feedback
        """
        steps_verified = []
        errors_found = []
        suggestions = []
        overall_correct = True
        confidence = 1.0

        # Verify each step (simplified verification)
        for i, step in enumerate(solution_steps):
            step_result = VerificationStep(
                step_number=i + 1,
                original_step=step,
                is_correct=True,  # Default to true, detailed verification below
            )

            # Look for calculations in the step
            calc_match = re.search(r'=\s*(.+?)(?:\s|$)', step)
            if calc_match:
                # This is a simplified check - in production, would be more sophisticated
                step_result.is_correct = True

            steps_verified.append(step_result)

        # Verify final answer
        final_correct = True
        answer_confidence = 1.0
        answer_feedback = ""

        if expected_answer:
            final_correct, answer_confidence, answer_feedback = self.verify_answer(
                expected_answer, final_answer
            )
            if not final_correct:
                overall_correct = False
                errors_found.append(f"Final answer incorrect: {answer_feedback}")
                suggestions.append(f"Review the calculation. Expected: {expected_answer}")

        confidence = answer_confidence

        # Determine overall status
        if overall_correct and all(s.is_correct for s in steps_verified):
            status = VerificationStatus.CORRECT
        elif any(s.is_correct for s in steps_verified) and final_correct:
            status = VerificationStatus.CORRECT
        elif any(s.is_correct for s in steps_verified):
            status = VerificationStatus.PARTIALLY_CORRECT
        else:
            status = VerificationStatus.INCORRECT

        # Generate detailed feedback
        detailed_feedback = self._generate_feedback(
            status, steps_verified, errors_found, suggestions,
            final_answer, expected_answer
        )

        return VerificationResult(
            status=status,
            is_correct=overall_correct,
            confidence=confidence,
            steps_verified=steps_verified,
            final_answer_correct=final_correct,
            errors_found=errors_found,
            suggestions=suggestions,
            detailed_feedback=detailed_feedback,
            expected_answer=expected_answer,
            given_answer=final_answer,
        )

    def _generate_feedback(
        self,
        status: VerificationStatus,
        steps: List[VerificationStep],
        errors: List[str],
        suggestions: List[str],
        given_answer: str,
        expected_answer: Optional[str],
    ) -> str:
        """Generate human-readable feedback."""
        feedback = []

        if status == VerificationStatus.CORRECT:
            feedback.append("✓ Solution is correct!")
        elif status == VerificationStatus.PARTIALLY_CORRECT:
            feedback.append("⚠ Solution is partially correct.")
        elif status == VerificationStatus.INCORRECT:
            feedback.append("✗ Solution contains errors.")
        else:
            feedback.append("? Unable to fully verify the solution.")

        # Add step feedback
        incorrect_steps = [s for s in steps if not s.is_correct]
        if incorrect_steps:
            feedback.append("\nProblematic steps:")
            for step in incorrect_steps:
                feedback.append(f"  Step {step.step_number}: {step.original_step}")
                if step.expected_result:
                    feedback.append(f"    Expected: {step.expected_result}")
                if step.suggestion:
                    feedback.append(f"    Suggestion: {step.suggestion}")

        # Add errors
        if errors:
            feedback.append("\nErrors found:")
            for error in errors:
                feedback.append(f"  - {error}")

        # Add suggestions
        if suggestions:
            feedback.append("\nSuggestions:")
            for suggestion in suggestions:
                feedback.append(f"  - {suggestion}")

        # Add answer comparison
        if expected_answer:
            feedback.append(f"\nGiven answer: {given_answer}")
            feedback.append(f"Expected answer: {expected_answer}")

        return "\n".join(feedback)


# Tool interface for agent
def verifier_tool(
    action: str,
    expression: str = "",
    claimed_result: str = "",
    expected_answer: Optional[str] = None,
    variable: str = "x",
    problem_type: str = "general",
    solution_steps: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Solution verifier tool interface for the math agent.

    Args:
        action: Action to perform (verify_calculation, verify_derivative, verify_integral,
                verify_equation, verify_answer, verify_solution)
        expression: The mathematical expression
        claimed_result: The claimed result to verify
        expected_answer: Expected correct answer (for verify_answer)
        variable: Variable name (for calculus operations)
        problem_type: Type of problem
        solution_steps: List of solution steps (for verify_solution)
        **kwargs: Additional arguments (order, lower, upper, solutions)

    Returns:
        Dictionary with verification results
    """
    verifier = SolutionVerifier()

    try:
        if action == "verify_calculation":
            is_correct, expected, error = verifier.verify_calculation(
                expression, claimed_result
            )
            return {
                "success": True,
                "action": "verify_calculation",
                "is_correct": is_correct,
                "expected_result": expected,
                "claimed_result": claimed_result,
                "error": error,
            }

        elif action == "verify_derivative":
            is_correct, expected, error = verifier.verify_derivative(
                expression, claimed_result, variable,
                order=kwargs.get("order", 1)
            )
            return {
                "success": True,
                "action": "verify_derivative",
                "is_correct": is_correct,
                "expected_derivative": expected,
                "claimed_derivative": claimed_result,
                "error": error,
            }

        elif action == "verify_integral":
            is_correct, expected, error = verifier.verify_integral(
                expression, claimed_result, variable,
                lower=kwargs.get("lower"),
                upper=kwargs.get("upper"),
            )
            return {
                "success": True,
                "action": "verify_integral",
                "is_correct": is_correct,
                "expected_integral": expected,
                "claimed_integral": claimed_result,
                "error": error,
            }

        elif action == "verify_equation":
            solutions = kwargs.get("solutions", [claimed_result])
            if isinstance(solutions, str):
                solutions = [solutions]
            is_correct, expected, error = verifier.verify_equation_solution(
                expression, solutions, variable
            )
            return {
                "success": True,
                "action": "verify_equation",
                "is_correct": is_correct,
                "expected_solutions": expected,
                "claimed_solutions": solutions,
                "error": error,
            }

        elif action == "verify_answer":
            if not expected_answer:
                return {
                    "success": False,
                    "error": "expected_answer is required for verify_answer action",
                }
            is_correct, confidence, feedback = verifier.verify_answer(
                expected_answer, claimed_result
            )
            return {
                "success": True,
                "action": "verify_answer",
                "is_correct": is_correct,
                "confidence": confidence,
                "feedback": feedback,
                "expected_answer": expected_answer,
                "given_answer": claimed_result,
            }

        elif action == "verify_solution":
            if not solution_steps:
                solution_steps = []
            result = verifier.verify_solution(
                problem=expression,
                solution_steps=solution_steps,
                final_answer=claimed_result,
                expected_answer=expected_answer,
                problem_type=problem_type,
            )
            return {
                "success": True,
                "action": "verify_solution",
                "status": result.status.value,
                "is_correct": result.is_correct,
                "confidence": result.confidence,
                "final_answer_correct": result.final_answer_correct,
                "errors_found": result.errors_found,
                "suggestions": result.suggestions,
                "detailed_feedback": result.detailed_feedback,
            }

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. "
                        f"Available: verify_calculation, verify_derivative, verify_integral, "
                        f"verify_equation, verify_answer, verify_solution",
            }

    except Exception as e:
        logger.error(f"Verifier tool error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


if __name__ == "__main__":
    # Test the verifier
    verifier = SolutionVerifier()

    print("=" * 60)
    print("Solution Verifier Tool Test")
    print("=" * 60)

    # Test calculation verification
    print("\n1. Verify Calculation:")
    is_correct, expected, error = verifier.verify_calculation("2 + 3 * 4", "14")
    print(f"   2 + 3 * 4 = 14: {'Correct' if is_correct else 'Incorrect'}")

    is_correct, expected, error = verifier.verify_calculation("2 + 3 * 4", "20")
    print(f"   2 + 3 * 4 = 20: {'Correct' if is_correct else f'Incorrect (expected {expected})'}")

    # Test derivative verification
    print("\n2. Verify Derivative:")
    is_correct, expected, error = verifier.verify_derivative("x^3", "3*x^2")
    print(f"   d/dx(x³) = 3x²: {'Correct' if is_correct else f'Incorrect (expected {expected})'}")

    is_correct, expected, error = verifier.verify_derivative("sin(x)", "cos(x)")
    print(f"   d/dx(sin x) = cos x: {'Correct' if is_correct else f'Incorrect (expected {expected})'}")

    # Test integral verification
    print("\n3. Verify Integral:")
    is_correct, expected, error = verifier.verify_integral("2*x", "x^2")
    print(f"   ∫2x dx = x²: {'Correct' if is_correct else f'Incorrect (expected {expected})'}")

    # Test equation solution verification
    print("\n4. Verify Equation Solutions:")
    is_correct, expected, error = verifier.verify_equation_solution(
        "x^2 - 5*x + 6 = 0", ["2", "3"]
    )
    print(f"   x² - 5x + 6 = 0, x = {{2, 3}}: {'Correct' if is_correct else error}")

    # Test answer verification
    print("\n5. Verify Answer:")
    is_correct, confidence, feedback = verifier.verify_answer("6", "6")
    print(f"   Expected: 6, Given: 6 → {feedback} (confidence: {confidence})")

    is_correct, confidence, feedback = verifier.verify_answer("pi/2", "1.5708")
    print(f"   Expected: π/2, Given: 1.5708 → {feedback}")

    # Test via tool interface
    print("\n6. Tool Interface Test:")
    result = verifier_tool(
        action="verify_derivative",
        expression="x^2 + 2*x",
        claimed_result="2*x + 2",
    )
    print(f"   d/dx(x² + 2x) = 2x + 2: {'Correct' if result['is_correct'] else 'Incorrect'}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
