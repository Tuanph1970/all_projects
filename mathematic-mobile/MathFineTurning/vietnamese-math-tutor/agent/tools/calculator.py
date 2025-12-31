"""
Calculator tool for Vietnamese Grade 12 Math Tutor.

Provides symbolic and numeric computation using SymPy.
Supports:
- Arithmetic operations
- Algebraic simplification
- Calculus (derivatives, integrals, limits)
- Equation solving
- Matrix operations
- Trigonometric calculations
"""

import re
import math
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass
from enum import Enum

import sympy as sp
from sympy import (
    symbols, Symbol, Rational, pi, E, I, oo,
    sin, cos, tan, cot, sec, csc,
    asin, acos, atan, acot,
    sinh, cosh, tanh, coth,
    exp, log, ln, sqrt, Abs, sign,
    factorial, binomial, fibonacci,
    diff, integrate, limit, series,
    solve, solveset, linsolve, nonlinsolve,
    simplify, expand, factor, collect, cancel,
    trigsimp, powsimp, radsimp, ratsimp,
    Matrix, det, Inverse, Transpose,
    Sum, Product, Function,
    latex, pretty,
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

logger = get_logger("calculator")


class CalculationType(Enum):
    """Types of calculations supported."""
    ARITHMETIC = "arithmetic"
    ALGEBRA = "algebra"
    CALCULUS = "calculus"
    EQUATION = "equation"
    MATRIX = "matrix"
    TRIGONOMETRY = "trigonometry"
    PROBABILITY = "probability"
    UNKNOWN = "unknown"


@dataclass
class CalculationResult:
    """Result of a calculation."""
    success: bool
    result: Any
    latex_result: str
    calculation_type: CalculationType
    steps: List[str]
    error_message: Optional[str] = None
    numeric_value: Optional[float] = None


class Calculator:
    """
    Advanced mathematical calculator using SymPy.

    Designed for Vietnamese Grade 12 math problems.
    """

    # Common symbols
    x, y, z = symbols('x y z')
    a, b, c, d = symbols('a b c d')
    n, k, m = symbols('n k m', integer=True)
    t = symbols('t')

    # Transformation rules for parsing
    TRANSFORMATIONS = (
        standard_transformations +
        (implicit_multiplication_application, convert_xor)
    )

    # Vietnamese math keywords mapping
    VIETNAMESE_KEYWORDS = {
        # Calculus
        "đạo hàm": "derivative",
        "tích phân": "integral",
        "giới hạn": "limit",
        "nguyên hàm": "antiderivative",

        # Algebra
        "giải phương trình": "solve",
        "phương trình": "equation",
        "bất phương trình": "inequality",
        "hệ phương trình": "system",
        "rút gọn": "simplify",
        "khai triển": "expand",
        "phân tích": "factor",

        # Functions
        "hàm số": "function",
        "cực trị": "extrema",
        "cực đại": "maximum",
        "cực tiểu": "minimum",
        "điểm uốn": "inflection",

        # Trigonometry
        "sin": "sin",
        "cos": "cos",
        "tan": "tan",
        "cot": "cot",

        # Probability
        "xác suất": "probability",
        "tổ hợp": "combination",
        "chỉnh hợp": "permutation",
        "hoán vị": "permutation",
    }

    def __init__(self):
        """Initialize the calculator."""
        self.local_dict = {
            'x': self.x, 'y': self.y, 'z': self.z,
            'a': self.a, 'b': self.b, 'c': self.c, 'd': self.d,
            'n': self.n, 'k': self.k, 'm': self.m, 't': self.t,
            'pi': pi, 'e': E, 'E': E, 'i': I, 'I': I,
            'oo': oo, 'inf': oo,
            'sin': sin, 'cos': cos, 'tan': tan, 'cot': cot,
            'sec': sec, 'csc': csc,
            'asin': asin, 'acos': acos, 'atan': atan, 'acot': acot,
            'sinh': sinh, 'cosh': cosh, 'tanh': tanh, 'coth': coth,
            'exp': exp, 'log': log, 'ln': ln, 'sqrt': sqrt,
            'abs': Abs, 'Abs': Abs, 'sign': sign,
            'factorial': factorial, 'C': binomial, 'P': self._permutation,
            'Matrix': Matrix, 'det': det,
        }
        logger.info("Calculator initialized")

    @staticmethod
    def _permutation(n: int, k: int) -> int:
        """Calculate permutation P(n, k) = n! / (n-k)!"""
        return factorial(n) / factorial(n - k)

    def parse_expression(self, expr_str: str) -> sp.Expr:
        """
        Parse a string expression into a SymPy expression.

        Args:
            expr_str: String representation of the expression

        Returns:
            SymPy expression
        """
        # Clean the expression
        expr_str = expr_str.strip()

        # Handle common notations
        expr_str = expr_str.replace('^', '**')
        expr_str = expr_str.replace('×', '*')
        expr_str = expr_str.replace('÷', '/')
        expr_str = expr_str.replace('√', 'sqrt')

        # Handle Vietnamese notations
        expr_str = re.sub(r'(\d+)!', r'factorial(\1)', expr_str)

        try:
            expr = parse_expr(
                expr_str,
                local_dict=self.local_dict,
                transformations=self.TRANSFORMATIONS,
            )
            return expr
        except Exception as e:
            logger.error(f"Failed to parse expression: {expr_str}, error: {e}")
            raise ValueError(f"Cannot parse expression: {expr_str}")

    def evaluate(
        self,
        expression: str,
        simplify_result: bool = True,
    ) -> CalculationResult:
        """
        Evaluate a mathematical expression.

        Args:
            expression: String expression to evaluate
            simplify_result: Whether to simplify the result

        Returns:
            CalculationResult with the computed value
        """
        steps = []

        try:
            steps.append(f"Input: {expression}")

            # Parse expression
            expr = self.parse_expression(expression)
            steps.append(f"Parsed: {expr}")

            # Simplify if requested
            if simplify_result:
                result = simplify(expr)
                if result != expr:
                    steps.append(f"Simplified: {result}")
            else:
                result = expr

            # Try to get numeric value
            numeric = None
            try:
                numeric = float(result.evalf())
                if not math.isnan(numeric) and not math.isinf(numeric):
                    steps.append(f"Numeric value: {numeric:.6g}")
                else:
                    numeric = None
            except:
                pass

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.ARITHMETIC,
                steps=steps,
                numeric_value=numeric,
            )

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.UNKNOWN,
                steps=steps,
                error_message=str(e),
            )

    def derivative(
        self,
        expression: str,
        variable: str = "x",
        order: int = 1,
    ) -> CalculationResult:
        """
        Compute the derivative of an expression.

        Args:
            expression: Expression to differentiate
            variable: Variable to differentiate with respect to
            order: Order of derivative (1 for first, 2 for second, etc.)

        Returns:
            CalculationResult with the derivative
        """
        steps = []

        try:
            steps.append(f"Function: f({variable}) = {expression}")
            steps.append(f"Find: d^{order}f/d{variable}^{order}" if order > 1 else f"Find: df/d{variable}")

            # Parse
            expr = self.parse_expression(expression)
            var = self.local_dict.get(variable, Symbol(variable))

            # Compute derivative
            result = diff(expr, var, order)
            steps.append(f"Apply differentiation rules")

            # Simplify
            result = simplify(result)
            steps.append(f"Result: {result}")

            # Numeric evaluation at some points
            numeric = None
            try:
                numeric = float(result.evalf())
            except:
                pass

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.CALCULUS,
                steps=steps,
                numeric_value=numeric,
            )

        except Exception as e:
            logger.error(f"Derivative failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.CALCULUS,
                steps=steps,
                error_message=str(e),
            )

    def integral(
        self,
        expression: str,
        variable: str = "x",
        lower: Optional[str] = None,
        upper: Optional[str] = None,
    ) -> CalculationResult:
        """
        Compute the integral (definite or indefinite).

        Args:
            expression: Expression to integrate
            variable: Variable of integration
            lower: Lower bound (for definite integral)
            upper: Upper bound (for definite integral)

        Returns:
            CalculationResult with the integral
        """
        steps = []

        try:
            is_definite = lower is not None and upper is not None

            steps.append(f"Integrand: {expression}")
            if is_definite:
                steps.append(f"Bounds: [{lower}, {upper}]")
            else:
                steps.append("Indefinite integral")

            # Parse
            expr = self.parse_expression(expression)
            var = self.local_dict.get(variable, Symbol(variable))

            # Compute integral
            if is_definite:
                lower_val = self.parse_expression(lower)
                upper_val = self.parse_expression(upper)
                result = integrate(expr, (var, lower_val, upper_val))
                steps.append(f"Evaluate definite integral")
            else:
                result = integrate(expr, var)
                steps.append(f"Find antiderivative")

            # Simplify
            result = simplify(result)
            steps.append(f"Result: {result}")

            if not is_definite:
                steps.append("(+ C for indefinite integral)")

            # Numeric evaluation
            numeric = None
            try:
                numeric = float(result.evalf())
                if not math.isnan(numeric) and not math.isinf(numeric):
                    steps.append(f"Numeric value: {numeric:.6g}")
                else:
                    numeric = None
            except:
                pass

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.CALCULUS,
                steps=steps,
                numeric_value=numeric,
            )

        except Exception as e:
            logger.error(f"Integration failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.CALCULUS,
                steps=steps,
                error_message=str(e),
            )

    def compute_limit(
        self,
        expression: str,
        variable: str = "x",
        point: str = "0",
        direction: str = "+-",
    ) -> CalculationResult:
        """
        Compute the limit of an expression.

        Args:
            expression: Expression to find limit of
            variable: Variable approaching the point
            point: Point to approach (can be "oo" for infinity)
            direction: "+" for right, "-" for left, "+-" for both

        Returns:
            CalculationResult with the limit
        """
        steps = []

        try:
            steps.append(f"Expression: {expression}")
            steps.append(f"Find: lim({variable}→{point}) {expression}")

            # Parse
            expr = self.parse_expression(expression)
            var = self.local_dict.get(variable, Symbol(variable))
            point_val = self.parse_expression(point)

            # Compute limit
            if direction == "+":
                result = limit(expr, var, point_val, '+')
                steps.append(f"Right-hand limit")
            elif direction == "-":
                result = limit(expr, var, point_val, '-')
                steps.append(f"Left-hand limit")
            else:
                result = limit(expr, var, point_val)
                steps.append(f"Two-sided limit")

            steps.append(f"Result: {result}")

            # Numeric evaluation
            numeric = None
            try:
                numeric = float(result.evalf())
            except:
                pass

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.CALCULUS,
                steps=steps,
                numeric_value=numeric,
            )

        except Exception as e:
            logger.error(f"Limit computation failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.CALCULUS,
                steps=steps,
                error_message=str(e),
            )

    def solve_equation(
        self,
        equation: str,
        variable: str = "x",
    ) -> CalculationResult:
        """
        Solve an equation or system of equations.

        Args:
            equation: Equation string (use "=" for equality)
            variable: Variable to solve for

        Returns:
            CalculationResult with solutions
        """
        steps = []

        try:
            steps.append(f"Equation: {equation}")
            steps.append(f"Solve for: {variable}")

            # Parse equation
            var = self.local_dict.get(variable, Symbol(variable))

            if "=" in equation:
                left, right = equation.split("=", 1)
                left_expr = self.parse_expression(left.strip())
                right_expr = self.parse_expression(right.strip())
                eq_expr = left_expr - right_expr
            else:
                eq_expr = self.parse_expression(equation)

            steps.append(f"Rewrite as: {eq_expr} = 0")

            # Solve
            solutions = solve(eq_expr, var)

            if not solutions:
                steps.append("No solutions found")
                return CalculationResult(
                    success=True,
                    result=[],
                    latex_result="\\emptyset",
                    calculation_type=CalculationType.EQUATION,
                    steps=steps,
                )

            # Format solutions
            if isinstance(solutions, list):
                steps.append(f"Solutions: {variable} = {solutions}")
                result_latex = ", ".join([latex(s) for s in solutions])
            else:
                steps.append(f"Solution: {variable} = {solutions}")
                result_latex = latex(solutions)

            # Numeric values
            numeric_values = []
            for sol in (solutions if isinstance(solutions, list) else [solutions]):
                try:
                    val = float(sol.evalf())
                    if not math.isnan(val) and not math.isinf(val):
                        numeric_values.append(val)
                except:
                    pass

            return CalculationResult(
                success=True,
                result=solutions,
                latex_result=result_latex,
                calculation_type=CalculationType.EQUATION,
                steps=steps,
                numeric_value=numeric_values[0] if len(numeric_values) == 1 else None,
            )

        except Exception as e:
            logger.error(f"Equation solving failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.EQUATION,
                steps=steps,
                error_message=str(e),
            )

    def simplify_expression(
        self,
        expression: str,
        method: str = "auto",
    ) -> CalculationResult:
        """
        Simplify a mathematical expression.

        Args:
            expression: Expression to simplify
            method: "auto", "trig", "power", "rational", "radical"

        Returns:
            CalculationResult with simplified expression
        """
        steps = []

        try:
            steps.append(f"Original: {expression}")

            expr = self.parse_expression(expression)

            # Apply simplification method
            if method == "trig":
                result = trigsimp(expr)
                steps.append("Apply trigonometric simplification")
            elif method == "power":
                result = powsimp(expr)
                steps.append("Apply power simplification")
            elif method == "rational":
                result = ratsimp(expr)
                steps.append("Apply rational simplification")
            elif method == "radical":
                result = radsimp(expr)
                steps.append("Apply radical simplification")
            else:
                result = simplify(expr)
                steps.append("Apply automatic simplification")

            steps.append(f"Result: {result}")

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.ALGEBRA,
                steps=steps,
            )

        except Exception as e:
            logger.error(f"Simplification failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.ALGEBRA,
                steps=steps,
                error_message=str(e),
            )

    def expand_expression(self, expression: str) -> CalculationResult:
        """
        Expand a mathematical expression.

        Args:
            expression: Expression to expand

        Returns:
            CalculationResult with expanded expression
        """
        steps = []

        try:
            steps.append(f"Original: {expression}")

            expr = self.parse_expression(expression)
            result = expand(expr)

            steps.append(f"Expanded: {result}")

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.ALGEBRA,
                steps=steps,
            )

        except Exception as e:
            logger.error(f"Expansion failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.ALGEBRA,
                steps=steps,
                error_message=str(e),
            )

    def factor_expression(self, expression: str) -> CalculationResult:
        """
        Factor a mathematical expression.

        Args:
            expression: Expression to factor

        Returns:
            CalculationResult with factored expression
        """
        steps = []

        try:
            steps.append(f"Original: {expression}")

            expr = self.parse_expression(expression)
            result = factor(expr)

            steps.append(f"Factored: {result}")

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.ALGEBRA,
                steps=steps,
            )

        except Exception as e:
            logger.error(f"Factorization failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.ALGEBRA,
                steps=steps,
                error_message=str(e),
            )

    def combination(self, n: int, k: int) -> CalculationResult:
        """
        Calculate combination C(n, k).

        Args:
            n: Total number of items
            k: Number of items to choose

        Returns:
            CalculationResult with combination value
        """
        steps = []

        try:
            steps.append(f"C({n}, {k}) = {n}! / ({k}! × ({n}-{k})!)")

            result = binomial(n, k)

            steps.append(f"= {n}! / ({k}! × {n-k}!)")
            steps.append(f"= {result}")

            return CalculationResult(
                success=True,
                result=result,
                latex_result=f"C_{{{n}}}^{{{k}}} = {result}",
                calculation_type=CalculationType.PROBABILITY,
                steps=steps,
                numeric_value=int(result),
            )

        except Exception as e:
            logger.error(f"Combination calculation failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.PROBABILITY,
                steps=steps,
                error_message=str(e),
            )

    def permutation(self, n: int, k: int) -> CalculationResult:
        """
        Calculate permutation P(n, k).

        Args:
            n: Total number of items
            k: Number of items to arrange

        Returns:
            CalculationResult with permutation value
        """
        steps = []

        try:
            steps.append(f"P({n}, {k}) = {n}! / ({n}-{k})!")

            result = factorial(n) // factorial(n - k)

            steps.append(f"= {n}! / {n-k}!")
            steps.append(f"= {result}")

            return CalculationResult(
                success=True,
                result=result,
                latex_result=f"A_{{{n}}}^{{{k}}} = {result}",
                calculation_type=CalculationType.PROBABILITY,
                steps=steps,
                numeric_value=int(result),
            )

        except Exception as e:
            logger.error(f"Permutation calculation failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.PROBABILITY,
                steps=steps,
                error_message=str(e),
            )

    def matrix_determinant(self, matrix_str: str) -> CalculationResult:
        """
        Calculate matrix determinant.

        Args:
            matrix_str: Matrix in format "[[a,b],[c,d]]"

        Returns:
            CalculationResult with determinant
        """
        steps = []

        try:
            steps.append(f"Matrix: {matrix_str}")

            # Parse matrix
            import ast
            matrix_list = ast.literal_eval(matrix_str)
            matrix = Matrix(matrix_list)

            steps.append(f"Matrix dimensions: {matrix.rows}×{matrix.cols}")

            # Calculate determinant
            result = matrix.det()

            steps.append(f"det(A) = {result}")

            return CalculationResult(
                success=True,
                result=result,
                latex_result=latex(result),
                calculation_type=CalculationType.MATRIX,
                steps=steps,
                numeric_value=float(result) if result.is_number else None,
            )

        except Exception as e:
            logger.error(f"Determinant calculation failed: {e}")
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.MATRIX,
                steps=steps,
                error_message=str(e),
            )

    def execute(
        self,
        operation: str,
        **kwargs,
    ) -> CalculationResult:
        """
        Execute a calculation based on operation type.

        This is the main entry point for the agent tool.

        Args:
            operation: Type of operation (eval, derivative, integral, limit, solve, etc.)
            **kwargs: Operation-specific arguments

        Returns:
            CalculationResult
        """
        operation = operation.lower().strip()

        operation_map = {
            "eval": self.evaluate,
            "evaluate": self.evaluate,
            "calc": self.evaluate,
            "calculate": self.evaluate,
            "derivative": self.derivative,
            "diff": self.derivative,
            "integral": self.integral,
            "integrate": self.integral,
            "limit": self.compute_limit,
            "lim": self.compute_limit,
            "solve": self.solve_equation,
            "equation": self.solve_equation,
            "simplify": self.simplify_expression,
            "expand": self.expand_expression,
            "factor": self.factor_expression,
            "combination": self.combination,
            "comb": self.combination,
            "permutation": self.permutation,
            "perm": self.permutation,
            "determinant": self.matrix_determinant,
            "det": self.matrix_determinant,
        }

        if operation not in operation_map:
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.UNKNOWN,
                steps=[],
                error_message=f"Unknown operation: {operation}. "
                             f"Available: {list(operation_map.keys())}",
            )

        try:
            return operation_map[operation](**kwargs)
        except TypeError as e:
            return CalculationResult(
                success=False,
                result=None,
                latex_result="",
                calculation_type=CalculationType.UNKNOWN,
                steps=[],
                error_message=f"Invalid arguments for {operation}: {e}",
            )


