"""The unified tool gateway: one FastAPI process exposing exactly the 13 named
tools in src.config.TOOL_CATALOG, each routed to the correct work-environment
process over real HTTP. Run standalone with:
    uvicorn src.gateway.app:app --host 127.0.0.1 --port 8800

Environment base URLs are read from env vars so scripts/run_servers.py can point
this gateway at whatever ports the three environment processes actually bound to
(picked dynamically if the defaults were busy).
"""

import os

import requests
from fastapi import FastAPI
from pydantic import BaseModel

from src import config

app = FastAPI(title="agent-env-benchmark-gateway")

ENV_BASE_URLS = {
    "crm": os.environ.get("AGENTENV_CRM_URL", f"http://{config.HOST}:{config.DEFAULT_PORTS['crm']}"),
    "ticketing": os.environ.get(
        "AGENTENV_TICKETING_URL", f"http://{config.HOST}:{config.DEFAULT_PORTS['ticketing']}"
    ),
    "inventory": os.environ.get(
        "AGENTENV_INVENTORY_URL", f"http://{config.HOST}:{config.DEFAULT_PORTS['inventory']}"
    ),
}


class ToolInvocation(BaseModel):
    tool: str
    args: dict


@app.post("/invoke")
def invoke(body: ToolInvocation):
    if body.tool not in config.TOOL_CATALOG:
        return {"ok": False, "tool": body.tool, "message": f"unknown tool: {body.tool}"}
    environment, method, path = config.TOOL_CATALOG[body.tool]
    base = ENV_BASE_URLS[environment]
    try:
        resp = requests.request(method, base + path, json=body.args, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        return {
            "ok": bool(payload.get("ok", False)),
            "tool": body.tool,
            "environment": environment,
            "message": "ok" if payload.get("ok") else "environment reported failure",
            "response": payload,
        }
    except Exception as exc:  # noqa: BLE001 - surfaced to the transcript, not swallowed
        return {
            "ok": False,
            "tool": body.tool,
            "environment": environment,
            "message": f"gateway call failed: {exc}",
            "response": None,
        }


@app.get("/tools")
def list_tools():
    return {"tools": sorted(config.TOOL_CATALOG.keys()), "count": len(config.TOOL_CATALOG)}


@app.get("/health")
def health():
    return {"ok": True, "service": "gateway"}
