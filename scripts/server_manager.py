"""Starts and stops the three environment processes and the gateway process as
real local subprocesses, each bound to its own port, holding their PIDs so they
can be torn down cleanly. If a default port is busy, the next free port is
picked and the gateway is launched with env vars pointing at the real ports.
"""

import os
import socket
import subprocess
import sys
import time

import requests

from src import config

PYTHON = sys.executable


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.bind((config.HOST, port))
            return True
        except OSError:
            return False


def _pick_port(preferred: int) -> int:
    port = preferred
    while not _port_free(port):
        port += 1
    return port


def _wait_healthy(url: str, timeout_s: float = 20.0):
    deadline = time.time() + timeout_s
    last_exc = None
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
        time.sleep(0.2)
    raise RuntimeError(f"server at {url} never became healthy: {last_exc}")


def start_all():
    ports = {name: _pick_port(p) for name, p in config.DEFAULT_PORTS.items()}
    procs = {}

    env_modules = {
        "crm": "src.environments.crm_service:app",
        "ticketing": "src.environments.ticketing_service:app",
        "inventory": "src.environments.inventory_service:app",
    }
    for name, module in env_modules.items():
        proc = subprocess.Popen(
            [PYTHON, "-m", "uvicorn", module, "--host", config.HOST, "--port", str(ports[name]), "--log-level", "warning"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs[name] = {"proc": proc, "port": ports[name], "url": f"http://{config.HOST}:{ports[name]}"}

    for name in env_modules:
        _wait_healthy(procs[name]["url"] + "/health")

    gw_env = dict(os.environ)
    gw_env["AGENTENV_CRM_URL"] = procs["crm"]["url"]
    gw_env["AGENTENV_TICKETING_URL"] = procs["ticketing"]["url"]
    gw_env["AGENTENV_INVENTORY_URL"] = procs["inventory"]["url"]

    gw_proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "src.gateway.app:app", "--host", config.HOST, "--port", str(ports["gateway"]), "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=gw_env,
    )
    procs["gateway"] = {"proc": gw_proc, "port": ports["gateway"], "url": f"http://{config.HOST}:{ports['gateway']}"}
    _wait_healthy(procs["gateway"]["url"] + "/health")

    return procs


def stop_all(procs: dict):
    for name, info in procs.items():
        proc = info["proc"]
        if proc.poll() is None:
            proc.terminate()
    deadline = time.time() + 10
    for name, info in procs.items():
        proc = info["proc"]
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            proc.kill()
