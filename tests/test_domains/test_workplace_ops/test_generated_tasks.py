import json
from collections import Counter
from collections.abc import Iterable
from copy import deepcopy

import pytest

from tau2.data_model.message import AssistantMessage, Message, ToolCall, UserMessage
from tau2.data_model.tasks import Action, Task
from tau2.domains.workplace_ops.environment import get_environment, get_tasks
from tau2.domains.workplace_ops.task_generator import (
    build_manifest,
    build_review_catalog,
    generate_hard_evidence_tasks,
    generate_tasks,
)
from tau2.domains.workplace_ops.utils import WORKPLACE_OPS_DATA_DIR
from tau2.evaluator.evaluator_env import EnvironmentEvaluator


def _replay_actions(task: Task, actions: Iterable[Action]) -> list[Message]:
    environment = get_environment()
    assert task.initial_state is not None
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    messages: list[Message] = []
    for action in actions:
        tool_call = ToolCall(
            id=action.action_id,
            name=action.name,
            arguments=action.arguments,
            requestor=action.requestor,
        )
        message_type = UserMessage if action.requestor == "user" else AssistantMessage
        messages.append(
            message_type(
                role=action.requestor,
                content=None,
                tool_calls=[tool_call],
            )
        )
        messages.append(environment.get_response(tool_call))
    return messages


def test_frozen_generated_collection_matches_generator() -> None:
    generated = generate_tasks()
    frozen = json.loads((WORKPLACE_OPS_DATA_DIR / "tasks_generated.json").read_text())
    frozen_manifest = json.loads(
        (WORKPLACE_OPS_DATA_DIR / "tasks_generated.manifest.json").read_text()
    )
    frozen_review = (WORKPLACE_OPS_DATA_DIR / "tasks_generated.review.md").read_text()

    assert frozen == [
        task.model_dump(mode="json", exclude_none=True) for task in generated
    ]
    assert frozen_manifest == build_manifest(generated)
    assert frozen_review == build_review_catalog(generated)


def test_frozen_hard_evidence_collection_matches_generator() -> None:
    generated = generate_hard_evidence_tasks()
    frozen = json.loads(
        (WORKPLACE_OPS_DATA_DIR / "tasks_generated_hard.json").read_text()
    )
    frozen_manifest = json.loads(
        (WORKPLACE_OPS_DATA_DIR / "tasks_generated_hard.manifest.json").read_text()
    )
    frozen_review = (
        WORKPLACE_OPS_DATA_DIR / "tasks_generated_hard.review.md"
    ).read_text()

    assert frozen == [
        task.model_dump(mode="json", exclude_none=True) for task in generated
    ]
    assert frozen_manifest == build_manifest(generated)
    assert frozen_review == build_review_catalog(generated)


def test_generated_collection_has_balanced_family_coverage() -> None:
    tasks = get_tasks("generated_review")
    families = Counter(
        next(
            component.split("=", 1)[1]
            for component in task.description.notes.split("; ")
            if component.startswith("family=")
        )
        for task in tasks
        if task.description is not None and task.description.notes is not None
    )

    assert len(tasks) == 50
    assert families == {
        "incident": 10,
        "vendor_invoice": 10,
        "customer_escalation": 10,
        "access_provisioning": 10,
        "renewal_portfolio": 10,
    }
    assert len(get_tasks("base")) == 57
    assert len(get_tasks("candidate_57")) == 57
    assert len(get_tasks("anchors_7")) == 7


def test_hard_evidence_collection_is_paired_and_dense() -> None:
    clean_tasks = get_tasks("generated_review")
    hard_tasks = get_tasks("generated_hard_evidence")

    assert len(hard_tasks) == len(clean_tasks) == 50
    for clean, hard in zip(clean_tasks, hard_tasks):
        assert clean.id.replace("_gen_", "_hard_") == hard.id
        clean_records = clean.initial_state.initialization_data.agent_data[
            "workplace_records"
        ]
        hard_records = hard.initial_state.initialization_data.agent_data[
            "workplace_records"
        ]
        assert len(hard_records) == len(clean_records) + 60
        assert all(record_id in hard_records for record_id in clean_records)
        evidence_records = [
            record
            for record_id, record in hard_records.items()
            if record_id.startswith("evidence_")
        ]
        assert len(evidence_records) == 60
        assert all(
            "decision_status" not in record["fields"]
            and "approved" not in record["fields"]
            for record in evidence_records
        )
        assert all(
            set(record["fields"])
            & {
                "workspace",
                "reporting_period",
                "legal_entity",
                "approval_state",
                "environment",
            }
            for record in evidence_records
        )
        assert clean.evaluation_criteria.communicate_info == (
            hard.evaluation_criteria.communicate_info
        )


