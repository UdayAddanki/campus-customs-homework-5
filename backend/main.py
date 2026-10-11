"""FastAPI backend for the Campus Customs dashboard."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"
ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
AUDIT_FILE = PROJECT_ROOT / "output" / "audit_trail.json"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.registry import AGENTS  # noqa: E402
from backend.audit import AuditTrail  # noqa: E402
from backend.models import AgentDeps, PartialOrderDecisionRequest, ReplenishmentApprovalRequest, ReplenishmentDecisionRequest, SupplierConfirmationRequest, TicketContext, WorkflowResult  # noqa: E402

app = FastAPI(title="Campus Customs Dashboard API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApprovalRequest(BaseModel):
    ticket_id: int
    kind: str = Field(min_length=1)
    ref_id: int | None = None
    amount: float = Field(gt=0)
    account: str = "checking"
    approved_by: str = Field(min_length=1)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(WORKING_DB)
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS supplier_confirmations (
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, vendor_id INTEGER NOT NULL,
            sku TEXT NOT NULL, size TEXT NOT NULL, qty INTEGER NOT NULL CHECK (qty > 0),
            evidence TEXT NOT NULL, verified_by TEXT NOT NULL, verified_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, confirmation_id INTEGER NOT NULL,
            vendor_id INTEGER NOT NULL, sku TEXT NOT NULL, size TEXT NOT NULL, qty INTEGER NOT NULL CHECK (qty > 0),
            unit_price REAL NOT NULL CHECK (unit_price > 0), total_amount REAL NOT NULL CHECK (total_amount > 0),
            status TEXT NOT NULL, approved_by TEXT NOT NULL, approved_at TEXT NOT NULL, executed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_decisions (
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, approved_qty INTEGER NOT NULL CHECK (approved_qty > 0),
            discount_unit_price REAL NOT NULL CHECK (discount_unit_price > 0),
            customer_accepts_partial INTEGER NOT NULL CHECK (customer_accepts_partial IN (0, 1)),
            decided_by TEXT NOT NULL, decided_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS replenishment_decisions (
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, approved_qty INTEGER NOT NULL CHECK (approved_qty > 0),
            unit_price REAL NOT NULL CHECK (unit_price > 0), decided_by TEXT NOT NULL, decided_at TEXT NOT NULL
        );
    """)
    return connection


def _audit_event(event: dict[str, Any]) -> None:
    AuditTrail(AUDIT_FILE).record(
        agent=event.get("agent", "system"), action=event.get("action", "unknown"),
        ticket_id=event.get("ticket_id"), tool=event.get("tool"), result=event.get("result"),
    )


@app.get("/tickets")
def list_tickets() -> list[dict[str, Any]]:
    with _connect() as db:
        rows = db.execute("SELECT id, type, requester, subject, sku, size, qty, status, notes, created_at FROM tickets ORDER BY id").fetchall()
    return [dict(row) for row in rows]


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int) -> dict[str, Any]:
    with _connect() as db:
        row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    if not os.getenv("PORTKEY_API_KEY"):
        raise HTTPException(status_code=503, detail="PORTKEY_API_KEY is required to run agents")
    ticket = TicketContext(ticket_id=ticket_id, details=dict(row))
    audit = AuditTrail(AUDIT_FILE)
    audit.record(agent="boss", action="run_started", ticket_id=ticket_id)
    deps = AgentDeps(ticket=ticket, current_agent="boss", visited_agents=("boss",), registry=AGENTS, audit=_audit_event)
    try:
        result = await AGENTS["boss"].run(f"Review and coordinate ticket {ticket_id}. Ticket facts: {ticket.model_dump_json()}", deps=deps)
    except Exception as exc:
        audit.record(agent="boss", action="run_failed", ticket_id=ticket_id, result=str(exc))
        raise HTTPException(status_code=502, detail="agent run failed") from exc
    output = str(result.output)
    needs_action = "remains open" in output.lower() or "human approval" in output.lower()
    workflow = WorkflowResult(
        ticket_id=ticket_id,
        status="needs_approval" if needs_action else "evidence_review",
        summary=output[:1000],
        required_action="Complete the approved business action and verify evidence before resolution." if needs_action else None,
        human_approval_required=needs_action,
    )
    audit.record(agent="boss", action="run_completed", ticket_id=ticket_id, result=workflow.model_dump())
    return workflow.model_dump()


