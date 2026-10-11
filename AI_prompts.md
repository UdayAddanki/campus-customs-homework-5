# AI Prompts

This file records the prompts used while completing Homework 5. Each problem will have its own section with the original prompt, any follow-up prompt, and a brief explanation of what was missing from the first prompt.

## Problem 1: Create and maintain an AI prompts record

**Prompt typed:**

> Create AI_Prompts.md file and keep it updated as you work. Put one section for each problem and each section must include - the problem number and title, at least one prompt i typed and one follow up prompt if i type any with 1 sentence explanation of what was lacking after the first

## Problem 2: Inspect the campus customs database

**Prompt typed:**

> for problem 2 we will study the campus custom database. Please inspect `data/campus_customs.db` and go through every table and its fields. Make a copy named `data/campus_customs_new.db`, since we will use that copy for later work and keep the original unchanged.
> Also, look at the three open tickets and trace how they connect to the other tables. Start `output/harness.md` with a list of every table, the fields in each table, and one short sentence explaining why each table matters to the agents. We will add to this harness in later problems.

## Problem 3: Build the campus customs MCP server

**Prompt typed:**

> In the third problem, we will build the MCP server. Build an MCP server inside `mcp_server/` using FastMCP, and connect its tools to our working database, `data/campus_customs_new.db`. For this problem, just create the server and its tools. Don't connect to or run it yet.
> Create three clearly named tools based on the three open tickets in the database. Use only information that actually exists in the database. Do not invent any data.
> Update `output/harness.md` to document each of the three tools. For each tool, include: a) The table it reads. b) Which ticket it helps resolve (101, 102, or 103). c) a specific, one-sentence explanation of why the tool is useful for that ticket. Explain what information the tool retrieves and how that information helps address the ticket's particular issue. Avoid vague descriptions such as simply saying that the tool "checks inventory" or "reads invoices."
> Also, create `mcp_server/README.md` explaining the purpose of the MCP server, which database file it uses, and what each of the three tools does.
> Make sure the tool names, descriptions, and documentation are consistent with the actual tickets and database contents.

## Problem 4: Connect and test the campus customs MCP server

**Prompt typed:**

> we will move to problem 4 - we will add the MCP server we created to this project so Codex can connect to it and use its tools. Save the connection settings in `.mcp.json` at the project root, or use the appropriate local MCP configuration format if the environment stores server connections elsewhere.
> Once the server is connected, test each of the three MCP tools to make sure they work. Save the test results in `output/mcp_smoke.json`.
> For each tool, record: prompt used to call the tool, tool's name, and tool's output.
> Verify that the outputs match the actual data in `data/campus_customs_new.db`. Do not make up or change any results. Make sure all three tools have been tested and documented in the evidence file.

## Problem 5: Build the Campus Customs multi-agent system

**Prompt typed:**

> good job, now we will do 5th problem where we need to build a multi-agent system for Campus Customs using PydanticAI. The system should have five agents: Boss, Inventory, Accounting, Facilities, and Customer Service.
> Each agent should have its own prompt file in `backend/prompts/`. Put shared data types in `backend/models.py` and organize the agent implementation files under `backend/`.
> Use `PORTKEY_API_KEY` and only the `gpt-6-luna` model for all agents. Every agent should be able to delegate tasks to any of the other agents.
> The agents must use our MCP server to access shop information from `data/campus_customs_new.db`. Do not create a separate tools layer that bypasses MCP.
> The agents should append an audit record to `output/audit_trail.json` at every agent-loop step, including their actions and tool usage. Preserve existing records when running the system again. Do not clear or overwrite the audit trail.
> Update `output/harness.md` to document all five agents and every MCP tool, including the database table each tool uses. Add a safety section covering customer communications, payment approvals, and ways to control token usage. Update `mcp_server/README.md` so its tool list matches the actual implementation.
> I will provide detailed instructions for each agent next. Use those instructions when creating the individual agent prompt files. Make sure the implementation follows the shop's business rules and does not invent information that is missing from the database.

**Follow-up prompt typed:**

