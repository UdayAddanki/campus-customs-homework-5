# Campus Customs MCP Server

This FastMCP server provides read-only tools that retrieve database context for Campus Customs tickets and calculate pricing margins. The tools use `data/campus_customs_new.db`, leaving the original database unchanged. The database is opened only when a tool is called; importing `server.py` does not connect to it, and running the file starts the MCP server through `mcp.run()`.

## Tools

- `get_ticket_101_replenishment_context` reads `tickets`, `inventory`, `invoices`, `vendors`, and `pricing` to show that the requested size-S Bulldog tee is out of stock and provide the linked rush-reprint invoice, supplier, and tee pricing needed to address replenishment.
- `get_ticket_102_rent_payment_context` reads `tickets`, `leases`, `desk`, `cash_accounts`, and `payments` to show the linked Chapel Street rent obligation, current date, available checking balance, and existing payment history needed to address the rent notice.
- `get_ticket_103_bulk_discount_context` reads `tickets`, `inventory`, `pricing`, and `vendors` to compare the requested 20 size-M hoodies with the 8 in stock and assess the listed cost/price and supplier lead-time context for the discount request.
- `check_margin` reads `pricing` for a SKU and proposed unit price, returning the recorded cost/list price, discount percentage, margins, and a `below_cost` safety flag. It calculates information only and does not approve a discount or change the database.

There are no payment, inventory-update, lease-update, customer-messaging, or agent-delegation tools in this MCP server. The server entry point is `server.py`.
