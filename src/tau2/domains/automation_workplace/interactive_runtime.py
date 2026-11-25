"""Discoverable app operations for authored interactive workplace tasks."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from tau2.domains.automation_workplace.data_model import (
    InteractiveWorkplaceWorld,
    LinearIssue,
    PagerDutyIncident,
    SlackMessage,
    StatuspageIncident,
)
from tau2.utils.pydantic_utils import BaseModelNoExtra


class DatadogQueryArguments(BaseModelNoExtra):
    query: str
    from_time: str
    to_time: str


class PagerDutyOnCallsArguments(BaseModelNoExtra):
    schedule_ids: list[str]
    since: str
    until: str


class PagerDutyCreateIncidentArguments(BaseModelNoExtra):
    title: str
    urgency: str
    assignee_id: str
    incident_key: str


class LinearSearchArguments(BaseModelNoExtra):
    query: str


class LinearUpdateArguments(BaseModelNoExtra):
    issue_id: str
    state: str
    assignee_id: str
    severity: str
    scope: str
    source_signal_ids: list[str]
    description: str = ""


class LinearCreateArguments(BaseModelNoExtra):
    team_id: str
    title: str
    state: str
    assignee_id: str
    due_date: str
    related_issue_id: str
    labels: list[str] = Field(default_factory=list)
    description: str = ""


class StatuspageCreateArguments(BaseModelNoExtra):
    page_id: str
    name: str
    status: str
    impact: str
    body: str
    component_ids: list[str]


class SlackPostArguments(BaseModelNoExtra):
    channel: str
    text: str


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
        "additionalProperties": False,
    }


DISCOVERABLE_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "datadog_query_metrics_v1": {
        "description": "Query Datadog metric series over an ISO-8601 time window.",
        "parameters": _schema(DatadogQueryArguments),
        "mutates_state": False,
    },
    "pagerduty_list_oncalls_v2": {
        "description": "List PagerDuty on-call entries overlapping a time window.",
        "parameters": _schema(PagerDutyOnCallsArguments),
        "mutates_state": False,
    },
    "pagerduty_create_incident_v2": {
        "description": "Create one PagerDuty incident assigned to a specific responder.",
        "parameters": _schema(PagerDutyCreateIncidentArguments),
        "mutates_state": True,
    },
    "linear_search_issues_graphql": {
        "description": "Search Linear issues by identifier or text.",
        "parameters": _schema(LinearSearchArguments),
        "mutates_state": False,
    },
    "linear_update_issue_graphql": {
        "description": "Update the existing Linear incident with triage facts.",
        "parameters": _schema(LinearUpdateArguments),
        "mutates_state": True,
    },
    "linear_create_issue_graphql": {
        "description": "Create a linked Linear follow-up issue.",
        "parameters": _schema(LinearCreateArguments),
        "mutates_state": True,
    },
    "statuspage_create_incident_v1": {
        "description": "Publish a scoped incident on an Atlassian Statuspage page.",
        "parameters": _schema(StatuspageCreateArguments),
        "mutates_state": True,
    },
    "slack_chat_post_message": {
        "description": "Post one message to a Slack channel.",
        "parameters": _schema(SlackPostArguments),
        "mutates_state": True,
    },
}


def tool_schema(tool_name: str) -> dict[str, Any]:
    """Return the registered schema for a discoverable tool."""
    if tool_name not in DISCOVERABLE_TOOL_SCHEMAS:
        raise ValueError(f"Unknown discoverable tool: {tool_name}")
    return {"name": tool_name, **DISCOVERABLE_TOOL_SCHEMAS[tool_name]}


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Time values must be ISO 8601 with a UTC offset") from exc


def _search_terms(value: str) -> set[str]:
    """Normalize simple singular/plural variants for simulated API search."""
    terms = re.findall(r"[a-z0-9]+", value.lower())
    return {
        term[:-1]
        if len(term) > 4
        and term.endswith("s")
        and not term.endswith(("ss", "us", "is"))
        else term
        for term in terms
    }


def _datadog_query(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = DatadogQueryArguments.model_validate(raw)
    start = _parse_time(args.from_time)
    end = _parse_time(args.to_time)
    if end <= start:
        raise ValueError("to_time must be after from_time")
    terms = _search_terms(args.query)
    series = []
    for signal in world.datadog.signals.values():
        updated_at = _parse_time(signal.updated_at)
        haystack = " ".join(
            [signal.title, signal.query, signal.scope, signal.channel, signal.region]
        )
        if terms and not terms.intersection(_search_terms(haystack)):
            continue
        if not start <= updated_at <= end:
            continue
        series.append(signal.model_dump(mode="json"))
    series.sort(key=lambda item: (item["updated_at"], item["signal_id"]))
    return {"status": "ok", "series": series}


def _pagerduty_oncalls(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = PagerDutyOnCallsArguments.model_validate(raw)
    start = _parse_time(args.since)
    end = _parse_time(args.until)
    if end <= start:
        raise ValueError("until must be after since")
    oncalls = [
        oncall.model_dump(mode="json")
        for oncall in world.pagerduty.oncalls.values()
        if oncall.schedule_id in args.schedule_ids
        and _parse_time(oncall.start) < end
        and _parse_time(oncall.end) > start
    ]
    oncalls.sort(key=lambda item: (item["start"], item["oncall_id"]))
    return {"oncalls": oncalls, "limit": len(oncalls), "more": False}


def _pagerduty_create(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = PagerDutyCreateIncidentArguments.model_validate(raw)
    if args.urgency not in {"high", "low"}:
        raise ValueError("urgency must be high or low")
    matching = [
        entry
        for entry in world.pagerduty.oncalls.values()
        if entry.user_id == args.assignee_id
    ]
    if not matching:
        raise ValueError("PagerDuty assignee not found")
    incident_id = f"PDINC-{len(world.pagerduty.incidents) + 1:03d}"
    incident = PagerDutyIncident(
        incident_id=incident_id,
        title=args.title,
        urgency=args.urgency,
        assignee_id=args.assignee_id,
        assignee_email=matching[0].user_email,
        incident_key=args.incident_key,
    )
    world.pagerduty.incidents[incident_id] = incident
    return {"incident": incident.model_dump(mode="json")}


def _linear_search(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = LinearSearchArguments.model_validate(raw)
    terms = _search_terms(args.query)
    nodes = []
    for issue in world.linear.issues.values():
        haystack = " ".join(
            [issue.identifier, issue.title, issue.description, issue.state]
        )
        if not terms or terms.issubset(_search_terms(haystack)):
            nodes.append(issue.model_dump(mode="json"))
    nodes.sort(key=lambda item: item["identifier"])
    return {"data": {"issues": {"nodes": nodes}}}


def _linear_update(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = LinearUpdateArguments.model_validate(raw)
    if args.issue_id not in world.linear.issues:
        raise ValueError("Linear issue not found")
    issue = world.linear.issues[args.issue_id]
    if issue.issue_type != "incident":
        raise ValueError(
            "Only the existing incident can be triaged with this operation"
        )
    oncall = next(
        (
            entry
            for entry in world.pagerduty.oncalls.values()
            if entry.user_id == args.assignee_id
        ),
        None,
    )
    if oncall is None:
        raise ValueError("Linear assignee is not a known incident responder")
    issue.state = args.state
    issue.assignee_id = args.assignee_id
    issue.assignee_email = oncall.user_email
    issue.severity = args.severity
    issue.scope = args.scope
    issue.source_signal_ids = list(args.source_signal_ids)
    issue.description = args.description
    return {
        "data": {
            "issueUpdate": {"success": True, "issue": issue.model_dump(mode="json")}
        }
    }


def _linear_create(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = LinearCreateArguments.model_validate(raw)
    if args.related_issue_id not in world.linear.issues:
        raise ValueError("Related Linear issue not found")
    oncall = next(
        (
            entry
            for entry in world.pagerduty.oncalls.values()
            if entry.user_id == args.assignee_id
        ),
        None,
    )
    if oncall is None:
        raise ValueError("Linear assignee is not a known incident responder")
    issue_id = f"lin_rca_{len(world.linear.issues) + 1}"
    issue = LinearIssue(
        issue_id=issue_id,
        identifier=f"PAY-{842 + len(world.linear.issues)}",
        team_id=args.team_id,
        issue_type="rca",
        title=args.title,
        state=args.state,
        assignee_id=args.assignee_id,
        assignee_email=oncall.user_email,
        due_date=args.due_date,
        related_issue_id=args.related_issue_id,
        labels=list(args.labels),
        description=args.description,
    )
    world.linear.issues[issue_id] = issue
    return {
        "data": {
            "issueCreate": {"success": True, "issue": issue.model_dump(mode="json")}
        }
    }


def _statuspage_create(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = StatuspageCreateArguments.model_validate(raw)
    incident_id = f"sp_incident_{len(world.statuspage.incidents) + 1}"
    incident = StatuspageIncident(
        incident_id=incident_id,
        page_id=args.page_id,
        name=args.name,
        status=args.status,
        impact=args.impact,
        body=args.body,
        component_ids=list(args.component_ids),
    )
    world.statuspage.incidents[incident_id] = incident
    return incident.model_dump(mode="json")


def _slack_post(
    world: InteractiveWorkplaceWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SlackPostArguments.model_validate(raw)
    message_id = f"slack_message_{len(world.slack.messages) + 1}"
    message = SlackMessage(
        message_id=message_id,
        channel=args.channel,
        text=args.text,
    )
    world.slack.messages[message_id] = message
    return {
        "ok": True,
        "channel": args.channel,
        "ts": f"1731330000.{len(world.slack.messages):06d}",
        "message": message.model_dump(mode="json"),
    }


_HANDLERS: dict[
    str, Callable[[InteractiveWorkplaceWorld, dict[str, Any]], dict[str, Any]]
] = {
    "datadog_query_metrics_v1": _datadog_query,
    "pagerduty_list_oncalls_v2": _pagerduty_oncalls,
    "pagerduty_create_incident_v2": _pagerduty_create,
    "linear_search_issues_graphql": _linear_search,
    "linear_update_issue_graphql": _linear_update,
    "linear_create_issue_graphql": _linear_create,
    "statuspage_create_incident_v1": _statuspage_create,
    "slack_chat_post_message": _slack_post,
}


def call_tool(world: InteractiveWorkplaceWorld, tool_name: str, arguments: str) -> str:
    """Execute one unlocked operation and return an API-shaped JSON response."""
    if tool_name not in _HANDLERS:
        raise ValueError(f"Unknown discoverable tool: {tool_name}")
    try:
        raw = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"arguments must be valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("arguments must encode one JSON object")
    return json.dumps(_HANDLERS[tool_name](world, raw), sort_keys=True)


def _contains_all(value: str, required: list[str]) -> bool:
    lowered = value.lower()
    return all(term.lower() in lowered for term in required)


def _contains_percent(value: str, expected: int) -> bool:
    """Match equivalent integer/decimal renderings of a percentage."""
    return bool(re.search(rf"\b{expected}(?:\.0+)?\s*%", value))


def check_assertion(
    world: InteractiveWorkplaceWorld, assertion: dict[str, Any]
) -> bool:
    """Evaluate one deterministic positive or negative authored-task assertion."""
    assertion_type = assertion["type"]
    if assertion_type == "linear_existing_incident_exact":
        issue = world.linear.issues.get("lin_incident_payments")
        return bool(
            issue
            and issue.identifier == "PAY-842"
            and issue.issue_type == "incident"
            and issue.state == "Investigating"
            and issue.assignee_id == "usr_nina"
            and issue.assignee_email == "nina@atlas.example"
            and issue.severity == "SEV-2"
            and issue.scope == "EU web checkout"
            and set(issue.source_signal_ids)
            == {"dd_eu_checkout", "dd_mobile_healthy", "dd_api_healthy"}
        )
    if assertion_type == "linear_no_duplicate_incident":
        incidents = {
            issue.issue_id: issue
            for issue in world.linear.issues.values()
            if issue.issue_type == "incident"
        }
        historical = incidents.get("lin_incident_payments_2025")
        return bool(
            set(incidents)
            == {
                "lin_incident_payments",
                "lin_incident_payments_2025",
            }
            and historical
            and historical.identifier == "PAY-611"
            and historical.state == "Resolved"
            and historical.assignee_id == "usr_omar"
            and historical.severity == "SEV-1"
            and historical.scope == "global payments"
        )
    if assertion_type == "pagerduty_only_current_responder":
        incidents = list(world.pagerduty.incidents.values())
        return bool(
            len(incidents) == 1
            and incidents[0].assignee_id == "usr_nina"
            and incidents[0].assignee_email == "nina@atlas.example"
            and incidents[0].incident_key == "PAY-842"
            and incidents[0].urgency == "high"
        )
    if assertion_type == "statuspage_scoped_update":
        incidents = list(world.statuspage.incidents.values())
        public_text = (
            incidents[0].name + " " + incidents[0].body if incidents else ""
        ).lower()
        return bool(
            len(incidents) == 1
            and incidents[0].page_id == "page_payments"
            and incidents[0].status == "investigating"
            and incidents[0].impact == "minor"
            and incidents[0].component_ids == ["cmp_eu_web_checkout"]
            and _contains_all(
                incidents[0].name + " " + incidents[0].body,
                ["EU", "web checkout", "mobile", "API"],
            )
            and not any(
                forbidden in public_text
                for forbidden in [
                    "12%",
                    "pay-842",
                    "nina",
                    "datadog",
                    "strategic customer",
                    "signal id",
                ]
            )
        )
    if assertion_type == "linear_rca_exact":
        issues = [
            issue
            for issue in world.linear.issues.values()
            if issue.issue_type == "rca"
            and issue.related_issue_id == "lin_incident_payments"
        ]
        return bool(
            len(issues) == 1
            and issues[0].team_id == "team_payments"
            and _contains_all(issues[0].title, ["RCA", "EU web checkout"])
            and issues[0].state == "Todo"
            and issues[0].assignee_id == "usr_nina"
            and issues[0].due_date == "2026-11-17"
            and issues[0].related_issue_id == "lin_incident_payments"
            and "rca" in {label.lower() for label in issues[0].labels}
        )
    if assertion_type == "slack_incident_update":
        messages = list(world.slack.messages.values())
        return bool(
            len(messages) == 1
            and messages[0].channel == "inc-payments"
            and _contains_percent(messages[0].text, 12)
            and _contains_all(
                messages[0].text,
                [
                    "SEV-2",
                    "EU web checkout",
                    "PAY-842",
                    "Nina",
                    "RCA",
                    "2026-11-17",
                    "mobile",
                    "API",
                ],
            )
        )
    if assertion_type == "unrelated_records_preserved":
        historical_rca = world.linear.issues.get("lin_rca_payments_2025")
        return bool(
            historical_rca
            and historical_rca.identifier == "PAY-612"
            and historical_rca.issue_type == "rca"
            and historical_rca.state == "Done"
            and historical_rca.assignee_id == "usr_omar"
            and historical_rca.due_date == "2025-04-07"
            and historical_rca.related_issue_id == "lin_incident_payments_2025"
        )
    if assertion_type == "no_forbidden_global_or_sev1_side_effects":
        linear_incidents = [
            issue
            for issue in world.linear.issues.values()
            if issue.issue_type == "incident"
            and issue.issue_id != "lin_incident_payments_2025"
        ]
        return bool(
            all(issue.severity != "SEV-1" for issue in linear_incidents)
            and all(issue.scope != "global payments" for issue in linear_incidents)
            and all(
                incident.assignee_id != "usr_omar"
                for incident in world.pagerduty.incidents.values()
            )
            and all(
                "cmp_global_payments" not in incident.component_ids
                and incident.impact not in {"major", "critical"}
                for incident in world.statuspage.incidents.values()
            )
        )
    if assertion_type == "incident_remains_open":
        issue = world.linear.issues.get("lin_incident_payments")
        return bool(issue and issue.state == "Investigating")
    raise ValueError(f"Unknown interactive assertion type: {assertion_type}")
