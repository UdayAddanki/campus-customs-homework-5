"""Inventory agent prompt binding."""

from ..prompt_loader import load_prompt
from .delegation import build_agent

INVENTORY_PROMPT = load_prompt("inventory.md")
INVENTORY_AGENT = build_agent("inventory", INVENTORY_PROMPT)
