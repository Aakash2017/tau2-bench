import json

import pytest

from tau2.data_model.tasks import RewardType
from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.utils import (
    AUTOMATION_WORKPLACE_INTERACTIVE_DIR,
)
from tau2.runner.build import build_user
from tau2.utils import load_file


@pytest.fixture
def pilot():
    task = get_tasks("interactive_pilot")[0]
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return task, environment


def _unlock(environment, *names: str) -> None:
    for name in names:
        environment.use_tool("unlock_discoverable_tool", discoverable_tool_name=name)


def _call(environment, name: str, arguments: dict) -> dict:
    return json.loads(
        environment.use_tool(
            "call_discoverable_tool",
            discoverable_tool_name=name,
            arguments=json.dumps(arguments),
        )
    )


def _complete_golden_state(environment) -> None:
    operations = (
        "linear_update_issue_graphql",
        "pagerduty_create_incident_v2",
        "statuspage_create_incident_v1",
        "linear_create_issue_graphql",
        "slack_chat_post_message",
    )
    _unlock(environment, *operations)
    _call(
        environment,
        "linear_update_issue_graphql",
        {
            "issue_id": "lin_incident_payments",
            "state": "Investigating",
            "assignee_id": "usr_nina",
            "severity": "SEV-2",
            "scope": "EU web checkout",
            "source_signal_ids": [
                "dd_eu_checkout",
                "dd_mobile_healthy",
                "dd_api_healthy",
            ],
            "description": (
                "Current impact is limited to EU web checkout. Mobile and API "
                "payments are healthy."
            ),
        },
    )
    _call(
        environment,
        "pagerduty_create_incident_v2",
        {
            "title": "SEV-2: EU web checkout payment degradation",
            "urgency": "high",
            "assignee_id": "usr_nina",
            "incident_key": "PAY-842",
        },
    )
    _call(
        environment,
        "statuspage_create_incident_v1",
        {
            "page_id": "page_payments",
            "name": "EU web checkout payment degradation",
            "status": "investigating",
            "impact": "minor",
            "body": (
                "We are investigating payment failures affecting EU web checkout. "
                "Mobile and API payments remain healthy."
            ),
            "component_ids": ["cmp_eu_web_checkout"],
        },
    )
    _call(
        environment,
        "linear_create_issue_graphql",
        {
            "team_id": "team_payments",
            "title": "RCA: PAY-842 EU web checkout payment degradation",
            "state": "Todo",
            "assignee_id": "usr_nina",
            "due_date": "2026-11-17",
            "related_issue_id": "lin_incident_payments",
            "labels": ["rca"],
            "description": "Complete RCA for PAY-842.",
        },
    )
    _call(
        environment,
        "slack_chat_post_message",
        {
            "channel": "inc-payments",
            "text": (
                "SEV-2 EU web checkout degradation is tracked in PAY-842 and "
                "has a measured 12% error rate. It is owned by Nina. Mobile and "
                "API payments are healthy. Nina was "
                "paged. The stale aggregate is not a global outage. RCA is due "
                "2026-11-17."
            ),
        },
    )


def test_pilot_is_exact_state_only_and_user_has_no_tools(pilot):
    task, _ = pilot

    assert task.id == "automation_workplace__interactive__incident_triage_001"
    assert task.user_tools == []
    assert task.evaluation_criteria.actions is None
    assert task.evaluation_criteria.communicate_info is None
    assert task.evaluation_criteria.reward_basis == [RewardType.ENV_ASSERTION]
    assert len(task.evaluation_criteria.env_assertions) == 9


def test_dataset_manifest_and_remaining_task_families_are_reviewable():
    manifest = load_file(AUTOMATION_WORKPLACE_INTERACTIVE_DIR / "manifest.json")
    families = load_file(AUTOMATION_WORKPLACE_INTERACTIVE_DIR / "task_families.json")

    assert manifest["task_count"] == 16
    assert manifest["knowledge_document_count"] == 94
    assert manifest["knowledge_bundle_count"] == 7
    assert manifest["planned_dataset"] == {
        "family_count": 6,
        "logical_tasks_per_family": 8,
        "logical_task_count": 48,
        "surface_instances_per_logical_task": 2,
        "planned_episode_count": 96,
        "primary_aggregation": "macro_average_over_families",
    }
    assert [family["family_id"] for family in families] == [
        "incident_triage",
        "vendor_invoice",
        "customer_escalation",
        "access_provisioning",
        "renewal_portfolio",
        "meeting_coordination",
    ]
    assert families[0]["status"] == "implemented_pilot"
    assert all(family["status"] == "implemented_canonical" for family in families[1:])


