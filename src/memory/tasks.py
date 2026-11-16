"""Builds the fact pool (target users plus distractor users) and the task
corpus that scores the four memory qualities separately: recall@10,
freshness after a contradicting update, per-user isolation under the
distractor pool, and abstention.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.memory.facts import QUERY_TEMPLATE_BY_SLOT, SLOTS, random_fact_text
from src.memory.store import insert_fact

N_TARGET_USERS = 60
N_DISTRACTOR_USERS = 1000
FACTS_PER_DISTRACTOR = 3
NOISE_FACTS_PER_TARGET = 5
SAME_SLOT_DECOYS_FOR_RECALL = 20  # stress-tests the "@10" cutoff for real
SAME_SLOT_BURST_FOR_FRESHNESS = 6  # old value, then a burst with "new" at a random slot in it


@dataclass
class Task:
    kind: str  # "recall" | "freshness" | "isolation" | "abstention"
    user_id: str
    query_text: str
    target_slot: str
    expected_value: str | None  # None means the correct behavior is to abstain
    expected_fact_id: int | None


def seed_distractors(cur, rng: random.Random) -> None:
    for i in range(N_DISTRACTOR_USERS):
        user_id = f"distractor_{i:04d}"
        for _ in range(FACTS_PER_DISTRACTOR):
            slot, value, text = random_fact_text(rng)
            insert_fact(cur, user_id, session_id=0, slot=slot, value=value, text=text)


def build_target_user_tasks(cur, rng: random.Random, user_id: str) -> list[Task]:
    """The abstention slot is reserved first and excluded from every other
    fact this user gets (including noise), so "no fact exists for this
    slot" is actually true rather than accidentally contradicted by a
    randomly generated noise fact landing on the same slot."""
    tasks: list[Task] = []
    session = 0

    abstain_slot = rng.choice(SLOTS)
    usable_slots = [s for s in SLOTS if s != abstain_slot]

    for _ in range(NOISE_FACTS_PER_TARGET):
        slot, value, text = random_fact_text(rng, rng.choice(usable_slots))
        insert_fact(cur, user_id, session, slot, value, text)
        session += 1

    # recall_slot gets a burst of same-slot decoys (stale, superseded-looking
    # statements) with the one true current fact inserted at a random point
    # in the burst, so whether it survives into the top 10 by recency among
    # same-score ties is a real, sometimes-failing test, not a trivial one
    recall_slot = rng.choice(usable_slots)
    real_position = rng.randint(0, SAME_SLOT_DECOYS_FOR_RECALL)
    recall_id = None
    recall_value = None
    for i in range(SAME_SLOT_DECOYS_FOR_RECALL + 1):
        if i == real_position:
            _, recall_value, recall_text = random_fact_text(rng, recall_slot)
            recall_id = insert_fact(cur, user_id, session, recall_slot, recall_value, recall_text)
        else:
            _, decoy_value, decoy_text = random_fact_text(rng, recall_slot)
            insert_fact(cur, user_id, session, recall_slot, decoy_value, decoy_text)
        session += 1
    tasks.append(Task("recall", user_id, QUERY_TEMPLATE_BY_SLOT[recall_slot], recall_slot, recall_value, recall_id))
    tasks.append(Task("isolation", user_id, QUERY_TEMPLATE_BY_SLOT[recall_slot], recall_slot, recall_value, recall_id))

    # fresh_slot: a definitely-oldest "old" value, then a burst where the
    # contradicting "new" value lands at a random point, not necessarily
    # last; anything genuinely later than "new" in the same slot is exactly
    # the scenario where a recency-only retrieval can still surface stale or
    # unrelated chatter about that slot instead of the real update
    fresh_slot = rng.choice([s for s in usable_slots if s != recall_slot])
    _, old_value, old_text = random_fact_text(rng, fresh_slot)
    insert_fact(cur, user_id, session, fresh_slot, old_value, old_text)
    session += 1
    new_position = rng.randint(0, SAME_SLOT_BURST_FOR_FRESHNESS)
    new_id = None
    new_value = None
    for i in range(SAME_SLOT_BURST_FOR_FRESHNESS + 1):
        if i == new_position:
            new_value = old_value
            while new_value == old_value:
                _, new_value, new_text = random_fact_text(rng, fresh_slot)
            new_id = insert_fact(cur, user_id, session, fresh_slot, new_value, new_text)
        else:
            _, burst_value, burst_text = random_fact_text(rng, fresh_slot)
            insert_fact(cur, user_id, session, fresh_slot, burst_value, burst_text)
        session += 1
    tasks.append(Task("freshness", user_id, QUERY_TEMPLATE_BY_SLOT[fresh_slot], fresh_slot, new_value, new_id))

    tasks.append(Task("abstention", user_id, QUERY_TEMPLATE_BY_SLOT[abstain_slot], abstain_slot, None, None))

    return tasks


def build_corpus(cur, seed: int) -> list[Task]:
    rng = random.Random(seed)
    seed_distractors(cur, rng)
    tasks: list[Task] = []
    for i in range(N_TARGET_USERS):
        tasks += build_target_user_tasks(cur, rng, f"target_{i:03d}")
    return tasks
