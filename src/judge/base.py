"""The judge interface: transcript in, verdict out. Every judge in this project
receives only a Transcript (instruction text plus tool/args/ok/message per step);
none of them is ever handed the oracle's expected state or a database handle, so a
measured divergence between a judge and the oracle means something.
"""

from dataclasses import dataclass


@dataclass
class JudgeVerdict:
    task_id: str
    passed: bool
    reason: str


class Judge:
    def verdict(self, transcript) -> JudgeVerdict:
        raise NotImplementedError
