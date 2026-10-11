"""FastMCP server exposing read-only context for the three open tickets.

The database is opened only when a tool is called; importing this module does
not connect to or start the MCP server.
"""

import json
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"

mcp = FastMCP("Campus Customs")


def _rows(connection: sqlite3.Connection, query: str, parameters: tuple = ()) -> list[dict]:
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(query, parameters).fetchall()]


@mcp.tool()
def check_margin(sku: str, proposed_unit_price: float, qty: int = 1) -> dict:
    """Calculate discount and margin from the recorded pricing table only."""
    if proposed_unit_price <= 0 or qty <= 0:
        raise ValueError("price and quantity must be positive")
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    if row is None:
        raise ValueError(f"no pricing exists for SKU {sku}")
    unit_cost = float(row["unit_cost"])
    list_price = float(row["list_price"])
    return {
        "sku": sku,
        "qty": qty,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "proposed_unit_price": proposed_unit_price,
        "discount_percent": round((1 - proposed_unit_price / list_price) * 100, 2),
        "unit_margin": round(proposed_unit_price - unit_cost, 2),
        "total_margin": round((proposed_unit_price - unit_cost) * qty, 2),
        "below_cost": proposed_unit_price <= unit_cost,
    }


@mcp.tool()
def get_ticket_101_replenishment_context() -> str:
    """Retrieve ticket 101's out-of-stock tee, related invoice, vendor, and pricing context."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        result = {
            "ticket": _rows(connection, "SELECT * FROM tickets WHERE id = 101"),
            "inventory": _rows(
                connection,
                "SELECT * FROM inventory WHERE sku = 'CC-TEE-WHITE' AND size = 'S'",
            ),
            "invoice": _rows(connection, "SELECT * FROM invoices WHERE id = 501"),
            "vendor": _rows(
                connection,
                "SELECT vendors.* FROM vendors JOIN invoices ON invoices.vendor_id = vendors.id WHERE invoices.id = 501",
            ),
            "pricing": _rows(connection, "SELECT * FROM pricing WHERE sku = 'CC-TEE-WHITE'"),
        }
    return json.dumps(result)


@mcp.tool()
def get_ticket_102_rent_payment_context() -> str:
    """Retrieve ticket 102's linked lease, current date, cash balance, and payment history."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        result = {
            "ticket": _rows(connection, "SELECT * FROM tickets WHERE id = 102"),
            "lease": _rows(
                connection,
                "SELECT leases.* FROM leases JOIN tickets ON tickets.lease_id = leases.id WHERE tickets.id = 102",
            ),
            "desk": _rows(connection, "SELECT * FROM desk"),
            "cash_accounts": _rows(connection, "SELECT * FROM cash_accounts"),
            "payments": _rows(connection, "SELECT * FROM payments"),
        }
    return json.dumps(result)


@mcp.tool()
def get_ticket_103_bulk_discount_context() -> str:
    """Retrieve ticket 103's requested hoodie quantity, stock, pricing, and vendor lead times."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        result = {
            "ticket": _rows(connection, "SELECT * FROM tickets WHERE id = 103"),
            "inventory": _rows(
                connection,
                "SELECT * FROM inventory WHERE sku = 'CC-HOOD-NAVY' AND size = 'M'",
            ),
            "pricing": _rows(connection, "SELECT * FROM pricing WHERE sku = 'CC-HOOD-NAVY'"),
            "vendors": _rows(connection, "SELECT * FROM vendors"),
        }
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()
