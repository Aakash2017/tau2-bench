import base64
import json

import pytest

from tau2.domains.automation_workplace import standalone_apps as apps
from tau2.domains.automation_workplace.environment import get_environment, get_tasks

TASK_ID = "automation_workplace__interactive__access_provisioning_007"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"


def _environment():
    task = next(t for t in get_tasks("access_precedent") if t.id == TASK_ID)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return task, environment


def _send(environment, to="ken.watanabe@atlas.example", subject="Update", body="Done."):
    raw = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}".encode()
    return json.loads(
        environment.use_tool(
            "api_fetch",
            method="POST",
            url=f"{GMAIL}/messages/send",
            body=json.dumps({"raw": base64.urlsafe_b64encode(raw).decode()}),
        )
    )


def _get(environment, url, **params):
    return json.loads(
        environment.use_tool(
            "api_fetch", method="GET", url=url, params=json.dumps(params) or None
        )
    )


def test_access_tasks_use_the_standalone_engine():
    task, environment = _environment()

    assert apps.is_standalone(environment.tools.db.world)
    assert task.initial_state.initialization_data.agent_data["world"]["meta"][
        "engine"
    ] == ("standalone")


def test_profile_and_empty_mailbox_and_drive():
    _, environment = _environment()

    profile = _get(environment, f"{GMAIL}/profile")
    assert profile["emailAddress"] == apps.DESK_ADDRESS
    assert _get(environment, f"{GMAIL}/messages")["messages"] == []
    drive = _get(environment, "https://www.googleapis.com/drive/v3/files")
    assert drive == {"kind": "drive#fileList", "files": [], "incompleteSearch": False}


def test_sent_message_is_stored_listed_fetched_and_filtered():
    _, environment = _environment()

    sent = _send(environment, subject="Access update", body="Sven has access.")
    listing = _get(environment, f"{GMAIL}/messages")
    fetched = _get(environment, f"{GMAIL}/messages/{sent['id']}")

    assert sent["labelIds"] == ["SENT"]
    assert [m["id"] for m in listing["messages"]] == [sent["id"]]
    headers = {h["name"]: h["value"] for h in fetched["payload"]["headers"]}
    assert headers["Subject"] == "Access update"
    assert _get(environment, f"{GMAIL}/messages", q="nothing-matches")["messages"] == []
    assert _get(environment, f"{GMAIL}/messages/missing")["error"]["code"] == 404


def test_sending_an_email_fails_the_no_email_assertion():
    task, environment = _environment()
    _send(environment)

    assert not all(
        environment.run_env_assertion(a, raise_assertion_error=False)
        for a in task.evaluation_criteria.env_assertions
    )


def test_reads_leave_the_state_unchanged_for_the_side_effect_check():
    task, environment = _environment()
    _get(environment, f"{GMAIL}/profile")
    _get(environment, f"{GMAIL}/messages", q="access")
    _get(environment, "https://www.googleapis.com/drive/v3/files", pageSize=5)

    assert environment.tools.db.world == environment.tools.db.initial_world


def test_other_services_are_not_connected():
    _, environment = _environment()

    response = _get(environment, "https://slack.com/api/users.list")

    assert response["error"]["code"] == 401


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("send an email", "gmail.users.messages.send"),
        ("list my messages", "gmail.users.messages.list"),
        ("current user profile", "gmail.users.getProfile"),
        ("drive files list", "google_drive.files.list"),
    ],
)
def test_api_search_finds_the_relevant_endpoint(query, expected):
    _, environment = _environment()

    results = json.loads(environment.use_tool("api_search", query=query, top_k=3))

    assert expected in [r["id"] for r in results["results"]]
    assert all(r["url"].startswith("https://") for r in results["results"])
