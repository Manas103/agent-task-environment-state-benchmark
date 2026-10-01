"""Permission roles: each is granted a subset of the three work environments.
Deliberately coarse (environment-level, not per-tool or per-field), because the
claim under test is that a plan touching an ungranted environment is refused
before execution at all, not a fine-grained authorization model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionRole:
    name: str
    granted_environments: frozenset


ADMIN = PermissionRole("ADMIN", frozenset({"crm", "ticketing", "inventory"}))
CRM_ONLY = PermissionRole("CRM_ONLY", frozenset({"crm"}))
TICKETING_ONLY = PermissionRole("TICKETING_ONLY", frozenset({"ticketing"}))
INVENTORY_ONLY = PermissionRole("INVENTORY_ONLY", frozenset({"inventory"}))
CRM_AND_TICKETING = PermissionRole("CRM_AND_TICKETING", frozenset({"crm", "ticketing"}))

NON_ADMIN_ROLES = [CRM_ONLY, TICKETING_ONLY, INVENTORY_ONLY, CRM_AND_TICKETING]
ALL_ROLES = [ADMIN] + NON_ADMIN_ROLES
