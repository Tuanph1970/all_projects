"""
Helper utilities for Vietnamese Grade 12 Math Tutor.

Common functions used across the project.
"""

import re
from typing import List, Dict, Tuple, Optional
import unicodedata


# Vietnamese mathematical terms mapping
VIETNAMESE_MATH_TERMS = {
    # Calculus
    "dao ham": "derivative",
    "tich phan": "integral",
    "nguyen ham": "antiderivative",
    "gioi han": "limit",
    "cuc tri": "extrema",
    "cuc dai": "maximum",
    "cuc tieu": "minimum",
    "diem uon": "inflection point",
    "tiem can": "asymptote",
    "tiep tuyen": "tangent line",
    "ham so": "function",
    "bien thien": "variation",
    "do thi": "graph",

    # Geometry
    "hinh hoc khong gian": "spatial geometry",
    "mat phang": "plane",
    "duong thang": "line",
    "goc": "angle",
    "khoang cach": "distance",
    "the tich": "volume",
    "dien tich": "area",
    "song song": "parallel",
    "vuong goc": "perpendicular",

    # Probability & Statistics
    "xac suat": "probability",
    "thong ke": "statistics",
    "trung binh": "mean",
    "phuong sai": "variance",
    "do lech chuan": "standard deviation",
    "bien co": "event",
    "khong gian mau": "sample space",

    # General
    "phuong trinh": "equation",
    "bat phuong trinh": "inequality",
    "nghiem": "solution",
    "he so": "coefficient",
    "da thuc": "polynomial",
}


def remove_vietnamese_accents(text: str) -> str:
    """
    Remove Vietnamese diacritical marks for easier processing.

    Args:
        text: Vietnamese text with accents

    Returns:
        Text without accents
    """
    # Normalize to NFD form
    nfkd_form = unicodedata.normalize('NFD', text)
    # Remove combining characters (accents)
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))


