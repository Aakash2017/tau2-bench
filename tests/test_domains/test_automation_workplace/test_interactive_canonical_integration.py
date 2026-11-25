import json
from pathlib import Path

import pytest

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import (
    access_provisioning,
    ap_payment_run,
    customer_escalation,
    escalation_conflicts,
    meeting_coordination,
    renewal_handoff,
    renewal_portfolio,
    vendor_invoice,
)

FAMILY_MODULES = {
    "vendor_invoice": vendor_invoice,
    "customer_escalation": customer_escalation,
    "access_provisioning": access_provisioning,
    "renewal_portfolio": renewal_portfolio,
    "meeting_coordination": meeting_coordination,
    "ap_payment_run": ap_payment_run,
    "renewal_handoff": renewal_handoff,
    "escalation_conflicts": escalation_conflicts,
}
# Families whose golden writes live in the task file.
SPEC_GOLDEN_FAMILIES = {"ap_payment_run", "renewal_handoff", "escalation_conflicts"}
TASKS_DIR = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive/tasks"
)


def _initialized_environment(task):
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return environment


@pytest.mark.parametrize(
    "task",
    [
        task
        for task in get_tasks("interactive_canonical")
        if task.initial_state.initialization_data.agent_data["interactive_family"]
        != "incident_triage"
    ],
    ids=lambda task: task.id.rsplit("__", 1)[-1],
)
def test_family_golden_sequences_pass_through_shared_environment(task):
    environment = _initialized_environment(task)
    family_id = environment.tools.db.interactive_family
    module = FAMILY_MODULES[family_id]

    task_key = environment.tools.db.family_world["task_id"]
    if family_id in SPEC_GOLDEN_FAMILIES:
        spec = json.loads((TASKS_DIR / f"{task_key}.json").read_text())
        sequence = module.golden_call_sequence(spec)
    elif family_id == "access_provisioning":
        sequence = module.golden_call_sequence(task_key)
    else:
        sequence = module.golden_call_sequence()
    for tool_name, arguments in sequence:
        if tool_name == "api_fetch":
            environment.use_tool("api_fetch", **arguments)
            continue
        environment.use_tool(
            "unlock_discoverable_tool",
            discoverable_tool_name=tool_name,
        )
        response = environment.use_tool(
            "call_discoverable_tool",
            discoverable_tool_name=tool_name,
            arguments=json.dumps(arguments),
        )
        assert isinstance(json.loads(response), dict)

    checks = [
        environment.run_env_assertion(assertion, raise_assertion_error=False)
        for assertion in task.evaluation_criteria.env_assertions
    ]

    assert checks == [True] * len(checks)


def test_active_family_rejects_another_familys_operation():
    task = next(
        task
        for task in get_tasks("interactive_canonical")
        if task.id.endswith("vendor_invoice_001")
    )
    environment = _initialized_environment(task)

    with pytest.raises(ValueError, match="Unknown discoverable tool"):
        environment.use_tool(
            "unlock_discoverable_tool",
            discoverable_tool_name="customer_gmail_send_message_v1",
        )


@pytest.mark.parametrize(
    "task",
    [
        task
        for task in get_tasks("interactive_canonical")
        if task.initial_state.initialization_data.agent_data["interactive_family"]
        != "incident_triage"
    ],
    ids=lambda task: task.id.rsplit("__", 1)[-1],
)
def test_every_family_operation_is_discoverable_in_selected_knowledge(task):
    agent_data = task.initial_state.initialization_data.agent_data
    family_id = agent_data["interactive_family"]
    documents = agent_data["knowledge_documents"].values()
    corpus = "\n".join(document["content"] for document in documents)

    statuses = {document["status"] for document in documents}
    assert "current" in statuses
    assert statuses <= {"current", "superseded"}
    assert all(
        tool_name in corpus for tool_name in FAMILY_MODULES[family_id].TOOL_SCHEMAS
    )
