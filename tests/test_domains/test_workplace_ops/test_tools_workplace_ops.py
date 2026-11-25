from collections.abc import Iterable

import pytest

from tau2.data_model.message import AssistantMessage, Message, ToolCall, UserMessage
from tau2.data_model.simulation import TextRunConfig
from tau2.data_model.tasks import Action, Task
from tau2.domains.workplace_ops.environment import get_environment, get_tasks
from tau2.domains.workplace_ops.prompts import USER_SIMULATION_GUIDELINES
from tau2.evaluator.evaluator_env import EnvironmentEvaluator
from tau2.runner.build import build_user
from tau2.runner.helpers import get_info


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


@pytest.fixture
def task() -> Task:
    return next(task for task in get_tasks(None) if task.id == "workplace_kickoff_001")


@pytest.fixture
def hard_task() -> Task:
    return next(task for task in get_tasks(None) if task.id == "workplace_kickoff_002")


def test_documents_expose_current_and_superseded_briefs() -> None:
    environment = get_environment()

    documents = environment.tools.search_documents("Nimbus Project Brief")

    assert [(document.version, document.status) for document in documents] == [
        (1, "superseded"),
        (2, "current"),
    ]
    assert documents[1].external_pilot == "confirmed"
    assert documents[1].required_functions == [
        "Product",
        "Engineering",
        "Design",
        "Legal",
    ]


def test_user_simulator_is_framed_as_an_internal_employee() -> None:
    user = build_user(
        "user_simulator",
        get_environment(),
        get_tasks()[0],
        llm="gpt-4.1-mini",
        llm_args={"temperature": 0},
    )

    assert "internal workplace chat" in user.system_prompt
    assert "customer service representative" not in user.system_prompt
    assert "never invent a proposal ID" in user.system_prompt
    assert "A revised proposal is a new approval attempt" in user.system_prompt


def test_hard_user_simulator_rejects_false_waiting_premise() -> None:
    hard_task = next(
        task for task in get_tasks(None) if task.id == "workplace_kickoff_002"
    )
    user = build_user(
        "user_simulator",
        get_environment(),
        hard_task,
        llm="gpt-4.1-mini",
        llm_args={"temperature": 0},
    )

    assert "do not wait or ask it to monitor clearance" in user.system_prompt
    assert "ask only for confirmation of the missing item" in user.system_prompt
    assert "Camille Okafor" not in user.system_prompt
    assert "2026-11-11T10:00:00-08:00" not in user.system_prompt


def test_user_simulator_guidelines_are_recorded_in_run_metadata() -> None:
    info = get_info(TextRunConfig(domain="workplace_ops"))

    assert info.user_info.global_simulation_guidelines == USER_SIMULATION_GUIDELINES


def test_user_approval_is_required_before_scheduling() -> None:
    environment = get_environment()
    proposal = environment.tools.create_meeting_proposal(
        title="Nimbus Project Kickoff",
        start="2026-11-11T10:00:00-08:00",
        end="2026-11-11T10:45:00-08:00",
        attendees=[
            "priya@atlas.example",
            "maya@atlas.example",
            "jordan@atlas.example",
            "mateo@atlas.example",
        ],
    )

    assert proposal.proposal_id == "proposal_1"
    with pytest.raises(ValueError, match="has not been approved"):
        environment.tools.schedule_approved_meeting(proposal.proposal_id)

    pending = environment.user_tools.get_pending_meeting_proposals()
    assert pending == [proposal]
    environment.user_tools.approve_meeting_proposal(proposal.proposal_id)
    event = environment.tools.schedule_approved_meeting(proposal.proposal_id)

    assert event.event_id == "event_proposal_1"
    assert event.attendees == sorted(proposal.attendees)


def test_user_constraints_reject_bad_proposals_without_leaving_stale_drafts() -> None:
    environment = get_environment()
    internal_attendees = [
        "priya@atlas.example",
        "maya@atlas.example",
        "jordan@atlas.example",
        "mateo@atlas.example",
    ]
    proposal = environment.tools.create_meeting_proposal(
        title="Nimbus Project Kickoff",
        start="2026-11-18T10:00:00-08:00",
        end="2026-11-18T10:45:00-08:00",
        attendees=internal_attendees,
    )

    with pytest.raises(ValueError, match="must be within"):
        environment.user_tools.approve_meeting_proposal(proposal.proposal_id)

    revised = environment.tools.create_meeting_proposal(
        title="Nimbus Project Kickoff",
        start="2026-11-11T10:00:00-08:00",
        end="2026-11-11T11:00:00-08:00",
        attendees=internal_attendees,
    )
    assert revised.proposal_id == proposal.proposal_id
    with pytest.raises(ValueError, match="must last 45 minutes"):
        environment.user_tools.approve_meeting_proposal(revised.proposal_id)

    revised = environment.tools.create_meeting_proposal(
        title="Nimbus Project Kickoff",
        start="2026-11-11T10:00:00-08:00",
        end="2026-11-11T10:45:00-08:00",
        attendees=[*internal_attendees, "taylor@pilot.example"],
    )
    with pytest.raises(ValueError, match="must not be invited"):
        environment.user_tools.approve_meeting_proposal(revised.proposal_id)

    revised = environment.tools.create_meeting_proposal(
        title="Nimbus Project Kickoff",
        start="2026-11-11T10:00:00-08:00",
        end="2026-11-11T10:45:00-08:00",
        attendees=internal_attendees,
    )
    environment.user_tools.approve_meeting_proposal(revised.proposal_id)

    assert list(environment.tools.db.meeting_proposals) == ["proposal_1"]
    assert environment.tools.db.meeting_proposals["proposal_1"].approved_by_user


