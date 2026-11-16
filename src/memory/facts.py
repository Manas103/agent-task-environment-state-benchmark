"""Synthetic fact generation for the memory extension. 5 typed slots, the
same kind of disclosed template-based generator the rest of this repo's
task corpora use (the 420-task CRM/ticketing/inventory generator, the
300-task silicon corpus): the generator is also the ground truth a later
oracle check is graded against, not a real chat log.
"""

from __future__ import annotations

import random

SLOTS = ["home_city", "job_title", "favorite_color", "pet_name", "allergy"]

VALUE_POOLS = {
    "home_city": ["Seattle", "Austin", "Denver", "Boston", "Raleigh", "Portland"],
    "job_title": ["data analyst", "product manager", "backend engineer", "designer"],
    "favorite_color": ["teal", "crimson", "navy", "amber", "forest green"],
    "pet_name": ["Mochi", "Biscuit", "Juniper", "Pixel", "Rocco"],
    "allergy": ["peanuts", "shellfish", "penicillin", "pollen"],
}

TEMPLATE_BY_SLOT = {
    "home_city": "I live in {value} these days.",
    "job_title": "I work as a {value}.",
    "favorite_color": "My favorite color is {value}.",
    "pet_name": "My pet's name is {value}.",
    "allergy": "I'm allergic to {value}.",
}

QUERY_TEMPLATE_BY_SLOT = {
    "home_city": "What city do I live in?",
    "job_title": "What do I do for work?",
    "favorite_color": "What's my favorite color?",
    "pet_name": "What's my pet's name?",
    "allergy": "What am I allergic to?",
}


def random_fact_text(rng: random.Random, slot: str | None = None) -> tuple[str, str, str]:
    slot = slot or rng.choice(SLOTS)
    value = rng.choice(VALUE_POOLS[slot])
    return slot, value, TEMPLATE_BY_SLOT[slot].format(value=value)
