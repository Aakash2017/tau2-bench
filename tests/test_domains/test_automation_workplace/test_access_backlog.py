import json
from pathlib import Path

import pytest

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import access_provisioning

TASK_ID = "automation_workplace__interactive__access_provisioning_003"
TASK_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive/tasks"
    / "access_provisioning_003.json"
)


def _spec() -> dict:
    return json.loads(TASK_PATH.read_text())


def _replay(sequence) -> dict:
    world = _spec()["family_world"]
    for tool_name, arguments in sequence:
        world, _ = access_provisioning.call_tool(
            world, tool_name, json.dumps(arguments)
        )
    return world


def _environment():
    task = next(
        task for task in get_tasks("interactive_canonical") if task.id == TASK_ID
    )
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return environment


def _family_results(world: dict) -> dict[str, bool]:
    return {
        assertion["message"]: access_provisioning.check_assertion(world, assertion)
        for assertion in _spec()["assertions"]
    }


def test_backlog_golden_path_passes_every_assertion():
    world = _replay(access_provisioning.golden_call_sequence("access_provisioning_003"))

    assert all(_family_results(world).values())


@pytest.mark.parametrize(
    "sequence",
    [[], access_provisioning.backlog_shortcut_call_sequence()],
    ids=["no-op", "approve-everything"],
)
def test_backlog_shortcuts_fail_most_assertions(sequence):
    results = _family_results(_replay(sequence))

    assert list(results.values()).count(False) >= 9


def test_backlog_partial_list_processing_fails():
    golden = access_provisioning.golden_call_sequence("access_provisioning_003")
    without_noor = [
        step
        for step in golden
        if "noor" not in json.dumps(step).lower()
        and "ACCESS-406" not in json.dumps(step)
    ]

    assert not all(_family_results(_replay(without_noor)).values())


def test_backlog_breakglass_after_window_fails():
    golden = access_provisioning.golden_call_sequence("access_provisioning_003")
    late = json.loads(json.dumps(golden).replace("2026-12-18", "2026-12-19"))

    assert not all(_family_results(_replay(late)).values())


def test_jira_search_by_approver_returns_the_queue():
    _, response = access_provisioning.call_tool(
        _spec()["family_world"],
        "jira_search_access_requests_v1",
        json.dumps({"approver_id": "worker_jordan_bell"}),
    )
    request_ids = {item["request_id"] for item in json.loads(response)["issues"]}

    assert {f"ACCESS-40{index}" for index in range(1, 7)} <= request_ids
    assert "ACCESS-407" not in request_ids


def test_okta_group_history_records_grants_and_removals():
    world = _replay(
        [
            (
                "okta_add_user_to_group_v1",
                {
                    "user_id": "okta_lena_ortiz",
                    "group_id": "grp_prod_readonly",
                    "expires_on": "2027-01-29",
                },
            ),
            (
                "okta_remove_user_from_group_v1",
                {"user_id": "okta_lena_ortiz", "group_id": "grp_prod_readonly"},
            ),
        ]
    )
    history = world["identities"]["okta_lena_ortiz"]["group_history"]

    assert history[-1] == {
        "group_id": "grp_prod_readonly",
        "added_on": "2026-12-16",
        "removed_on": "2026-12-16",
    }


def _side_effect_check(environment) -> bool:
    assertions = environment.tools.db.interactive_assertions
    index = next(
        position
        for position, assertion in enumerate(assertions)
        if assertion["type"] == "access_no_unrelated_api_side_effects"
    )
    return environment.tools.assert_interactive_assertion(index)


def test_generic_reads_of_seeded_evidence_are_not_side_effects():
    environment = _environment()
    tools = environment.tools

    listing = json.loads(
        tools.api_fetch(
            method="GET",
            url="https://gmail.googleapis.com/gmail/v1/users/me/messages",
            params=json.dumps({"q": "break-glass"}),
        )
    )
    assert {item["id"] for item in listing["messages"]} >= {"msg_cto_inc901"}
    message = json.loads(
        tools.api_fetch(
            method="GET",
            url="https://gmail.googleapis.com/gmail/v1/users/me/messages/msg_cto_inc901",
        )
    )
    assert "2026-12-18 10:00 PT" in message["body_plain"]
    sheet = json.loads(
        tools.api_fetch(
            method="GET",
            url=(
                "https://sheets.googleapis.com/v4/spreadsheets/"
                "ss_contractor_sow/values/Amendments"
            ),
        )
    )
    assert ["Dev Raghavan", "2", "2027-03-31"] == sheet["values"][2][:3]

    assert _side_effect_check(environment)


def test_generic_send_is_a_side_effect():
    environment = _environment()
    environment.tools.api_fetch(
        method="POST",
        url="https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        body=json.dumps(
            {
                "raw": environment.tools.base64_encode(
                    "To: sam.whitaker@atlas.example\r\nSubject: Access\r\n\r\nDone."
                )
            }
        ),
    )

    assert not _side_effect_check(environment)


def test_backlog_task_loads_deterministically():
    def generic_world():
        task = next(
            task for task in get_tasks("interactive_canonical") if task.id == TASK_ID
        )
        return task.initial_state.initialization_data.agent_data["world"]

    assert generic_world() == generic_world()


SCOPING_TASK_PATH = TASK_PATH.with_name("access_provisioning_004.json")


def _scoping_results(sequence) -> list[bool]:
    spec = json.loads(SCOPING_TASK_PATH.read_text())
    world = spec["family_world"]
    for tool_name, arguments in sequence:
        world, _ = access_provisioning.call_tool(
            world, tool_name, json.dumps(arguments)
        )
    return [
        access_provisioning.check_assertion(world, assertion)
        for assertion in spec["assertions"]
    ]


def test_scoping_golden_path_passes_every_assertion():
    golden = access_provisioning.golden_call_sequence("access_provisioning_004")

    assert all(_scoping_results(golden))


def test_scoping_shortcut_fails_most_assertions():
    results = _scoping_results(access_provisioning.scoping_shortcut_call_sequence())

    assert results.count(False) >= 10


def test_scoping_granting_requested_admin_fails():
    golden = access_provisioning.golden_call_sequence("access_provisioning_004")
    as_requested = json.loads(
        json.dumps(golden).replace(
            '"okta_hana_sato", "group_id": "grp_prod_readonly"',
            '"okta_hana_sato", "group_id": "grp_prod_admin"',
        )
    )

    assert not all(_scoping_results(as_requested))


def test_scoping_resolving_conflict_by_removing_role_fails():
    golden = access_provisioning.golden_call_sequence("access_provisioning_004")
    removal = (
        "okta_remove_user_from_group_v1",
        {"user_id": "okta_tomas_rivera", "group_id": "grp_release_approver"},
    )

    assert not all(_scoping_results([removal, *golden]))


def test_slack_post_rejects_unknown_channels_and_strips_hash():
    world = _spec()["family_world"]

    with pytest.raises(ValueError, match="channel_not_found"):
        access_provisioning.call_tool(
            world,
            "slack_chat_post_message",
            json.dumps({"channel": "access-requests", "text": "hello"}),
        )
    updated, response = access_provisioning.call_tool(
        world,
        "slack_chat_post_message",
        json.dumps({"channel": "#eng-access-requests", "text": "hello"}),
    )
    assert json.loads(response)["message"]["channel"] == "eng-access-requests"
