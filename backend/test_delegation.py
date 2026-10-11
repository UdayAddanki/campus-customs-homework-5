"""Focused tests for bounded specialist delegation."""

from backend.models import AgentDeps, TicketContext


def deps() -> AgentDeps:
    return AgentDeps(ticket=TicketContext(ticket_id=101), current_agent="boss", visited_agents=("boss",))


def test_boss_inventory_accounting_boss_path_is_allowed() -> None:
    returned = deps().child("inventory", "Check stock").child("accounting", "Review invoice 501").child("boss", "Return findings")
    assert returned.visited_agents == ("boss", "inventory", "accounting", "boss")
    assert returned.delegation_depth == 3


def test_self_delegation_is_rejected() -> None:
    try:
        deps().child("boss", "Do my own work")
    except RuntimeError as exc:
        assert "loop prevented" in str(exc)
    else:
        raise AssertionError("self-delegation was not rejected")


def test_non_root_cycle_is_rejected() -> None:
    accounting = deps().child("inventory", "Check stock").child("accounting", "Review invoice")
    try:
        accounting.child("inventory", "Ask for stock again")
    except RuntimeError as exc:
        assert "loop prevented" in str(exc)
    else:
        raise AssertionError("non-root cycle was not rejected")


def test_root_cannot_delegate_after_return() -> None:
    returned = deps().child("inventory", "Check stock").child("accounting", "Review invoice").child("boss", "Return findings")
    try:
        returned.child("customer_service", "Draft a message")
    except RuntimeError as exc:
        assert "depth limit" in str(exc)
    else:
        raise AssertionError("depth limit was not enforced")
