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
        (access_provisioning, "access_provisioning_001", "access_provisioning"),
        (access_provisioning, "access_provisioning_002", "access_provisioning"),
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
        (access_provisioning, "access_provisioning_001"),
        (access_provisioning, "access_provisioning_002"),
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
        ("access_provisioning_001", "access_provisioning", {"current"}),
        ("access_provisioning_002", "access_provisioning", {"current"}),
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


@pytest.mark.parametrize(
    ("blocker", "expected"),
    [
        ("pending secure-production-access-2026 completion", True),
        ("pending production training", True),
        ("pending role-owner approval", False),
    ],
)
def test_access_manager_update_accepts_course_id_as_training(blocker, expected):
    task = _task("access_provisioning_001")
    final = _replay(
        access_provisioning,
        task["family_world"],
        access_provisioning.golden_call_sequence(),
    )
    message = next(
        item
        for item in final["slack_messages"].values()
        if "priya raman" in item["text"].lower()
    )
    message["text"] = (
        "Priya Raman received staging read-only through 2026-12-14. "
        f"Production access remains blocked {blocker}."
    )

    assert (
        access_provisioning.check_assertion(
            final, {"type": "access_manager_notified_once"}
        )
        is expected
    )


def test_access_negative_assertions_detect_privilege_and_identity_errors():
    task = _task("access_provisioning_001")
    final = _replay(
        access_provisioning,
        task["family_world"],
        access_provisioning.golden_call_sequence(),
    )

    overgranted, _ = access_provisioning.call_tool(
        final,
        "okta_add_user_to_group_v1",
        json.dumps(
            {
                "user_id": "okta_priya_active",
                "group_id": "grp_prod_admin",
                "expires_on": "2026-12-19",
            }
        ),
    )
    assert not access_provisioning.check_assertion(
        overgranted, {"type": "access_no_production_entitlement"}
    )
    assert not access_provisioning.check_assertion(
        overgranted, {"type": "access_active_identity_staging_only"}
    )

    stale_granted = json.loads(json.dumps(final))
    stale_granted["identities"]["okta_priya_stale"]["groups"] = ["grp_staging_readonly"]
    assert not access_provisioning.check_assertion(
        stale_granted, {"type": "access_stale_identity_preserved"}
    )


def test_access_rippling_directory_has_realistic_same_name_ambiguity():
    task = _task("access_provisioning_001")
    unchanged, response = access_provisioning.call_tool(
        task["family_world"],
        "rippling_search_people_v1",
        json.dumps({"query": "Priya"}),
    )
    result = json.loads(response)

    assert unchanged == access_provisioning.validate_world(
        task["family_world"]
    ).model_dump(mode="json")
    assert result["company"] == "Atlas Labs"
    assert result["company_people_count"] == 100
    assert result["count"] == 2
    assert {
        (person["legal_name"], person["manager_name"]) for person in result["people"]
    } == {
        ("Priya Raman", "Jordan Bell"),
        ("Priya Shah", "Amara Kapoor"),
    }


def test_production_only_access_variant_has_entity_overlapping_noise():
    task = _task("access_provisioning_002")

    _, people_response = access_provisioning.call_tool(
        task["family_world"],
        "rippling_search_people_v1",
        json.dumps({"query": "Priya"}),
    )
    people_result = json.loads(people_response)
    people = people_result["people"]
    assert people_result["company_people_count"] == 200
    assert len(people) == 2
    assert {person["legal_name"] for person in people} == {
        "Priya Raman",
        "Priya Shah",
    }
    target_people = [
        person
        for person in people
        if person["legal_name"] == "Priya Raman"
        and person["manager_name"] == "Jordan Bell"
    ]
    assert len(target_people) == 1

    _, identity_response = access_provisioning.call_tool(
        task["family_world"],
        "okta_search_users_v1",
        json.dumps({"query": "Priya"}),
    )
    identities = json.loads(identity_response)["users"]
    assert len(identities) == 3
    assert {identity["worker_id"] for identity in identities} >= {
        "worker_priya_raman",
        "worker_priya_shah",
    }

    _, miguel_response = access_provisioning.call_tool(
        task["family_world"],
        "rippling_search_people_v1",
        json.dumps({"query": "Miguel"}),
    )
    miguels = json.loads(miguel_response)["people"]
    assert len(miguels) == 2
    assert {person["legal_name"] for person in miguels} == {
        "Miguel Santos",
        "Miguel Santiago",
    }


def test_production_only_user_prompt_does_not_contain_final_state_answer_key():
    task = _task("access_provisioning_002")
    instructions = task["user_scenario"]["instructions"]
    task_instructions = instructions["task_instructions"]

    assert (
        "which follow-through the access workflow requires"
        in instructions["unknown_info"]
    )
    assert "staging access was removed" not in task_instructions
    assert "current production course was assigned" not in task_instructions
    assert "existing production request was blocked" not in task_instructions
    assert "Do not name the action it should take" in task_instructions
    assert "Do not combine this disclosure with the assignment disclosure" in (
        task_instructions
    )