# Tool interface for agent
def calculator_tool(
    operation: str,
    expression: str = "",
    variable: str = "x",
    **kwargs,
) -> Dict[str, Any]:
    """
    Calculator tool interface for the math agent.

    Args:
        operation: Type of calculation (eval, derivative, integral, limit, solve, simplify, expand, factor, combination, permutation, determinant)
        expression: Mathematical expression
        variable: Variable name (default: x)
        **kwargs: Additional arguments (order, lower, upper, point, direction, n, k, method)

    Returns:
        Dictionary with result and metadata
    """
    calc = Calculator()

    # Map expression to appropriate kwargs
    if operation in ["eval", "evaluate", "calc", "calculate"]:
        result = calc.execute(operation, expression=expression)
    elif operation in ["derivative", "diff"]:
        result = calc.execute(
            operation,
            expression=expression,
            variable=variable,
            order=kwargs.get("order", 1),
        )
    elif operation in ["integral", "integrate"]:
        result = calc.execute(
            operation,
            expression=expression,
            variable=variable,
            lower=kwargs.get("lower"),
            upper=kwargs.get("upper"),
        )
    elif operation in ["limit", "lim"]:
        result = calc.execute(
            operation,
            expression=expression,
            variable=variable,
            point=kwargs.get("point", "0"),
            direction=kwargs.get("direction", "+-"),
        )
    elif operation in ["solve", "equation"]:
        result = calc.execute(
            operation,
            equation=expression,
            variable=variable,
        )
    elif operation in ["simplify"]:
        result = calc.execute(
            operation,
            expression=expression,
            method=kwargs.get("method", "auto"),
        )
    elif operation in ["expand", "factor"]:
        result = calc.execute(operation, expression=expression)
    elif operation in ["combination", "comb"]:
        result = calc.execute(
            operation,
            n=kwargs.get("n", 0),
            k=kwargs.get("k", 0),
        )
    elif operation in ["permutation", "perm"]:
        result = calc.execute(
            operation,
            n=kwargs.get("n", 0),
            k=kwargs.get("k", 0),
        )
    elif operation in ["determinant", "det"]:
        result = calc.execute(operation, matrix_str=expression)
    else:
        result = calc.execute(operation, expression=expression, **kwargs)

    return {
        "success": result.success,
        "result": str(result.result),
        "latex": result.latex_result,
        "type": result.calculation_type.value,
        "steps": result.steps,
        "numeric_value": result.numeric_value,
        "error": result.error_message,
    }


