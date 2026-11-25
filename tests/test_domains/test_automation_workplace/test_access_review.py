import base64
import json

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import access_provisioning

TASK_ID = "automation_workplace__interactive__access_provisioning_006"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


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
    return task, environment


def _call(environment, tool_name, arguments):
    if tool_name == "api_fetch":
        return environment.use_tool("api_fetch", **arguments)
    environment.use_tool("unlock_discoverable_tool", discoverable_tool_name=tool_name)
    return environment.use_tool(
        "call_discoverable_tool",
        discoverable_tool_name=tool_name,
        arguments=json.dumps(arguments),
    )


def _email(to, subject, body):
    raw = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}".encode()
    return (
        "api_fetch",
        {
            "method": "POST",
            "url": SEND_URL,
            "body": json.dumps({"raw": base64.urlsafe_b64encode(raw).decode()}),
        },
    )


def _results(writes) -> list[bool]:
    task, environment = _environment()
    for tool_name, arguments in writes:
        _call(environment, tool_name, arguments)
    return [
        environment.run_env_assertion(assertion, raise_assertion_error=False)
        for assertion in task.evaluation_criteria.env_assertions
    ]


def _golden():
    return access_provisioning.golden_call_sequence("access_provisioning_006")


def test_review_golden_path_passes_every_assertion():
    assert all(_results(_golden()))


def test_first_okta_call_for_leon_times_out_without_applying():
    _, environment = _environment()
    arguments = {
        "user_id": "okta_leon_brandt",
        "group_id": "grp_prod_readonly",
        "expires_on": "2027-01-05",
    }

    first = json.loads(_call(environment, "okta_add_user_to_group_v1", arguments))
    groups = environment.tools.db.family_world["identities"]["okta_leon_brandt"][
        "groups"
    ]
    second = json.loads(_call(environment, "okta_add_user_to_group_v1", arguments))

    assert first["error"] == "upstream_timeout"
    assert "grp_prod_readonly" not in groups
    assert "grp_prod_readonly" in second["user"]["groups"]


def test_trusting_the_timed_out_call_fails():
    golden = _golden()
    retry = golden.index(
        next(step for step in golden if step[1].get("user_id") == "okta_leon_brandt")
    )

    assert not all(_results(golden[:retry] + golden[retry + 1 :]))


def test_leon_through_the_unentered_amendment_fails():
    writes = json.loads(
        json.dumps(_golden()).replace(
            '"okta_leon_brandt", "group_id": "grp_prod_readonly", '
            '"expires_on": "2027-01-05"',
            '"okta_leon_brandt", "group_id": "grp_prod_readonly", '
            '"expires_on": "2027-03-31"',
        )
    )

    assert not all(_results([tuple(step) for step in writes]))


def test_keeping_unmarked_review_row_fails():
    writes = [step for step in _golden() if step[1].get("user_id") != "okta_tomas_ruiz"]

    assert not all(_results(writes))


def test_missing_or_extra_emails_fail():
    golden = _golden()
    without_ask = [step for step in golden if step[0] != "api_fetch"]
    extra = _email(
        "people-ops@atlas.example",
        "Leon Brandt contract date",
        "Please enter Leon's signed amendment in Rippling.",
    )

    assert not all(_results(without_ask))
    assert not all(_results([*golden, extra]))


def test_marking_review_rows_applied_is_not_graded():
    update = (
        "api_fetch",
        {
            "method": "PUT",
            "url": "https://sheets.googleapis.com/v4/spreadsheets/ss_q4_review/"
            "values/Data Platform!E2",
            "params": json.dumps({"valueInputOption": "RAW"}),
            "body": json.dumps({"values": [["2026-12-14"]]}),
        },
    )

    assert all(_results([*_golden(), update]))
