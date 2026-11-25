"""AP payment run without a checklist (vendor_invoice_004)."""

import json

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import ap_payment_run
from tau2.utils.utils import DATA_DIR

TASK_ID = "automation_workplace__interactive__vendor_invoice_004"
INTERACTIVE = DATA_DIR / "tau2/domains/automation_workplace/interactive"
SPEC = json.loads((INTERACTIVE / "tasks/vendor_invoice_004.json").read_text())
KB = json.loads((INTERACTIVE / SPEC["knowledge_file"]).read_text())
SHEET = "sh_ap_exceptions_fy26"


def _failed(writes):
    task = next(t for t in get_tasks("interactive_canonical") if t.id == TASK_ID)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    for name, args in writes:
        environment.use_tool("unlock_discoverable_tool", discoverable_tool_name=name)
        environment.use_tool(
            "call_discoverable_tool",
            discoverable_tool_name=name,
            arguments=json.dumps(args),
        )
    return [
        a.message
        for a in task.evaluation_criteria.env_assertions
        if not environment.run_env_assertion(a, raise_assertion_error=False)
    ]


def _golden():
    return ap_payment_run.golden_call_sequence(SPEC)


def _without(predicate):
    return [(n, a) for n, a in _golden() if not predicate(n, a)]


def _swap(predicate, change):
    return [(n, change(a)) if predicate(n, a) else (n, a) for n, a in _golden()]


def _row(bill_id):
    return lambda n, a: (
        n == "sheets_append_row_v1" and a["values"]["bill_id"] == bill_id
    )


def test_golden_path_passes_every_assertion():
    assert _failed(_golden()) == []


def test_negative_path_fails():
    assert _failed(ap_payment_run.negative_call_sequence(SPEC))


def test_pinecrest_paid_to_vendor_account_fails():
    writes = _swap(
        lambda n, a: n == "netsuite_create_payment_v1" and a["bill_id"] == "bill_2206",
        lambda a: {**a, "bank_account_id": "ba_pinecrest_01"},
    )
    assert _failed(writes)


def test_pinecrest_remittance_to_vendor_fails():
    writes = _swap(
        lambda n, a: (
            n == "gmail_send_message_v1" and a["to"] == ["cash@harborfunding.example"]
        ),
        lambda a: {**a, "to": ["ar@pinecrest.example"]},
    )
    assert _failed(writes)


def test_missing_exception_row_fails():
    assert _failed(_without(_row("bill_2211")))


def test_extra_row_for_deferred_bill_fails():
    extra = (
        "sheets_append_row_v1",
        {
            "sheet_id": SHEET,
            "values": {"run_date": "2026-12-15", "bill_id": "bill_2207"},
        },
    )
    assert _failed([*_golden(), extra])


def test_wrong_reason_code_fails():
    writes = _swap(
        _row("bill_2204"),
        lambda a: {**a, "values": {**a["values"], "reason_code": "HOLD"}},
    )
    assert _failed(writes)


def test_missing_procurement_note_fails():
    assert _failed(
        _without(
            lambda n, a: (
                n == "slack_chat_post_message" and a["channel"] == "procurement"
            )
        )
    )


def test_missing_treasury_summary_fails():
    assert _failed(
        _without(
            lambda n, a: (
                n == "slack_chat_post_message" and a["channel"] == "treasury-ops"
            )
        )
    )


def test_side_obligations_live_only_in_records():
    text = " ".join(d["content"] for d in KB if d["status"] == "current").lower()
    for term in ["exceptions", "procurement", "treasury-ops", "harbor"]:
        assert term not in text
    procedure = next(
        d for d in KB if d["document_id"] == "kb_ap_payment_run_procedure_2026_11"
    )
    for term in ["duplicate", "receipt", "remittance", "banking"]:
        assert term not in procedure["content"].lower()
    mailbox = SPEC["family_world"]["mailbox"]
    assert "treasury-ops" in mailbox["msg_tr_1214"]["body"]
    assert "AP Exceptions FY26" in mailbox["msg_controller_exceptions"]["body"]
    assert "#procurement" in mailbox["msg_marco_corvid"]["body"]


def test_user_states_stale_beliefs_and_never_asks_for_summary():
    instructions = SPEC["user_scenario"]["instructions"]
    assert "110k" in instructions["reason_for_call"]
    assert "lumen" in instructions["reason_for_call"]
    assert "Never ask for a summary" in instructions["task_instructions"]