> Now create a separate prompt for each of the five agents. Save them in `backend/prompts/`, with one file each for Boss, Inventory, Accounting, Facilities, and Customer Service. Use the instructions below to define what each agent should do, which shop rules it must follow, and what it must not do. Make sure the corresponding agent code uses its prompt.

> [Detailed instructions for the Boss, Inventory, Accounting, Facilities, and Customer Service agents, including MCP usage, delegation, approvals, customer communication, and evidence requirements.]

**What was lacking after the first prompt:**

The first prompt established the required five-agent architecture and constraints but did not provide the role-specific duties and safety rules needed to write each agent’s prompt.

**Follow-up prompt typed:**

> Please check that all five agent implementations load their corresponding prompt files from `backend/prompts/`. Verify that each prompt includes the responsibilities, shop rules, and restrictions specified in our instructions. Also check that the prompts are consistent with the existing MCP tools and business rules. If anything is missing, fix it and tell me what you changed.

**What was lacking after the previous prompt:**

The previous prompt created the five role prompts but did not require verifying that implementation modules load them or that their rules match the currently available read-only MCP tools.

## Problem 5 follow-up: Implement agent delegation

**Follow-up prompt typed:**

> Now lets work on delegation between the five agents. I want every agent to be able to call the other four agents whenever it needs help. For example, Inventory should be able to ask Accounting about invoices or payments, and Customer Service should be able to ask Inventory about stock availability. The Boss agent should be able to assign tasks to any agent and coordinate between multiple agents when needed.
> Please implement this using PydanticAI and reuse the agent modules we have already created under `backend/agents/`. Make sure agents pass the relevant ticket details when asking another agent for help and use the response they receive to continue their work.
> Also make sure agents dont keep calling each other in loops and that the delegation follows the existing agent prompts and shop rules. They should continue to get shop information through MCP and should not make up missing information or bypass payment approval requirements.
> Once this is done, test that every agent can call the other four agents and share which tests passed, any issues you found, and which files you changed.

## Problem 5 follow-up: Implement the audit trail

**Follow-up prompt typed:**

> Now lets implement the audit trail. I want the agents to record what they do at every step, including which agent is working, what action it takes, which tools it calls, and the results it gets back.
> Save these records in `output/audit_trail.json`. Make sure new records are appended to the existing file and previous records are not deleted or overwritten when we run the agents again.
> Please make sure the audit trail also captures delegation between agents so we can follow how a ticket is handled from start to finish. Keep the records useful for understanding what happened without storing unnecessary information.
> After implementing this, test that the audit trail is created correctly and that new records are added without removing existing ones. Share the test results and the files you changed.

## Problem 5 follow-up: Update agent and MCP documentation

**Follow-up prompt typed:**

> Now lets update the documentation for Problem 5. Please update `output/harness.md` to include all five agents, what each agent does, how they delegate work to each other, and every MCP tool with the database table it uses.
> Also add a safety section explaining how we prevent agents from sending customer messages directly, how payment approval works, how we prevent payments from creating a negative cash balance, and how we keep token usage under control.
> Please update `mcp_server/README.md` so the list of tools matches the tools actually available in the MCP server. Make sure the documentation reflects the actual implementation and doesnt describe features that are not implemented.
> After making the changes, check both files for missing or inconsistent information and tell me what you updated.

## Problem 6: Review open tickets and MCP tools

**Prompt typed:**

> Before we write the Expected sections for Problem 6, please show me the details of open tickets 101, 102, and 103 from our working database. For each ticket, include what the issue is and the relevant information from the related tables. Also list our three MCP tools, what each tool returns, and which ticket each tool is useful for. Dont change any files or run the agents yet. I want to use this information to write my expected plan first.

**Continuation:**

> Create `output/desk_tickets.html` as a page I can open by double-clicking. Add one tab each for tickets 101, 102, and 103, plus Cash and Reflection tabs for later problems. For each ticket, put the requested Expected section first and leave an empty Actual section underneath it. Keep Cash and Reflection blank or add a short "Coming later" note. Make the page simple and easy to read. Do not run the agents or change the database for this problem.

