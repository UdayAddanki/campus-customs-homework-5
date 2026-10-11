"""Load the role prompts used by the Campus Customs agents."""

from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(filename: str) -> str:
    """Return a required agent prompt from backend/prompts."""
    path = PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing agent prompt: {path}")
    return path.read_text(encoding="utf-8")
