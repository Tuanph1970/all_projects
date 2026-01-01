import os
import re
import logging
import asyncio
from typing import Dict, List, Optional, Any
from sympy import (
    sympify, solve, simplify, expand, factor, diff, integrate,
    symbols, Eq, parse_expr, N, oo, limit, series, sin, cos, tan,
    exp, log, sqrt, pi, E, I, Symbol, latex
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)

logger = logging.getLogger(__name__)


class MathSolverService:
    """Service for solving mathematical problems"""

    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.use_ai = bool(self.openai_api_key or self.anthropic_api_key)

        # Define common symbols
        self.x, self.y, self.z = symbols('x y z')
        self.a, self.b, self.c = symbols('a b c')
        self.t, self.n = symbols('t n')

    async def solve(
        self,
        problem_text: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Solve a mathematical problem

        Args:
            problem_text: The problem to solve
            category: Problem category (algebra, calculus, etc.)

        Returns:
            Dictionary with solution, steps, and metadata
        """
        try:
            # First try symbolic solving
            result = await self._solve_symbolic(problem_text)

            if result["success"]:
                return result

            # If symbolic fails and AI is available, try AI
            if self.use_ai:
                result = await self._solve_with_ai(problem_text, category)
                if result["success"]:
                    return result

            return {
                "success": False,
                "error": "Could not solve the problem",
                "method": "none"
            }

        except Exception as e:
            logger.error(f"Solver error: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "error"
            }

    async def _solve_symbolic(self, problem_text: str) -> Dict[str, Any]:
        """Solve problem using SymPy symbolic computation"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._symbolic_solve, problem_text
            )
            return result

        except Exception as e:
            logger.warning(f"Symbolic solve failed: {e}")
            return {"success": False, "error": str(e)}

    def _symbolic_solve(self, problem_text: str) -> Dict[str, Any]:
        """Synchronous symbolic solving"""
        steps = []
        problem_text = problem_text.strip()

        # Parse transformations
        transformations = (
            standard_transformations +
            (implicit_multiplication_application, convert_xor)
        )

        # Detect problem type and solve
        if "=" in problem_text:
            return self._solve_equation(problem_text, transformations, steps)
        elif any(kw in problem_text.lower() for kw in ["derivative", "diff", "d/dx"]):
            return self._solve_derivative(problem_text, transformations, steps)
        elif any(kw in problem_text.lower() for kw in ["integral", "integrate", "∫"]):
            return self._solve_integral(problem_text, transformations, steps)
        elif any(kw in problem_text.lower() for kw in ["simplify", "expand", "factor"]):
            return self._simplify_expression(problem_text, transformations, steps)
        else:
            # Try to evaluate as expression
            return self._evaluate_expression(problem_text, transformations, steps)

    def _solve_equation(
        self,
        problem_text: str,
        transformations: tuple,
        steps: List[str]
    ) -> Dict[str, Any]:
        """Solve an equation"""
        try:
            steps.append(f"Given equation: {problem_text}")

            # Parse equation
            parts = problem_text.split("=")
            if len(parts) != 2:
                return {"success": False, "error": "Invalid equation format"}

            lhs = parse_expr(parts[0].strip(), transformations=transformations)
            rhs = parse_expr(parts[1].strip(), transformations=transformations)

            steps.append(f"Left side: {lhs}")
            steps.append(f"Right side: {rhs}")

            # Create equation
            eq = Eq(lhs, rhs)
            steps.append(f"Equation: {eq}")

            # Find variables
            variables = eq.free_symbols
            if not variables:
                # Check if equation is true/false
                result = simplify(lhs - rhs) == 0
                return {
                    "success": True,
                    "solution": f"The equation is {'True' if result else 'False'}",
                    "steps": steps,
                    "method": "symbolic",
                    "confidence": 1.0
                }

            # Solve for the first variable found
            var = list(variables)[0]
            steps.append(f"Solving for: {var}")

            solutions = solve(eq, var)
            steps.append(f"Solutions: {solutions}")

            if not solutions:
                return {"success": False, "error": "No solution found"}

            # Format solution
            if len(solutions) == 1:
                solution_text = f"{var} = {solutions[0]}"
            else:
                solution_text = ", ".join([f"{var} = {s}" for s in solutions])

            return {
                "success": True,
                "solution": solution_text,
                "steps": steps,
                "method": "symbolic",
                "confidence": 0.95
            }

        except Exception as e:
            logger.warning(f"Equation solving failed: {e}")
            return {"success": False, "error": str(e)}

    def _solve_derivative(
        self,
        problem_text: str,
        transformations: tuple,
        steps: List[str]
    ) -> Dict[str, Any]:
        """Compute derivative"""
        try:
            # Extract expression
            expr_text = re.sub(
                r'(derivative|diff|d/dx|of)',
                '',
                problem_text,
                flags=re.IGNORECASE
            ).strip()

            steps.append(f"Expression to differentiate: {expr_text}")

            expr = parse_expr(expr_text, transformations=transformations)
            steps.append(f"Parsed expression: {expr}")

            # Find variable
            variables = expr.free_symbols
            var = self.x if self.x in variables else list(variables)[0] if variables else self.x

            steps.append(f"Differentiating with respect to: {var}")

            # Compute derivative
            derivative = diff(expr, var)
            steps.append(f"Derivative: {derivative}")

            # Simplify
            simplified = simplify(derivative)
            steps.append(f"Simplified: {simplified}")

            return {
                "success": True,
                "solution": f"d/d{var}({expr}) = {simplified}",
                "steps": steps,
                "method": "symbolic",
                "confidence": 0.95
            }

        except Exception as e:
            logger.warning(f"Derivative computation failed: {e}")
            return {"success": False, "error": str(e)}

    def _solve_integral(
        self,
        problem_text: str,
        transformations: tuple,
        steps: List[str]
    ) -> Dict[str, Any]:
        """Compute integral"""
        try:
            # Extract expression
            expr_text = re.sub(
                r'(integral|integrate|∫|of|dx)',
                '',
                problem_text,
                flags=re.IGNORECASE
            ).strip()

            steps.append(f"Expression to integrate: {expr_text}")

            expr = parse_expr(expr_text, transformations=transformations)
            steps.append(f"Parsed expression: {expr}")

            # Find variable
            variables = expr.free_symbols
            var = self.x if self.x in variables else list(variables)[0] if variables else self.x

            steps.append(f"Integrating with respect to: {var}")

            # Compute integral
            integral = integrate(expr, var)
            steps.append(f"Integral: {integral}")

            return {
                "success": True,
                "solution": f"∫{expr}d{var} = {integral} + C",
                "steps": steps,
                "method": "symbolic",
                "confidence": 0.95
            }

        except Exception as e:
            logger.warning(f"Integration failed: {e}")
            return {"success": False, "error": str(e)}

    def _simplify_expression(
        self,
        problem_text: str,
        transformations: tuple,
        steps: List[str]
    ) -> Dict[str, Any]:
        """Simplify, expand, or factor expression"""
        try:
            # Determine operation
            if "expand" in problem_text.lower():
                operation = "expand"
            elif "factor" in problem_text.lower():
                operation = "factor"
            else:
                operation = "simplify"

            # Extract expression
            expr_text = re.sub(
                r'(simplify|expand|factor)',
                '',
                problem_text,
                flags=re.IGNORECASE
            ).strip()

            steps.append(f"Expression: {expr_text}")
            steps.append(f"Operation: {operation}")

            expr = parse_expr(expr_text, transformations=transformations)

            if operation == "expand":
                result = expand(expr)
            elif operation == "factor":
                result = factor(expr)
            else:
                result = simplify(expr)

            steps.append(f"Result: {result}")

            return {
                "success": True,
                "solution": f"{operation}({expr}) = {result}",
                "steps": steps,
                "method": "symbolic",
                "confidence": 0.95
            }

        except Exception as e:
            logger.warning(f"Simplification failed: {e}")
            return {"success": False, "error": str(e)}

    def _evaluate_expression(
        self,
        problem_text: str,
        transformations: tuple,
        steps: List[str]
    ) -> Dict[str, Any]:
        """Evaluate a mathematical expression"""
        try:
            steps.append(f"Expression: {problem_text}")

            expr = parse_expr(problem_text, transformations=transformations)
            steps.append(f"Parsed: {expr}")

            # Try to simplify
            result = simplify(expr)
            steps.append(f"Simplified: {result}")

            # Try numerical evaluation if possible
            try:
                numerical = N(result)
                if numerical != result:
                    steps.append(f"Numerical value: {numerical}")
            except:
                pass

            return {
                "success": True,
                "solution": str(result),
                "steps": steps,
                "method": "symbolic",
                "confidence": 0.9
            }

        except Exception as e:
            logger.warning(f"Expression evaluation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _solve_with_ai(
        self,
        problem_text: str,
        category: Optional[str]
    ) -> Dict[str, Any]:
        """Solve problem using AI (OpenAI or Anthropic)"""
        try:
            if self.openai_api_key:
                return await self._solve_with_openai(problem_text, category)
            elif self.anthropic_api_key:
                return await self._solve_with_anthropic(problem_text, category)
            else:
                return {"success": False, "error": "No AI API key configured"}

        except Exception as e:
            logger.error(f"AI solving failed: {e}")
            return {"success": False, "error": str(e)}

    async def _solve_with_openai(
        self,
        problem_text: str,
        category: Optional[str]
    ) -> Dict[str, Any]:
        """Solve using OpenAI API"""
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.openai_api_key)

            prompt = f"""Solve the following mathematical problem step by step.
Problem: {problem_text}
Category: {category or 'General'}

Please provide:
1. The solution
2. Step-by-step explanation
3. Final answer

Format your response as:
SOLUTION: [final answer]
STEPS:
1. [step 1]
2. [step 2]
...
"""

            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a mathematics expert. Solve problems accurately and explain step by step."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )

            content = response.choices[0].message.content

            # Parse response
            solution = ""
            steps = []

            if "SOLUTION:" in content:
                solution_part = content.split("SOLUTION:")[1]
                if "STEPS:" in solution_part:
                    solution = solution_part.split("STEPS:")[0].strip()
                    steps_part = content.split("STEPS:")[1]
                    steps = [s.strip() for s in steps_part.split("\n") if s.strip()]
                else:
                    solution = solution_part.strip()
            else:
                solution = content

            return {
                "success": True,
                "solution": solution,
                "steps": steps,
                "method": "ai-openai",
                "confidence": 0.85
            }

        except Exception as e:
            logger.error(f"OpenAI solving failed: {e}")
            return {"success": False, "error": str(e)}

    async def _solve_with_anthropic(
        self,
        problem_text: str,
        category: Optional[str]
    ) -> Dict[str, Any]:
        """Solve using Anthropic API"""
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)

            prompt = f"""Solve the following mathematical problem step by step.
Problem: {problem_text}
Category: {category or 'General'}

Please provide:
1. The solution
2. Step-by-step explanation
3. Final answer

Format your response as:
SOLUTION: [final answer]
STEPS:
1. [step 1]
2. [step 2]
...
"""

            response = await client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # Parse response (same as OpenAI)
            solution = ""
            steps = []

            if "SOLUTION:" in content:
                solution_part = content.split("SOLUTION:")[1]
                if "STEPS:" in solution_part:
                    solution = solution_part.split("STEPS:")[0].strip()
                    steps_part = content.split("STEPS:")[1]
                    steps = [s.strip() for s in steps_part.split("\n") if s.strip()]
                else:
                    solution = solution_part.strip()
            else:
                solution = content

            return {
                "success": True,
                "solution": solution,
                "steps": steps,
                "method": "ai-anthropic",
                "confidence": 0.85
            }

        except Exception as e:
            logger.error(f"Anthropic solving failed: {e}")
            return {"success": False, "error": str(e)}