def test_production_only_access_variant_has_dense_slack_noise():
    task = _task("access_provisioning_002")
    assert len(task["family_world"]["slack_messages"]) == 30
    assert (
        len(
            {
                message["channel"]
                for message in task["family_world"]["slack_messages"].values()
            }
        )
        >= 20
    )

    _, response = access_provisioning.call_tool(
        task["family_world"],
        "slack_search_messages_v1",
        json.dumps({"query": "access"}),
    )
    result = json.loads(response)
    assert result["count"] >= 10
    assert "eng-access-requests" in result["channels"]
    assert {"it-help", "security", "data-access", "app-requests"} <= set(
        result["channels"]
    )


def test_production_only_kb_uses_recency_without_superseded_labels():
    task = _task("access_provisioning_002")
    documents = json.loads((DATA_DIR / task["knowledge_file"]).read_text())
    by_id = {item["document_id"]: item for item in documents}

    assert {item["status"] for item in documents} == {"current"}
    assert all("superseded" not in item["title"].lower() for item in documents)

    staging = by_id["kb_staging_data_loading_2025_01"]
    boundary = by_id["kb_production_data_boundary_2026_11"]
    temporary_access = by_id["kb_temporary_access_2026_09"]
    assert "backend/scripts/load_to_staging" in staging["content"]
    assert staging["updated_at"] < boundary["updated_at"]
    assert "cannot retrieve or exfiltrate live production data" in boundary["content"]
    assert "kept only if it meets this standard" in temporary_access["content"]


def test_production_only_noise_keeps_critical_documents_retrievable():
    task = _task("access_provisioning_002")
    raw_documents = json.loads((DATA_DIR / task["knowledge_file"]).read_text())
    documents = {
        item["document_id"]: KnowledgeDocument.model_validate(item)
        for item in raw_documents
    }
    assert len(documents) == 39

    def top_ids(query: str) -> list[str]:
        return [
            item["document_id"] for item in search_documents(documents, query, top_k=5)
        ]

    policy_ids = top_ids("contractor production access signed paperwork training")
    assert "kb_production_access_standard_2026_10" in policy_ids
    assert "kb_department_manager_prod_access_2025_10" in policy_ids

    assert "kb_temporary_access_2026_09" in top_ids(
        "contract end date expiration contractor"
    )
    assert "kb_access_desk_runbook_2026_10" in top_ids(
        "access request jira status blocked"
    )
    assert "kb_access_desk_runbook_2026_10" in top_ids(
        "slack post access request update"
    )
    assert top_ids("secure production access course")[0] == "tech_lms_training_v1"
    assert "kb_employee_emergency_breakglass_2026_11" in top_ids(
        "emergency exception break-glass"
    )

    staging_ids = top_ids("staging customer data")
    assert "kb_production_data_boundary_2026_11" in staging_ids
    assert "kb_staging_data_loading_2025_01" in staging_ids

    exception_ids = top_ids("temporary production exception manager approval")
    assert "kb_employee_emergency_breakglass_2026_11" in exception_ids
    assert "kb_department_manager_prod_access_2025_10" in exception_ids


@pytest.mark.parametrize(
    "task_name", ["access_provisioning_001", "access_provisioning_002"]
)
def test_access_opening_does_not_disclose_worker_type(task_name):
    task = _task(task_name)
    opening = task["user_scenario"]["instructions"]["reason_for_call"].lower()

    assert "contractor" not in opening
    assert "employee" not in opening
    assert "onboarding paperwork" in opening


def test_access_task_one_user_keeps_staging_sufficient_ground_truth():
    task = _task("access_provisioning_001")
    instructions = task["user_scenario"]["instructions"]
    scenario = (
        f"{instructions['known_info']} {instructions['task_instructions']}".lower()
    )

    assert "staging contains everything" in scenario
    assert "staging configuration is sufficient" in scenario
    assert "never claim or imply that the work requires production" in scenario


def test_access_policy_precedence_requires_worker_type_and_recency():
    task = _task("access_provisioning_002")
    documents = {
        item["document_id"]: item
        for item in json.loads((DATA_DIR / task["knowledge_file"]).read_text())
    }
    manager_guide = documents["kb_department_manager_prod_access_2025_10"]
    production_standard = documents["kb_production_access_standard_2026_10"]
    emergency_policy = documents["kb_employee_emergency_breakglass_2026_11"]

    assert manager_guide["status"] == "current"
    assert all(
        marker not in manager_guide["title"].lower()
        for marker in ("legacy", "archive", "superseded")
    )
    assert manager_guide["updated_at"] < production_standard["updated_at"]
    assert all(
        phrase in manager_guide["content"]
        for phrase in (
            "Engineering and Research",
            "Marketing and Sales workers are not eligible",
            "Deployment Specialists",
            "customer's authorized data owner",
        )
    )
    assert all(
        phrase in emergency_policy["content"]
        for phrase in (
            "written CTO approval",
            "without current secure-production-access training",
            "Contractors",
            "ineligible",
        )
    )


