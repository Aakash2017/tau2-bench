"""Replay and mutation tests for the outage escalation-conflicts task."""

import json
import re
from pathlib import Path

import pytest

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import escalation_conflicts

TASK_ID = "automation_workplace__interactive__customer_escalation_002"
INTERACTIVE = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive"
)
SPEC = json.loads((INTERACTIVE / "tasks/customer_escalation_002.json").read_text())
CREDIT = "billing_issue_service_credit_v1"


def _failed(writes) -> list[str]:
    task = next(t for t in get_tasks("interactive_canonical") if t.id == TASK_ID)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    for name, arguments in writes:
        environment.use_tool("unlock_discoverable_tool", discoverable_tool_name=name)
        environment.use_tool(
            "call_discoverable_tool",
            discoverable_tool_name=name,
            arguments=json.dumps(arguments),
        )
    return [
        a.message
        for a in task.evaluation_criteria.env_assertions
        if not environment.run_env_assertion(a, raise_assertion_error=False)
    ]


def _golden():
    return escalation_conflicts.golden_call_sequence(SPEC)


def _swap(writes, match, new):
    out = [
        new if all(a.get(k) == v for k, v in match.items()) else (n, a)
        for n, a in writes
    ]
    assert out != writes
    return [w for w in out if w is not None]


def test_golden_path_passes_every_assertion():
    assert _failed(_golden()) == []


def test_flat_ten_percent_for_everyone_fails():
    assert _failed(escalation_conflicts.negative_call_sequence(SPEC))


@pytest.mark.parametrize(
    "match,new",
    [
        (
            {"account_id": "acc_northwind"},  # stale 2h summary -> 5%
            (
                CREDIT,
                {
                    "account_id": "acc_northwind",
                    "amount": 900.0,
                    "currency": "USD",
                    "incident_id": "INC-731",
                    "reason": "5%",
                },
            ),
        ),
        (
            {"account_id": "acc_vela"},  # order form instead of amendment
            (
                CREDIT,
                {
                    "account_id": "acc_vela",
                    "amount": 900.0,
                    "currency": "USD",
                    "incident_id": "INC-731",
                    "reason": "10%",
                },
            ),
        ),
        (
            {"to": ["it-admin@northwind.example"]},  # reply to unverified requester
            (
                "gmail_send_message_v1",
                {
                    "to": ["cto@northwind-corp.example"],
                    "subject": "Credit",
                    "body": "$1,800.00 credit applied.",
                },
            ),
        ),
        (
            {"to": ["ops@quantumbakeries.example"]},  # promising an amount
            (
                "gmail_send_message_v1",
                {
                    "to": ["ops@quantumbakeries.example"],
                    "subject": "Credit",
                    "body": "You'll receive a $1,200 credit.",
                },
            ),
        ),
        ({"project": "SUPOPS"}, None),
        (
            {"ticket_id": "ZD-5124"},
            ("zendesk_update_ticket_v1", {"ticket_id": "ZD-5124", "status": "solved"}),
        ),
    ],
)
def test_single_mistakes_fail(match, new):
    assert _failed(_swap(_golden(), match, new))


def test_crediting_quantum_on_verbal_claim_fails():
    extra = (
        CREDIT,
        {
            "account_id": "acc_quantum",
            "amount": 1200.0,
            "currency": "USD",
            "incident_id": "INC-731",
            "reason": "EU",
        },
    )
    assert _failed(_golden() + [extra])


def test_kb_does_not_name_task_entities():
    kb = json.loads((INTERACTIVE / SPEC["knowledge_file"]).read_text())
    world = SPEC["family_world"]
    names = [a["name"].split()[0] for a in world["accounts"].values()]
    names += list(world["tenants"]) + list(world["tickets"])
    text = " ".join(d["content"] + d["title"] for d in kb)
    assert [n for n in names if re.search(rf"\b{re.escape(n)}\b", text)] == []
