import json
from copy import deepcopy
from pathlib import Path

import pytest

from tau2.domains.automation_workplace.families import (
    customer_escalation,
    renewal_portfolio,
)

DATA_DIR = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive"
)

FAMILIES = [
    (customer_escalation, "customer_escalation_001", "customer_escalation"),
    (renewal_portfolio, "renewal_portfolio_001", "renewal_portfolio"),
]


def _task(task_name: str) -> dict:
    return json.loads((DATA_DIR / "tasks" / f"{task_name}.json").read_text())


def _replay(module, initial: dict, calls: list[tuple[str, dict]]) -> dict:
    world = deepcopy(initial)
    for tool_name, arguments in calls:
        world, response = module.call_tool(world, tool_name, json.dumps(arguments))
        assert isinstance(json.loads(response), dict)
    return world


@pytest.mark.parametrize(("module", "task_name", "family_id"), FAMILIES)
def test_family_contract_and_tool_schemas(module, task_name, family_id):
    task = _task(task_name)

    assert module.FAMILY_ID == family_id
    assert task["interactive_family"] == family_id
    assert module.validate_world(task["interactive_world"]).task_id == task_name
    assert module.TOOL_SCHEMAS
    assert all(
        name.startswith(family_id.split("_")[0] + "_") for name in module.TOOL_SCHEMAS
    )
    assert all(
        set(schema) == {"description", "parameters", "mutates_state"}
        and schema["parameters"]["type"] == "object"
        and schema["parameters"]["additionalProperties"] is False
        and isinstance(schema["mutates_state"], bool)
        for schema in module.TOOL_SCHEMAS.values()
    )


@pytest.mark.parametrize(("module", "task_name", "family_id"), FAMILIES)
def test_golden_sequences_pass_every_exact_state_assertion(
    module, task_name, family_id
):
    del family_id
    task = _task(task_name)

    initial_results = [
        module.check_assertion(task["interactive_world"], assertion)
        for assertion in task["assertions"]
    ]
    assert not all(initial_results)

    final = _replay(
        module,
        task["interactive_world"],
        module.golden_call_sequence(),
    )
    assert [
        module.check_assertion(final, assertion) for assertion in task["assertions"]
    ] == [True] * len(task["assertions"])


@pytest.mark.parametrize(("module", "task_name", "family_id"), FAMILIES)
def test_negative_sequences_produce_material_failure_signal(
    module, task_name, family_id
):
    del family_id
    task = _task(task_name)
    final = _replay(
        module,
        task["interactive_world"],
        module.negative_call_sequence(),
    )
    results = {
        assertion["type"]: module.check_assertion(final, assertion)
        for assertion in task["assertions"]
    }

    assert sum(not result for result in results.values()) >= 4
    if task_name == "customer_escalation_001":
        assert not results["customer_verified_single_outreach"]
        assert not results["customer_credit_exact_and_authorized"]
        assert not results["customer_case_exact"]
        assert results["customer_source_records_preserved"]
    else:
        assert not results["renewal_qualifier_tasks_exact"]
        assert not results["renewal_permitted_outreach_exact"]
        assert not results["renewal_legal_hold_respected"]
        assert not results["renewal_parent_child_deduplicated"]
        assert results["renewal_unrelated_records_preserved"]


@pytest.mark.parametrize(("module", "task_name", "family_id"), FAMILIES)
def test_call_tool_returns_a_new_serializable_world(module, task_name, family_id):
    del family_id
    task = _task(task_name)
    original = deepcopy(task["interactive_world"])
    tool_name, arguments = module.golden_call_sequence()[0]

    updated, response = module.call_tool(original, tool_name, json.dumps(arguments))

    assert original == task["interactive_world"]
    assert updated != original
    assert module.validate_world(updated).model_dump(mode="json") == updated
    assert isinstance(json.loads(response), dict)


@pytest.mark.parametrize(("module", "task_name", "family_id"), FAMILIES)
def test_every_referenced_knowledge_document_and_tool_is_reviewable(
    module, task_name, family_id
):
    del family_id
    task = _task(task_name)
    documents = json.loads((DATA_DIR / task["knowledge_file"]).read_text())
    by_id = {document["document_id"]: document for document in documents}

    assert set(task["knowledge_document_ids"]) == set(by_id)
    assert {document["status"] for document in documents} == {
        "current",
        "superseded",
    }
    corpus = "\n".join(document["content"] for document in documents)
    assert all(tool_name in corpus for tool_name in module.TOOL_SCHEMAS)
    assert all(
        by_id[document_id]["status"] in {"current", "superseded"}
        and by_id[document_id]["updated_at"]
        and by_id[document_id]["content"]
        for document_id in task["knowledge_document_ids"]
    )
