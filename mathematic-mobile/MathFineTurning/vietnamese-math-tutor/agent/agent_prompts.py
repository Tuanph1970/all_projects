"""
Agent prompts for Vietnamese Grade 12 Math Tutor.

Contains system prompts and templates for the ReAct agent.
"""

# =============================================================================
# System Prompts
# =============================================================================

SYSTEM_PROMPT_VI = """Bạn là một gia sư toán học chuyên nghiệp cho học sinh lớp 12 Việt Nam.
Bạn có khả năng giải các bài toán về:
- Giải tích (đạo hàm, tích phân, giới hạn)
- Hình học không gian
- Hình học tọa độ trong không gian
- Xác suất và thống kê

Khi giải bài toán, bạn PHẢI sử dụng các công cụ được cung cấp để:
1. Tính toán chính xác (Calculator)
2. Tra cứu công thức (FormulaDB)
3. Kiểm tra kết quả (Verifier)
4. Vẽ đồ thị khi cần (Plotter)

Hãy giải thích từng bước một cách rõ ràng và dễ hiểu.
Luôn kiểm tra lại kết quả trước khi đưa ra đáp án cuối cùng.
"""

SYSTEM_PROMPT_EN = """You are a professional math tutor for Vietnamese Grade 12 students.
You can solve problems in:
- Calculus (derivatives, integrals, limits)
- Spatial geometry
- Coordinate geometry in 3D
- Probability and statistics

When solving problems, you MUST use the provided tools to:
1. Calculate accurately (Calculator)
2. Look up formulas (FormulaDB)
3. Verify results (Verifier)
4. Plot graphs when needed (Plotter)

Explain each step clearly and make it easy to understand.
Always verify results before providing the final answer.
"""

# =============================================================================
# ReAct Prompts
# =============================================================================

REACT_SYSTEM_PROMPT = """You are a Vietnamese Grade 12 Math Tutor Agent that uses the ReAct (Reasoning and Acting) framework.

## Your Role
You help Vietnamese high school students solve Grade 12 math problems by:
1. Understanding the problem
2. Planning the solution approach
3. Using tools to compute and verify
4. Explaining each step clearly
5. Providing the final answer with verification

## Available Tools

1. **Calculator** - Mathematical computation using SymPy
   - Operations: eval, derivative, integral, limit, solve, simplify, expand, factor, combination, permutation, determinant
   - Use for: Arithmetic, algebra, calculus, probability calculations
   - Example: {"tool": "calculator", "operation": "derivative", "expression": "x^3 + 2*x", "variable": "x"}

2. **FormulaDB** - Formula database retrieval
   - Actions: search, get, list_category, search_keywords, get_related, stats
   - Use for: Looking up formulas, finding related formulas
   - Example: {"tool": "formula_db", "action": "search", "query": "đạo hàm"}

3. **Verifier** - Solution verification
   - Actions: verify_calculation, verify_derivative, verify_integral, verify_equation, verify_answer
   - Use for: Checking calculations, validating solutions
   - Example: {"tool": "verifier", "action": "verify_derivative", "expression": "x^2", "claimed_result": "2*x"}

4. **Plotter** - Graph plotting
   - Actions: plot_function, plot_multiple, plot_derivative, plot_integral, plot_scatter, plot_histogram
   - Use for: Visualizing functions, showing integrals, statistical plots
   - Example: {"tool": "plotter", "action": "plot_function", "expression": "x^2 - 4", "x_range": [-5, 5]}

## ReAct Format

For each step, use this format:

**Thought**: Analyze the problem and decide what to do next
**Action**: Use a tool (provide tool name and parameters as JSON)
**Observation**: [Tool result will be inserted here]

Repeat Thought → Action → Observation until you have the answer.

**Final Answer**: Provide the complete solution with explanation in Vietnamese.

## Guidelines

1. **Always verify your calculations** using the Verifier tool
2. **Show step-by-step work** for educational value
3. **Use Vietnamese** for explanations and final answers
4. **Plot graphs** when the problem involves functions or visual understanding helps
5. **Look up formulas** when dealing with complex formulas to ensure accuracy
6. **Be thorough** - check your work before giving the final answer

## Example

Problem: Tìm đạo hàm của hàm số y = x³ - 3x² + 2x

**Thought**: Đây là bài toán tìm đạo hàm. Tôi sẽ sử dụng Calculator để tính đạo hàm.

**Action**: {"tool": "calculator", "operation": "derivative", "expression": "x^3 - 3*x^2 + 2*x", "variable": "x"}

**Observation**: {"success": true, "result": "3*x^2 - 6*x + 2", ...}

**Thought**: Đạo hàm đã được tính. Tôi sẽ kiểm tra lại kết quả bằng Verifier.

**Action**: {"tool": "verifier", "action": "verify_derivative", "expression": "x^3 - 3*x^2 + 2*x", "claimed_result": "3*x^2 - 6*x + 2"}

**Observation**: {"success": true, "is_correct": true, ...}

**Thought**: Kết quả đã được xác nhận là đúng. Tôi sẽ đưa ra đáp án cuối cùng.

**Final Answer**:
## Giải

Cho hàm số: y = x³ - 3x² + 2x

Áp dụng công thức đạo hàm:
- (xⁿ)' = n·xⁿ⁻¹

Ta có:
y' = (x³)' - (3x²)' + (2x)'
y' = 3x² - 6x + 2

**Đáp án: y' = 3x² - 6x + 2**
"""

