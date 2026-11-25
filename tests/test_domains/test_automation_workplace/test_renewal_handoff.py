"""Replay and mutation tests for the renewal handoff-resume task."""

import json
import re
from pathlib import Path

import pytest

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import renewal_handoff

TASK_ID = "automation_workplace__interactive__renewal_portfolio_002"
INTERACTIVE = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive"
)
SPEC = json.loads((INTERACTIVE / "tasks/renewal_portfolio_002.json").read_text())
SEND = "gmail_send_message_v1"
CRM = "salesforce_update_renewal_v1"


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
    return renewal_handoff.golden_call_sequence(SPEC)


def _without(writes, **match):
    out = [w for w in writes if not all(w[1].get(k) == v for k, v in match.items())]
    assert len(out) == len(writes) - 1, match
    return out


def test_golden_path_passes_every_assertion():
    assert _failed(_golden()) == []


def test_trusting_the_handoff_note_fails():
    failed = _failed(renewal_handoff.negative_call_sequence(SPEC))
    assert len(failed) >= 8


@pytest.mark.parametrize(
    "extra",
    [
        # Resend to the bounced address.
        (
            SEND,
            {
                "to": ["jo.marsh@birchline.example"],
                "subject": "Renewal",
                "body": "Renewal price: $84,000.00",
            },
        ),
        # Duplicate a correct delivered notice.
        (
            SEND,
            {
                "to": ["finance@cobaltrobotics.example"],
                "subject": "Renewal",
                "body": "Renewal price: $66,950.00",
            },
        ),
        # Contact an account under an active hold.
        (
            SEND,
            {
                "to": ["legal@glenrock.example"],
                "subject": "Renewal",
                "body": "Renewal price: $160,500.00",
            },
        ),
        # Separate notice to a covered subsidiary.
        (
            SEND,
            {
                "to": ["ops@elmsteadclinics.example"],
                "subject": "Renewal",
                "body": "Renewal price: $96,300.00",
            },
        ),
        # CAD account counted at face value.
        (
            SEND,
            {
                "to": ["ap@larchoutfitters.example"],
                "subject": "Renewal",
                "body": "Renewal price: CA$64,200.00",
            },
        ),
        # Second completion post.
        ("slack_chat_post_message", {"channel": "renewals-ops", "text": "done"}),
    ],
)
def test_extra_side_effects_fail(extra):
    assert _failed(_golden() + [extra])


@pytest.mark.parametrize(
    "match",
    [
        {"to": ["procurement@dunmore.example"]},
        {"to": ["billing@harborfs.example"]},
        {"to": ["finance@ivorydental.example"]},
        {"account_id": "acc_cobalt"},
        {"account_id": "acc_elmstead"},
        {"account_id": "acc_glenrock"},
    ],
)
def test_missing_step_fails(match):
    assert _failed(_without(_golden(), **match))


def test_uncapped_dunmore_correction_fails():
    writes = [
        (n, {**a, "body": "Corrected renewal price: $214,000.00"})
        if a.get("to") == ["procurement@dunmore.example"]
        else (n, a)
        for n, a in _golden()
    ]
    assert _failed(writes)


def test_kb_does_not_name_task_entities():
    kb = json.loads((INTERACTIVE / SPEC["knowledge_file"]).read_text())
    names = [a["name"].split()[0] for a in SPEC["family_world"]["accounts"].values()]
    text = " ".join(d["content"] + d["title"] for d in kb)
    assert [n for n in names if re.search(rf"\b{n}\b", text)] == []
