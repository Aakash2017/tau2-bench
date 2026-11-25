"""Exact-state tests for the canonical meeting-coordination family."""

import json
from copy import deepcopy

from tau2.domains.automation_workplace.families import meeting_coordination
from tau2.domains.automation_workplace.utils import (
    AUTOMATION_WORKPLACE_INTERACTIVE_TASKS_DIR,
)
from tau2.utils import load_file

TASK_PATH = AUTOMATION_WORKPLACE_INTERACTIVE_TASKS_DIR / "meeting_coordination_001.json"


def _replay(world: dict, calls: list[tuple[str, dict]]) -> tuple[dict, list[dict]]:
    responses = []
    for tool_name, arguments in calls:
        world, response = meeting_coordination.call_tool(
            world,
            tool_name,
            json.dumps(arguments),
        )
        responses.append(json.loads(response))
    return world, responses


def test_meeting_golden_sequence_passes_every_exact_state_assertion():
    spec = load_file(TASK_PATH)
    world, responses = _replay(
        deepcopy(spec["family_world"]),
        meeting_coordination.golden_call_sequence(),
    )

    assert responses[0]["id"] == "gcal_event_002"
    assert responses[1] == {
        "errors": [],
        "id": "opp_meridian_rollout",
        "success": True,
    }
    assert responses[2]["message"]["message_id"] == "slack_message_002"
    assert [
        meeting_coordination.check_assertion(world, assertion)
        for assertion in spec["assertions"]
    ] == [True] * 6


def test_meeting_negative_sequence_fails_only_changed_business_state():
    spec = load_file(TASK_PATH)
    world, _ = _replay(
        deepcopy(spec["family_world"]),
        meeting_coordination.negative_call_sequence(),
    )

    results = {
        assertion["type"]: meeting_coordination.check_assertion(world, assertion)
        for assertion in spec["assertions"]
    }

    assert results == {
        "meeting_calendar_event_exact": False,
        "meeting_pilot_contact_excluded": False,
        "meeting_salesforce_followthrough": False,
        "meeting_slack_followthrough": False,
        "meeting_no_stale_brief_side_effect": False,
        "meeting_unrelated_records_preserved": True,
    }