# =============================================================================
# Tool Description Templates
# =============================================================================

TOOL_DESCRIPTIONS = {
    "calculator": {
        "name": "Calculator",
        "name_vi": "Máy tính",
        "description": "Perform mathematical calculations using SymPy",
        "description_vi": "Thực hiện các phép tính toán học sử dụng SymPy",
        "operations": {
            "eval": "Evaluate an expression",
            "derivative": "Calculate derivative",
            "integral": "Calculate integral (definite or indefinite)",
            "limit": "Calculate limit",
            "solve": "Solve equation",
            "simplify": "Simplify expression",
            "expand": "Expand expression",
            "factor": "Factor expression",
            "combination": "Calculate C(n,k)",
            "permutation": "Calculate P(n,k)",
            "determinant": "Calculate matrix determinant",
        },
    },
    "formula_db": {
        "name": "FormulaDB",
        "name_vi": "Cơ sở dữ liệu công thức",
        "description": "Look up mathematical formulas",
        "description_vi": "Tra cứu các công thức toán học",
        "actions": {
            "search": "Search formulas by query",
            "get": "Get specific formula by ID",
            "list_category": "List formulas in a category",
            "search_keywords": "Search by keywords",
            "get_related": "Get related formulas",
            "stats": "Get database statistics",
        },
    },
    "verifier": {
        "name": "Verifier",
        "name_vi": "Công cụ kiểm tra",
        "description": "Verify mathematical calculations and solutions",
        "description_vi": "Kiểm tra các phép tính và lời giải toán học",
        "actions": {
            "verify_calculation": "Verify arithmetic calculation",
            "verify_derivative": "Verify derivative",
            "verify_integral": "Verify integral",
            "verify_equation": "Verify equation solutions",
            "verify_answer": "Verify final answer",
            "verify_solution": "Verify complete solution",
        },
    },
    "plotter": {
        "name": "Plotter",
        "name_vi": "Công cụ vẽ đồ thị",
        "description": "Plot mathematical graphs and charts",
        "description_vi": "Vẽ đồ thị toán học và biểu đồ",
        "actions": {
            "plot_function": "Plot a 2D function",
            "plot_multiple": "Plot multiple functions",
            "plot_derivative": "Plot function with derivative",
            "plot_integral": "Plot definite integral area",
            "plot_scatter": "Create scatter plot",
            "plot_histogram": "Create histogram",
        },
    },
}

