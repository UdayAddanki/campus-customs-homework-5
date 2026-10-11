"""Boss agent prompt binding."""

from ..prompt_loader import load_prompt
from .delegation import build_agent

BOSS_PROMPT = load_prompt("boss.md")
BOSS_AGENT = build_agent("boss", BOSS_PROMPT)
