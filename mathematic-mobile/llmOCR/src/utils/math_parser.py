"""
Mathematical expression parser and evaluator.
"""
import re
import ast
import operator
from typing import Any, Dict, Union, List
from loguru import logger


class MathExpressionParser:
    """Safe mathematical expression parser and evaluator."""
    
    def __init__(self):
        # Supported operators
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        # Supported functions
        self.functions = {
            'abs': abs,
            'round': round,
            'max': max,
            'min': min,
            'sum': sum,
        }
    
    def evaluate_expression(self, expression: str) -> Union[float, int]:
        """
        Safely evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression as string
            
        Returns:
            Numerical result
            
        Raises:
            ValueError: If expression is invalid or unsafe
        """
        try:
            # Clean the expression
            cleaned_expr = self._clean_expression(expression)
            
            # Parse the expression
            tree = ast.parse(cleaned_expr, mode='eval')
            
            # Evaluate the AST
            result = self._eval_node(tree.body)
            
            return result
            
        except Exception as e:
            logger.error(f"Expression evaluation failed: {e}")
            raise ValueError(f"Invalid mathematical expression: {str(e)}")
    
    def _clean_expression(self, expression: str) -> str:
        """Clean and normalize the mathematical expression."""
        # Remove whitespace
        expression = expression.strip()
        
        # Replace common mathematical symbols
        replacements = {
            '×': '*',
            '÷': '/',
            '−': '-',
            '^': '**',  # Power operator
        }
        
        for old, new in replacements.items():
            expression = expression.replace(old, new)
        
        # Validate characters (only allow safe mathematical characters)
        allowed_chars = set('0123456789+-*/().** ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Expression contains invalid characters")
        
        return expression
    
    def _eval_node(self, node: ast.AST) -> Union[float, int]:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)
        
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            else:
                raise ValueError("Only numeric constants are allowed")
        
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = self.operators.get(type(node.op))
            
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
            
            # Handle division by zero
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("Division by zero")
            
            return op(left, right)
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = self.operators.get(type(node.op))
            
            if op is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
            
            return op(operand)
        
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            
            if func_name not in self.functions:
                raise ValueError(f"Function '{func_name}' is not allowed")
            
            args = [self._eval_node(arg) for arg in node.args]
            return self.functions[func_name](*args)
        
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")
    
    def parse_word_problem(self, problem_text: str) -> Dict[str, Any]:
        """
        Parse a word problem and extract mathematical components.
        
        Args:
            problem_text: Word problem as text
            
        Returns:
            Dictionary with parsed components
        """
        # This is a basic implementation - can be enhanced with NLP
        
        # Extract numbers from the text
        numbers = self._extract_numbers(problem_text)
        
        # Identify operation keywords
        operations = self._identify_operations(problem_text)
        
        # Try to construct a mathematical expression
        expression = self._construct_expression(numbers, operations, problem_text)
        
        return {
            'numbers': numbers,
            'operations': operations,
            'expression': expression,
            'problem_type': self._classify_problem_type(problem_text)
        }
    
    def _extract_numbers(self, text: str) -> List[Union[int, float]]:
        """Extract numeric values from text."""
        # Pattern to match integers and floats
        number_pattern = r'-?\d+\.?\d*'
        matches = re.findall(number_pattern, text)
        
        numbers = []
        for match in matches:
            try:
                if '.' in match:
                    numbers.append(float(match))
                else:
                    numbers.append(int(match))
            except ValueError:
                continue
        
        return numbers
    
    def _identify_operations(self, text: str) -> List[str]:
        """Identify mathematical operations mentioned in text."""
        operation_keywords = {
            'addition': ['add', 'plus', 'sum', 'total', 'combined', 'altogether'],
            'subtraction': ['subtract', 'minus', 'difference', 'less', 'remove', 'take away'],
            'multiplication': ['multiply', 'times', 'product', 'of', 'each', 'per'],
            'division': ['divide', 'divided by', 'quotient', 'split', 'share', 'each']
        }
        
        identified_ops = []
        text_lower = text.lower()
        
        for operation, keywords in operation_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if operation not in identified_ops:
                        identified_ops.append(operation)
                    break
        
        return identified_ops
    
    def _construct_expression(self, numbers: List[Union[int, float]], 
                            operations: List[str], text: str) -> str:
        """Attempt to construct a mathematical expression from components."""
        if not numbers or not operations:
            return ""
        
        # This is a very basic implementation
        # In practice, you'd need more sophisticated NLP to understand context
        
        if len(numbers) >= 2:
            if 'addition' in operations:
                return f"{numbers[0]} + {numbers[1]}"
            elif 'subtraction' in operations:
                return f"{numbers[0]} - {numbers[1]}"
            elif 'multiplication' in operations:
                return f"{numbers[0]} * {numbers[1]}"
            elif 'division' in operations:
                return f"{numbers[0]} / {numbers[1]}"
        
        return ""
    
    def _classify_problem_type(self, text: str) -> str:
        """Classify the type of mathematical problem."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['percentage', 'percent', '%']):
            return 'percentage'
        elif any(word in text_lower for word in ['area', 'perimeter', 'volume', 'geometry']):
            return 'geometry'
        elif any(word in text_lower for word in ['equation', 'solve for', 'unknown', 'x']):
            return 'algebra'
        elif any(word in text_lower for word in ['probability', 'chance', 'likelihood']):
            return 'probability'
        else:
            return 'arithmetic'
    
    def validate_expression(self, expression: str) -> bool:
        """
        Validate if an expression is safe to evaluate.
        
        Args:
            expression: Mathematical expression
            
        Returns:
            True if safe, False otherwise
        """
        try:
            # Try to parse the expression
            tree = ast.parse(expression, mode='eval')
            
            # Check for unsafe operations
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if node.func.id not in self.functions:
                        return False
                elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Exec, ast.Eval)):
                    return False
                elif isinstance(node, ast.Attribute):
                    return False  # No attribute access
            
            return True
            
        except:
            return False