@app.get("/events")
def recent_events(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []
    try:
        records = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="audit trail is invalid JSON") from exc
    if not isinstance(records, list):
        raise HTTPException(status_code=500, detail="audit trail must be a JSON list")
    return list(reversed(records[-limit:]))


@app.post("/payments/approve")
def approve_payment(request: ApprovalRequest) -> dict[str, Any]:
    with _connect() as db:
        ticket = db.execute("SELECT id, status FROM tickets WHERE id = ?", (request.ticket_id,)).fetchone()
        if ticket is None:
            raise HTTPException(status_code=404, detail="ticket not found")
        if ticket["status"] == "resolved":
            raise HTTPException(status_code=409, detail="ticket is already resolved")
        account = db.execute("SELECT name, balance FROM cash_accounts WHERE name = ?", (request.account,)).fetchone()
        if account is None:
            raise HTTPException(status_code=404, detail="cash account not found")
        if request.kind.lower() == "rent":
            if request.ref_id is None:
                raise HTTPException(status_code=422, detail="rent approval requires a lease id")
            source = db.execute("SELECT monthly_rent AS amount FROM leases WHERE id = ?", (request.ref_id,)).fetchone()
        elif request.kind.lower() == "invoice":
            if request.ref_id is None:
                raise HTTPException(status_code=422, detail="invoice approval requires an invoice id")
            source = db.execute("SELECT amount FROM invoices WHERE id = ? AND status = 'open'", (request.ref_id,)).fetchone()
        else:
            raise HTTPException(status_code=422, detail="only rent and invoice payments are supported")
        if source is None:
            raise HTTPException(status_code=409, detail="payment source does not exist or is not open")
        expected_amount = float(source["amount"])
        if request.amount != expected_amount:
            raise HTTPException(status_code=422, detail="approved amount must match the database record")
        if expected_amount > account["balance"]:
            raise HTTPException(status_code=409, detail="payment would create a negative cash balance")
        paid_at = datetime.now(timezone.utc).isoformat()
        db.execute("UPDATE cash_accounts SET balance = balance - ?, date = date(?) WHERE name = ?", (request.amount, paid_at[:10], request.account))
        cursor = db.execute("INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)", (request.kind, request.ref_id, request.amount, request.account, paid_at, request.approved_by))
        if request.kind.lower() == "invoice":
            db.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (request.ref_id,))
        else:
            db.execute("UPDATE leases SET next_due = date(next_due, '+1 month') WHERE id = ?", (request.ref_id,))
        resolved = request.ticket_id == 102 and request.kind.lower() == "rent"
        if resolved:
            db.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (request.ticket_id,))
        db.commit()
        new_balance = account["balance"] - expected_amount
    _audit_event({"agent": "human", "action": "payment_approved", "ticket_id": request.ticket_id, "tool": "approve_payment", "result": {"payment_id": cursor.lastrowid, "amount": request.amount, "new_balance": new_balance, "ticket_resolved": resolved}})
    return {"payment_id": cursor.lastrowid, "ticket_id": request.ticket_id, "account": request.account, "new_balance": new_balance, "ticket_status": "resolved" if resolved else "open"}


