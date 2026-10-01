"""OracleStateInterpreter: diffs ActualStateReader's real-database read against
ReferenceSimulator's independently-computed expected state, field by field. This
is the only grading path in the project that reads real final state rather than
a transcript.
"""

from dataclasses import dataclass, field

from src.oracle import actual_state_reader, reference_simulator


@dataclass
class OracleVerdict:
    task_id: str
    passed: bool
    mismatches: list = field(default_factory=list)  # list[str], empty if passed


def grade(task) -> OracleVerdict:
    expected = reference_simulator.simulate(task.reference_plan)
    actual = actual_state_reader.read_actual_state(expected)

    mismatches = []
    for table in ("accounts", "contacts", "opportunities", "tickets", "products"):
        for entity_id, expected_fields in expected[table].items():
            actual_fields = actual[table].get(entity_id)
            if actual_fields is None:
                mismatches.append(f"{table}/{entity_id}: missing from database")
                continue
            for field_name, expected_value in expected_fields.items():
                actual_value = actual_fields.get(field_name)
                if actual_value != expected_value:
                    mismatches.append(
                        f"{table}/{entity_id}.{field_name}: expected {expected_value!r}, actual {actual_value!r}"
                    )
    for (prd_id, wh), expected_qty in expected["stock"].items():
        actual_qty = actual["stock"].get((prd_id, wh), 0)
        if actual_qty != expected_qty:
            mismatches.append(f"stock/{prd_id}@{wh}: expected {expected_qty}, actual {actual_qty}")

    return OracleVerdict(task_id=task.id, passed=(len(mismatches) == 0), mismatches=mismatches)