def clean_vietnamese_text(text: str) -> str:
    """
    Clean and normalize Vietnamese text.

    Args:
        text: Input text

    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")

    return text


def format_math_expression(expr: str) -> str:
    """
    Format mathematical expression for display.

    Converts common patterns to proper notation.

    Args:
        expr: Raw mathematical expression

    Returns:
        Formatted expression
    """
    # Replace ** with ^ for display
    formatted = expr.replace("**", "^")

    # Replace * with proper multiplication
    formatted = re.sub(r'(\d)\*([a-zA-Z])', r'\1\2', formatted)  # 3*x -> 3x
    formatted = re.sub(r'([a-zA-Z])\*([a-zA-Z])', r'\1·\2', formatted)  # x*y -> x·y

    # Format fractions
    formatted = re.sub(r'(\d+)/(\d+)', r'\1/\2', formatted)

    return formatted


def parse_math_expression(expr: str) -> str:
    """
    Parse display math expression to SymPy format.

    Args:
        expr: Display format expression

    Returns:
        SymPy-compatible expression
    """
    # Replace ^ with **
    parsed = expr.replace("^", "**")

    # Add explicit multiplication
    parsed = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', parsed)  # 3x -> 3*x
    parsed = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', parsed)  # x2 -> x*2
    parsed = re.sub(r'([a-zA-Z])([a-zA-Z])', r'\1*\2', parsed)  # xy -> x*y

    return parsed


def estimate_complexity(problem: str) -> float:
    """
    Estimate problem complexity based on various factors.

    Args:
        problem: Problem text

    Returns:
        Complexity score (0.0 to 1.0)
    """
    score = 0.0

    # Length factor
    if len(problem) > 200:
        score += 0.2

    # Mathematical operations
    complex_patterns = [
        (r'khao sat', 0.3),  # Function analysis
        (r'the tich', 0.25),  # Volume calculation
        (r'tich phan', 0.2),  # Integration
        (r'phuong trinh mat phang', 0.25),  # Plane equation
        (r'khoang cach', 0.2),  # Distance calculation
        (r'xac suat', 0.15),  # Probability
    ]

    problem_lower = remove_vietnamese_accents(problem.lower())
    for pattern, weight in complex_patterns:
        if re.search(pattern, problem_lower):
            score += weight

    # Multiple parts indicator
    if re.search(r'[abc]\)', problem) or re.search(r'\d\)', problem):
        score += 0.1

    return min(score, 1.0)


def format_step_by_step(steps: List[Dict[str, str]], language: str = "vi") -> str:
    """
    Format solution steps for display.

    Args:
        steps: List of step dictionaries with 'title' and 'content'
        language: Output language ('vi' or 'en')

    Returns:
        Formatted step-by-step solution
    """
    step_label = "Buoc" if language == "vi" else "Step"
    result = []

    for i, step in enumerate(steps, 1):
        title = step.get('title', '')
        content = step.get('content', '')

        if title:
            result.append(f"**{step_label} {i}: {title}**")
        else:
            result.append(f"**{step_label} {i}:**")

        result.append(content)
        result.append("")  # Empty line between steps

    return "\n".join(result)


def extract_answer(solution: str, language: str = "vi") -> Optional[str]:
    """
    Extract the final answer from a solution text.

    Args:
        solution: Full solution text
        language: Language of the solution

    Returns:
        Extracted answer or None
    """
    # Vietnamese patterns
    vi_patterns = [
        r'\*\*Dap an:\*\*\s*(.+?)(?:\n|$)',
        r'\*\*Ket qua:\*\*\s*(.+?)(?:\n|$)',
        r'Vay\s+(.+?)(?:\n|$)',
    ]

    # English patterns
    en_patterns = [
        r'\*\*Answer:\*\*\s*(.+?)(?:\n|$)',
        r'\*\*Result:\*\*\s*(.+?)(?:\n|$)',
        r'Therefore,?\s+(.+?)(?:\n|$)',
    ]

    patterns = vi_patterns if language == "vi" else en_patterns

    for pattern in patterns:
        match = re.search(pattern, solution, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def split_problem_parts(problem: str) -> List[Tuple[str, str]]:
    """
    Split a multi-part problem into individual parts.

    Args:
        problem: Problem text with multiple parts (a), b), 1), 2), etc.)

    Returns:
        List of (label, content) tuples
    """
    # Pattern for part labels
    pattern = r'([a-d]|\d)\)\s*'

    parts = re.split(pattern, problem)

    # Group label with content
    result = []
    if parts[0].strip():  # Main problem text before parts
        result.append(("main", parts[0].strip()))

    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            label = parts[i]
            content = parts[i + 1].strip()
            result.append((label, content))

    return result


def format_vietnamese_number(number: float, decimal_places: int = 2) -> str:
    """
    Format number using Vietnamese conventions.

    Vietnamese uses comma as decimal separator and period as thousand separator.

    Args:
        number: Number to format
        decimal_places: Number of decimal places

    Returns:
        Formatted number string
    """
    # Format with periods as thousand separators
    formatted = f"{number:,.{decimal_places}f}"

    # Swap comma and period for Vietnamese convention
    formatted = formatted.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

    return formatted


def is_vietnamese_text(text: str) -> bool:
    """
    Check if text contains Vietnamese-specific characters.

    Args:
        text: Text to check

    Returns:
        True if text contains Vietnamese characters
    """
    vietnamese_chars = set('ăâđêôơưàằầèềìòồờùừỳáắấéếíóốớúứýảẳẩẻểỉỏổởủửỷãẵẫẽễĩõỗỡũữỹạặậẹệịọộợụựỵ')
    text_lower = text.lower()
    return any(char in vietnamese_chars for char in text_lower)


def tokenize_math_problem(problem: str) -> Dict[str, any]:
    """
    Tokenize a math problem into components.

    Args:
        problem: Math problem text

    Returns:
        Dictionary with problem components
    """
    result = {
        "raw_text": problem,
        "clean_text": clean_vietnamese_text(problem),
        "language": "vi" if is_vietnamese_text(problem) else "en",
        "complexity": estimate_complexity(problem),
        "has_multiple_parts": bool(re.search(r'[a-d]\)|[1-4]\)', problem)),
        "expressions": re.findall(r'[a-zA-Z]\s*\([a-zA-Z]\)\s*=\s*[^,\n]+', problem),
        "numbers": re.findall(r'-?\d+\.?\d*', problem),
    }

    return result


if __name__ == "__main__":
    # Test helpers
    test_problem = "Khao sat su bien thien va ve do thi ham so y = x^3 - 3x^2 + 4"

    print("Original:", test_problem)
    print("Cleaned:", clean_vietnamese_text(test_problem))
    print("Is Vietnamese:", is_vietnamese_text(test_problem))
    print("Complexity:", estimate_complexity(test_problem))
    print("Tokenized:", tokenize_math_problem(test_problem))
