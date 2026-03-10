"""
Unit tests for MathExpressionParser.
"""
import pytest
from src.utils.math_parser import MathExpressionParser


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def parser():
    return MathExpressionParser()


# ──────────────────────────────────────────────────────────────
# evaluate_expression – basic arithmetic
# ──────────────────────────────────────────────────────────────

class TestEvaluateExpression:
    def test_addition(self, parser):
        assert parser.evaluate_expression("2 + 3") == 5

    def test_subtraction(self, parser):
        assert parser.evaluate_expression("10 - 4") == 6

    def test_multiplication(self, parser):
        assert parser.evaluate_expression("3 * 4") == 12

    def test_division(self, parser):
        assert parser.evaluate_expression("10 / 2") == 5.0

    def test_power(self, parser):
        assert parser.evaluate_expression("2 ** 3") == 8

    def test_caret_power_operator(self, parser):
        assert parser.evaluate_expression("2^3") == 8

    def test_negative_number(self, parser):
        assert parser.evaluate_expression("-5 + 2") == -3

    def test_float_result(self, parser):
        assert abs(parser.evaluate_expression("1 / 3") - 0.3333) < 0.001

    def test_parentheses(self, parser):
        assert parser.evaluate_expression("(2 + 3) * 4") == 20

    def test_nested_parentheses(self, parser):
        assert parser.evaluate_expression("((1 + 2) * (3 + 4))") == 21

    def test_complex_expression(self, parser):
        assert parser.evaluate_expression("2 + 3 * 4 - 1") == 13

    def test_unary_minus(self, parser):
        assert parser.evaluate_expression("-(-5)") == 5

    def test_unary_plus(self, parser):
        assert parser.evaluate_expression("+5") == 5


# ──────────────────────────────────────────────────────────────
# evaluate_expression – math symbols replacement
# ──────────────────────────────────────────────────────────────

class TestEvaluateExpressionSymbols:
    def test_times_symbol(self, parser):
        assert parser.evaluate_expression("3 × 4") == 12

    def test_division_symbol(self, parser):
        assert parser.evaluate_expression("8 ÷ 2") == 4.0

    def test_minus_symbol(self, parser):
        assert parser.evaluate_expression("5 − 3") == 2

    def test_mixed_symbols(self, parser):
        assert parser.evaluate_expression("2 × 3 − 1") == 5


# ──────────────────────────────────────────────────────────────
# evaluate_expression – error cases
# ──────────────────────────────────────────────────────────────

class TestEvaluateExpressionErrors:
    def test_division_by_zero_raises(self, parser):
        with pytest.raises(ValueError, match="[Dd]ivision by zero"):
            parser.evaluate_expression("5 / 0")

    def test_invalid_expression_raises(self, parser):
        with pytest.raises(ValueError):
            parser.evaluate_expression("invalid text")

    def test_unsafe_import_raises(self, parser):
        with pytest.raises(ValueError):
            parser.evaluate_expression("__import__('os').system('ls')")

    def test_empty_string_raises(self, parser):
        with pytest.raises((ValueError, SyntaxError)):
            parser.evaluate_expression("")

    def test_unsafe_characters_raise(self, parser):
        with pytest.raises(ValueError):
            parser.evaluate_expression("os.listdir('.')")


# ──────────────────────────────────────────────────────────────
# validate_expression
# ──────────────────────────────────────────────────────────────

class TestValidateExpression:
    def test_valid_arithmetic(self, parser):
        assert parser.validate_expression("2 + 3") is True

    def test_valid_complex(self, parser):
        assert parser.validate_expression("(2 + 3) * 4") is True

    def test_invalid_syntax_returns_false(self, parser):
        assert parser.validate_expression("2 + + +") is False

    def test_attribute_access_returns_false(self, parser):
        assert parser.validate_expression("os.path") is False

    def test_empty_returns_false(self, parser):
        assert parser.validate_expression("") is False


# ──────────────────────────────────────────────────────────────
# _extract_numbers
# ──────────────────────────────────────────────────────────────

