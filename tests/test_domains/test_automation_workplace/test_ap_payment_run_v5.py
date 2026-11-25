"""AP payment run learned from Slack history (vendor_invoice_005)."""

import json

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import ap_payment_run
from tau2.utils.utils import DATA_DIR

TASK_ID = "automation_workplace__interactive__vendor_invoice_005"
INTERACTIVE = DATA_DIR / "tau2/domains/automation_workplace/interactive"
SPEC = json.loads((INTERACTIVE / "tasks/vendor_invoice_005.json").read_text())
KB = json.loads((INTERACTIVE / SPEC["knowledge_file"]).read_text())
SLACK = SPEC["family_world"]["slack_messages"]


def _env():
    task = next(t for t in get_tasks("interactive_canonical") if t.id == TASK_ID)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return task, environment


def _call(environment, name, args):
    environment.use_tool("unlock_discoverable_tool", discoverable_tool_name=name)
    return environment.use_tool(
        "call_discoverable_tool",
        discoverable_tool_name=name,
        arguments=json.dumps(args),
    )


def _failed(writes):
    task, environment = _env()
    for name, args in writes:
        _call(environment, name, args)
    return [
        a.message
        for a in task.evaluation_criteria.env_assertions
        if not environment.run_env_assertion(a, raise_assertion_error=False)
    ]


def _golden():
    return ap_payment_run.golden_call_sequence(SPEC)


def test_golden_path_passes_every_assertion():
    assert _failed(_golden()) == []


def test_negative_path_fails():
    assert _failed(ap_payment_run.negative_call_sequence(SPEC))


def test_extra_email_fails():
    extra = (
        "gmail_send_message_v1",
        {"to": ["marco.diaz@atlas.example"], "subject": "Corvid", "body": "paid"},
    )
    assert _failed([*_golden(), extra])


def test_extra_slack_post_fails():
    extra = ("slack_chat_post_message", {"channel": "ap-payments", "text": "done"})
    assert _failed([*_golden(), extra])


def test_wrong_run_date_format_in_exceptions_row_fails():
    writes = [
        (
            n,
            {**a, "values": {**a["values"], "run_date": "12/15"}}
            if n == "sheets_append_row_v1"
            else a,
        )
        for n, a in _golden()
    ]
    assert _failed(writes)


def test_touching_tidewell_fails():
    extra = (
        "netsuite_update_bill_v1",
        {"bill_id": "bill_2212", "scheduled_run_date": "2026-12-22"},
    )
    writes = [*_golden(), extra]
    names = {n for n, _ in _golden()}
    if "netsuite_update_bill_v1" in names:
        assert _failed(writes)


def test_seeded_slack_is_not_counted_as_agent_posts():
    assert all(m["user"] != "ap-bot" for m in SLACK.values())
    assert {m["channel"] for m in SLACK.values()} >= {
        "ap-payments",
        "treasury-ops",
        "procurement",
        "eng-access",
        "general",
    }


def test_channel_history_paginates_and_threads_resolve():
    _, environment = _env()
    first = json.loads(
        _call(environment, "slack_get_channel_history_v1", {"channel": "ap-payments"})
    )
    assert first["total_pages"] == 2
    assert len(first["messages"]) == 8
    assert first["messages"][0]["ts"] > first["messages"][-1]["ts"]
    run_thread = next(m for m in SLACK.values() if m["text"].startswith("11/24 run"))
    thread = json.loads(
        _call(
            environment,
            "slack_get_thread_v1",
            {"channel": "ap-payments", "thread_ts": run_thread["ts"]},
        )
    )
    assert any("vendor master" in m["text"] for m in thread["messages"])


def test_no_procedure_in_kb_and_practice_only_in_slack():
    ids = {d["document_id"] for d in KB}
    assert (
        not {
            "kb_ap_payment_run_procedure_2026_11",
            "kb_ap_payment_run_procedure_2025_03",
            "kb_ap_remittance_advice_2026_10",
        }
        & ids
    )
    text = " ".join(d["content"] for d in KB if d["status"] == "current").lower()
    for term in ["treasury-ops", "exceptions fy26", "scheduled run date", "skip it"]:
        assert term not in text
    mailbox = SPEC["family_world"]["mailbox"]
    assert "msg_controller_exceptions" not in mailbox
    assert "treasury-ops" not in mailbox["msg_tr_1214"]["body"]
    slack_text = " ".join(m["text"] for m in SLACK.values())
    for term in ["#treasury-ops", "AP Exceptions FY26", "vendor master", "past due"]:
        assert term in slack_text


def test_user_is_not_a_teacher():
    instructions = SPEC["user_scenario"]["instructions"]["task_instructions"]
    assert "never point the assistant to Slack" in instructions
    assert "Never ask for a summary" in instructions
