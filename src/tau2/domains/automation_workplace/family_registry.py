"""Runtime dispatch for locally authored interactive workplace families."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from tau2.domains.automation_workplace.data_model import AutomationWorkplaceDB

FAMILY_MODULES = {
    "access_provisioning": (
        "tau2.domains.automation_workplace.families.access_provisioning"
    ),
}


def _module(family_id: str) -> Any:
    module_path = FAMILY_MODULES.get(family_id)
    if module_path is None:
        raise ValueError(f"Unknown interactive workplace family: {family_id}")
    return import_module(module_path)


def tool_schemas(family_id: str) -> dict[str, dict[str, Any]]:
    """Return the active family's discoverable-operation registry."""
    module = _module(family_id)
    return module.TOOL_SCHEMAS


def tool_schema(family_id: str, tool_name: str) -> dict[str, Any]:
    """Return one discoverable operation's public schema."""
    schemas = tool_schemas(family_id)
    if tool_name not in schemas:
        raise ValueError(f"Unknown {family_id} tool: {tool_name}")
    return {"name": tool_name, **schemas[tool_name]}


def call_tool(db: AutomationWorkplaceDB, tool_name: str, arguments: str) -> str:
    """Execute one operation and persist the validated family state."""
    family_id = db.interactive_family
    module = _module(family_id)
    updated_world, response = module.call_tool(
        db.family_world,
        tool_name,
        arguments,
    )
    db.family_world = updated_world
    return response


def check_assertion(db: AutomationWorkplaceDB, assertion: dict[str, Any]) -> bool:
    """Evaluate one final-state assertion with the active family checker."""
    if assertion.get("type") == "access_no_unrelated_api_side_effects":
        return db.world == {}
    family_id = db.interactive_family
    return _module(family_id).check_assertion(db.family_world, assertion)
