"""A transcript-only judge for the 300 silicon-design tasks: the same overcrediting mechanism
as this repo's `judge/deterministic_judge.py`, applied to a transcript string instead of a
tool-call-success flag. It reads only `task.transcript` (a confident-sounding description of
what the candidate submitted, never the real oracle result) and passes whenever the transcript
contains no explicit admission of failure, which none of this benchmark's transcripts do
(every one is phrased as a confident claim, by construction, the same way a real submission
message almost never says "this is wrong"). Structurally, it cannot see the real oracle result
in oracles.py, so it cannot do better than this on the ~1/3 of tasks that are deliberately wrong.
"""

from __future__ import annotations

from .tasks import Task

_FAILURE_MARKERS = ("failed", "error", "incorrect", "does not work", "broken")


def judge_passes(task: Task) -> bool:
    text = task.transcript.lower()
    return not any(marker in text for marker in _FAILURE_MARKERS)