class TestExtractNumbers:
    def test_extracts_integers(self, parser):
        numbers = parser._extract_numbers("I have 3 apples and 5 oranges")
        assert 3 in numbers
        assert 5 in numbers

    def test_extracts_floats(self, parser):
        numbers = parser._extract_numbers("The price is 3.14 dollars")
        assert any(abs(n - 3.14) < 0.001 for n in numbers)

    def test_no_numbers_returns_empty(self, parser):
        numbers = parser._extract_numbers("no numbers here")
        assert numbers == []

    def test_multiple_numbers(self, parser):
        numbers = parser._extract_numbers("1 2 3 4 5")
        assert len(numbers) == 5


# ──────────────────────────────────────────────────────────────
# _identify_operations
# ──────────────────────────────────────────────────────────────

class TestIdentifyOperations:
    def test_addition_keywords(self, parser):
        ops = parser._identify_operations("add 3 and 5 together")
        assert "addition" in ops

    def test_subtraction_keywords(self, parser):
        ops = parser._identify_operations("subtract 3 from 10")
        assert "subtraction" in ops

    def test_multiplication_keywords(self, parser):
        ops = parser._identify_operations("multiply 4 times 5")
        assert "multiplication" in ops

    def test_division_keywords(self, parser):
        ops = parser._identify_operations("divide 10 by 2")
        assert "division" in ops

    def test_no_operation_returns_empty(self, parser):
        ops = parser._identify_operations("the cat sat on the mat")
        assert ops == []

    def test_multiple_operations(self, parser):
        ops = parser._identify_operations("add 3 then subtract 1")
        assert "addition" in ops
        assert "subtraction" in ops

    def test_no_duplicates_in_operations(self, parser):
        ops = parser._identify_operations("add 2 plus 3 sum together")
        assert ops.count("addition") == 1


# ──────────────────────────────────────────────────────────────
# parse_word_problem
# ──────────────────────────────────────────────────────────────

class TestParseWordProblem:
    def test_returns_dict_with_required_keys(self, parser):
        result = parser.parse_word_problem("Add 3 and 5")
        assert "numbers" in result
        assert "operations" in result
        assert "expression" in result
        assert "problem_type" in result

    def test_addition_problem(self, parser):
        result = parser.parse_word_problem("John has 3 apples. Mary adds 5 more. Total?")
        assert 3 in result["numbers"]
        assert 5 in result["numbers"]
        assert "addition" in result["operations"]

    def test_subtraction_problem(self, parser):
        result = parser.parse_word_problem("Subtract 3 from 10")
        assert "subtraction" in result["operations"]

    def test_empty_expression_when_no_numbers(self, parser):
        result = parser.parse_word_problem("This is a question with no numbers")
        assert result["expression"] == ""


# ──────────────────────────────────────────────────────────────
# _classify_problem_type
# ──────────────────────────────────────────────────────────────

class TestClassifyProblemType:
    def test_percentage_type(self, parser):
        assert parser._classify_problem_type("What is 25% of 80?") == "percentage"

    def test_geometry_type(self, parser):
        assert parser._classify_problem_type("Find the area of the rectangle") == "geometry"

    def test_algebra_type(self, parser):
        assert parser._classify_problem_type("Solve for x: 2x + 3 = 7") == "algebra"

    def test_probability_type(self, parser):
        assert parser._classify_problem_type("What is the probability of rolling 6?") == "probability"

    def test_arithmetic_default(self, parser):
        assert parser._classify_problem_type("What is 2 plus 3?") == "arithmetic"


# ──────────────────────────────────────────────────────────────
# MathExpressionParser initialization
# ──────────────────────────────────────────────────────────────

class TestMathExpressionParserInit:
    def test_operators_dict_not_empty(self, parser):
        assert len(parser.operators) > 0

    def test_functions_dict_not_empty(self, parser):
        assert len(parser.functions) > 0

    def test_has_basic_operators(self, parser):
        import ast as ast_module
        assert ast_module.Add in parser.operators
        assert ast_module.Sub in parser.operators
        assert ast_module.Mult in parser.operators
        assert ast_module.Div in parser.operators