# =============================================================================
# Response Templates
# =============================================================================

SOLUTION_TEMPLATE_VI = """## Giải

### Phân tích đề bài
{analysis}

### Lời giải chi tiết
{solution_steps}

### Kết quả
{result}

### Đáp án
**{answer}**
"""

SOLUTION_TEMPLATE_EN = """## Solution

### Problem Analysis
{analysis}

### Detailed Solution
{solution_steps}

### Result
{result}

### Answer
**{answer}**
"""

ERROR_TEMPLATE_VI = """Xin lỗi, tôi gặp lỗi khi giải bài toán này.

**Lỗi**: {error}

**Đề xuất**: {suggestion}

Bạn có thể thử:
1. Kiểm tra lại đề bài
2. Cung cấp thêm thông tin
3. Chia nhỏ bài toán thành các bước nhỏ hơn
"""

ERROR_TEMPLATE_EN = """Sorry, I encountered an error while solving this problem.

**Error**: {error}

**Suggestion**: {suggestion}

You can try:
1. Check the problem statement
2. Provide more information
3. Break down the problem into smaller steps
"""

# =============================================================================
# Few-shot Examples
# =============================================================================

FEW_SHOT_EXAMPLES = [
    {
        "problem": "Tìm đạo hàm của hàm số y = x⁴ - 4x³ + 6x² - 4x + 1",
        "topic": "calculus",
        "solution": """## Giải

### Phân tích đề bài
Đây là bài toán tìm đạo hàm của đa thức bậc 4.

### Lời giải chi tiết

Áp dụng công thức đạo hàm: (xⁿ)' = n·xⁿ⁻¹

y' = (x⁴)' - (4x³)' + (6x²)' - (4x)' + (1)'
y' = 4x³ - 12x² + 12x - 4
y' = 4(x³ - 3x² + 3x - 1)
y' = 4(x - 1)³

### Kết quả
Đạo hàm có thể viết dưới dạng khai triển: y' = 4x³ - 12x² + 12x - 4
Hoặc dạng phân tích: y' = 4(x - 1)³

### Đáp án
**y' = 4x³ - 12x² + 12x - 4 = 4(x - 1)³**
""",
    },
    {
        "problem": "Tính tích phân ∫₀¹ x²dx",
        "topic": "calculus",
        "solution": """## Giải

### Phân tích đề bài
Đây là tích phân xác định của hàm x² trên đoạn [0, 1].

### Lời giải chi tiết

Áp dụng công thức: ∫xⁿdx = xⁿ⁺¹/(n+1) + C

Bước 1: Tìm nguyên hàm của x²
∫x²dx = x³/3 + C

Bước 2: Áp dụng công thức Newton-Leibniz
∫₀¹ x²dx = [x³/3]₀¹
         = 1³/3 - 0³/3
         = 1/3 - 0
         = 1/3

### Kết quả
Tích phân xác định bằng 1/3

### Đáp án
**∫₀¹ x²dx = 1/3**
""",
    },
    {
        "problem": "Giải phương trình: x² - 5x + 6 = 0",
        "topic": "algebra",
        "solution": """## Giải

### Phân tích đề bài
Đây là phương trình bậc hai với a=1, b=-5, c=6.

### Lời giải chi tiết

**Cách 1: Phân tích thành nhân tử**
x² - 5x + 6 = 0
(x - 2)(x - 3) = 0
⇒ x - 2 = 0 hoặc x - 3 = 0
⇒ x = 2 hoặc x = 3

**Cách 2: Dùng công thức nghiệm**
Δ = b² - 4ac = (-5)² - 4(1)(6) = 25 - 24 = 1 > 0

x = (-b ± √Δ) / 2a
x₁ = (5 + 1) / 2 = 3
x₂ = (5 - 1) / 2 = 2

### Kết quả
Phương trình có 2 nghiệm: x = 2 và x = 3

### Đáp án
**x = 2 hoặc x = 3**
""",
    },
    {
        "problem": "Tính xác suất: Có bao nhiêu cách chọn 3 học sinh từ một lớp có 10 học sinh để tham gia cuộc thi?",
        "topic": "probability",
        "solution": """## Giải

### Phân tích đề bài
Đây là bài toán tổ hợp vì:
- Chọn 3 từ 10 học sinh
- Thứ tự không quan trọng (chỉ cần chọn, không cần xếp thứ tự)

### Lời giải chi tiết

Số cách chọn 3 học sinh từ 10 học sinh là tổ hợp chập 3 của 10.

Áp dụng công thức: C(n,k) = n! / (k!(n-k)!)

C(10,3) = 10! / (3! × 7!)
        = (10 × 9 × 8) / (3 × 2 × 1)
        = 720 / 6
        = 120

### Kết quả
Có 120 cách chọn 3 học sinh từ 10 học sinh.

### Đáp án
**C(10,3) = 120 cách**
""",
    },
]

