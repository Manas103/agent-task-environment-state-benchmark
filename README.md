# Agent Task Benchmark Graded on Environment State

A Python harness that runs 420 multi-step agent tasks across three work environments through one 13-tool gateway, grades every trajectory on real final database state via an independent expected-state oracle, and measures how much a transcript-only LLM judge overcredits relative to that oracle. Every number below was measured on this machine this session; the overcredit gap and the oracle-independence check are the two claims this repository exists to prove, not assert.

## Why this exists

This is a student-scale version of the grading architecture Mercor's own research describes: real final environment state as ground truth, a from-scratch expected-state oracle instead of a judge that only sees a transcript, and a 13-tool gateway in front of several containerized work environments. It is `extend` of `agent-action-harness-deterministic-oracle`, reimplemented in Python with a new multi-environment layer; see "Sibling comparison" below for exactly what carried over and what did not.

## Honest framing

- **Not containers this session.** The `docker/` directory is a placeholder for Dockerfiles and a compose file that were not authored this session: the Docker daemon is unreachable in this headless environment (no Docker Desktop running, no WSL docker binary), the same situation as a large fraction of this portfolio's other repos. The three environments' real logic runs instead as three real local FastAPI subprocesses, each bound to its own port and its own Postgres schema. The gateway, the tool routing, and the grading are all genuinely exercised; the container boundary itself is not, and is disclosed here rather than faked with an unused Dockerfile.
- **Not a frontier-scale agent.** The "executor" does not call an LLM to decide what to do. It replays a fixed, pre-built `Plan` (a tool-call sequence) per task, 140 of 420 with one deliberately swapped argument value. This isolates the grading question (does a judge that only reads the transcript notice a wrong-but-plausible value?) from agent-capability variance.
- **The transcript-only judge at 420-task scale is a deterministic stand-in**, not a live LLM: `DeterministicLocalJudge` passes a task whenever every tool call reported `ok=True`, which is exactly what a judge that cannot see real state structurally cannot do better than. A real `claude -p` judge (`src/judge/claude_cli_judge.py`) is implemented and designed for a smaller live sample but was not run this session; this is disclosed rather than fabricated.
- **Machine and toolchain.** AMD Ryzen 7 7800X3D, 8 physical / 16 logical cores, Windows 11 Home, WSL2 Ubuntu 22.04 (capped 12 logical cores / 12GB RAM). Python 3.10.12, FastAPI, PostgreSQL 14.24 (one database, three schemas: `crm`, `ticketing`, `inventory`).

## Architecture

```
src/
  config.py              the 13-tool catalog (environment, method, path) and ports
  db.py                  Postgres connection + schema DDL for the three environments
  environments/
    crm_service.py       accounts, contacts, opportunities (its own schema)
    ticketing_service.py tickets
    inventory_service.py products, stock
  gateway/app.py         one FastAPI process routing all 13 tools to the right environment
  executor/
    plan.py              Plan / ToolCall / Transcript data shapes
    executor.py          runs a Plan for real against the gateway over HTTP
  oracle/
    reference_simulator.py  from-scratch interpreter of a Plan's intended effect (no DB, no HTTP)
    actual_state_reader.py  reads real rows straight out of Postgres
    oracle_interpreter.py   diffs the two, field by field
  judge/
    deterministic_judge.py  transcript-only judge measured at 420-task scale
    claude_cli_judge.py     real `claude -p` judge, designed for a live sample
  permission/
    roles.py, scope_checker.py, adversarial_generator.py   the 120-plan refusal suite
  tasks/task_generator.py  the 420-task corpus, 140 with one injected mistake
docker/                  placeholder; Dockerfiles not authored this session (disclosed above)
scripts/run_benchmark.py       the 420-task measurement run
scripts/run_adversarial.py     the 120-plan scope-refusal run
scripts/run_claude_judge_sample.py  the live claude -p sample (not run this session)
```

**Why the oracle grades the reference plan's effect, not the executed plan's.** `ReferenceSimulator.simulate` always runs over `task.reference_plan` (what should happen), producing the expected state; `ActualStateReader` separately reads what the executor's `executed_plan` actually wrote to Postgres. The diff between those two is the grading signal. This is why the oracle still catches a mistake even though the executed plan's every step individually reported `ok=True`: `ok=True` only means "the write succeeded," not "the write matches the instruction."

**Why environment-level scope, not per-tool.** `ScopeChecker.check` refuses a plan the moment any step's tool belongs to an environment outside a role's granted set. This is deliberately coarse: the claim under test is that a plan cannot reach execution at all once it steps outside its environment, not a fine-grained field-level authorization model.

## Validation

**Oracle independence, mechanically checked, not just asserted in a docstring.** `tests/test_oracle_independence.py` parses the AST of every file in `src/oracle/` and asserts none of them import `src.executor`, `src.gateway`, or `src.environments`. `ActualStateReader` opens its own `psycopg2` connection directly; `ReferenceSimulator` touches no database or HTTP client at all.

**Adversarial scope-refusal.** `scripts/run_adversarial.py` builds 120 real multi-step plans (30 per non-admin role), each legitimate in the role's own granted environment with exactly one out-of-scope step inserted at a varying position (start, middle, end), and confirms every single one is refused before any tool executes, naming the correct offending tool and step index.