def test_access_slack_history_contains_noise_and_workflow_examples():
    task = _task("access_provisioning_001")
    channels = {
        message["channel"]
        for message in task["family_world"]["slack_messages"].values()
    }

    assert {
        "eng-access-requests",
        "product",
        "eng",
        "sales",
        "marketing",
        "finance",
        "incidents",
    } <= channels
    assert len(channels) >= 10

    _, response = access_provisioning.call_tool(
        task["family_world"],
        "slack_search_messages_v1",
        json.dumps({"query": "access"}),
    )
    result = json.loads(response)
    assert "eng-access-requests" in result["channels"]
    assert result["count"] >= 3


def test_access_ticket_assertion_relies_on_structured_fields_not_prose_wording():
    task = _task("access_provisioning_001")
    final = _replay(
        access_provisioning,
        task["family_world"],
        access_provisioning.golden_call_sequence(),
    )
    final["access_requests"]["ACCESS-391"]["description"] = (
        "grp_staging_readonly granted; prod blocked."
    )

    assert access_provisioning.check_assertion(
        final, {"type": "access_existing_request_blocked_exact"}
    )


def test_production_only_access_variant_requires_no_entitlement():
    task = _task("access_provisioning_002")
    assert not access_provisioning.check_assertion(
        task["family_world"], {"type": "access_active_identity_no_entitlements"}
    )
    assert access_provisioning.golden_call_sequence("access_provisioning_002")[0] == (
        "okta_remove_user_from_group_v1",
        {
            "user_id": "okta_priya_active",
            "group_id": "grp_staging_readonly",
        },
    )
    final = _replay(
        access_provisioning,
        task["family_world"],
        access_provisioning.golden_call_sequence("access_provisioning_002"),
    )

    assert all(
        access_provisioning.check_assertion(final, assertion)
        for assertion in task["assertions"]
    )
    assert final["identities"]["okta_priya_active"]["groups"] == []
    assert final["access_requests"]["ACCESS-391"]["granted_groups"] == []
    assert final["access_requests"]["ACCESS-391"]["access_expiration"] is None


def test_production_only_access_variant_preserves_distractor_records():
    task = _task("access_provisioning_002")
    final = _replay(
        access_provisioning,
        task["family_world"],
        access_provisioning.golden_call_sequence("access_provisioning_002"),
    )
    assertion = {"type": "access_noise_records_preserved"}
    assert access_provisioning.check_assertion(final, assertion)

    mutated, _ = access_provisioning.call_tool(
        final,
        "okta_remove_user_from_group_v1",
        json.dumps(
            {
                "user_id": "okta_priya_shah",
                "group_id": "grp_salesforce_readonly",
            }
        ),
    )
    assert not access_provisioning.check_assertion(mutated, assertion)


def test_provisional_staging_grant_can_be_repaired_after_user_clarification():
    task = _task("access_provisioning_002")
    world = task["family_world"]
    assert world["identities"]["okta_priya_active"]["groups"] == [
        "grp_staging_readonly"
    ]
    assert world["access_requests"]["ACCESS-391"]["granted_groups"] == [
        "grp_staging_readonly"
    ]
    repaired, response = access_provisioning.call_tool(
        world,
        "okta_remove_user_from_group_v1",
        json.dumps(
            {
                "user_id": "okta_priya_active",
                "group_id": "grp_staging_readonly",
            }
        ),
    )

    assert json.loads(response)["user"]["groups"] == []
    assert repaired["identities"]["okta_priya_active"]["groups"] == []
    assert repaired["identities"]["okta_priya_active"]["group_expirations"] == {}


def test_production_only_variant_forbids_redundant_priya_slack_announcement():
    task = _task("access_provisioning_002")
    assertion = {"type": "access_no_priya_slack_update"}
    assert access_provisioning.check_assertion(task["family_world"], assertion)

    posted, _ = access_provisioning.call_tool(
        task["family_world"],
        "slack_chat_post_message",
        json.dumps(
            {
                "channel": "eng-access-requests",
                "text": "Priya Raman received no access; production remains blocked.",
            }
        ),
    )
    assert not access_provisioning.check_assertion(posted, assertion)


def test_provisional_slack_disposition_can_be_updated_without_a_duplicate():
    task = _task("access_provisioning_002")
    world, response = access_provisioning.call_tool(
        task["family_world"],
        "slack_chat_post_message",
        json.dumps(
            {
                "channel": "eng-access-requests",
                "text": "Priya Raman received staging read-only; production is blocked pending training.",
            }
        ),
    )
    message_id = json.loads(response)["message"]["message_id"]
    updated, response = access_provisioning.call_tool(
        world,
        "slack_chat_update_message_v1",
        json.dumps(
            {
                "channel": "eng-access-requests",
                "message_id": message_id,
                "text": "Priya Raman received no access. Production remains blocked pending training.",
            }
        ),
    )

    assert json.loads(response)["message"]["text"].startswith(
        "Priya Raman received no access"
    )
    priya_messages = [
        message
        for message in updated["slack_messages"].values()
        if "Priya Raman" in message["text"]
    ]
    assert len(priya_messages) == 1
