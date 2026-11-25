"""Multimodal AP payment run (vendor_invoice_003): image-only evidence."""

import json
from pathlib import Path

from tau2.data_model.message import ToolCall, ToolMessage, ToolOutputWithImages
from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import ap_payment_run
from tau2.utils.llm_utils import to_litellm_messages
from tau2.utils.utils import DATA_DIR

TASK_ID = "automation_workplace__interactive__vendor_invoice_003"
INTERACTIVE = DATA_DIR / "tau2/domains/automation_workplace/interactive"
SPEC = json.loads((INTERACTIVE / "tasks/vendor_invoice_003.json").read_text())
KB = json.loads((INTERACTIVE / SPEC["knowledge_file"]).read_text())


def _environment():
    task = next(t for t in get_tasks("interactive_canonical") if t.id == TASK_ID)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return task, environment


def _call(environment, tool_name, arguments):
    environment.use_tool("unlock_discoverable_tool", discoverable_tool_name=tool_name)
    return environment.use_tool(
        "call_discoverable_tool",
        discoverable_tool_name=tool_name,
        arguments=json.dumps(arguments),
    )


def _failed(writes):
    task, environment = _environment()
    for name, args in writes:
        _call(environment, name, args)
    return [
        a.message
        for a in task.evaluation_criteria.env_assertions
        if not environment.run_env_assertion(a, raise_assertion_error=False)
    ]


def test_golden_path_passes_every_assertion():
    assert _failed(ap_payment_run.golden_call_sequence(SPEC)) == []


def test_every_referenced_attachment_exists():
    world = SPEC["family_world"]
    referenced = {a for d in KB for a in d.get("attachments", [])}
    for record in [*world["bills"].values(), *world["mailbox"].values()]:
        referenced.update(record.get("attachment_ids", []))
    assert referenced == set(world["attachments"])
    for file in world["attachments"].values():
        assert (DATA_DIR / file["path"]).is_file()


def test_decisive_facts_are_not_in_text():
    world = SPEC["family_world"]
    matrix = next(d for d in KB if d["document_id"] == "kb_ap_approval_matrix_2026_10")
    assert "limit" not in matrix["content"] and matrix["attachments"]
    assert "100,000" not in world["mailbox"]["msg_tr_1214"]["body"]
    assert "8842" not in world["bills"]["bill_2203"]["remit_to_note"]
    kestrel = world["bills"]["bill_2204"]
    assert kestrel["invoice_number"] != "INV-020931"
    assert "020931" not in world["mailbox"]["msg_kestrel_resend"]["body"]


def test_deferring_miskeyed_duplicate_instead_of_rejecting_fails():
    writes = [
        (n, {"bill_id": "bill_2204", "scheduled_run_date": "2026-12-22"})
        if a.get("bill_id") == "bill_2204" and n == "netsuite_update_bill_v1"
        else (n, a)
        for n, a in ap_payment_run.golden_call_sequence(SPEC)
    ]
    assert _failed(writes)


def test_attachment_reaches_the_model_as_an_image():
    _, environment = _environment()
    out = _call(
        environment,
        "files_get_attachment_v1",
        {"attachment_id": "att_scan_kestrel_resend"},
    )
    assert isinstance(out, ToolOutputWithImages)
    assert "_image_paths" not in out.content
    message = environment.get_response(
        ToolCall(
            id="c1",
            name="call_discoverable_tool",
            arguments={
                "discoverable_tool_name": "files_get_attachment_v1",
                "arguments": json.dumps({"attachment_id": "att_scan_kestrel_resend"}),
            },
        )
    )
    assert message.images and Path(DATA_DIR / message.images[0]).is_file()
    other = ToolMessage(id="c2", role="tool", content="{}")
    converted = to_litellm_messages([message, other])
    assert [m["role"] for m in converted] == ["tool", "tool", "user"]
    parts = converted[-1]["content"]
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
