"""PlanExecutor: runs a Plan for real against the gateway (which routes to the real
environment processes and their real Postgres schemas), and records a Transcript.
This module, plus src/gateway and src/environments, is the "executor side" of the
project. src/oracle never imports anything from here; see
tests/test_oracle_independence.py for the mechanical check.
"""

import requests

from src.executor.plan import Plan, StepOutcome, Transcript


class PlanExecutor:
    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url.rstrip("/")

    def execute(self, task_id: str, instruction: str, plan: Plan) -> Transcript:
        transcript = Transcript(task_id=task_id, instruction=instruction)
        for call in plan.steps:
            try:
                resp = requests.post(
                    f"{self.gateway_url}/invoke",
                    json={"tool": call.tool, "args": call.args},
                    timeout=10,
                )
                resp.raise_for_status()
                payload = resp.json()
                transcript.steps.append(
                    StepOutcome(
                        tool=call.tool,
                        args=call.args,
                        ok=bool(payload.get("ok", False)),
                        message=str(payload.get("message", "")),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                transcript.steps.append(
                    StepOutcome(tool=call.tool, args=call.args, ok=False, message=f"executor error: {exc}")
                )
        return transcript
