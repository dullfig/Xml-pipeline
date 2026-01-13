"""
Calculate tool - evaluate mathematical expressions.

Uses simpleeval for safe expression evaluation with Python syntax.
"""

from .base import tool, ToolResult

# TODO: pip install simpleeval
# from simpleeval import simple_eval
# import math

MATH_FUNCTIONS = {
    # "abs": abs,
    # "round": round,
    # "min": min,
    # "max": max,
    # "sqrt": math.sqrt,
    # "sin": math.sin,
    # "cos": math.cos,
    # "tan": math.tan,
    # "log": math.log,
    # "log10": math.log10,
}

MATH_CONSTANTS = {
    # "pi": math.pi,
    # "e": math.e,
}


@tool
async def calculate(expression: str) -> ToolResult:
    """
    Evaluate a mathematical expression using Python syntax.

    Supported:
    - Basic ops: + - * / // % **
    - Comparisons: < > <= >= == !=
    - Functions: abs, round, min, max, sqrt, sin, cos, tan, log, log10
    - Constants: pi, e
    - Parentheses for grouping

    Examples:
    - "2 + 2" → 4
    - "(10 + 5) * 3" → 45
    - "sqrt(16) + pi" → 7.141592...
    """
    # TODO: Implement with simpleeval
    # try:
    #     result = simple_eval(
    #         expression,
    #         functions=MATH_FUNCTIONS,
    #         names=MATH_CONSTANTS,
    #     )
    #     return ToolResult(success=True, data=result)
    # except Exception as e:
    #     return ToolResult(success=False, error=str(e))

    return ToolResult(success=False, error="Not implemented - install simpleeval")