if __name__ == "__main__":
    # Test the calculator
    calc = Calculator()

    print("=" * 60)
    print("Calculator Tool Test")
    print("=" * 60)

    # Test basic evaluation
    print("\n1. Basic Evaluation:")
    result = calc.evaluate("2 + 3 * 4")
    print(f"   2 + 3 * 4 = {result.result}")

    # Test derivative
    print("\n2. Derivative:")
    result = calc.derivative("x^3 + 2*x^2 - x + 1", "x")
    print(f"   d/dx(x³ + 2x² - x + 1) = {result.result}")

    # Test integral
    print("\n3. Indefinite Integral:")
    result = calc.integral("3*x^2 + 4*x - 1", "x")
    print(f"   ∫(3x² + 4x - 1)dx = {result.result}")

    # Test definite integral
    print("\n4. Definite Integral:")
    result = calc.integral("x^2", "x", "0", "2")
    print(f"   ∫₀² x² dx = {result.result}")

    # Test limit
    print("\n5. Limit:")
    result = calc.compute_limit("sin(x)/x", "x", "0")
    print(f"   lim(x→0) sin(x)/x = {result.result}")

    # Test equation solving
    print("\n6. Solve Equation:")
    result = calc.solve_equation("x^2 - 5*x + 6 = 0", "x")
    print(f"   x² - 5x + 6 = 0 → x = {result.result}")

    # Test combination
    print("\n7. Combination:")
    result = calc.combination(10, 3)
    print(f"   C(10, 3) = {result.result}")

    # Test via tool interface
    print("\n8. Tool Interface Test:")
    tool_result = calculator_tool("derivative", "sin(x) * cos(x)", "x")
    print(f"   d/dx(sin(x)cos(x)) = {tool_result['result']}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
