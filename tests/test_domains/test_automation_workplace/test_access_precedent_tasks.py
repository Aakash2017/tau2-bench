import base64
import json

import pytest

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import access_provisioning

NUMBERS = ["008", "009", "010"]


def _task(number):
    task_id = f"automation_workplace__interactive__access_provisioning_{number}"
    return next(t for t in get_tasks("interactive_canonical") if t.id == task_id)


def _results(number, writes) -> list[bool]:
    task = _task(number)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    for tool_name, arguments in writes:
        environment.use_tool(
            "unlock_discoverable_tool", discoverable_tool_name=tool_name
        )
        environment.use_tool(
            "call_discoverable_tool",
            discoverable_tool_name=tool_name,
            arguments=json.dumps(arguments),
        )
    return [
        environment.run_env_assertion(a, raise_assertion_error=False)
        for a in task.evaluation_criteria.env_assertions
    ]


def _golden(number):
    return access_provisioning.golden_call_sequence(f"access_provisioning_{number}")


def _with_expiry(writes, old, new):
    return [tuple(json.loads(json.dumps(s).replace(old, new))) for s in writes]


@pytest.mark.parametrize("number", NUMBERS)
def test_golden_passes_every_assertion(number):
    assert all(_results(number, _golden(number)))


@pytest.mark.parametrize("number", NUMBERS)
def test_no_writes_fails(number):
    assert not all(_results(number, []))


@pytest.mark.parametrize("number", NUMBERS)
def test_one_combined_announcement_fails(number):
    golden = _golden(number)
    posts = [s for s in golden if s[0] == "slack_chat_post_message"]
    rest = [s for s in golden if s[0] != "slack_chat_post_message"]
    combined = (
        "slack_chat_post_message",
        {
            "channel": "eng-access-requests",
            "text": " ".join(step[1]["text"] for step in posts),
        },
    )

    assert not all(_results(number, [*rest, combined]))


@pytest.mark.parametrize(
    ("number", "right", "wrong"),
    [
        ("008", "2026-12-28", "2027-01-13"),
        ("008", "2027-03-14", "2027-01-13"),
        ("009", "2026-12-21", "2027-01-13"),
        ("009", "2027-01-08", "2027-01-13"),
        ("009", "2027-01-13", "2027-06-30"),
        ("010", "2027-01-08", "2027-01-13"),
        ("010", "2027-01-13", "2027-03-31"),
    ],
)
def test_default_window_where_a_specific_one_applies_fails(number, right, wrong):
    assert not all(_results(number, _with_expiry(_golden(number), right, wrong)))


@pytest.mark.parametrize("number", NUMBERS)
def test_sending_an_email_fails(number):
    raw = b"To: ken.watanabe@atlas.example\r\nSubject: Access update\r\n\r\nDone."
    send = (
        "api_fetch",
        {
            "method": "POST",
            "url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            "body": json.dumps({"raw": base64.urlsafe_b64encode(raw).decode()}),
        },
    )
    task = _task(number)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    for tool_name, arguments in _golden(number):
        environment.use_tool(
            "unlock_discoverable_tool", discoverable_tool_name=tool_name
        )
        environment.use_tool(
            "call_discoverable_tool",
            discoverable_tool_name=tool_name,
            arguments=json.dumps(arguments),
        )
    environment.use_tool("api_fetch", **send[1])

    assert not all(
        environment.run_env_assertion(a, raise_assertion_error=False)
        for a in task.evaluation_criteria.env_assertions
    )
