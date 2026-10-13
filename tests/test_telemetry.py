import json
import time

from src import telemetry


def test_estimate_tokens_counts_word_like_substrings():
    assert telemetry.estimate_tokens({"a": "hello world", "b": 3}) == 5  # a, hello, world, b, 3


def test_tool_call_span_writes_real_latency_and_estimated_tokens(tmp_path):
    out_path = tmp_path / "spans.jsonl"
    telemetry.configure(out_path)

    with telemetry.tool_call_span("create_account", "crm", {"id": "a1", "name": "Acme"}) as record:
        time.sleep(0.02)
        record["response"] = {"ok": True, "id": "a1"}
        record["ok"] = True

    rows = [json.loads(line) for line in out_path.read_text().splitlines()]
    assert len(rows) == 1
    attrs = rows[0]["attributes"]
    assert attrs["gen_ai.tool.name"] == "create_account"
    assert attrs["agentbench.environment"] == "crm"
    assert attrs["agentbench.ok"] is True
    assert attrs["agentbench.latency_ms"] >= 20.0
    assert attrs["agentbench.request_tokens"] > 0
    assert attrs["agentbench.response_tokens"] > 0
    assert attrs["agentbench.cost_usd"] > 0


def test_tool_call_span_records_failure(tmp_path):
    out_path = tmp_path / "spans.jsonl"
    telemetry.configure(out_path)

    with telemetry.tool_call_span("adjust_stock", "inventory", {"id": "p1"}) as record:
        record["response"] = None
        record["ok"] = False

    rows = [json.loads(line) for line in out_path.read_text().splitlines()]
    assert rows[0]["attributes"]["agentbench.ok"] is False
    assert rows[0]["attributes"]["agentbench.response_tokens"] == 0
