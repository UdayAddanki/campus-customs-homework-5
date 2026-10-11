"""Shared registry wiring all five agents for peer delegation."""

from .accounting import ACCOUNTING_AGENT
from .boss import BOSS_AGENT
from .customer_service import CUSTOMER_SERVICE_AGENT
from .facilities import FACILITIES_AGENT
from .inventory import INVENTORY_AGENT

AGENTS = {
    "boss": BOSS_AGENT,
    "inventory": INVENTORY_AGENT,
    "accounting": ACCOUNTING_AGENT,
    "facilities": FACILITIES_AGENT,
    "customer_service": CUSTOMER_SERVICE_AGENT,
}
