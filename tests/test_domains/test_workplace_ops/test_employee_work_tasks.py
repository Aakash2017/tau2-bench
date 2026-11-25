from collections.abc import Iterable

import pytest

from tau2.data_model.message import AssistantMessage, Message, ToolCall, UserMessage
from tau2.data_model.tasks import Action, Task
from tau2.domains.workplace_ops.environment import get_environment, get_tasks
from tau2.evaluator.evaluator_env import EnvironmentEvaluator

EMPLOYEE_WORK_TASK_IDS = [
    "incident_triage_001",
    "vendor_invoice_001",
    "customer_escalation_001",
    "access_provisioning_001",
    "renewal_portfolio_001",
]


def _get_task(task_id: str) -> Task:
    return next(task for task in get_tasks(None) if task.id == task_id)


def _replay_actions(task: Task, actions: Iterable[Action]) -> list[Message]:
    environment = get_environment()
    initial_state = task.initial_state
    environment.set_state(
        initialization_data=(
            initial_state.initialization_data if initial_state is not None else None
        ),
        initialization_actions=(
            initial_state.initialization_actions if initial_state is not None else None
        ),
        message_history=(
            initial_state.message_history
            if initial_state is not None and initial_state.message_history is not None
            else []
        ),
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


@pytest.mark.parametrize("task_id", EMPLOYEE_WORK_TASK_IDS)
def test_employee_work_reference_end_state_passes(task_id: str) -> None:
    task = _get_task(task_id)
    messages = _replay_actions(task, task.evaluation_criteria.actions)

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
    ("task_id", "omitted_action_id"),
    [
        ("incident_triage_001", "incident_9"),
        ("vendor_invoice_001", "invoice_8"),
        ("customer_escalation_001", "customer_8"),
        ("access_provisioning_001", "access_8"),
        ("renewal_portfolio_001", "renewal_15"),
    ],
)
def test_employee_work_task_fails_when_downstream_record_is_missing(
    task_id: str, omitted_action_id: str
) -> None:
    task = _get_task(task_id)
    actions = [
        action
        for action in task.evaluation_criteria.actions
        if action.action_id != omitted_action_id
    ]
    messages = _replay_actions(task, actions)

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 0.0
    assert result.db_check is not None and not result.db_check.db_match


def test_external_messages_require_exact_user_approval() -> None:
    task = _get_task("customer_escalation_001")
    environment = get_environment()
    assert task.initial_state is not None
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    proposal = environment.tools.create_action_proposal(
        proposal_type="customer_escalation",
        title="Acme customer recovery plan",
        details={
            "credit_amount": 2500,
            "tone": "concise_accountable",
            "external_messages": [
                {
                    "system": "Email",
                    "recipient": "jules.martin@acme.example",
                    "subject": "Acme outage follow-up",
                    "facts": {"service_credit": 2500},
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="has not been approved"):
        environment.tools.send_approved_external_messages(proposal.proposal_id)

    pending = environment.user_tools.get_pending_action_proposals()
    assert pending == [proposal]
    environment.user_tools.approve_action_proposal(proposal.proposal_id)
    messages = environment.tools.send_approved_external_messages(proposal.proposal_id)

    assert [message.recipient for message in messages] == ["jules.martin@acme.example"]


def test_user_private_constraints_reject_wrong_vendor_resolution() -> None:
    task = _get_task("vendor_invoice_001")
    environment = get_environment()
    assert task.initial_state is not None
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    proposal = environment.tools.create_action_proposal(
        proposal_type="vendor_invoice_resolution",
        title="Northstar invoice exception",
        details={
            "resolution": "amend_purchase_order",
            "authorized_amount": 48200,
            "invoice_action": "pay",
            "bank_change": True,
        },
    )

    with pytest.raises(ValueError, match="request_corrected_invoice"):
        environment.user_tools.approve_action_proposal(proposal.proposal_id)

    assert not proposal.approved_by_user


def test_production_access_is_blocked_while_training_is_incomplete() -> None:
    task = _get_task("access_provisioning_001")
    environment = get_environment()
    assert task.initial_state is not None
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )
    proposal = environment.tools.create_action_proposal(
        proposal_type="access_plan",
        title="Rowan compliant onboarding access",
        details={"access_level": "production_admin", "production_access": True},
    )
    proposal.approved_by_user = True

    with pytest.raises(ValueError, match="before training completion"):
        environment.tools.provision_approved_access(
            proposal_id=proposal.proposal_id,
            identity_record_id="identity_rowan_current",
            access_level="production_admin",
            expires_on="2027-02-08",
        )

    assert environment.tools.db.access_grants == []


def test_incident_records_expose_stale_alarm_and_current_scope() -> None:
    task = _get_task("incident_triage_001")
    environment = get_environment()
    assert task.initial_state is not None
    environment.set_state(
        task.initial_state.initialization_data,
        task.initial_state.initialization_actions,
        task.initial_state.message_history or [],
    )

    records = environment.tools.search_workplace_records(
        query="payments", system="Datadog"
    )

    assert {record.record_id for record in records} == {
        "dd_global_stale",
        "dd_eu_checkout",
        "dd_mobile_healthy",
        "dd_api_healthy",
    }
    assert environment.tools.get_workplace_record("dd_eu_checkout").status == "current"
