"""
Agent-based inference module for Vietnamese Grade 12 Math Tutor.

Combines the fine-tuned model with the ReAct agent for tool-augmented inference.
"""

import torch
from typing import Dict, Any, Optional, List, Generator, Callable
from pathlib import Path
from dataclasses import dataclass

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import get_config, Config
from training.model_config import load_model_and_tokenizer, load_trained_model
from agent import (
    MathTutorAgent,
    create_agent,
    AgentResult,
    calculator_tool,
    formula_db_tool,
    verifier_tool,
    plotter_tool,
)
from chatbot.inference import MathTutorInference, GenerationConfig
from utils.logger import get_logger

logger = get_logger("agent_inference")


@dataclass
class AgentInferenceResult:
    """Result from agent-based inference."""
    success: bool
    answer: str
    solution_steps: List[str]
    tool_calls: List[Dict[str, Any]]
    graphs: List[str]
    thinking_process: str
    raw_response: str
    error: Optional[str] = None


class AgentInferenceEngine:
    """
    Agent-based inference engine combining model and tools.

    Provides full ReAct-style inference with:
    - Fine-tuned model for math reasoning
    - Calculator for computation
    - Formula database for lookup
    - Verifier for validation
    - Plotter for visualization
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        config: Optional[Config] = None,
        quantization: bool = True,
        language: str = "vi",
        max_agent_steps: int = 10,
        verbose: bool = True,
    ):
        """
        Initialize the agent inference engine.

        Args:
            model_path: Path to trained model
            config: Configuration object
            quantization: Use quantization
            language: Output language
            max_agent_steps: Maximum agent reasoning steps
            verbose: Verbose output
        """
        self.config = config or get_config()
        self.language = language
        self.verbose = verbose

        # Initialize model inference
        logger.info("Initializing model inference engine...")
        self.inference = MathTutorInference(
            model_path=model_path,
            config=self.config,
            quantization=quantization,
            language=language,
        )

        # Initialize agent with model
        logger.info("Initializing agent with model...")
        self.agent = MathTutorAgent(
            model=self.inference.model,
            tokenizer=self.inference.tokenizer,
            max_steps=max_agent_steps,
            language=language,
            verbose=verbose,
        )

        logger.info("Agent inference engine ready")

    def solve(
        self,
        problem: str,
        use_agent: bool = True,
        verify_answer: bool = True,
        plot_if_needed: bool = True,
    ) -> AgentInferenceResult:
        """
        Solve a math problem using agent or simple inference.

        Args:
            problem: The math problem to solve
            use_agent: Use agent mode (vs simple inference)
            verify_answer: Verify the answer using verifier tool
            plot_if_needed: Generate plots if problem involves functions

        Returns:
            AgentInferenceResult with solution
        """
        if use_agent:
            return self._solve_with_agent(problem, verify_answer, plot_if_needed)
        else:
            return self._solve_simple(problem)

    def _solve_with_agent(
        self,
        problem: str,
        verify_answer: bool = True,
        plot_if_needed: bool = True,
    ) -> AgentInferenceResult:
        """Solve using the ReAct agent."""
        logger.info(f"Solving with agent: {problem[:50]}...")

        # Run agent
        result = self.agent.solve(problem)

        # Extract solution steps
        solution_steps = []
        thinking_process = []

        for step in result.steps:
            if step.thought:
                thinking_process.append(f"Thought: {step.thought}")
                solution_steps.append(step.thought)
            if step.action:
                thinking_process.append(f"Action: {step.action.tool} - {step.action.parameters}")
            if step.observation:
                thinking_process.append(f"Observation: {step.observation}")

        # Additional verification if requested
        if verify_answer and result.success:
            # Try to verify the final answer
            pass  # Verification already done in agent

        # Plot if needed
        graphs = result.graphs.copy()
        if plot_if_needed and not graphs:
            # Check if problem involves functions that should be plotted
            if self._should_plot(problem):
                plot_result = self._auto_plot(problem, result)
                if plot_result:
                    graphs.append(plot_result)

        return AgentInferenceResult(
            success=result.success,
            answer=result.answer,
            solution_steps=solution_steps,
            tool_calls=result.tool_calls,
            graphs=graphs,
            thinking_process="\n".join(thinking_process),
            raw_response=result.raw_response,
            error=result.error,
        )

    def _solve_simple(self, problem: str) -> AgentInferenceResult:
        """Solve using simple model inference."""
        logger.info(f"Solving with simple inference: {problem[:50]}...")

        result = self.inference.solve(problem)

        return AgentInferenceResult(
            success=result["success"],
            answer=result["solution"],
            solution_steps=[result["solution"]],
            tool_calls=[],
            graphs=[],
            thinking_process="Direct model inference (no agent)",
            raw_response=result["solution"],
        )

    def _should_plot(self, problem: str) -> bool:
        """Check if the problem should include a plot."""
        plot_keywords = [
            "đồ thị", "graph", "vẽ", "plot",
            "hàm số", "function",
            "khảo sát", "investigate",
            "cực trị", "extrema",
        ]
        problem_lower = problem.lower()
        return any(kw in problem_lower for kw in plot_keywords)

    def _auto_plot(
        self,
        problem: str,
        result: AgentResult,
    ) -> Optional[str]:
        """Automatically generate a plot if appropriate."""
        # Try to extract function expression from problem or result
        import re

        # Look for function definition
        patterns = [
            r'y\s*=\s*([^\n,]+)',
            r'f\(x\)\s*=\s*([^\n,]+)',
            r'hàm số\s*y\s*=\s*([^\n,]+)',
        ]

        expression = None
        for pattern in patterns:
            match = re.search(pattern, problem, re.IGNORECASE)
            if match:
                expression = match.group(1).strip()
                break

        if not expression:
            return None

        try:
            plot_result = plotter_tool(
                action="plot_function",
                expression=expression,
                x_range=(-10, 10),
                language=self.language,
            )
            if plot_result.get("success"):
                return plot_result.get("image_path")
        except Exception as e:
            logger.warning(f"Auto-plot failed: {e}")

        return None

    def solve_stream(
        self,
        problem: str,
        use_agent: bool = False,
    ) -> Generator[str, None, None]:
        """
        Solve with streaming output.

        Note: Agent mode doesn't support streaming (returns full result).

        Args:
            problem: The math problem
            use_agent: Use agent mode (falls back to non-streaming)

        Yields:
            Generated text tokens (simple mode) or full result (agent mode)
        """
        if use_agent:
            # Agent doesn't support streaming, return full result
            result = self.solve(problem, use_agent=True)
            yield result.answer
        else:
            # Use streaming inference
            for token in self.inference.generate_stream(problem):
                yield token

    def quick_calculate(self, expression: str) -> str:
        """
        Quick calculation without full inference.

        Args:
            expression: Mathematical expression

        Returns:
            Calculation result
        """
        result = calculator_tool("eval", expression=expression)
        if result["success"]:
            return f"{expression} = {result['result']}"
        else:
            return f"Error: {result.get('error', 'Unknown error')}"

    def lookup_formula(self, query: str) -> str:
        """
        Look up a formula from the database.

        Args:
            query: Search query

        Returns:
            Formatted formula information
        """
        result = formula_db_tool(
            action="search",
            query=query,
            max_results=3,
            language=self.language,
        )

        if result["success"] and result["results"]:
            output = []
            for r in result["results"]:
                output.append(f"**{r['name']}**")
                output.append(f"  Formula: {r['formula']}")
                output.append(f"  {r['description']}")
                output.append("")
            return "\n".join(output)
        else:
            return f"No formulas found for: {query}"

    def verify_calculation(
        self,
        expression: str,
        claimed_result: str,
    ) -> str:
        """
        Verify a calculation.

        Args:
            expression: The expression
            claimed_result: The claimed result

        Returns:
            Verification result
        """
        result = verifier_tool(
            action="verify_calculation",
            expression=expression,
            claimed_result=claimed_result,
        )

        if result["success"]:
            if result["is_correct"]:
                return f"✓ Correct! {expression} = {claimed_result}"
            else:
                return f"✗ Incorrect. Expected: {result['expected_result']}, Got: {claimed_result}"
        else:
            return f"Error: {result.get('error', 'Unknown error')}"


def create_agent_inference_engine(
    model_path: Optional[str] = None,
    quantization: bool = True,
    language: str = "vi",
    max_agent_steps: int = 10,
) -> AgentInferenceEngine:
    """
    Factory function to create agent inference engine.

    Args:
        model_path: Path to trained model
        quantization: Use quantization
        language: Output language
        max_agent_steps: Maximum agent steps

    Returns:
        AgentInferenceEngine instance
    """
    return AgentInferenceEngine(
        model_path=model_path,
        quantization=quantization,
        language=language,
        max_agent_steps=max_agent_steps,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Inference Engine Test")
    print("=" * 60)

    # Test without model (just the agent with mock generation)
    print("\nTesting agent without model...")

    # Create agent directly for testing
    agent = create_agent(model=None, tokenizer=None, verbose=True)

    test_problems = [
        "Tìm đạo hàm của hàm số y = x^3 - 3x^2 + 2x",
        "Tính C(10, 3)",
    ]

    for problem in test_problems:
        print(f"\n{'='*50}")
        print(f"Problem: {problem}")
        print("=" * 50)

        result = agent.solve(problem)
        print(f"Success: {result.success}")
        print(f"Tool calls: {len(result.tool_calls)}")
        if result.tool_calls:
            for call in result.tool_calls:
                print(f"  - {call['tool']}: {call['result'].get('result', 'N/A')[:50]}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("Note: Full testing requires a trained model")
    print("=" * 60)
