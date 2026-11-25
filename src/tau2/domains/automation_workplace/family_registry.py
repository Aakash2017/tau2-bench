"""Runtime dispatch for locally authored interactive workplace families."""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from typing import Any

from tau2.domains.automation_workplace import standalone_apps
from tau2.domains.automation_workplace.automationbench_source import (
    world_state_from_dict,
)
from tau2.domains.automation_workplace.data_model import AutomationWorkplaceDB
from tau2.domains.automation_workplace.interactive_runtime import (
    DISCOVERABLE_TOOL_SCHEMAS as INCIDENT_TOOL_SCHEMAS,
)
from tau2.domains.automation_workplace.interactive_runtime import (
    call_tool as call_incident_tool,
)
from tau2.domains.automation_workplace.interactive_runtime import (
    check_assertion as check_incident_assertion,
)
from tau2.domains.automation_workplace.interactive_runtime import (
    tool_schema as incident_tool_schema,
)

FAMILY_MODULES = {
    "vendor_invoice": "tau2.domains.automation_workplace.families.vendor_invoice",
    "customer_escalation": (
        "tau2.domains.automation_workplace.families.customer_escalation"
    ),
    "access_provisioning": (
        "tau2.domains.automation_workplace.families.access_provisioning"
    ),
    "renewal_portfolio": (
        "tau2.domains.automation_workplace.families.renewal_portfolio"
    ),
    "meeting_coordination": (
        "tau2.domains.automation_workplace.families.meeting_coordination"
    ),
    "ap_payment_run": "tau2.domains.automation_workplace.families.ap_payment_run",
    "escalation_conflicts": (
        "tau2.domains.automation_workplace.families.escalation_conflicts"
    ),
    "renewal_handoff": ("tau2.domains.automation_workplace.families.renewal_handoff"),
}


def _module(family_id: str) -> Any:
    module_path = FAMILY_MODULES.get(family_id)
    if module_path is None:
        raise ValueError(f"Unknown interactive workplace family: {family_id}")
    return import_module(module_path)


def tool_schemas(family_id: str) -> dict[str, dict[str, Any]]:
    """Return the active family's discoverable-operation registry."""
    if family_id == "incident_triage":
        return INCIDENT_TOOL_SCHEMAS
    module = _module(family_id)
    return module.TOOL_SCHEMAS


def tool_schema(family_id: str, tool_name: str) -> dict[str, Any]:
    """Return one discoverable operation's public schema."""
    if family_id == "incident_triage":
        return incident_tool_schema(tool_name)
    schemas = tool_schemas(family_id)
    if tool_name not in schemas:
        raise ValueError(f"Unknown {family_id} tool: {tool_name}")
    return {"name": tool_name, **schemas[tool_name]}


def call_tool(db: AutomationWorkplaceDB, tool_name: str, arguments: str) -> str:
    """Execute one operation and persist the validated family state."""
    family_id = db.interactive_family
    if family_id == "incident_triage":
        return call_incident_tool(db.interactive_world, tool_name, arguments)
    module = _module(family_id)
    updated_world, response = module.call_tool(
        db.family_world,
        tool_name,
        arguments,
    )
    db.family_world = updated_world
    return response


def _generic_state(world: dict[str, Any]) -> dict[str, Any]:
    """Normalize a generic-app world for comparison, ignoring clock metadata.

    Any api_fetch, even a read, rewrites the stored world in normalized form, so a
    raw comparison would count reads of an unseeded world as side effects.
    """
    if standalone_apps.is_standalone(world):
        return standalone_apps.generic_state(world)
    normalized = world_state_from_dict(deepcopy(world)).model_dump(mode="json")
    normalized.pop("meta", None)
    return normalized


def _sent_emails_match(db: AutomationWorkplaceDB, assertion: dict[str, Any]) -> bool:
    """Exactly the expected new emails, and no other generic-app changes.

    Each expected email names acceptable recipients, required terms and an
    optional rubric for the content judge. Apps listed in ``tolerate_apps`` may
    change freely.
    """
    before = _generic_state(db.initial_world)
    after = _generic_state(db.world)
    initial_ids = {message["id"] for message in before["gmail"]["messages"]}
    sent = [
        message
        for message in after["gmail"]["messages"]
        if message["id"] not in initial_ids
    ]
    before["gmail"]["messages"] = after["gmail"]["messages"] = []
    # Record-keeping edits (e.g. marking review rows applied) are not graded.
    for app in assertion.get("tolerate_apps", []):
        before.pop(app, None)
        after.pop(app, None)
    if before != after or len(sent) != len(assertion["emails"]):
        return False
    judge = _module("access_provisioning")
    remaining = list(sent)
    for expected in assertion["emails"]:
        match = next(
            (
                message
                for message in remaining
                if set(expected["recipients_any"])
                & {address.lower() for address in message["to"] + message["cc"]}
                and judge._contains_all(
                    f"{message['subject']}\n{message['body_plain']}",
                    expected.get("all_of", []),
                )
                and (
                    not expected.get("rubric")
                    or judge._content_meets(
                        f"Subject: {message['subject']}\n\n{message['body_plain']}",
                        expected["rubric"],
                    )
                )
            ),
            None,
        )
        if match is None:
            return False
        remaining.remove(match)
    return True


def check_assertion(db: AutomationWorkplaceDB, assertion: dict[str, Any]) -> bool:
    """Evaluate one final-state assertion with the active family checker."""
    if assertion.get("type") == "access_no_unrelated_api_side_effects":
        return _generic_state(db.world) == _generic_state(db.initial_world)
    if assertion.get("type") == "access_sent_emails_exact":
        return _sent_emails_match(db, assertion)
    family_id = db.interactive_family
    if family_id == "incident_triage":
        return check_incident_assertion(db.interactive_world, assertion)
    return _module(family_id).check_assertion(db.family_world, assertion)