def test_reference_end_state_passes_all_environment_checks(task: Task) -> None:
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


def test_equivalent_write_path_passes_without_reference_reads(task: Task) -> None:
    writes_only = [
        action
        for action in task.evaluation_criteria.actions
        if action.name
        not in {
            "search_documents",
            "list_employees",
            "get_calendar_availability",
            "get_pending_meeting_proposals",
        }
    ]
    messages = _replay_actions(task, writes_only)

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 1.0
    assert result.db_check is not None and result.db_check.db_match


def test_corrected_early_guess_passes_when_final_state_is_exact(task: Task) -> None:
    wrong_draft = Action(
        action_id="early_guess",
        requestor="assistant",
        name="create_meeting_proposal",
        arguments={
            "title": "Nimbus Project Kickoff",
            "start": "2026-11-11T10:00:00-08:00",
            "end": "2026-11-11T10:30:00-08:00",
            "attendees": [
                "maya@atlas.example",
                "priya@atlas.example",
                "mateo@atlas.example",
                "jordan@atlas.example",
            ],
        },
    )
    actions = []
    for action in task.evaluation_criteria.actions:
        if action.name == "create_meeting_proposal":
            actions.append(wrong_draft)
        actions.append(action)

    messages = _replay_actions(task, actions)
    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 1.0
    assert result.db_check is not None and result.db_check.db_match


def test_extra_downstream_write_fails_exact_state_check(task: Task) -> None:
    messages = _replay_actions(task, task.evaluation_criteria.actions)
    environment = get_environment()
    environment.set_state(None, None, messages)
    tool_call = ToolCall(
        id="extra_write",
        name="create_project_task",
        arguments={
            "title": "Unrequested Nimbus follow-up",
            "assignee": "maya@atlas.example",
            "due_date": "2026-11-12",
        },
        requestor="assistant",
    )
    messages.extend(
        [
            AssistantMessage(role="assistant", content=None, tool_calls=[tool_call]),
            environment.get_response(tool_call),
        ]
    )

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=task,
        full_trajectory=messages,
    )

    assert result.reward == 0.0
    assert result.db_check is not None and not result.db_check.db_match


def test_hard_task_initial_state_has_real_tradeoff_and_decoys(
    hard_task: Task,
) -> None:
    environment = get_environment()
    initial_state = hard_task.initial_state
    assert initial_state is not None
    environment.set_state(
        initialization_data=initial_state.initialization_data,
        initialization_actions=initial_state.initialization_actions,
        message_history=initial_state.message_history or [],
    )

    briefs = environment.tools.search_documents("Nimbus Project Brief")
    assert [(brief.version, brief.status) for brief in briefs] == [
        (1, "superseded"),
        (2, "superseded"),
        (3, "current"),
    ]
    records = environment.tools.search_project_records("Nimbus")
    assert any(
        record.record_type == "delegation"
        and record.status == "current"
        and record.delegate_email == "camille@atlas.example"
        for record in records
    )
    assert any(
        record.record_type == "delegation"
        and record.status == "expired"
        and record.delegate_email == "avery@atlas.example"
        for record in records
    )
    assert any(
        record.record_type == "clearance"
        and record.status == "pending"
        and record.clearance_status == "pending"
        for record in records
    )
    assert any(
        record.record_type == "clearance"
        and record.status == "superseded"
        and record.clearance_status == "approved"
        for record in records
    )

    availability = environment.tools.get_calendar_availability(
        emails=[
            "maya@atlas.example",
            "priya@atlas.example",
            "mateo@atlas.example",
            "jordan@atlas.example",
            "camille@atlas.example",
        ],
        start="2026-11-11T08:00:00-08:00",
        end="2026-11-12T17:00:00-08:00",
    )
    assert {
        "start": "2026-11-11T08:00:00-08:00",
        "end": "2026-11-11T12:00:00-08:00",
    } in availability["jordan@atlas.example"]
    assert not any(
        interval["start"] < "2026-11-11T10:45:00-08:00"
        and interval["end"] > "2026-11-11T10:00:00-08:00"
        for interval in availability["camille@atlas.example"]
    )


