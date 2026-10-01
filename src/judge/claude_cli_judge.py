"""ClaudeCliJudgeClient: a real `claude -p` subprocess judge. It receives the same
Transcript-only input as DeterministicLocalJudge (instruction text plus
tool/args/ok/message per step) and asks a live Claude model whether the task was
completed as instructed. The prompt is piped over the child process's stdin
rather than passed as a command-line argument, to avoid Windows argument
re-quoting corrupting multi-line prompts containing quotes and colons (see
README findings for the real breakage this avoided during development of this
repository, and agent-action-harness-deterministic-oracle's own README for the
same bug in a different language).

Exercised on a 20-task live sample only (see docs/claude_judge_sample.txt); the
420-task scale measurement uses DeterministicLocalJudge instead.
"""

import re
import subprocess

from src.judge.base import Judge, JudgeVerdict

PROMPT_TEMPLATE = """You are grading whether an AI agent completed a task correctly.

Task instruction (what the agent was asked to do):
{instruction}

Transcript of the tool calls the agent actually made (tool name, arguments, and \
whether the environment reported success):
{steps}

Judge ONLY from this transcript. You cannot query any database or see real \
system state, only what is written above. Decide whether the transcript shows \
the instruction was followed correctly, including whether every argument value \
matches what the instruction asked for (not just whether each call reported ok).

Reply with exactly one line in the form:
VERDICT: PASS
or
VERDICT: FAIL
followed by one short sentence of reasoning.
"""


def _format_steps(transcript) -> str:
    lines = []
    for i, step in enumerate(transcript.steps, 1):
        lines.append(f"  {i}. tool={step.tool} args={step.args} ok={step.ok} message={step.message!r}")
    return "\n".join(lines)


class ClaudeCliJudgeClient(Judge):
    def __init__(self, claude_bin: str = "claude", timeout_s: int = 60):
        self.claude_bin = claude_bin
        self.timeout_s = timeout_s

    def verdict(self, transcript) -> JudgeVerdict:
        prompt = PROMPT_TEMPLATE.format(instruction=transcript.instruction, steps=_format_steps(transcript))
        try:
            proc = subprocess.run(
                [self.claude_bin, "-p"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            return JudgeVerdict(task_id=transcript.task_id, passed=False, reason=f"claude CLI call failed: {exc}")

        raw = (proc.stdout or "").strip()
        match = re.search(r"VERDICT:\s*(PASS|FAIL)", raw, re.IGNORECASE)
        if not match:
            return JudgeVerdict(
                task_id=transcript.task_id,
                passed=False,
                reason=f"unparseable claude output: {raw[:200]!r}",
            )
        passed = match.group(1).upper() == "PASS"
        return JudgeVerdict(task_id=transcript.task_id, passed=passed, reason=raw)
