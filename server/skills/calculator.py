from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel
from typing import Type

class CalculatorInput(BaseModel):
    expression: str = Field(description="The mathematical expression to evaluate (e.g., '2 + 2', '3 * 5').")

class CalculatorSkill(BaseTool):
    name: str = "calculator"
    description: str = "Useful for performing simple mathematical calculations."
    args_schema: Type[BaseModel] = CalculatorInput

    def _run(self, expression: str) -> str:
        try:
            # Dangerous in production, but okay for demo if controlled
            # In real world, use a safe eval library or llm
            # For this context, we'll just use eval but be careful
            allowed_chars = "0123456789+-*/(). "
            if not all(c in allowed_chars for c in expression):
                return "Error: Invalid characters in expression."
            
            return str(eval(expression))
        except Exception as e:
            return f"Error calculating: {e}"

# Export instance
calculator = CalculatorSkill()