**Continuation:**

> Now lets build the backend that our React dashboard can call. In `backend/main.py`, use FastAPI to add routes for tickets, running the agent team, recent agent events, human payment or purchase approval, the checking balance, and resetting the working database from the original. Use `data/campus_customs_new.db`, preserve shop safety rules, start the server with Uvicorn, test the routes, and update `output/harness.md` with one line per route.

## Problem 7: Build the FastAPI dashboard backend

**Prompt typed:**

> Now lets build the backend that our React dashboard can call. In `backend/main.py`, use FastAPI to add routes for the following:
> a) Return the three tickets and show whether each one is open or resolved.
> b) Take a ticket ID and run our agent team on that ticket.
> c) Return recent agent events, including what each agent said and which tools it used, so the dashboard can refresh.
> d) Approve a payment or purchase when a human clicks approve. The agents should only prepare the payment or purchase. The approval route should make the actual change to the cash balance.
> e) Return the current checking balance from `cash_accounts`.
> f) Reset the working database to its original values so we can try a fresh run.
> Keep the existing shop rules and safety checks in place. Use `data/campus_customs_new.db` for the working database and never change the original database.
> After implementing the routes, start the server from the `backend/` folder using `uvicorn main:app --reload --port 8000` and check that the routes work.
> Update `output/harness.md` with one line for each route, explaining its URL and what it does. Tell me which routes you tested and whether they passed.

## Problem 8: Build the React operations dashboard

**Prompt typed:**

> lets do problem 8 - now lets build the frontend dashboard in `frontend/` using React, Vite, and TypeScript. It should connect to our backend at `http://localhost:8000`, and the backend should allow requests from the Vite page at `http://localhost:5173`.
> I want the dashboard to feel like a real shop operations desk. Keep the design clean, modern, and easy to scan, with a navy and light neutral colour scheme and a clear accent colour for important actions.
> Show the three tickets as separate cards or rows, make the selected ticket easy to spot, and make open and resolved statuses visually different.
> When I choose a ticket and start the agents, show each agent's activity in a clear activity feed so I can follow what they are doing and which tools they use. When the run finishes, show a short summary of what each agent did and mark the ticket resolved only if the backend confirms the run finished successfully.
> Make any payment or purchase that needs approval stand out, with a clear human approve action. Keep the current checking balance visible and refresh it after an approved payment. Show errors and pending states clearly so I know what is happening.
> Make the page responsive and polished without overcrowding it. Use the existing backend routes from Problem 7.
> For now, focus on building the dashboard and getting it working. We will write `output/design.md` later after reviewing the actual design, so dont create or update that file yet.
> Run the frontend with `npm run dev` and check that the page loads and can call the backend. Tell me what you tested and whether it passed.

## Problem 9: Run and verify all three tickets

**Prompt typed:**

> First, reset `data/campus_customs_new.db` to match the original database so we start with a clean database. Note the starting checking balance. Then run all three tickets, 101, 102, and 103, using the dashboard until each ticket is resolved. Check the actual agent runs, delegation, tools, cash changes, resolved ticket evidence, audit trail, and harness documentation. Do not mark a ticket resolved unless the run actually succeeded, and if something fails, report what failed and what needs fixing before continuing.

**Continuation:**

> Let's fix the Problem 9 failure. Boss delegates to Inventory, but Inventory tries to delegate back to Boss, causing a loop. Also, no MCP tools completed. Please fix the delegation flow and MCP tool integration so agents can use the tools and return their findings to Boss. Keep all the safety rules and existing audit history. Add tests and run them to verify the fixes. Don't reset the database or run the tickets yet. Tell me what you fixed and whether the tests passed.

**Continuation:**

> Ticket 101 still failed because the delegation guard blocked the required Boss → Inventory → Accounting path. Please fix the guard to allow this workflow while still preventing agents from getting stuck in loops. Add tests for this path and for loop prevention, then run the tests. Don't reset the database or run any tickets yet. Keep the existing results and audit history unchanged. Tell me what you fixed and whether the tests passed.