def test_hard_incident_user_is_not_given_the_gold_severity() -> None:
    task = next(
        task
        for task in get_tasks("generated_hard_evidence")
        if task.id == "incident_triage_hard_001"
    )
    instructions = task.user_scenario.instructions
    rules = task.initial_state.initialization_data.agent_data["action_approval_rules"]
    rule = next(iter(rules.values()))

    assert "SEV-2" not in instructions.known_info
    assert "EU web checkout" not in instructions.known_info
    assert "challenge it once" in instructions.task_instructions
    assert rule["required_details"] == {}


def test_customer_tone_choices_are_exposed_in_the_agent_tool_schema() -> None:
    environment = get_environment()
    schema = environment.tools.get_tools()["propose_customer_escalation"].openai_schema

    assert schema["function"]["parameters"]["properties"]["tone"]["enum"] == [
        "concise_accountable",
        "empathetic_direct",
        "factual_accountable",
    ]


def test_private_structured_choices_are_exposed_in_agent_tool_schemas() -> None:
    tools = get_environment().tools.get_tools()
    vendor_properties = tools["propose_vendor_invoice_resolution"].openai_schema[
        "function"
    ]["parameters"]["properties"]
    renewal_properties = tools["propose_renewal_batch"].openai_schema["function"][
        "parameters"
    ]["properties"]

    assert vendor_properties["resolution"]["enum"] == [
        "request_corrected_invoice",
        "verify_bank_details",
    ]
    assert renewal_properties["priority_rule"]["const"] == ("critical_support_then_arr")
    assert renewal_properties["legal_hold_action"]["const"] == "internal_only"


@pytest.mark.parametrize(
    "task",
    [
        task
        for task in get_tasks("generated_review")
        if task.id.startswith("renewal_portfolio_gen_")
    ],
    ids=lambda task: task.id,
)
def test_renewal_owner_choice_is_user_owned_and_part_of_exact_approval(
    task: Task,
) -> None:
    assert task.initial_state is not None
    assert task.evaluation_criteria is not None
    initialization_data = task.initial_state.initialization_data
    assert initialization_data is not None
    records = initialization_data.agent_data["workplace_records"]
    unowned_ids = [
        record_id
        for record_id, record in records.items()
        if record["system"] == "CRM"
        and record["record_type"] == "account"
        and record.get("owner") is None
    ]
    assert len(unowned_ids) == 1
    expected_updates = {unowned_ids[0]: "revenue-ops@atlas.example"}

    rules = initialization_data.agent_data["action_approval_rules"]
    rule = next(iter(rules.values()))
    assert rule["required_details"]["owner_updates"] == expected_updates
    proposal = next(
        action
        for action in task.evaluation_criteria.actions or []
        if action.name == "propose_renewal_batch"
    )
    assert proposal.arguments["owner_updates"] == expected_updates

    instructions = task.user_scenario.instructions
    assert "only after the agent identifies" in instructions.task_instructions
    assert "revenue-ops@atlas.example" in instructions.known_info
    assert "regardless of ARR" in instructions.known_info


def test_renewal_proposal_rejects_an_unowned_account_without_user_choice() -> None:
    task = next(
        task
        for task in get_tasks("generated_review")
        if task.id == "renewal_portfolio_gen_001"
    )
    assert task.initial_state is not None
    assert task.evaluation_criteria is not None
    environment = get_environment()
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    proposal = next(
        action
        for action in task.evaluation_criteria.actions or []
        if action.name == "propose_renewal_batch"
    )
    arguments = deepcopy(proposal.arguments)
    arguments["owner_updates"] = {}

    with pytest.raises(ValueError, match="requester-selected owner"):
        environment.tools.propose_renewal_batch(**arguments)


