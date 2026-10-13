"""Per-step OpenTelemetry instrumentation for the gateway's one chokepoint,
`POST /invoke` in src/gateway/app.py. Every tool call gets one span carrying
the tool name, the environment it was routed to, its real wall-clock
latency, and an estimated token count and cost for that call.

Two things here are honestly disclosed stand-ins, not measurements against a
live model:

- **Token counts are estimated from payload size**, not a live LLM's own
  tokenizer: `estimate_tokens` counts word-like substrings in the serialized
  request and response JSON. No LLM is called during a replay run (the
  executor replays a fixed Plan; see the top-level README), so there is no
  real token count to attribute. This estimate is a reasonable proxy for
  request/response *size*, not a claim about what any specific model's
  tokenizer would report.
- **Cost is tokens times a stated, illustrative per-1K-token rate**
  (`COST_PER_1K_TOKENS`, modeled on a small hosted model's published input
  rate), not a real bill. The latency each span reports is real: it is the
  actual wall-clock time the gateway spent on that specific HTTP round trip
  to the environment process, measured with `time.perf_counter`.
"""

from __future__ import annotations

import json
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

COST_PER_1K_TOKENS = 0.00015  # matches a published small hosted model's per-1K input-token rate, stated for scale only

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def estimate_tokens(obj) -> int:
    """A disclosed proxy for token count: the number of word-like substrings
    in the object's JSON serialization. See the module docstring. A missing
    response (obj is None, e.g. a failed call) is 0 tokens, not the token
    count of the literal word "null"."""
    if obj is None:
        return 0
    return len(_TOKEN_PATTERN.findall(json.dumps(obj, default=str)))


class JsonlSpanExporter(SpanExporter):
    """Writes one JSON line per finished span to a file. This is the "raw
    output committed under docs/" this portfolio's README convention asks
    for; see docs/otel_spans_baseline.jsonl and
    docs/otel_spans_regressed.jsonl."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "a", encoding="utf-8")

    def export(self, spans) -> SpanExportResult:
        for span in spans:
            row = {
                "name": span.name,
                "start_time_ns": span.start_time,
                "end_time_ns": span.end_time,
                "duration_ms": round((span.end_time - span.start_time) / 1e6, 3),
                "attributes": dict(span.attributes or {}),
            }
            self._file.write(json.dumps(row) + "\n")
        self._file.flush()
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self._file.close()


_tracer = None
_exporter = None
_provider = None


def configure(jsonl_path: Path) -> None:
    """(Re)points tracing at a fresh JSONL file. Called once per measurement
    run (baseline, then regressed) so the two capture files never mix spans
    from different runs. Keeps its own TracerProvider rather than relying on
    `trace.set_tracer_provider`, because the OpenTelemetry API only allows
    the global provider to be set once per process; a second `configure()`
    call (as happens between the baseline and regressed capture passes, or
    between tests) would otherwise silently keep using the first run's
    already-closed exporter."""
    global _tracer, _exporter, _provider
    if _exporter is not None:
        _exporter.shutdown()
    _exporter = JsonlSpanExporter(jsonl_path)
    _provider = TracerProvider(resource=Resource.create({"service.name": "agent-env-benchmark-gateway"}))
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    _provider.add_span_processor(SimpleSpanProcessor(_exporter))
    _tracer = _provider.get_tracer("agent-env-benchmark")


def _get_tracer():
    global _tracer
    if _tracer is None:
        configure(Path("docs/otel_spans.jsonl"))
    return _tracer


@contextmanager
def tool_call_span(tool: str, environment: str, request_payload: dict) -> Iterator[dict]:
    """Usage in the gateway:

        with tool_call_span(tool, environment, body.args) as record:
            ... make the real HTTP call to the environment ...
            record["response"] = payload
            record["ok"] = bool(payload.get("ok"))

    On exit, the span is closed with gen_ai.tool.name, agentbench.environment,
    agentbench.latency_ms (real), agentbench.request_tokens,
    agentbench.response_tokens and agentbench.cost_usd (estimated; see the
    module docstring) attached.
    """
    tracer = _get_tracer()
    record: dict = {"response": None, "ok": False}
    start = time.perf_counter()
    with tracer.start_as_current_span("gen_ai.tool_call") as span:
        try:
            yield record
        finally:
            latency_ms = (time.perf_counter() - start) * 1000.0
            request_tokens = estimate_tokens(request_payload)
            response_tokens = estimate_tokens(record["response"])
            cost_usd = (request_tokens + response_tokens) / 1000.0 * COST_PER_1K_TOKENS
            span.set_attribute("gen_ai.tool.name", tool)
            span.set_attribute("agentbench.environment", environment)
            span.set_attribute("agentbench.latency_ms", round(latency_ms, 3))
            span.set_attribute("agentbench.request_tokens", request_tokens)
            span.set_attribute("agentbench.response_tokens", response_tokens)
            span.set_attribute("agentbench.cost_usd", round(cost_usd, 8))
            span.set_attribute("agentbench.ok", bool(record["ok"]))
