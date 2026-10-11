"""Customer Service agent prompt binding."""

from ..prompt_loader import load_prompt
from .delegation import build_agent

CUSTOMER_SERVICE_PROMPT = load_prompt("customer_service.md")
CUSTOMER_SERVICE_AGENT = build_agent("customer_service", CUSTOMER_SERVICE_PROMPT)
