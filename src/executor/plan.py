"""Plan and transcript data shapes. A Plan is a fixed, ordered list of tool calls
decided before execution starts (no live negotiation with an agent mid-plan). A
Transcript is the only thing a judge is ever allowed to see: tool name, args, ok,
message. It carries no reference to the oracle's expected state or to any database
handle, so a judge cannot structurally cheat by inspecting ground truth.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: dict


@dataclass(frozen=True)
class Plan:
    steps: tuple  # tuple[ToolCall, ...]


@dataclass(frozen=True)
class StepOutcome:
    tool: str
    args: dict
    ok: bool
    message: str


@dataclass
class Transcript:
    task_id: str
    instruction: str
    steps: list = field(default_factory=list)  # list[StepOutcome]

    def all_ok(self) -> bool:
        return all(s.ok for s in self.steps)
