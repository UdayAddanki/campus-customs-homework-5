# Campus Customs Homework 5

Campus Customs is a shop-operations project with a FastMCP server, a PydanticAI agent team, a FastAPI backend, and a React dashboard.

## Project layout

- `data/` contains the original `campus_customs.db` and working `campus_customs_new.db` databases.
- `mcp_server/` contains the read-only shop-information MCP server.
- `backend/` contains shared models, agent implementations, prompts, API routes, and tests.
- `frontend/` contains the React/Vite dashboard.
- `output/` contains harness documentation, smoke-test evidence, dashboard pages, screenshots, resolved-ticket records, and the append-only audit trail.

## Setup

1. Create a Python environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and set `PORTKEY_API_KEY` when running agents.
3. Start the API from `backend/` with `uvicorn main:app --reload --port 8000`.
4. Start the dashboard from `frontend/` with `npm run dev`.

The original database is kept unchanged. Workflows use `data/campus_customs_new.db` and require human approval for payments and purchases.