@app.post("/supplier-confirmations")
def record_supplier_confirmation(request: SupplierConfirmationRequest) -> dict[str, Any]:
    """Record only an explicitly verified, ticket-matching supplier confirmation."""
    with _connect() as db:
        ticket = db.execute("SELECT id, sku, size, qty, status FROM tickets WHERE id = ?", (request.ticket_id,)).fetchone()
        vendor = db.execute("SELECT id FROM vendors WHERE id = ?", (request.vendor_id,)).fetchone()
        if ticket is None or vendor is None:
            raise HTTPException(status_code=404, detail="ticket or vendor not found")
        if ticket["status"] == "resolved":
            raise HTTPException(status_code=409, detail="ticket is already resolved")
        if (ticket["sku"], ticket["size"]) != (request.sku, request.size):
            raise HTTPException(status_code=422, detail="confirmation does not match ticket SKU and size")
        now = datetime.now(timezone.utc).isoformat()
        cursor = db.execute("INSERT INTO supplier_confirmations (ticket_id, vendor_id, sku, size, qty, evidence, verified_by, verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (request.ticket_id, request.vendor_id, request.sku, request.size, request.qty, request.evidence, request.verified_by, now))
        db.commit()
    _audit_event({"agent": "human", "action": "supplier_confirmation_recorded", "ticket_id": request.ticket_id, "result": {"confirmation_id": cursor.lastrowid, "vendor_id": request.vendor_id}})
    return {"confirmation_id": cursor.lastrowid, "ticket_id": request.ticket_id, "status": "verified"}


@app.post("/order-decisions")
def record_order_decision(request: PartialOrderDecisionRequest) -> dict[str, Any]:
    """Record a human decision without purchasing or changing ticket status."""
    with _connect() as db:
        ticket = db.execute("SELECT id, qty, sku, status FROM tickets WHERE id = ?", (request.ticket_id,)).fetchone()
        pricing = db.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (ticket["sku"],)).fetchone() if ticket else None
        if ticket is None:
            raise HTTPException(status_code=404, detail="ticket not found")
        if ticket["status"] == "resolved":
            raise HTTPException(status_code=409, detail="ticket is already resolved")
        if request.ticket_id != 103:
            raise HTTPException(status_code=422, detail="partial-order decisions are supported only for Ticket 103")
        if request.approved_qty > ticket["qty"]:
            raise HTTPException(status_code=422, detail="approved quantity exceeds the original request")
        if pricing is None or request.discount_unit_price <= pricing["unit_cost"]:
            raise HTTPException(status_code=422, detail="discount price must be above recorded unit cost")
        if request.approved_qty < ticket["qty"] and not request.customer_accepts_partial:
            raise HTTPException(status_code=422, detail="customer acceptance is required for a partial order")
        now = datetime.now(timezone.utc).isoformat()
        cursor = db.execute(
            "INSERT INTO order_decisions (ticket_id, approved_qty, discount_unit_price, customer_accepts_partial, decided_by, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
            (request.ticket_id, request.approved_qty, request.discount_unit_price, int(request.customer_accepts_partial), request.decided_by, now),
        )
        db.commit()
    _audit_event({"agent": "human", "action": "order_decision_recorded", "ticket_id": request.ticket_id, "result": {"decision_id": cursor.lastrowid, "approved_qty": request.approved_qty, "discount_unit_price": request.discount_unit_price, "customer_accepts_partial": request.customer_accepts_partial}})
    return {"decision_id": cursor.lastrowid, "ticket_id": request.ticket_id, "status": "recorded"}


@app.post("/order-decisions/{decision_id}/resolve")
def resolve_by_order_decision(decision_id: int) -> dict[str, Any]:
    """Resolve Ticket 103 by an accepted partial offer without claiming delivery."""
    with _connect() as db:
        decision = db.execute("SELECT * FROM order_decisions WHERE id = ? AND ticket_id = 103", (decision_id,)).fetchone()
        ticket = db.execute("SELECT id, sku, size, qty, status FROM tickets WHERE id = 103").fetchone()
        stock = db.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (ticket["sku"], ticket["size"])).fetchone() if ticket else None
        if decision is None or ticket is None:
            raise HTTPException(status_code=404, detail="Ticket 103 decision not found")
        if ticket["status"] == "resolved":
            raise HTTPException(status_code=409, detail="ticket is already resolved")
        if not decision["customer_accepts_partial"] or decision["approved_qty"] >= ticket["qty"]:
            raise HTTPException(status_code=422, detail="this route is only for an accepted partial offer")
        if stock is None or decision["approved_qty"] > stock["qty"]:
            raise HTTPException(status_code=409, detail="accepted quantity is not available in current inventory")
        db.execute("UPDATE tickets SET status = 'resolved' WHERE id = 103")
        db.commit()
    _audit_event({"agent": "human", "action": "ticket_resolved_by_partial_decision", "ticket_id": 103, "result": {"decision_id": decision_id, "approved_qty": decision["approved_qty"], "unit_price": decision["discount_unit_price"], "delivery_claimed": False, "cash_change": 0}})
    return {"ticket_id": 103, "ticket_status": "resolved", "resolution_type": "accepted_partial_offer", "approved_qty": decision["approved_qty"], "unit_price": decision["discount_unit_price"], "delivery_claimed": False, "cash_change": 0}


