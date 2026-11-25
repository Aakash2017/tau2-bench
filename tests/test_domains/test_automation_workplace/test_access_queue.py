import json
from pathlib import Path

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import access_provisioning

TASK_ID = "automation_workplace__interactive__access_provisioning_005"
TASK_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive/tasks"
    / "access_provisioning_005.json"
)


def _spec() -> dict:
    return json.loads(TASK_PATH.read_text())


def _expected_writes(spec: dict) -> list[tuple[str, dict]]:
    """Derive a golden trajectory from the task's own expected end state."""
    world = spec["family_world"]
    writes = []
    for assertion in spec["assertions"]:
        if assertion["type"] == "backlog_identity_exact":
            before = world["identities"][assertion["user_id"]]["groups"]
            for group in sorted(set(assertion["groups"]) - set(before)):
                writes.append(
                    (
                        "okta_add_user_to_group_v1",
                        {
                            "user_id": assertion["user_id"],
                            "group_id": group,
                            "expires_on": assertion["group_expirations"][group],
                        },
                    )
                )
        elif assertion["type"] == "backlog_request_exact":
            writes.append(
                (
                    "jira_update_access_request_v1",
                    {
                        "request_id": assertion["request_id"],
                        "status": assertion["status"],
                        "granted_groups": assertion["granted_groups"],
                        "blocked_reason": assertion["blocked_reason"],
                        "access_expiration": assertion["access_expiration"],
                        "description": " ".join(
                            assertion.get("description_contains", ["Closed out."])
                        ),
                    },
                )
            )
        elif assertion["type"] == "backlog_training_assignments_exact":
            writes += [
                ("lms_assign_training_v1", item) for item in assertion["assignments"]
            ]
        elif assertion["type"] == "backlog_slack_updates_exact":
            for person in assertion["announced"]:
                parts = [person["name"], "received access through"]
                parts += person.get("all_of", [])
                parts += [options[0] for options in person.get("any_of", [])]
                if person.get("mentions_training"):
                    parts.append("pending training")
                writes.append(
                    (
                        "slack_chat_post_message",
                        {"channel": assertion["channel"], "text": " ".join(parts)},
                    )
                )
    return writes


def _results(writes) -> list[bool]:
    spec = _spec()
    world = spec["family_world"]
    for tool_name, arguments in writes:
        world, _ = access_provisioning.call_tool(
            world, tool_name, json.dumps(arguments)
        )
    return [
        access_provisioning.check_assertion(world, assertion)
        for assertion in spec["assertions"]
    ]


def test_queue_expected_state_is_reachable():
    assert all(_results(_expected_writes(_spec())))


def test_queue_skipping_last_request_fails():
    writes = [
        write
        for write in _expected_writes(_spec())
        if "pavel" not in json.dumps(write).lower()
        and "ACCESS-432" not in json.dumps(write)
    ]

    assert not all(_results(writes))


def test_queue_granting_requested_admin_instead_of_read_only_fails():
    writes = json.loads(
        json.dumps(_expected_writes(_spec())).replace(
            '"okta_carla_mendes", "group_id": "grp_prod_readonly"',
            '"okta_carla_mendes", "group_id": "grp_prod_admin"',
        )
    )

    assert not all(_results(writes))


def test_queue_reads_of_seeded_sheets_are_not_side_effects():
    task = next(
        task for task in get_tasks("interactive_canonical") if task.id == TASK_ID
    )
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    sheet = json.loads(
        environment.tools.api_fetch(
            method="GET",
            url="https://sheets.googleapis.com/v4/spreadsheets/ss_sod_matrix/values/Pairs",
        )
    )
    assert sheet["values"][1][:2] == ["grp_release_approver", "grp_prod_admin"]
    assertions = environment.tools.db.interactive_assertions
    index = next(
        position
        for position, assertion in enumerate(assertions)
        if assertion["type"] == "access_no_unrelated_api_side_effects"
    )
    assert environment.tools.assert_interactive_assertion(index)