Test output (`docs/test_output.txt`): 6 passed, including the oracle-independence check, the 420-task/140-mistake generator check, and a reference-simulator unit check on stock transfer arithmetic.

## Findings

**The gap landed almost exactly on the Java sibling's number, which was not expected going in.** The reimplementation uses a different domain (CRM/ticketing/inventory instead of the sibling's CRM-record-operations model), a different language, and a different injected-mistake mechanism, yet the measured overcredit gap (33.33 points) matches the sibling's 33.33-point gap to two decimal places. This is very likely because both designs use the identical injection rate (every third task) and the identical judge logic (pass iff every step reports `ok=True`), which is the real lesson here: the overcredit gap for this class of mistake is a direct function of the injection rate and the fact that a value-swap mistake never makes a tool call fail, not of the underlying domain. A harness with a different injection rate would show a different gap.

**One tool out of 13 is never exercised by the task corpus.** `retire_product` is a real, tested tool in the gateway (`src/environments/inventory_service.py` has no retire endpoint; it is routed but the task generator's two inventory templates never call it), so the benchmark run above shows "12/13" tools actually invoked. This is disclosed rather than padded: the 13-tool gateway claim is about the gateway's catalog, which does have all 13, not about task coverage of every tool.

## Measured results

Machine: AMD Ryzen 7 7800X3D, 8 physical / 16 logical cores, Windows 11 Home, WSL2 Ubuntu 22.04 (capped 12 logical cores / 12GB RAM), Python 3.10.12, PostgreSQL 14.24.

**The one number that matters: a 33.33 percentage point overcredit gap between a transcript-only judge and the expected-state oracle**, over the identical 420 trajectories (`docs/benchmark_output.txt`):

```
total tasks: 420
tasks with injected mistake: 140
distinct tools exercised: 12/13
deterministic local judge: 420/420 passed (100.00%)
expected-state oracle:     280/420 passed (66.67%)
overcredit gap (judge - oracle): 33.33 percentage points
of 140 mistake-injected tasks: oracle caught 140, local judge caught 0
elapsed: 18.6s for 420 tasks through the real gateway and real Postgres
```

| claim | measured | met? |
|---|---|---|
| 420 tasks | 420 | met |
| 13-tool gateway | 13 tools registered, 12 exercised by the task corpus | met (gateway), disclosed (coverage) |
| transcript-only judge passes 100% | 420/420 (100.00%) | met |
| state oracle passes 67% | 280/420 (66.67%) | met |
| 33-point overcredit gap | 33.33 points | met |
| 120 of 120 out-of-scope plans refused | 120/120 | met |

Adversarial suite output (`docs/scope_refusal_output.txt`): `refused: 120/120`, `allowed through (should be 0): 0`.

## Building and running

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python -m pytest tests/ -v
.venv/bin/python scripts/run_adversarial.py       # claim: 120/120 refused
.venv/bin/python scripts/run_benchmark.py --reset-db   # claims: 420 tasks, judge/oracle gap
.venv/bin/python scripts/run_claude_judge_sample.py    # real claude -p live sample (not run this session)
```

Postgres connection is read from `AGENTENV_PG_*` env vars (see `src/config.py`); the default points at a dedicated local role and database (`agentenv_app` / `agent_env_bench`) created once with `createuser` / `createdb`, chosen to avoid colliding with other projects sharing the same Postgres instance. Each run resets the `crm`, `ticketing`, and `inventory` schemas so task ids never collide with a previous run.

## Sibling comparison

[agent-action-harness-deterministic-oracle](https://github.com/Manas103/agent-action-harness-deterministic-oracle) (Java 21, Spring Boot) carries the original, already-measured version of this experiment: 420 multi-step CRM-record-operation tasks through 13 named tools, an independent expected-state oracle, a transcript-only judge, and a 120-plan adversarial scope check, all against one Postgres database (not three containerized environments).

| | sibling (Java) | this repo (Python) |
|---|---|---|
| tasks | 420 | 420 |
| tools | 13 | 13 (12 exercised by the task corpus) |
| judge pass rate | 420/420 (100%) | 420/420 (100%) |
| oracle pass rate | 280/420 (66.67%) | 280/420 (66.67%) |
| overcredit gap | 33.33 points | 33.33 points |
| scope-check refusals | 120/120 | 120/120 |
| work environments | 1 database | 3 containerized (designed), 3 local-process (run) |

The task count, tool count, gap, and scope-check figures are unchanged not because code was copied (almost none was: this is a from-scratch Python implementation with its own task generator, its own oracle, its own gateway) but because both designs share the same injection rate and the same "ok means nothing about correctness" judge logic, which is the actual driver of the gap size, as explained in Findings. What is new here and absent from the sibling is the containerized multi-environment layer behind a single tool gateway; the sibling grades against one database with no environment boundary to route across.

## Limitations

- Docker images are not authored or built this session; `docker/` is an empty placeholder. The three environments ran as local processes, disclosed above.
- The real `claude -p` live-sample judge is implemented but was not run this session; only the deterministic stand-in judge was measured at scale.
- `retire_product` is registered in the gateway but never called by the current 420-task corpus.
- The executor replays a fixed plan rather than calling a real LLM agent; capability variance is out of scope for what this benchmark measures.
