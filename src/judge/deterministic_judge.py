"""DeterministicLocalJudge: a fast, honest stand-in for what a transcript-only
judge structurally can and cannot see. It calls a task successful whenever every
step in the transcript reported ok=True, exactly the signal a plausible-looking
but semantically wrong tool call (the injected-mistake mechanism in
src.tasks.task_generator) cannot trip, by construction. This is what is measured
at the full 420-task scale; see src.judge.claude_cli_judge for the real-LLM
judge, exercised on a smaller live sample.
"""

from src.judge.base import Judge, JudgeVerdict


class DeterministicLocalJudge(Judge):
    def verdict(self, transcript) -> JudgeVerdict:
        ok = transcript.all_ok()
        reason = "all steps reported ok" if ok else "at least one step reported failure"
        return JudgeVerdict(task_id=transcript.task_id, passed=ok, reason=reason)
