"""
Math Agent for Vietnamese Grade 12 Math Tutor.

Implements the ReAct (Reasoning and Acting) pattern for solving math problems.
Orchestrates tool usage for computation, verification, and visualization.
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.logger import get_logger
from agent.tools import (
    calculator_tool,
    formula_db_tool,
    verifier_tool,
    plotter_tool,
)
from agent.agent_prompts import (
    REACT_SYSTEM_PROMPT,
    get_system_prompt,
    format_solution,
    format_error,
)

logger = get_logger("math_agent")


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class AgentAction:
    """Represents an action to take."""
    tool: str
    parameters: Dict[str, Any]
    raw_action: str = ""


@dataclass
class AgentStep:
    """A single step in the agent's reasoning."""
    thought: str
    action: Optional[AgentAction] = None
    observation: Optional[str] = None
    is_final: bool = False


@dataclass
class AgentResult:
    """Final result from the agent."""
    success: bool
    answer: str
    steps: List[AgentStep]
    tool_calls: List[Dict[str, Any]]
    graphs: List[str]
    error: Optional[str] = None
    raw_response: str = ""


class MathTutorAgent:
    """
    ReAct Agent for Vietnamese Grade 12 Math Tutoring.

    Uses Think-Act-Observe loop to solve math problems with tool assistance.
    """

    # Available tools mapping
    TOOLS = {
        "calculator": calculator_tool,
        "formula_db": formula_db_tool,
        "verifier": verifier_tool,
        "plotter": plotter_tool,
    }

    # Tool parameter mappings
    TOOL_PARAMS = {
        "calculator": ["operation", "expression", "variable", "order", "lower", "upper", "point", "direction", "n", "k", "method"],
        "formula_db": ["action", "query", "category", "keywords", "formula_id", "max_results", "language"],
        "verifier": ["action", "expression", "claimed_result", "expected_answer", "variable", "problem_type", "solution_steps", "order", "lower", "upper", "solutions"],
        "plotter": ["action", "expression", "x_range", "y_range", "language", "title", "expressions", "labels", "show_original", "lower", "upper", "x_data", "y_data", "data", "bins", "show_regression", "show_stats", "show_critical_points"],
    }

    def __init__(
        self,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        max_steps: int = 10,
        language: str = "vi",
        verbose: bool = True,
    ):
        """
        Initialize the Math Tutor Agent.

        Args:
            model: Language model for generation
            tokenizer: Tokenizer for the model
            max_steps: Maximum reasoning steps
            language: Output language ("vi" or "en")
            verbose: Print verbose output
        """
        self.model = model
        self.tokenizer = tokenizer
        self.max_steps = max_steps
        self.language = language
        self.verbose = verbose
        self.state = AgentState.IDLE

        # Conversation history for context
        self.history: List[Dict[str, str]] = []

        # Tool call history
        self.tool_calls: List[Dict[str, Any]] = []

        # Generated graphs
        self.graphs: List[str] = []

        logger.info(f"MathTutorAgent initialized (max_steps={max_steps}, language={language})")

    def reset(self):
        """Reset agent state for new problem."""
        self.state = AgentState.IDLE
        self.history = []
        self.tool_calls = []
        self.graphs = []
        logger.info("Agent state reset")

    def _parse_action(self, text: str) -> Optional[AgentAction]:
        """
        Parse an action from model output.

        Looks for JSON formatted action in the text.

        Args:
            text: Model output text

        Returns:
            AgentAction if found, None otherwise
        """
        # Try to find JSON action
        json_patterns = [
            r'\*\*Action\*\*:\s*(\{.*?\})',
            r'Action:\s*(\{.*?\})',
            r'```json\s*(\{.*?\})\s*```',
            r'(\{"tool":\s*".*?".*?\})',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    action_dict = json.loads(match)
                    if "tool" in action_dict:
                        tool = action_dict.pop("tool")
                        return AgentAction(
                            tool=tool,
                            parameters=action_dict,
                            raw_action=match,
                        )
                except json.JSONDecodeError:
                    continue

        return None

    def _parse_thought(self, text: str) -> str:
        """
        Extract thought/reasoning from model output.

        Args:
            text: Model output text

        Returns:
            Thought string
        """
        patterns = [
            r'\*\*Thought\*\*:\s*(.*?)(?=\*\*Action\*\*|\*\*Final Answer\*\*|$)',
            r'Thought:\s*(.*?)(?=Action:|Final Answer:|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return text.strip()

    def _parse_final_answer(self, text: str) -> Optional[str]:
        """
        Extract final answer from model output.

        Args:
            text: Model output text

        Returns:
            Final answer if found, None otherwise
        """
        patterns = [
            r'\*\*Final Answer\*\*:\s*(.*?)$',
            r'Final Answer:\s*(.*?)$',
            r'## Đáp án\s*(.*?)$',
            r'**Đáp án:**\s*(.*?)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _execute_tool(self, action: AgentAction) -> Dict[str, Any]:
        """
        Execute a tool action.

        Args:
            action: The action to execute

        Returns:
            Tool result dictionary
        """
        tool_name = action.tool.lower()

        if tool_name not in self.TOOLS:
            return {
                "success": False,
                "error": f"Unknown tool: {action.tool}. Available: {list(self.TOOLS.keys())}",
            }

        tool_func = self.TOOLS[tool_name]

        # Filter parameters to only those accepted by the tool
        valid_params = self.TOOL_PARAMS.get(tool_name, [])
        filtered_params = {
            k: v for k, v in action.parameters.items()
            if k in valid_params
        }

        try:
            logger.info(f"Executing tool: {tool_name} with params: {filtered_params}")
            result = tool_func(**filtered_params)

            # Track tool call
            self.tool_calls.append({
                "tool": tool_name,
                "parameters": filtered_params,
                "result": result,
            })

            # Track graphs
            if tool_name == "plotter" and result.get("success"):
                image_path = result.get("image_path")
                if image_path:
                    self.graphs.append(image_path)

            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _format_observation(self, result: Dict[str, Any]) -> str:
        """
        Format tool result as observation string.

        Args:
            result: Tool result dictionary

        Returns:
            Formatted observation string
        """
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        # Format based on tool type
        obs_parts = []

        if "result" in result:
            obs_parts.append(f"Result: {result['result']}")

        if "latex" in result:
            obs_parts.append(f"LaTeX: {result['latex']}")

        if "steps" in result and result["steps"]:
            obs_parts.append("Steps:")
            for step in result["steps"][:5]:  # Limit steps
                obs_parts.append(f"  - {step}")

        if "is_correct" in result:
            correct_str = "✓ Correct" if result["is_correct"] else "✗ Incorrect"
            obs_parts.append(correct_str)

        if "image_path" in result:
            obs_parts.append(f"Graph saved: {result['image_path']}")

        if "results" in result:  # Formula search results
            obs_parts.append(f"Found {len(result['results'])} results:")
            for r in result["results"][:3]:
                obs_parts.append(f"  - {r.get('name', 'N/A')}: {r.get('formula', 'N/A')}")

        if "numeric_value" in result and result["numeric_value"] is not None:
            obs_parts.append(f"Numeric value: {result['numeric_value']}")

        return "\n".join(obs_parts) if obs_parts else str(result)

    def _generate_with_model(self, prompt: str) -> str:
        """
        Generate response using the language model.

        Args:
            prompt: Input prompt

        Returns:
            Model response
        """
        if self.model is None or self.tokenizer is None:
            # Return a mock response for testing without model
            return self._mock_generate(prompt)

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.pad_token_id,
            )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Remove the prompt from response
            if response.startswith(prompt):
                response = response[len(prompt):]

            return response.strip()

        except Exception as e:
            logger.error(f"Model generation failed: {e}")
            return ""

    def _mock_generate(self, prompt: str) -> str:
        """
        Mock generation for testing without model.

        Provides simple rule-based responses.
        """
        # Extract problem from prompt
        problem_lower = prompt.lower()

        if "đạo hàm" in problem_lower or "derivative" in problem_lower:
            # Extract expression if possible
            expr_match = re.search(r'y\s*=\s*([^\n]+)', prompt)
            if expr_match:
                expr = expr_match.group(1).strip()
                return f'''**Thought**: Đây là bài toán tìm đạo hàm. Tôi sẽ sử dụng Calculator.

**Action**: {{"tool": "calculator", "operation": "derivative", "expression": "{expr}", "variable": "x"}}'''

        elif "tích phân" in problem_lower or "integral" in problem_lower:
            return '''**Thought**: Đây là bài toán tích phân. Tôi sẽ tính tích phân.

**Action**: {"tool": "calculator", "operation": "integral", "expression": "x^2", "variable": "x"}'''

        elif "giải" in problem_lower and ("phương trình" in problem_lower or "equation" in problem_lower):
            return '''**Thought**: Đây là bài toán giải phương trình.

**Action**: {"tool": "calculator", "operation": "solve", "expression": "x^2 - 4 = 0", "variable": "x"}'''

        elif "xác suất" in problem_lower or "tổ hợp" in problem_lower:
            return '''**Thought**: Đây là bài toán tổ hợp/xác suất.

**Action**: {"tool": "calculator", "operation": "combination", "n": 10, "k": 3}'''

        else:
            return '''**Thought**: Tôi sẽ tìm công thức liên quan.

**Action**: {"tool": "formula_db", "action": "search", "query": "đạo hàm"}'''

    def solve(self, problem: str) -> AgentResult:
        """
        Solve a math problem using ReAct pattern.

        Args:
            problem: The math problem to solve

        Returns:
            AgentResult with solution and steps
        """
        self.reset()
        self.state = AgentState.THINKING

        steps: List[AgentStep] = []
        final_answer = None

        # Build initial prompt
        system_prompt = get_system_prompt(self.language)
        full_prompt = f"{system_prompt}\n\n## Problem\n{problem}\n\n"

        if self.verbose:
            logger.info(f"Solving problem: {problem[:100]}...")

        for step_num in range(self.max_steps):
            if self.verbose:
                logger.info(f"Step {step_num + 1}/{self.max_steps}")

            # Generate response
            self.state = AgentState.THINKING
            response = self._generate_with_model(full_prompt)

            if not response:
                logger.warning("Empty response from model")
                break

            # Parse thought
            thought = self._parse_thought(response)

            # Check for final answer
            final_answer = self._parse_final_answer(response)
            if final_answer:
                steps.append(AgentStep(
                    thought=thought,
                    is_final=True,
                ))
                self.state = AgentState.FINISHED
                break

            # Parse action
            action = self._parse_action(response)

            if action:
                self.state = AgentState.ACTING

                # Execute tool
                result = self._execute_tool(action)

                self.state = AgentState.OBSERVING

                # Format observation
                observation = self._format_observation(result)

                steps.append(AgentStep(
                    thought=thought,
                    action=action,
                    observation=observation,
                ))

                # Update prompt with observation
                full_prompt += f"**Thought**: {thought}\n\n"
                full_prompt += f"**Action**: {action.raw_action}\n\n"
                full_prompt += f"**Observation**: {observation}\n\n"

            else:
                # No action found, might be reasoning step
                steps.append(AgentStep(
                    thought=thought,
                ))
                full_prompt += f"**Thought**: {thought}\n\n"

        # If no final answer was given, try to construct one
        if not final_answer and steps:
            final_answer = self._construct_answer(problem, steps)

        # Build result
        success = final_answer is not None
        if not success:
            final_answer = format_error(
                error="Could not solve the problem",
                suggestion="Please rephrase or provide more details",
                language=self.language,
            )

        return AgentResult(
            success=success,
            answer=final_answer,
            steps=steps,
            tool_calls=self.tool_calls,
            graphs=self.graphs,
            raw_response=full_prompt,
        )

    def _construct_answer(self, problem: str, steps: List[AgentStep]) -> str:
        """
        Construct a final answer from steps when model didn't provide one.

        Args:
            problem: Original problem
            steps: List of reasoning steps

        Returns:
            Constructed answer string
        """
        # Look for calculation results in tool calls
        results = []
        for call in self.tool_calls:
            if call["result"].get("success"):
                if "result" in call["result"]:
                    results.append(call["result"]["result"])

        if results:
            analysis = "Bài toán được giải bằng các công cụ tính toán."
            solution_steps = "\n".join([s.thought for s in steps if s.thought])
            result = f"Kết quả: {results[-1]}"
            answer = str(results[-1])

            return format_solution(
                analysis=analysis,
                solution_steps=solution_steps,
                result=result,
                answer=answer,
                language=self.language,
            )

        return None

    def solve_simple(self, problem: str) -> str:
        """
        Solve a problem without full ReAct loop (single tool call).

        Useful for simple calculations.

        Args:
            problem: The math problem

        Returns:
            Solution string
        """
        # Detect problem type and use appropriate tool
        problem_lower = problem.lower()

        if any(kw in problem_lower for kw in ["đạo hàm", "derivative", "d/dx"]):
            # Extract expression
            expr_match = re.search(r'y\s*=\s*([^\n,]+)', problem)
            if expr_match:
                expr = expr_match.group(1).strip()
                result = calculator_tool("derivative", expression=expr, variable="x")
                if result["success"]:
                    return f"Đạo hàm: y' = {result['result']}"

        elif any(kw in problem_lower for kw in ["tích phân", "integral", "∫"]):
            expr_match = re.search(r'∫\s*([^\s]+)\s*dx', problem)
            if expr_match:
                expr = expr_match.group(1).strip()
                result = calculator_tool("integral", expression=expr, variable="x")
                if result["success"]:
                    return f"Tích phân: ∫{expr}dx = {result['result']} + C"

        elif any(kw in problem_lower for kw in ["giải phương trình", "solve"]):
            eq_match = re.search(r'[:]\s*([^\n]+)', problem)
            if eq_match:
                eq = eq_match.group(1).strip()
                result = calculator_tool("solve", expression=eq, variable="x")
                if result["success"]:
                    return f"Nghiệm: x = {result['result']}"

        elif any(kw in problem_lower for kw in ["c(", "tổ hợp", "combination"]):
            nums = re.findall(r'\d+', problem)
            if len(nums) >= 2:
                n, k = int(nums[0]), int(nums[1])
                result = calculator_tool("combination", n=n, k=k)
                if result["success"]:
                    return f"C({n},{k}) = {result['result']}"

        # If no pattern matched, return generic message
        return "Không thể giải bài toán này ở chế độ đơn giản. Hãy thử chế độ agent."


def create_agent(
    model=None,
    tokenizer=None,
    language: str = "vi",
    verbose: bool = True,
) -> MathTutorAgent:
    """
    Factory function to create a Math Tutor Agent.

    Args:
        model: Language model (optional)
        tokenizer: Tokenizer (optional)
        language: Output language
        verbose: Verbose output

    Returns:
        MathTutorAgent instance
    """
    return MathTutorAgent(
        model=model,
        tokenizer=tokenizer,
        language=language,
        verbose=verbose,
    )


if __name__ == "__main__":
    # Test the agent
    print("=" * 60)
    print("Math Tutor Agent Test")
    print("=" * 60)

    # Create agent without model (uses mock generation)
    agent = create_agent(model=None, tokenizer=None, verbose=True)

    # Test problems
    test_problems = [
        "Tìm đạo hàm của hàm số y = x^3 - 3*x^2 + 2*x",
        "Tính C(10, 3)",
        "Giải phương trình: x^2 - 5*x + 6 = 0",
    ]

    for i, problem in enumerate(test_problems, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {problem}")
        print("=" * 60)

        # Test simple solve
        print("\n[Simple Mode]")
        simple_result = agent.solve_simple(problem)
        print(f"Result: {simple_result}")

        # Test full solve
        print("\n[Agent Mode]")
        result = agent.solve(problem)
        print(f"Success: {result.success}")
        print(f"Steps: {len(result.steps)}")
        print(f"Tool calls: {len(result.tool_calls)}")
        if result.tool_calls:
            for call in result.tool_calls:
                print(f"  - {call['tool']}: {call['result'].get('success', False)}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