def test_hard_reference_end_state_passes(hard_task: Task) -> None:
    messages = _replay_actions(hard_task, hard_task.evaluation_criteria.actions)

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=hard_task,
        full_trajectory=messages,
    )

    assert result.reward == 1.0
    assert result.db_check is not None and result.db_check.db_match
    assert result.env_assertions is not None
    assert all(check.met for check in result.env_assertions)


def test_hard_user_approval_allows_non_gold_conditional_option(
    hard_task: Task,
) -> None:
    environment = get_environment()
    initial_state = hard_task.initial_state
    assert initial_state is not None
    environment.set_state(
        initialization_data=initial_state.initialization_data,
        initialization_actions=initial_state.initialization_actions,
        message_history=initial_state.message_history or [],
    )
    proposal = environment.tools.create_meeting_proposal(
        title="Nimbus Project Kickoff",
        start="2026-11-12T14:00:00-08:00",
        end="2026-11-12T14:45:00-08:00",
        attendees=[
            "maya@atlas.example",
            "priya@atlas.example",
            "mateo@atlas.example",
            "jordan@atlas.example",
        ],
    )

    environment.user_tools.approve_meeting_proposal(proposal.proposal_id)

    assert proposal.approved_by_user
    assert proposal.start == "2026-11-12T14:00:00-08:00"


@pytest.mark.parametrize(
    "omitted_action",
    [
        "update_engineering_task",
        "update_legal_task",
        "update_design_task",
        "create_product_task",
        "update_project_milestone",
        "post_project_update",
    ],
)
def test_hard_task_fails_when_downstream_work_is_missing(
    hard_task: Task, omitted_action: str
) -> None:
    actions = []
    for action in hard_task.evaluation_criteria.actions:
        label = action.name
        if action.name == "update_project_task":
            label = {
                "task_1": "update_engineering_task",
                "task_2": "update_legal_task",
                "task_4": "update_design_task",
            }[action.arguments["task_id"]]
        if action.name == "create_project_task":
            label = "create_product_task"
        if label != omitted_action:
            actions.append(action)
    messages = _replay_actions(hard_task, actions)

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=hard_task,
        full_trajectory=messages,
    )

    assert result.reward == 0.0
    assert result.db_check is not None and not result.db_check.db_match


def test_hard_task_wrong_legal_employee_is_not_repaired_by_approval(
    hard_task: Task,
) -> None:
    actions = []
    for action in hard_task.evaluation_criteria.actions:
        action = action.model_copy(deep=True)
        if action.name == "create_meeting_proposal":
            action.arguments["attendees"] = [
                "maya@atlas.example",
                "priya@atlas.example",
                "mateo@atlas.example",
                "avery@atlas.example",
            ]
        if (
            action.name == "update_project_task"
            and action.arguments["task_id"] == "task_2"
        ):
            action.arguments["assignee"] = "avery@atlas.example"
        actions.append(action)
    messages = _replay_actions(hard_task, actions)

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=hard_task,
        full_trajectory=messages,
    )

    assert result.reward == 0.0
    assert result.db_check is not None and not result.db_check.db_match


def test_hard_task_cannot_reopen_completed_prior_cycle_agenda(
    hard_task: Task,
) -> None:
    actions = []
    for action in hard_task.evaluation_criteria.actions:
        if action.name == "create_project_task":
            actions.append(
                Action(
                    action_id="reopen_old_agenda",
                    requestor="assistant",
                    name="update_project_task",
                    arguments={
                        "task_id": "task_3",
                        "due_date": "2026-11-10",
                        "status": "open",
                    },
                )
            )
            continue
        action = action.model_copy(deep=True)
        if action.name == "post_project_update":
            action.arguments["preparation_task_ids"] = [
                "task_1",
                "task_2",
                "task_3",
                "task_4",
            ]
        actions.append(action)
    messages = _replay_actions(hard_task, actions)

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=hard_task,
        full_trajectory=messages,
    )

    assert result.reward == 0.0
    assert result.db_check is not None and not result.db_check.db_match


def test_hard_task_corrected_early_option_passes(hard_task: Task) -> None:
    wrong_draft = Action(
        action_id="hard_early_thursday",
        requestor="assistant",
        name="create_meeting_proposal",
        arguments={
            "title": "Nimbus Project Kickoff",
            "start": "2026-11-12T14:00:00-08:00",
            "end": "2026-11-12T14:45:00-08:00",
            "attendees": [
                "maya@atlas.example",
                "priya@atlas.example",
                "mateo@atlas.example",
                "jordan@atlas.example",
            ],
        },
    )
    actions = []
    for action in hard_task.evaluation_criteria.actions:
        if action.name == "create_meeting_proposal":
            actions.append(wrong_draft)
        actions.append(action)
    messages = _replay_actions(hard_task, actions)

    result = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=hard_task,
        full_trajectory=messages,
    )

    assert result.reward == 1.0
    assert result.db_check is not None and result.db_check.db_match
