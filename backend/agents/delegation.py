"""PydanticAI agent construction and bounded peer delegation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..models import AgentDeps, DelegationRequest

AGENT_NAMES = ("boss", "inventory", "accounting", "facilities", "customer_service")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MCP_TOOLSET = MCPToolset(str(PROJECT_ROOT / "mcp_server" / "server.py"), id="campus-customs-mcp")


def _model() -> OpenAIChatModel:
    """Use only gpt-6-luna through Portkey; construction does not make a request."""
    return OpenAIChatModel(
        "gpt-6-luna",
        provider=OpenAIProvider(
            base_url="https://api.portkey.ai/v1",
            api_key=os.getenv("PORTKEY_API_KEY"),
        ),
    )


async def _delegate(ctx: RunContext[AgentDeps], request: DelegationRequest) -> str:
    target = request.requester.strip().lower()
    if target not in AGENT_NAMES:
        raise ValueError(f"unknown agent: {request.requester}")
    if target == ctx.deps.current_agent:
        raise RuntimeError("an agent cannot delegate to itself")
    target_agent = ctx.deps.registry.get(target)
    if target_agent is None:
        raise RuntimeError(f"agent not registered: {target}")
    child_deps = ctx.deps.child(target, request.question)
    if ctx.deps.audit:
        ctx.deps.audit({"agent": ctx.deps.current_agent, "action": "tool_call_started", "tool": f"delegate_to_{target}", "ticket_id": child_deps.ticket.ticket_id})
    prompt = (
        f"Ticket context (do not discard or alter facts): {child_deps.ticket.model_dump_json()}\n"
        f"The {ctx.deps.current_agent} agent asks: {request.question}"
    )
    try:
        result = await target_agent.run(prompt, deps=child_deps)
    except RuntimeError as exc:
        # A peer may reasonably need the caller's facts, but cannot call back
        # through the same delegation chain. Return that limitation as a
        # finding so the parent can continue instead of aborting the ticket.
        if "delegation loop prevented" not in str(exc) and "delegation depth limit" not in str(exc):
            raise
        response = f"Delegation was safely stopped: {exc}. Continue using verified MCP findings and report the missing peer input."
        if ctx.deps.audit:
            ctx.deps.audit({"agent": ctx.deps.current_agent, "action": "delegation_blocked", "tool": f"delegate_to_{target}", "ticket_id": child_deps.ticket.ticket_id, "result": response})
        return response
    if ctx.deps.audit:
        ctx.deps.audit({"agent": ctx.deps.current_agent, "action": "tool_call_completed", "tool": f"delegate_to_{target}", "ticket_id": child_deps.ticket.ticket_id, "result": str(result.output)[:500]})
    return str(result.output)


def build_agent(name: str, prompt: str) -> Agent[AgentDeps, str]:
    """Build one agent with delegation tools for every other agent."""
    agent = Agent(_model(), name=name, system_prompt=prompt, deps_type=AgentDeps, model_settings={"openai_reasoning_effort": "none"}, toolsets=[MCP_TOOLSET])
    for target in AGENT_NAMES:
        if target == name:
            continue

        async def delegate(ctx: RunContext[AgentDeps], question: str, _target: str = target) -> str:
            request = DelegationRequest(ticket=ctx.deps.ticket, question=question, requester=_target)
            return await _delegate(ctx, request)

        delegate.__name__ = f"delegate_to_{target}"
        delegate.__doc__ = f"Ask the {target} agent for help using the current ticket context."
        agent.tool(delegate)
    return agent