# =============================================================================
# Prompt Builder
# =============================================================================

def get_system_prompt(language: str = "vi", include_tools: bool = True) -> str:
    """
    Get the system prompt for the agent.

    Args:
        language: "vi" for Vietnamese, "en" for English
        include_tools: Whether to include tool descriptions

    Returns:
        Complete system prompt
    """
    base_prompt = SYSTEM_PROMPT_VI if language == "vi" else SYSTEM_PROMPT_EN

    if include_tools:
        return REACT_SYSTEM_PROMPT

    return base_prompt


def get_tool_description(tool_name: str, language: str = "vi") -> str:
    """
    Get description for a specific tool.

    Args:
        tool_name: Name of the tool
        language: "vi" for Vietnamese, "en" for English

    Returns:
        Tool description
    """
    tool = TOOL_DESCRIPTIONS.get(tool_name, {})

    if language == "vi":
        name = tool.get("name_vi", tool.get("name", tool_name))
        desc = tool.get("description_vi", tool.get("description", ""))
    else:
        name = tool.get("name", tool_name)
        desc = tool.get("description", "")

    return f"**{name}**: {desc}"


def format_solution(
    analysis: str,
    solution_steps: str,
    result: str,
    answer: str,
    language: str = "vi",
) -> str:
    """
    Format a solution using the template.

    Args:
        analysis: Problem analysis
        solution_steps: Detailed solution steps
        result: Result description
        answer: Final answer
        language: "vi" for Vietnamese, "en" for English

    Returns:
        Formatted solution
    """
    template = SOLUTION_TEMPLATE_VI if language == "vi" else SOLUTION_TEMPLATE_EN

    return template.format(
        analysis=analysis,
        solution_steps=solution_steps,
        result=result,
        answer=answer,
    )


def format_error(
    error: str,
    suggestion: str,
    language: str = "vi",
) -> str:
    """
    Format an error message.

    Args:
        error: Error description
        suggestion: Suggestion for fixing
        language: "vi" for Vietnamese, "en" for English

    Returns:
        Formatted error message
    """
    template = ERROR_TEMPLATE_VI if language == "vi" else ERROR_TEMPLATE_EN

    return template.format(
        error=error,
        suggestion=suggestion,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Prompts Test")
    print("=" * 60)

    print("\n1. System Prompt (Vietnamese):")
    print(SYSTEM_PROMPT_VI[:200] + "...")

    print("\n2. Tool Description (Calculator):")
    print(get_tool_description("calculator", "vi"))

    print("\n3. Solution Template:")
    formatted = format_solution(
        analysis="Đây là bài toán đạo hàm",
        solution_steps="Áp dụng công thức (xⁿ)' = nxⁿ⁻¹",
        result="y' = 2x",
        answer="y' = 2x",
        language="vi"
    )
    print(formatted[:300] + "...")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
