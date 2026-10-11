"""Accounting agent prompt binding."""

from ..prompt_loader import load_prompt
from .delegation import build_agent

ACCOUNTING_PROMPT = load_prompt("accounting.md")
ACCOUNTING_AGENT = build_agent("accounting", ACCOUNTING_PROMPT)