@pytest.mark.parametrize(
    "task",
    [
        task
        for task in get_tasks("generated_review")
        if task.id.startswith("access_provisioning_gen_")
    ],
    ids=lambda task: task.id,
)
def test_completed_training_has_an_explicit_preservation_assertion(task: Task) -> None:
    assert task.initial_state is not None
    assert task.evaluation_criteria is not None
    records = task.initial_state.initialization_data.agent_data["workplace_records"]
    completed_ids = {
        record_id
        for record_id, record in records.items()
        if record["record_type"] == "security_training"
        and record["status"] == "completed"
    }
    preservation_ids = {
        assertion.arguments["record_id"]
        for assertion in task.evaluation_criteria.env_assertions or []
        if assertion.func_name == "assert_workplace_record"
        and assertion.arguments.get("status") == "completed"
    }
    assert preservation_ids == completed_ids


def test_access_plan_preserves_completed_training() -> None:
    task = next(
        task
        for task in get_tasks("generated_hard_evidence")
        if task.id == "access_provisioning_hard_002"
    )
    assert task.initial_state is not None
    environment = get_environment()
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    records = environment.tools.db.workplace_records
    identity = next(
        record for record in records.values() if record.record_type == "identity"
    )
    training = next(
        record
        for record in records.values()
        if record.record_type == "security_training"
        and record.fields.get("identity_record_id") == identity.record_id
    )
    original_training = deepcopy(training)

    proposal = environment.tools.propose_access_plan(
        identity_record_id=identity.record_id,
        access_level="production_standard",
    )
    assert proposal.details["training_status"] == "completed"
    assert proposal.details["training_action"] == "none"
    environment.user_tools.approve_action_proposal(proposal.proposal_id)

    with pytest.raises(ValueError, match="does not require assignment"):
        environment.tools.assign_required_training(
            proposal_id=proposal.proposal_id,
            training_record_id=training.record_id,
        )
    assert training == original_training


def test_access_plan_requires_assignment_for_incomplete_training() -> None:
    task = next(
        task
        for task in get_tasks("generated_hard_evidence")
        if task.id == "access_provisioning_hard_001"
    )
    assert task.initial_state is not None
    environment = get_environment()
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    records = environment.tools.db.workplace_records
    identity = next(
        record for record in records.values() if record.record_type == "identity"
    )
    training = next(
        record
        for record in records.values()
        if record.record_type == "security_training"
        and record.fields.get("identity_record_id") == identity.record_id
    )

    proposal = environment.tools.propose_access_plan(
        identity_record_id=identity.record_id,
        access_level="staging_read_only",
    )
    assert proposal.details["training_status"] == "not_started"
    assert proposal.details["training_action"] == "assign"
    environment.user_tools.approve_action_proposal(proposal.proposal_id)

    assigned = environment.tools.assign_required_training(
        proposal_id=proposal.proposal_id,
        training_record_id=training.record_id,
    )
    assert assigned.status == "assigned"


@pytest.mark.parametrize(
    "task", get_tasks("generated_review"), ids=lambda task: task.id
)
def test_generated_reference_end_state_passes(task: Task) -> None:
    assert task.evaluation_criteria is not None
    messages = _replay_actions(task, task.evaluation_criteria.actions or [])

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 1.0
    assert result.db_check is not None and result.db_check.db_match
    assert result.env_assertions is not None
    assert all(check.met for check in result.env_assertions)


@pytest.mark.parametrize(
    "task", get_tasks("generated_hard_evidence"), ids=lambda task: task.id
)
def test_hard_evidence_reference_end_state_passes(task: Task) -> None:
    assert task.evaluation_criteria is not None
    messages = _replay_actions(task, task.evaluation_criteria.actions or [])

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 1.0
    assert result.db_check is not None and result.db_check.db_match
    assert result.env_assertions is not None
    assert all(check.met for check in result.env_assertions)


