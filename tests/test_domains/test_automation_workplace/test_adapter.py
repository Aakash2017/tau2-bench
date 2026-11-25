import json

from tau2.data_model.message import AssistantMessage, ToolCall
from tau2.data_model.tasks import EvaluationCriteria, RewardType
from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.prompts import USER_SIMULATION_GUIDELINES
from tau2.evaluator.evaluator_env import EnvironmentEvaluator
from tau2.runner.build import build_user


def _initialized_environment(task_index: int = 0):
    task = get_tasks(None)[task_index]
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return task, environment


def test_catalog_preserves_source_control_and_adds_interactive_canonicals():
    tasks = get_tasks("source_control")
    all_tasks = get_tasks(None)

    assert len(tasks) == 10
    assert sum(len(task.evaluation_criteria.env_assertions) for task in tasks) == 158
    assert len(all_tasks) == 26
    assert len(get_tasks("interactive_pilot")) == 1
    assert len(get_tasks("interactive_canonical")) == 16
    assert all(
        task.evaluation_criteria.reward_basis == [RewardType.ENV_ASSERTION]
        for task in tasks
    )
    assert all(task.evaluation_criteria.actions is None for task in tasks)
    assert all(task.evaluation_criteria.communicate_info is None for task in tasks)


def test_agent_surface_is_api_native_and_schema_discoverable():
    environment = get_environment()

    assert {tool.name for tool in environment.get_tools()} == {
        "api_search",
        "api_fetch",
        "base64_encode",
        "knowledge_search",
        "unlock_discoverable_tool",
        "call_discoverable_tool",
    }
    result = json.loads(
        environment.use_tool(
            "api_search",
            query="Salesforce update opportunity",
            top_k=1,
        )
    )

    assert result["count"] == 1
    assert result["results"][0]["method"] == "PATCH"
    assert result["results"][0]["url"].startswith("https://")


def test_real_url_write_mutates_pydantic_world_and_satisfies_assertion():
    _, environment = _initialized_environment()
    endpoint = json.loads(
        environment.use_tool(
            "api_search",
            query="Salesforce update opportunity",
            top_k=1,
        )
    )["results"][0]

    assert not environment.tools.assert_source_assertion(0)
    response = environment.use_tool(
        "api_fetch",
        method=endpoint["method"],
        url=endpoint["url"].replace("{id}", "006xx000004MER1"),
        body=json.dumps({"StageName": "Closed Won"}),
    )

    assert response == "{}"
    assert environment.tools.assert_source_assertion(0)
    opportunity = next(
        record
        for record in environment.tools.db.world["salesforce"]["opportunities"]
        if record["id"] == "006xx000004MER1"
    )
    assert opportunity["stage_name"] == "Closed Won"


def test_disconnected_service_returns_credentials_error_without_side_effect():
    _, environment = _initialized_environment()
    original_stages = {
        record["id"]: record["stage_name"]
        for record in environment.tools.db.world["salesforce"]["opportunities"]
    }

    response = json.loads(
        environment.use_tool(
            "api_fetch",
            method="GET",
            url="https://api.zoom.us/v2/users/me/meetings",
        )
    )

    assert response["error"]["code"] == 401
    assert "No zoom account is connected" in response["error"]["message"]
    assert {
        record["id"]: record["stage_name"]
        for record in environment.tools.db.world["salesforce"]["opportunities"]
    } == original_stages
    assert environment.tools.db.world["zoom"]["meetings"] == []


def test_mutating_api_call_replays_into_exact_state_evaluator():
    task, environment = _initialized_environment()
    read_call = ToolCall(
        id="read-opportunity",
        name="api_fetch",
        arguments={
            "method": "GET",
            "url": "https://yourinstance.salesforce.com/services/data/v61.0/query",
            "params": json.dumps(
                {
                    "q": (
                        "SELECT FIELDS(ALL) FROM Opportunity WHERE Id = "
                        "'006xx000004MER1' LIMIT 1"
                    )
                }
            ),
        },
    )
    read_response = environment.get_response(read_call)
    endpoint = json.loads(
        environment.use_tool(
            "api_search",
            query="Salesforce update opportunity",
            top_k=1,
        )
    )["results"][0]
    call = ToolCall(
        id="update-opportunity",
        name="api_fetch",
        arguments={
            "method": endpoint["method"],
            "url": endpoint["url"].replace("{id}", "006xx000004MER1"),
            "body": json.dumps({"StageName": "Closed Won"}),
        },
    )
    response = environment.get_response(call)
    one_assertion_task = task.model_copy(
        update={
            "evaluation_criteria": EvaluationCriteria(
                env_assertions=[task.evaluation_criteria.env_assertions[0]],
                reward_basis=[RewardType.ENV_ASSERTION],
            )
        }
    )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment,
        task=one_assertion_task,
        full_trajectory=[
            AssistantMessage(role="assistant", tool_calls=[read_call]),
            read_response,
            AssistantMessage(role="assistant", tool_calls=[call]),
            response,
        ],
    )

    assert reward.reward == 1.0
    assert reward.env_assertions[0].met


def test_user_overlay_withholds_system_facts_and_has_no_user_tools():
    tasks = get_tasks("source_control")

    for task in tasks:
        instructions = task.user_scenario.instructions
        assert "Open by saying only" in instructions.reason_for_call
        assert "connected workplace apps" in instructions.unknown_info
        assert (
            "Do not quote the hidden source request" in instructions.task_instructions
        )
        assert task.user_tools == []


def test_runtime_user_receives_workplace_specific_system_prompt():
    task = get_tasks(None)[0]
    user = build_user(
        user_name="user_simulator",
        environment=get_environment(),
        task=task,
        llm="test-model",
    )

    assert USER_SIMULATION_GUIDELINES in user.system_prompt
    assert 'vague completion claims such as "done"' in user.system_prompt
    assert task.user_scenario.persona in user.system_prompt
    assert task.user_scenario.instructions.reason_for_call in user.system_prompt