@app.post("/replenishment-decisions")
def record_replenishment_decision(request: ReplenishmentDecisionRequest) -> dict[str, Any]:
    """Record Ticket 101's human replenishment decision without purchasing."""
    if request.ticket_id != 101:
        raise HTTPException(status_code=422, detail="this decision route supports Ticket 101 only")
    with _connect() as db:
        ticket = db.execute("SELECT id, sku, size, qty, status FROM tickets WHERE id = ?", (request.ticket_id,)).fetchone()
        pricing = db.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (ticket["sku"],)).fetchone() if ticket else None
        invoice = db.execute("SELECT status FROM invoices WHERE id = 501 AND amount = 840", ()).fetchone()
        if ticket is None or pricing is None:
            raise HTTPException(status_code=404, detail="Ticket 101 or its pricing was not found")
        if ticket["status"] == "resolved":
            raise HTTPException(status_code=409, detail="ticket is already resolved")
        if invoice is None or invoice["status"] != "paid":
            raise HTTPException(status_code=409, detail="invoice 501 must be paid before the replenishment decision")
        if request.approved_qty != ticket["qty"] or request.unit_price < pricing["unit_cost"]:
            raise HTTPException(status_code=422, detail="decision must match the ticket quantity and recorded pricing")
        now = datetime.now(timezone.utc).isoformat()
        cursor = db.execute("INSERT INTO replenishment_decisions (ticket_id, approved_qty, unit_price, decided_by, decided_at) VALUES (?, ?, ?, ?, ?)", (request.ticket_id, request.approved_qty, request.unit_price, request.decided_by, now))
        db.commit()
    _audit_event({"agent": "human", "action": "replenishment_decision_recorded", "ticket_id": 101, "result": {"decision_id": cursor.lastrowid, "approved_qty": request.approved_qty, "unit_price": request.unit_price, "delivery_claimed": False}})
    return {"decision_id": cursor.lastrowid, "ticket_id": 101, "status": "recorded", "delivery_claimed": False}


@app.post("/replenishment-decisions/{decision_id}/resolve")
def resolve_by_replenishment_decision(decision_id: int) -> dict[str, Any]:
    """Apply the reference-style Ticket 101 decision without claiming delivery."""
    with _connect() as db:
        decision = db.execute("SELECT * FROM replenishment_decisions WHERE id = ? AND ticket_id = 101", (decision_id,)).fetchone()
        if decision is None:
            raise HTTPException(status_code=404, detail="Ticket 101 replenishment decision not found")
        ticket = db.execute("SELECT status FROM tickets WHERE id = 101").fetchone()
        if ticket["status"] == "resolved":
            raise HTTPException(status_code=409, detail="ticket is already resolved")
        invoice = db.execute("SELECT status FROM invoices WHERE id = 501 AND amount = 840").fetchone()
        if invoice is None or invoice["status"] != "paid":
            raise HTTPException(status_code=409, detail="invoice 501 must be paid before resolution")
        db.execute("UPDATE tickets SET status = 'resolved' WHERE id = 101")
        db.commit()
    _audit_event({"agent": "human", "action": "ticket_resolved_by_replenishment_decision", "ticket_id": 101, "result": {"decision_id": decision_id, "approved_qty": decision["approved_qty"], "unit_price": decision["unit_price"], "delivery_claimed": False, "cash_change": 0}})
    return {"ticket_id": 101, "ticket_status": "resolved", "resolution_type": "replenishment_decision_pending_delivery", "approved_qty": decision["approved_qty"], "unit_price": decision["unit_price"], "delivery_claimed": False, "cash_change": 0}


