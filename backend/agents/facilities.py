"""Facilities agent prompt binding."""

from ..prompt_loader import load_prompt
from .delegation import build_agent

FACILITIES_PROMPT = load_prompt("facilities.md")
FACILITIES_AGENT = build_agent("facilities", FACILITIES_PROMPT)
