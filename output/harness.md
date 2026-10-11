# Campus Customs Agent Harness

This harness documents the database schema and the relationships relevant to the agents.

## Tables and fields

- `cash_accounts`: `name` (primary key), `balance`, `date`. Tracks available cash and the date of the account snapshot so agents can assess affordability and liquidity.
- `desk`: `date_today`, `notes`. Provides the shop’s current operating date and shared desk notes for time-sensitive decisions.
- `inventory`: `sku`, `name`, `size`, `qty`, `location` (primary key: `sku`, `size`). Shows product stock by size and where it is located, allowing agents to check availability and fulfillment feasibility.
- `invoices`: `id` (primary key), `vendor_id` (foreign key to `vendors.id`), `amount`, `due_date`, `status`, `description`. Records vendor bills so agents can manage obligations, due dates, and purchasing context.
- `leases`: `id` (primary key), `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`. Stores shop lease obligations so agents can respond to rent notices and plan payments.
- `payments`: `id` (primary key), `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`. Provides the payment history needed to verify or record financial actions.
- `pricing`: `sku` (primary key), `unit_cost`, `list_price`. Supplies cost and selling-price data for margin checks and price decisions.
- `tickets`: `id` (primary key), `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id` (foreign key to `leases.id`), `invoice_id` (foreign key to `invoices.id`), `status`, `notes`, `created_at`. Centralizes incoming work and links operational requests to inventory, lease, and invoice records.
- `vendors`: `id` (primary key), `name`, `specialty`, `lead_days`. Identifies suppliers and their lead times so agents can evaluate sourcing options.

## Open ticket relationships

- Ticket `101` (customer order for one `CC-TEE-WHITE`, size `S`) links to inventory (`CC-TEE-WHITE`, `S`, quantity `0`) and invoice `501`. Invoice `501` links to vendor `1`, Bulldog Print Co., for an `$840` rush reprint; pricing lists the tee at `$8` unit cost and `$28` list price. The item is out of stock, so the invoice/vendor path is relevant to replenishment.
- Ticket `102` (rent notice from Elm City Properties) links to lease `1`, the Chapel Street shop lease, with `$2,400` monthly rent due `2026-09-02`. The desk date is `2026-08-31`, matching the note that rent is due in two days; cash account `checking` has `$3,400`, and payments currently has no rows.
- Ticket `103` (bulk price request for 20 `CC-HOOD-NAVY` hoodies, size `M`) links to inventory (`CC-HOOD-NAVY`, `M`, quantity `8`) and pricing (`$22` unit cost, `$58` list price). It has no direct lease or invoice link; agents need to account for a shortfall of 12 units and evaluate the requested discount against the listed margin and vendor lead times.

## MCP tools

- `get_ticket_101_replenishment_context` reads `tickets`, `inventory`, `invoices`, `vendors`, and `pricing` for ticket `101`; it retrieves the size-S tee’s zero stock plus its rush-reprint invoice, supplier, and pricing so an agent can address the customer’s unavailable item and replenishment path.
- `get_ticket_102_rent_payment_context` reads `tickets`, `leases`, `desk`, `cash_accounts`, and `payments` for ticket `102`; it retrieves the linked rent obligation, current date, checking balance, and payment history so an agent can assess the imminent rent notice and whether a payment is already recorded.
- `get_ticket_103_bulk_discount_context` reads `tickets`, `inventory`, `pricing`, and `vendors` for ticket `103`; it retrieves the requested quantity, current size-M stock, hoodie cost/list price, and supplier lead times so an agent can evaluate the 20-unit discount request and its 12-unit stock shortfall.
- `check_margin` reads `pricing` for a proposed Ticket 103 unit price and returns the recorded cost, list price, discount percentage, margins, and whether the price is at or below cost; it does not approve the discount or write data.

## Agent delegation

The five PydanticAI agents are:

- **Boss** (`backend/agents/boss.py`): reviews tickets, assigns work, coordinates multiple specialists, and checks evidence before resolution.
- **Inventory** (`backend/agents/inventory.py`): checks SKU/size quantities, identifies shortages, and evaluates recorded vendor and lead-time information before suggesting restock.
- **Accounting** (`backend/agents/accounting.py`): reviews cash, invoices, payments, and pricing; it prepares payment recommendations but cannot approve or complete payments.
- **Facilities** (`backend/agents/facilities.py`): handles lease, rent, dates, and shop-space issues and asks Accounting to verify related financial facts.
- **Customer Service** (`backend/agents/customer_service.py`): drafts accurate customer messages for human review and coordinates with Inventory, Accounting, and Boss when facts or direction are needed.

Each implementation loads its role prompt from `backend/prompts/` and uses the `gpt-6-luna` model through the Portkey endpoint. Each agent exposes delegation tools for the other four agents; every delegation request includes the current `TicketContext` and the requesting agent’s question. The delegated agent’s response is returned to the caller so it can continue its work.

Delegation is bounded by three hops and a visited-agent set: the expected Boss → specialist → specialist → Boss return is allowed, while self-delegation, non-root cycles, and any delegation after the return are rejected. A blocked delegation is delivered to the parent as a bounded finding instead of aborting the parent run. Each agent is also given the existing `MCPToolset` for `mcp_server/server.py`, so shop facts come through the MCP tools rather than a database-bypass layer. Peer responses do not authorize payments, customer contact, database writes, or invented facts.

## Safety controls

- **Customer communications:** Customer Service only drafts messages; its prompt forbids sending email, contacting customers directly, promising unverified delivery dates, or claiming an unsupported resolution. Human review is required.
- **Payment approvals:** Accounting can prepare and explain a payment recommendation, but every payment requires human approval. The current MCP server is read-only and has no payment-write or approval tool, so agents cannot represent a payment as completed.
- **Negative cash balances:** Available cash is read from `cash_accounts`; agents must not recommend a payment that would make the balance negative. No payment execution tool exists in the current implementation, so no balance-changing payment can be performed.
- **Token usage:** All agents use only `gpt-6-luna`; delegation depth is capped at two and repeated agents are rejected. Delegation questions and audit results are compact, and audit output truncates long string results to 500 characters.

## Audit trail

Agent events are appended to `output/audit_trail.json` through `backend/audit.py`. Records include a UTC timestamp, agent, action, ticket ID when available, tool name when applicable, and a compact result; delegation start/completion and peer responses are recorded so ticket handling can be traced without storing full transcripts. Existing JSON records are loaded and preserved before each append.

## Dashboard API routes

- `GET /tickets` returns the three working-database tickets and their current status.
- `POST /tickets/{ticket_id}/run` runs the Boss agent for a ticket and allows bounded delegation to the registered agent team.
- `GET /events?limit=50` returns recent audit events, including agent actions, delegation/tool names, and compact results.
- `POST /payments/approve` applies a human-approved payment, records it in `payments`, and debits the selected cash account only when the balance will not become negative.
- `GET /cash` returns the current checking balance from `cash_accounts`.
- `POST /order-decisions` records a human Ticket 103 quantity/discount decision and required customer acceptance without purchasing or changing ticket status; partial fulfillment remains open until the original order is complete.
- `POST /order-decisions/{decision_id}/resolve` supports the reference workflow's accepted partial offer: it requires customer acceptance and enough existing stock, marks Ticket 103 handled without claiming delivery, and makes no cash change.
- `POST /replenishment-decisions` and `POST /replenishment-decisions/{decision_id}/resolve` provide the reference-style Ticket 101 path after invoice 501 is paid; they record and apply a human $8 replenishment decision without claiming delivery or creating a purchase transaction.
- `POST /reset` restores `data/campus_customs_new.db` from the unchanged original database.

Approval results are ticket-linked. A successful approved rent payment for ticket `102` marks that ticket resolved; approvals for tickets `101` and `103` do not resolve them because replenishment/supplier evidence is still required.

`POST /supplier-confirmations` and `POST /replenishments/approve` are the guarded human workflow for future tickets 101/103 evidence: confirmation must match the ticket, replenishment must match verified evidence and recorded unit cost, cash must remain non-negative, and only successful execution resolves the ticket.