def test_renewal_end_state_is_independent_of_unordered_inputs_and_creation_order() -> (
    None
):
    task = next(
        task
        for task in get_tasks("generated_review")
        if task.id == "renewal_portfolio_gen_003"
    )
    assert task.evaluation_criteria is not None
    actions = deepcopy(task.evaluation_criteria.actions or [])

    proposal = next(
        action for action in actions if action.name == "propose_renewal_batch"
    )
    proposal.arguments["internal_only_account_ids"].reverse()
    proposal.arguments["excluded_account_ids"].reverse()

    follow_up_indexes = [
        index
        for index, action in enumerate(actions)
        if action.name == "create_renewal_follow_up"
    ]
    reversed_follow_ups = [actions[index] for index in follow_up_indexes][::-1]
    for index, action in zip(follow_up_indexes, reversed_follow_ups):
        actions[index] = action

    messages = _replay_actions(task, actions)
    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 1.0
    assert result.db_check is not None and result.db_check.db_match


@pytest.mark.parametrize(
    "task", get_tasks("generated_review"), ids=lambda task: task.id
)
def test_generated_task_fails_when_final_internal_update_is_missing(task: Task) -> None:
    assert task.evaluation_criteria is not None
    actions = task.evaluation_criteria.actions or []
    assert actions[-1].name == "post_approved_workflow_update"
    messages = _replay_actions(task, actions[:-1])

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 0.0
    assert result.db_check is not None and not result.db_check.db_match


@pytest.mark.parametrize(
    "task_id",
    [
        "incident_triage_gen_001",
        "vendor_invoice_gen_001",
        "customer_escalation_gen_001",
        "access_provisioning_gen_001",
        "renewal_portfolio_gen_001",
    ],
)
def test_generated_user_rejects_proposal_that_violates_private_rule(
    task_id: str,
) -> None:
    task = next(task for task in get_tasks("generated_review") if task.id == task_id)
    assert task.initial_state is not None
    assert task.evaluation_criteria is not None
    environment = get_environment()
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    rule = next(iter(environment.tools.db.action_approval_rules.values()))
    details = dict(rule.required_details)
    key, expected = next(iter(rule.required_details.items()))
    details[key] = not expected if isinstance(expected, bool) else f"wrong-{expected}"
    proposal = environment.tools.create_action_proposal(
        proposal_type=rule.proposal_type,
        title=rule.title,
        details=details,
    )

    with pytest.raises(ValueError, match=f"{key} must be"):
        environment.user_tools.approve_action_proposal(proposal.proposal_id)

    assert not proposal.approved_by_user


def test_generated_user_prompts_do_not_leak_environment_ids() -> None:
    for task in get_tasks("generated_review"):
        instructions = str(task.user_scenario.instructions)
        assert "action_proposal_1" not in instructions
        assert "generated_record_" not in instructions
        assert "crm_" not in instructions
        assert "linear_" not in instructions


def test_generated_search_accepts_natural_phrasing_and_record_type_aliases() -> None:
    task = next(
        task
        for task in get_tasks("generated_review")
        if task.id == "incident_triage_gen_001"
    )
    assert task.initial_state is not None
    environment = get_environment()
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )

    signals = environment.tools.search_workplace_records(
        query="card authorization service status", system="Datadog"
    )
    schedules = environment.tools.search_workplace_records(
        query="card authorization responder",
        system="PagerDuty",
        record_type="on-call",
    )

    assert any(record.status == "current" for record in signals)
    assert {record.record_type for record in schedules} == {"on_call_schedule"}


def test_hard_evidence_search_is_bounded_but_authority_is_retrievable() -> None:
    task = next(
        task
        for task in get_tasks("generated_hard_evidence")
        if task.id == "incident_triage_hard_001"
    )
    environment = get_environment()
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )

    broad = environment.tools.search_workplace_records(query="Card authorization")
    signals = environment.tools.search_workplace_records(
        query="Card authorization current impact",
        system="Datadog",
        status="current",
        limit=10,
    )
    policy = environment.tools.search_workplace_records(
        query="Incident severity policy",
        system="Knowledge",
        status="current",
        limit=10,
    )

    assert len(broad) == 10
    assert any(
        record.record_id == "signal_card_authorization_impact" for record in signals
    )
    assert any(record.status == "current" for record in policy)

    with pytest.raises(ValueError, match="between 1 and 10"):
        environment.tools.search_workplace_records(query="incident", limit=11)
