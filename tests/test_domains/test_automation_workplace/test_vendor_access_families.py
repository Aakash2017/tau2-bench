import json
from pathlib import Path

import pytest

from tau2.domains.automation_workplace.data_model import KnowledgeDocument
from tau2.domains.automation_workplace.families import (
    access_provisioning,
    vendor_invoice,
)
from tau2.domains.automation_workplace.knowledge import search_documents

DATA_DIR = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive"
)


def _task(name: str) -> dict:
    return json.loads((DATA_DIR / "tasks" / f"{name}.json").read_text())


def _replay(module, raw_world: dict, sequence: list[tuple[str, dict]]) -> dict:
    world = json.loads(json.dumps(raw_world))
    for tool_name, arguments in sequence:
        world, response = module.call_tool(
            world,
            tool_name,
            json.dumps(arguments),
        )
        assert isinstance(json.loads(response), dict)
    return world


@pytest.mark.parametrize(
    ("module", "task_name", "family_id"),
    [
        (vendor_invoice, "vendor_invoice_001", "vendor_invoice"),
    ],
)
def test_family_contract_and_golden_state(module, task_name, family_id):
    task = _task(task_name)
    world = module.validate_world(task["family_world"])

    assert module.FAMILY_ID == family_id
    assert task["family"] == family_id
    assert module.TOOL_SCHEMAS
    assert all(
        {"description", "parameters", "mutates_state"} <= schema.keys()
        for schema in module.TOOL_SCHEMAS.values()
    )
    assert not all(
        module.check_assertion(world.model_dump(mode="json"), assertion)
        for assertion in task["assertions"]
    )

    sequence = (
        module.golden_call_sequence(world.task_id)
        if module is access_provisioning
        else module.golden_call_sequence()
    )
    final = _replay(module, task["family_world"], sequence)
    assert all(
        module.check_assertion(final, assertion) for assertion in task["assertions"]
    )

    golden_model = module.apply_golden_path(module.validate_world(task["family_world"]))
    assert golden_model.model_dump(mode="json") == final


@pytest.mark.parametrize(
    ("module", "task_name"),
    [
        (vendor_invoice, "vendor_invoice_001"),
    ],
)
def test_negative_call_sequence_is_executable_and_fails_exact_state(module, task_name):
    task = _task(task_name)
    sequence = (
        module.production_only_negative_call_sequence()
        if task_name == "access_provisioning_002"
        else module.negative_call_sequence()
    )
    final = _replay(module, task["family_world"], sequence)
    results = [
        module.check_assertion(final, assertion) for assertion in task["assertions"]
    ]

    assert not all(results)
    assert results.count(False) >= 3


@pytest.mark.parametrize(
    ("task_name", "knowledge_name", "expected_statuses"),
    [
        ("vendor_invoice_001", "vendor_invoice", {"current", "superseded"}),
    ],
)
def test_every_referenced_family_document_exists(
    task_name, knowledge_name, expected_statuses
):
    task = _task(task_name)
    documents = json.loads(
        (DATA_DIR / "knowledge" / f"{knowledge_name}.json").read_text()
    )

    assert set(task["knowledge_document_ids"]) == {
        item["document_id"] for item in documents
    }
    assert {item["status"] for item in documents} == expected_statuses


def test_vendor_call_contract_returns_new_serializable_world():
    task = _task("vendor_invoice_001")
    original = task["family_world"]
    updated, response = vendor_invoice.call_tool(
        original,
        "netsuite_update_bill_v1",
        json.dumps(
            {
                "bill_id": "bill_northstar_7842",
                "status": "on_hold",
                "hold_reason_codes": ["UNCONTRACTED_CHARGE"],
            }
        ),
    )

    assert original["bills"]["bill_northstar_7842"]["status"] == "draft"
    assert updated["bills"]["bill_northstar_7842"]["status"] == "on_hold"
    assert json.loads(response)["bill"]["status"] == "on_hold"


def test_vendor_negative_assertions_detect_material_wrong_side_effects():
    task = _task("vendor_invoice_001")
    final = _replay(
        vendor_invoice,
        task["family_world"],
        vendor_invoice.golden_call_sequence(),
    )

    paid, _ = vendor_invoice.call_tool(
        final,
        "netsuite_create_payment_v1",
        json.dumps(
            {
                "bill_id": "bill_northstar_7842",
                "amount": 53800.0,
                "bank_last4": "9917",
            }
        ),
    )
    assert not vendor_invoice.check_assertion(paid, {"type": "invoice_no_payment"})

    bank_changed, _ = vendor_invoice.call_tool(
        final,
        "netsuite_update_vendor_bank_v1",
        json.dumps(
            {
                "vendor_id": "vendor_northstar",
                "bank_last4": "9917",
                "verification_status": "email_only",
            }
        ),
    )
    assert not vendor_invoice.check_assertion(
        bank_changed, {"type": "invoice_bank_record_preserved"}
    )
