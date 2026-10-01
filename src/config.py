"""Static configuration shared by infrastructure code (gateway routing, environment
services, the task generator). Nothing in src/oracle imports this module; the oracle
re-derives everything it needs about tool semantics from scratch (see
src/oracle/reference_simulator.py) so that its correctness never depends on this file
being right.
"""

import os

# Postgres connection. A dedicated role/database for this project only, created once
# with: createuser agentenv_app; createdb agent_env_bench -O agentenv_app
PG_HOST = os.environ.get("AGENTENV_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("AGENTENV_PG_PORT", "5432"))
PG_DB = os.environ.get("AGENTENV_PG_DB", "agent_env_bench")
PG_USER = os.environ.get("AGENTENV_PG_USER", "agentenv_app")
PG_PASSWORD = os.environ.get("AGENTENV_PG_PASSWORD", "agentenv_pw")

# Each of the three work environments is a separate local HTTP process with its own
# Postgres schema. Ports chosen in the 8800s to avoid colliding with other concurrent
# builds on this machine; if a port is ever busy, scripts/run_servers.py picks the next
# free one and writes the real ports to .pids/ports.json.
DEFAULT_PORTS = {
    "gateway": 8800,
    "crm": 8801,
    "ticketing": 8802,
    "inventory": 8803,
}

HOST = "127.0.0.1"

# The 13-tool gateway catalog: tool name -> (environment, HTTP method, path).
# This is infrastructure wiring (how a tool call reaches an environment process),
# not grading logic, so it is safe for the gateway, executor, and task generator to
# share it. The oracle does not import this: ReferenceSimulator re-encodes its own
# understanding of each tool's effect independently.
TOOL_CATALOG = {
    "create_account": ("crm", "POST", "/accounts"),
    "update_account_tier": ("crm", "POST", "/accounts/tier"),
    "create_contact": ("crm", "POST", "/contacts"),
    "delete_contact": ("crm", "POST", "/contacts/delete"),
    "create_opportunity": ("crm", "POST", "/opportunities"),
    "create_ticket": ("ticketing", "POST", "/tickets"),
    "assign_ticket": ("ticketing", "POST", "/tickets/assign"),
    "escalate_ticket": ("ticketing", "POST", "/tickets/escalate"),
    "close_ticket": ("ticketing", "POST", "/tickets/close"),
    "create_product": ("inventory", "POST", "/products"),
    "adjust_stock": ("inventory", "POST", "/stock/adjust"),
    "transfer_stock": ("inventory", "POST", "/stock/transfer"),
    "retire_product": ("inventory", "POST", "/products/retire"),
}

assert len(TOOL_CATALOG) == 13, "the resume claims exactly 13 named tools"

ENVIRONMENTS = ("crm", "ticketing", "inventory")

TOOLS_BY_ENVIRONMENT = {
    env: sorted(name for name, (e, _, _) in TOOL_CATALOG.items() if e == env)
    for env in ENVIRONMENTS
}
