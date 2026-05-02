import json
import re


def clean_openai_json(content: str) -> str:
    """
    Strips markdown code fences from OpenAI chat responses so the result
    can be safely passed to json.loads().
    Handles both ```json ... ``` and plain ``` ... ``` wrappers.
    """
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return content.strip()


def parse_json_response(content: str) -> dict | None:
    """
    Cleans and parses an OpenAI JSON response.
    Returns None if parsing fails instead of raising.
    """
    try:
        return json.loads(clean_openai_json(content))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a float value between min_val and max_val."""
    return max(min_val, min(max_val, value))


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Divides a by b; returns default if b is zero."""
    return a / b if b != 0 else default


def format_response(data: dict) -> dict:
    """Wraps a data dict into a standard API response envelope."""
    return {"data": data, "success": True}