**Continuation:**

> Let's go with option 1 for now. Ticket 102 can be resolved after the rent payment is approved and successfully completed. Tickets 101 and 103 should remain open if supplier capability or other required evidence cannot be verified. Please implement the minimum changes needed for structured results, ticket-linked human approvals, cash checks, and safe ticket status updates. Preserve the existing audit history and follow all safety rules. Add tests and run them, but don't run the actual tickets yet. Keep the code simple and tell me what changed and whether the tests passed.

**Continuation:**

> Please finish the screenshot part of Problem 9. Run the React dashboard and capture actual screenshots for Tickets 101, 102, and 103, showing each ticket's real status and results from the latest run. Add all three screenshots to `output/resolved_board.html` so I can open it in a browser and view them. Keep Ticket 102 resolved and Tickets 101 and 103 open. Don't change the database or rerun the tickets just to take screenshots. Tell me when it's done and where the screenshots are saved.

**Continuation:**

> Please investigate why Tickets 101 and 102 show “No activity yet” in the dashboard. Check `output/audit_trail.json` and the dashboard's activity feed logic to find the cause. Fix the issue so the actual recorded events appear for each ticket. Do not invent events, rerun workflows, reset the database, or change ticket statuses. After fixing it, tell me how to verify the activity feed and recapture the screenshots.

**Continuation:**

> For Problem 9, implement the smallest safe changes needed for Tickets 101 and 103. Only record supplier evidence when it is actually verified. Require human approval before payments or purchases, validate available cash, and resolve a ticket only after the approved action succeeds. Add tests for these safeguards. Preserve existing audit records and output files until real actions occur. Do not reset the database. If verified supplier evidence is unavailable, leave the ticket open and explain what is still needed.

**Continuation:**

> Record my human decisions using the new workflow. For Ticket 101, approve recording the $8 replenishment decision for one CC-TEE-WHITE, size S, with delivery not claimed. For Ticket 103, record my decision to offer the 8 in-stock CC-HOOD-NAVY hoodies, size M, at $58 each with no discount, and decline the $264 restock because current funds are insufficient. Do not fabricate supplier evidence, customer acceptance, payments, purchases, or inventory changes. Update the audit trail and Problem 9 output files, run all tests, and report final statuses and checking balance.

**Continuation:**

> For Ticket 103, the customer has accepted the offer of 8 available CC-HOOD-NAVY hoodies, size M, at $58 each, with no discount. Record this decision using the existing workflow and human approval. distinguish the decision from actual delivery, and do not claim that the remaining 12 hoodies were supplied. Update the audit trail and Problem 9 output files, run all tests, and report the final statuses and checking balance.

**Continuation:**

> Let's do one final check of Problem 9. Check whether all three tickets are resolved, the checking balance is $160, payments and inventory are correct, and all output files are updated. Check whether the screenshots are correct, especially Ticket 101. Run all tests and tell me if everything is ready to submit. Do not change anything; just verify.

## Problem 10: Fix the project layout

**Prompt typed:**

> For problem 10, first check whether my project matches the expected file layout. Check all required files and folders, including both database files under `data/` and all required files under `output/`. Also check `README.md`, `requirements.txt`, `.env.example`, `.gitignore`, and `.mcp.json`. Do not change anything yet. Give me a simple checklist of what is present, missing, or in the wrong location, and tell me what needs to be fixed before pushing to GitHub.

**Continuation:**

> Please fix the project layout based on the checklist. Add `requirements.txt`, `.env.example`, `.gitignore`, root `README.md`, and `output/github_url.txt`. Fix the `AI_Prompts.md` filename capitalization and rename the five agent prompt files from `.txt` to `.md`, updating any code references if needed. Keep both database files and all required output files. Exclude `.env`, `.DS_Store`, and `data (3).zip` from Git. Do not change database contents, ticket decisions, audit history, or working logic. Run the tests and verify the layout again. Do not push to GitHub yet.