def test_pilot_user_receives_workplace_simulator_prompt(pilot):
    task, _ = pilot
    user = build_user(
        user_name="user_simulator",
        environment=get_environment(),
        task=task,
        llm="test-model",
    )

    assert "Acknowledge or approve a proposed course of action in prose" in (
        user.system_prompt
    )
    assert task.user_scenario.persona in user.system_prompt
    assert "Do not use tools or invent system facts" in user.system_prompt


def test_bm25_search_exposes_versioned_policy_and_technical_tool_docs(pilot):
    _, environment = pilot

    policy_results = environment.use_tool(
        "knowledge_search", query="production incident severity SEV-1 SEV-2", top_k=5
    )
    datadog_results = environment.use_tool(
        "knowledge_search", query="Datadog metrics query API", top_k=3
    )

    assert {result["status"] for result in policy_results} == {
        "current",
        "superseded",
    }
    assert any(
        "datadog_query_metrics_v1" in result["content"] for result in datadog_results
    )


def test_discoverable_operation_must_be_unlocked_and_returns_live_state(pilot):
    _, environment = pilot

    with pytest.raises(ValueError, match="is locked"):
        _call(
            environment,
            "datadog_query_metrics_v1",
            {
                "query": "payments",
                "from_time": "2026-11-08T00:00:00-08:00",
                "to_time": "2026-11-11T09:05:00-08:00",
            },
        )

    _unlock(environment, "datadog_query_metrics_v1")
    response = _call(
        environment,
        "datadog_query_metrics_v1",
        {
            "query": "payments",
            "from_time": "2026-11-08T00:00:00-08:00",
            "to_time": "2026-11-11T09:05:00-08:00",
        },
    )

    assert {series["signal_id"] for series in response["series"]} == {
        "dd_global_stale",
        "dd_eu_checkout",
        "dd_mobile_healthy",
        "dd_api_healthy",
        "dd_us_authorization_latency",
        "dd_apac_settlement_backlog",
        "dd_staging_checkout",
    }


def test_golden_state_passes_every_independent_assertion(pilot):
    task, environment = pilot
    _complete_golden_state(environment)

    checks = [
        environment.run_env_assertion(assertion, raise_assertion_error=False)
        for assertion in task.evaluation_criteria.env_assertions
    ]

    assert checks == [True] * 9


def test_text_assertions_accept_equivalent_operational_wording(pilot):
    task, environment = pilot
    _complete_golden_state(environment)
    world = environment.tools.db.interactive_world
    statuspage = next(iter(world.statuspage.incidents.values()))
    slack = next(iter(world.slack.messages.values()))

    statuspage.body = (
        "We are investigating payment failures affecting EU web checkout. "
        "API and mobile payments are operating normally."
    )
    slack.text = slack.text.replace("12%", "12.0%")

    assert environment.run_env_assertion(
        task.evaluation_criteria.env_assertions[3], raise_assertion_error=False
    )
    assert environment.run_env_assertion(
        task.evaluation_criteria.env_assertions[5], raise_assertion_error=False
    )


def test_second_internal_update_is_a_real_cardinality_failure(pilot):
    task, environment = pilot
    _complete_golden_state(environment)
    _call(
        environment,
        "slack_chat_post_message",
        {
            "channel": "inc-payments",
            "text": "A redundant second incident update.",
        },
    )

    checks = [
        environment.run_env_assertion(assertion, raise_assertion_error=False)
        for assertion in task.evaluation_criteria.env_assertions
    ]

    assert checks[5] is False
    assert all(check for index, check in enumerate(checks) if index != 5)


def test_wrong_severity_and_old_responder_have_specific_failure_signal(pilot):
    task, environment = pilot
    _unlock(
        environment,
        "linear_update_issue_graphql",
        "pagerduty_create_incident_v2",
    )
    _call(
        environment,
        "linear_update_issue_graphql",
        {
            "issue_id": "lin_incident_payments",
            "state": "Investigating",
            "assignee_id": "usr_omar",
            "severity": "SEV-1",
            "scope": "global payments",
            "source_signal_ids": ["dd_global_stale"],
        },
    )
    _call(
        environment,
        "pagerduty_create_incident_v2",
        {
            "title": "SEV-1 global outage",
            "urgency": "high",
            "assignee_id": "usr_omar",
            "incident_key": "PAY-842",
        },
    )

    checks = [
        environment.run_env_assertion(assertion, raise_assertion_error=False)
        for assertion in task.evaluation_criteria.env_assertions
    ]

    assert checks[0] is False
    assert checks[2] is False
    assert checks[6] is False
    assert checks[1] is True
    assert checks[7] is True
