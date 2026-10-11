"""Shared Pydantic models for agent runs and bounded delegation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class TicketContext(BaseModel):
    """Ticket facts passed unchanged when an agent asks another agent for help."""

    ticket_id: int
    details: dict[str, Any] = Field(default_factory=dict)


class DelegationRequest(BaseModel):
    """A typed request sent from one named agent to another."""

    ticket: TicketContext
    question: str = Field(min_length=1)
    requester: str


class WorkflowResult(BaseModel):
    """Structured evidence used to decide whether a ticket may be resolved."""

    ticket_id: int
    status: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    required_action: str | None = None
    human_approval_required: bool = False


class SupplierConfirmationRequest(BaseModel):
    ticket_id: int
    vendor_id: int
    sku: str = Field(min_length=1)
    size: str = Field(min_length=1)
    qty: int = Field(gt=0)
    evidence: str = Field(min_length=1)
    verified_by: str = Field(min_length=1)


class ReplenishmentApprovalRequest(BaseModel):
    ticket_id: int
    confirmation_id: int
    vendor_id: int
    sku: str = Field(min_length=1)
    size: str = Field(min_length=1)
    qty: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    approved_by: str = Field(min_length=1)
    decision_id: int | None = None


class PartialOrderDecisionRequest(BaseModel):
    """A human decision about a partial Ticket 103 fulfillment."""

    ticket_id: int
    approved_qty: int = Field(gt=0)
    discount_unit_price: float = Field(gt=0)
    customer_accepts_partial: bool
    decided_by: str = Field(min_length=1)


class ReplenishmentDecisionRequest(BaseModel):
    """A human decision to proceed with a replenishment before delivery is recorded."""

    ticket_id: int
    approved_qty: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    decided_by: str = Field(min_length=1)


class AgentDeps(BaseModel):
    """Dependencies shared by all agents, including loop protection."""

    ticket: TicketContext
    current_agent: str
    delegation_depth: int = 0
    # Three hops permit Boss -> specialist -> specialist -> Boss.
    max_delegation_depth: int = 3
    visited_agents: tuple[str, ...] = ()
    registry: dict[str, Any] = Field(default_factory=dict)
    audit: Callable[[dict[str, Any]], None] | None = None

    model_config = {"arbitrary_types_allowed": True}

    def child(self, target: str, question: str) -> "AgentDeps":
        if self.delegation_depth >= self.max_delegation_depth:
            raise RuntimeError("delegation depth limit reached")
        root_agent = self.visited_agents[0] if self.visited_agents else self.current_agent
        is_allowed_root_return = target == root_agent and self.delegation_depth >= 2
        if target in self.visited_agents and not is_allowed_root_return:
            raise RuntimeError(f"delegation loop prevented: {target} already visited")
        child = self.model_copy(update={
            "current_agent": target,
            "delegation_depth": self.delegation_depth + 1,
            "visited_agents": (*self.visited_agents, target),
        })
        if child.audit:
            child.audit({"agent": self.current_agent, "action": "delegated", "tool": f"delegate_to_{target}", "ticket_id": self.ticket.ticket_id, "question": question})
        return child