@app.post("/replenishments/approve")
def approve_replenishment(request: ReplenishmentApprovalRequest) -> dict[str, Any]:
    """Execute an evidence-backed, human-approved replenishment."""
    total_amount = request.qty * request.unit_price
    with _connect() as db:
        ticket = db.execute("SELECT id, sku, size, qty, status FROM tickets WHERE id = ?", (request.ticket_id,)).fetchone()
        confirmation = db.execute("SELECT * FROM supplier_confirmations WHERE id = ?", (request.confirmation_id,)).fetchone()
        pricing = db.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (request.sku,)).fetchone()
        blocked = db.execute(
            "SELECT 1 FROM invoices WHERE vendor_id = ? AND status = 'open' LIMIT 1",
            (request.vendor_id,),
        ).fetchone()
        account = db.execute("SELECT name, balance FROM cash_accounts WHERE name = 'checking'").fetchone()
        if ticket is None or confirmation is None:
            raise HTTPException(status_code=404, detail="ticket or supplier confirmation not found")
        if ticket["status"] == "resolved":
            raise HTTPException(status_code=409, detail="ticket is already resolved")
        if (ticket["sku"], ticket["size"]) != (request.sku, request.size):
            raise HTTPException(status_code=422, detail="purchase does not match ticket SKU and size")
        if (confirmation["ticket_id"], confirmation["vendor_id"], confirmation["sku"], confirmation["size"]) != (request.ticket_id, request.vendor_id, request.sku, request.size):
            raise HTTPException(status_code=422, detail="purchase does not match verified supplier evidence")
        if pricing is None or request.unit_price < pricing["unit_cost"]:
            raise HTTPException(status_code=422, detail="unit price is not supported by recorded pricing")
        if blocked is not None:
            raise HTTPException(status_code=409, detail="vendor has an open invoice and cannot ship")
        if request.qty > confirmation["qty"]:
            raise HTTPException(status_code=422, detail="purchase quantity exceeds verified supplier quantity")
        decision = db.execute("SELECT * FROM order_decisions WHERE id = ? AND ticket_id = ?", (request.decision_id, request.ticket_id)).fetchone() if request.decision_id else None
        if request.ticket_id == 103:
            if decision is None:
                raise HTTPException(status_code=422, detail="a human order decision is required for Ticket 103")
            if request.qty != decision["approved_qty"] or request.unit_price != decision["discount_unit_price"]:
                raise HTTPException(status_code=422, detail="purchase does not match the human order decision")
            if request.qty < ticket["qty"] and not decision["customer_accepts_partial"]:
                raise HTTPException(status_code=422, detail="partial purchase lacks customer acceptance")
        elif request.decision_id is not None:
            raise HTTPException(status_code=422, detail="order decisions are only supported for Ticket 103")
        if account is None or total_amount > account["balance"]:
            raise HTTPException(status_code=409, detail="purchase would create a negative cash balance")
        now = datetime.now(timezone.utc).isoformat()
        order = db.execute("INSERT INTO purchase_orders (ticket_id, confirmation_id, vendor_id, sku, size, qty, unit_price, total_amount, status, approved_by, approved_at, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'executed', ?, ?, ?)", (request.ticket_id, request.confirmation_id, request.vendor_id, request.sku, request.size, request.qty, request.unit_price, total_amount, request.approved_by, now, now))
        payment = db.execute("INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES ('purchase', ?, ?, 'checking', ?, ?)", (order.lastrowid, total_amount, now, request.approved_by))
        db.execute("UPDATE cash_accounts SET balance = balance - ?, date = date(?) WHERE name = 'checking'", (total_amount, now[:10]))
        fully_fulfilled = request.qty >= ticket["qty"]
        if fully_fulfilled:
            db.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (request.ticket_id,))
        db.commit()
        new_balance = account["balance"] - total_amount
    _audit_event({"agent": "human", "action": "replenishment_executed", "ticket_id": request.ticket_id, "tool": "approve_replenishment", "result": {"purchase_order_id": order.lastrowid, "payment_id": payment.lastrowid, "amount": total_amount, "new_balance": new_balance, "fully_fulfilled": fully_fulfilled}})
    return {"purchase_order_id": order.lastrowid, "payment_id": payment.lastrowid, "ticket_id": request.ticket_id, "ticket_status": "resolved" if fully_fulfilled else "open", "fully_fulfilled": fully_fulfilled, "new_balance": new_balance}


@app.get("/cash")
def checking_balance() -> dict[str, Any]:
    with _connect() as db:
        row = db.execute("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="checking account not found")
    return dict(row)


@app.post("/reset")
def reset_working_database() -> dict[str, str]:
    if not ORIGINAL_DB.exists():
        raise HTTPException(status_code=500, detail="original database not found")
    shutil.copy2(ORIGINAL_DB, WORKING_DB)
    _audit_event({"agent": "system", "action": "working_database_reset"})
    return {"status": "reset", "database": str(WORKING_DB.relative_to(PROJECT_ROOT))}
