"""Pydantic-backed runtime for the canonical customer-escalation task."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable

from pydantic import BaseModel, Field

from tau2.utils.pydantic_utils import BaseModelNoExtra

FAMILY_ID = "customer_escalation"


class Contact(BaseModelNoExtra):
    contact_id: str
    name: str
    email: str
    role: str
    verified_for_external_incident_comms: bool


class Account(BaseModelNoExtra):
    account_id: str
    name: str
    owner_name: str
    owner_email: str
    service_credit_authority_usd: int
    contacts: dict[str, Contact] = Field(default_factory=dict)


class SalesforceCase(BaseModelNoExtra):
    case_id: str
    account_id: str
    subject: str
    status: str
    priority: str
    incident_id: str | None = None
    external_message_id: str | None = None
    approved_credit_usd: int | None = None
    resolution_summary: str = ""


class SalesforceState(BaseModelNoExtra):
    accounts: dict[str, Account] = Field(default_factory=dict)
    cases: dict[str, SalesforceCase] = Field(default_factory=dict)


class ZendeskTicket(BaseModelNoExtra):
    ticket_id: str
    account_id: str
    status: str
    requester_email: str
    summary: str
    updated_at: str


class ZendeskState(BaseModelNoExtra):
    tickets: dict[str, ZendeskTicket] = Field(default_factory=dict)


class LinearIncident(BaseModelNoExtra):
    issue_id: str
    identifier: str
    title: str
    state: str
    scope: str
    impact_summary: str
    updated_at: str


class LinearFollowup(BaseModelNoExtra):
    issue_id: str
    identifier: str
    title: str
    state: str
    assignee_email: str
    related_incident_id: str
    due_date: str


class LinearState(BaseModelNoExtra):
    incidents: dict[str, LinearIncident] = Field(default_factory=dict)
    followups: dict[str, LinearFollowup] = Field(default_factory=dict)


class GmailMessage(BaseModelNoExtra):
    message_id: str
    to: str
    subject: str
    body: str


class GmailState(BaseModelNoExtra):
    sent: dict[str, GmailMessage] = Field(default_factory=dict)


class SlackMessage(BaseModelNoExtra):
    message_id: str
    channel: str
    text: str


class SlackState(BaseModelNoExtra):
    messages: dict[str, SlackMessage] = Field(default_factory=dict)


class CustomerEscalationWorld(BaseModelNoExtra):
    task_id: str
    current_time: str
    salesforce: SalesforceState = Field(default_factory=SalesforceState)
    zendesk: ZendeskState = Field(default_factory=ZendeskState)
    linear: LinearState = Field(default_factory=LinearState)
    gmail: GmailState = Field(default_factory=GmailState)
    slack: SlackState = Field(default_factory=SlackState)


class AccountGetArguments(BaseModelNoExtra):
    account_id: str


class TicketGetArguments(BaseModelNoExtra):
    ticket_id: str


class IncidentGetArguments(BaseModelNoExtra):
    issue_id: str


class GmailSendArguments(BaseModelNoExtra):
    to: str
    subject: str
    body: str


class CaseUpdateArguments(BaseModelNoExtra):
    case_id: str
    status: str
    priority: str
    incident_id: str
    external_message_id: str
    approved_credit_usd: int
    resolution_summary: str


class FollowupCreateArguments(BaseModelNoExtra):
    title: str
    state: str
    assignee_email: str
    related_incident_id: str
    due_date: str


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


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "customer_salesforce_get_account_v1": {
        "description": "Get a Salesforce account, contacts, and credit authority.",
        "parameters": _schema(AccountGetArguments),
        "mutates_state": False,
    },
    "customer_zendesk_get_ticket_v2": {
        "description": "Get the current stored Zendesk ticket summary.",
        "parameters": _schema(TicketGetArguments),
        "mutates_state": False,
    },
    "customer_linear_get_incident_v1": {
        "description": "Get the authoritative current Linear incident record.",
        "parameters": _schema(IncidentGetArguments),
        "mutates_state": False,
    },
    "customer_gmail_send_message_v1": {
        "description": "Send one external message using the Gmail API shape.",
        "parameters": _schema(GmailSendArguments),
        "mutates_state": True,
    },
    "customer_salesforce_update_case_v1": {
        "description": "Update a Salesforce escalation case with its final outcome.",
        "parameters": _schema(CaseUpdateArguments),
        "mutates_state": True,
    },
    "customer_linear_create_followup_v1": {
        "description": "Create a Linear customer-incident follow-up issue.",
        "parameters": _schema(FollowupCreateArguments),
        "mutates_state": True,
    },
    "customer_slack_post_message_v1": {
        "description": "Post one internal customer-escalation Slack update.",
        "parameters": _schema(SlackPostArguments),
        "mutates_state": True,
    },
}


def validate_world(raw: dict[str, Any]) -> CustomerEscalationWorld:
    """Validate a serialized customer-escalation world."""
    return CustomerEscalationWorld.model_validate(raw)


def _get_account(world: CustomerEscalationWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = AccountGetArguments.model_validate(raw)
    account = world.salesforce.accounts.get(args.account_id)
    if account is None:
        raise ValueError("Salesforce account not found")
    return {"records": [account.model_dump(mode="json")], "totalSize": 1}


def _get_ticket(world: CustomerEscalationWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = TicketGetArguments.model_validate(raw)
    ticket = world.zendesk.tickets.get(args.ticket_id)
    if ticket is None:
        raise ValueError("Zendesk ticket not found")
    return {"ticket": ticket.model_dump(mode="json")}


def _get_incident(
    world: CustomerEscalationWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = IncidentGetArguments.model_validate(raw)
    incident = world.linear.incidents.get(args.issue_id)
    if incident is None:
        raise ValueError("Linear incident not found")
    return {"data": {"issue": incident.model_dump(mode="json")}}


def _send_message(
    world: CustomerEscalationWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = GmailSendArguments.model_validate(raw)
    message_id = f"gmail_customer_{len(world.gmail.sent) + 1:03d}"
    message = GmailMessage(message_id=message_id, **args.model_dump())
    world.gmail.sent[message_id] = message
    return {
        "id": message_id,
        "threadId": f"thread_{message_id}",
        "labelIds": ["SENT"],
    }


def _update_case(world: CustomerEscalationWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = CaseUpdateArguments.model_validate(raw)
    case = world.salesforce.cases.get(args.case_id)
    if case is None:
        raise ValueError("Salesforce case not found")
    if args.external_message_id not in world.gmail.sent:
        raise ValueError("external_message_id is not a sent Gmail message")
    if args.incident_id not in world.linear.incidents:
        raise ValueError("incident_id is not a Linear incident")
    for field, value in args.model_dump(exclude={"case_id"}).items():
        setattr(case, field, value)
    return {"id": case.case_id, "success": True, "errors": []}


def _create_followup(
    world: CustomerEscalationWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = FollowupCreateArguments.model_validate(raw)
    if args.related_incident_id not in world.linear.incidents:
        raise ValueError("related_incident_id is not a Linear incident")
    issue_id = f"linear_customer_followup_{len(world.linear.followups) + 1:03d}"
    followup = LinearFollowup(
        issue_id=issue_id,
        identifier=f"CUST-{910 + len(world.linear.followups)}",
        **args.model_dump(),
    )
    world.linear.followups[issue_id] = followup
    return {
        "data": {
            "issueCreate": {"success": True, "issue": followup.model_dump(mode="json")}
        }
    }


def _post_slack(world: CustomerEscalationWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = SlackPostArguments.model_validate(raw)
    message_id = f"slack_customer_{len(world.slack.messages) + 1:03d}"
    message = SlackMessage(message_id=message_id, **args.model_dump())
    world.slack.messages[message_id] = message
    return {"ok": True, "channel": args.channel, "ts": message_id}


_HANDLERS: dict[
    str, Callable[[CustomerEscalationWorld, dict[str, Any]], dict[str, Any]]
] = {
    "customer_salesforce_get_account_v1": _get_account,
    "customer_zendesk_get_ticket_v2": _get_ticket,
    "customer_linear_get_incident_v1": _get_incident,
    "customer_gmail_send_message_v1": _send_message,
    "customer_salesforce_update_case_v1": _update_case,
    "customer_linear_create_followup_v1": _create_followup,
    "customer_slack_post_message_v1": _post_slack,
}


def call_tool(
    raw_world: dict[str, Any], tool_name: str, arguments: str
) -> tuple[dict[str, Any], str]:
    """Execute one family operation and return serialized state plus JSON response."""
    if tool_name not in _HANDLERS:
        raise ValueError(f"Unknown {FAMILY_ID} tool: {tool_name}")
    try:
        raw_arguments = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"arguments must be valid JSON: {exc}") from exc
    if not isinstance(raw_arguments, dict):
        raise ValueError("arguments must encode one JSON object")
    world = validate_world(deepcopy(raw_world))
    response = _HANDLERS[tool_name](world, raw_arguments)
    return world.model_dump(mode="json"), json.dumps(response, sort_keys=True)


def _contains_all(value: str, terms: list[str]) -> bool:
    lowered = value.lower()
    return all(term.lower() in lowered for term in terms)


def check_assertion(raw_world: dict[str, Any], assertion: dict[str, Any]) -> bool:
    """Evaluate one exact-state assertion against serialized family state."""
    world = validate_world(raw_world)
    assertion_type = assertion["type"]
    verified = world.salesforce.accounts["acct_northstar"].contacts["contact_priya"]
    sent = list(world.gmail.sent.values())
    if assertion_type == "customer_verified_single_outreach":
        if len(sent) != 1:
            return False
        text = f"{sent[0].subject} {sent[0].body}"
        forbidden = ["global outage", "resolved", "sam.lee", "20%"]
        return bool(
            sent[0].to == verified.email
            and _contains_all(text, ["EU data exports", "investigating", "$400"])
            and not any(term in text.lower() for term in forbidden)
        )
    if assertion_type == "customer_credit_exact_and_authorized":
        case = world.salesforce.cases["case_1042"]
        return bool(
            case.approved_credit_usd == 400
            and case.approved_credit_usd
            <= world.salesforce.accounts[case.account_id].service_credit_authority_usd
            and len(sent) == 1
            and "$400" in sent[0].body
        )
    if assertion_type == "customer_case_exact":
        case = world.salesforce.cases["case_1042"]
        return bool(
            case.status == "Escalated - Monitoring"
            and case.priority == "High"
            and case.incident_id == "lin_incident_558"
            and case.external_message_id in world.gmail.sent
            and _contains_all(
                case.resolution_summary,
                ["EU data exports", "investigating", "Priya", "$400"],
            )
        )
    if assertion_type == "customer_followup_exact":
        followups = list(world.linear.followups.values())
        return bool(
            len(followups) == 1
            and followups[0].state == "Todo"
            and followups[0].assignee_email == "maya@atlas.example"
            and followups[0].related_incident_id == "lin_incident_558"
            and followups[0].due_date == "2026-11-18"
            and _contains_all(followups[0].title, ["Northstar", "RCA"])
        )
    if assertion_type == "customer_slack_exact":
        messages = list(world.slack.messages.values())
        return bool(
            len(messages) == 1
            and messages[0].channel == "customer-escalations"
            and _contains_all(
                messages[0].text,
                [
                    "Northstar",
                    "CASE-1042",
                    "EU data exports",
                    "investigating",
                    "Priya",
                    "$400",
                    "2026-11-18",
                ],
            )
        )
    if assertion_type == "customer_source_records_preserved":
        ticket = world.zendesk.tickets["zd_7791"]
        incident = world.linear.incidents["lin_incident_558"]
        return bool(
            ticket.status == "solved"
            and ticket.updated_at == "2026-11-13T07:20:00-08:00"
            and incident.state == "Investigating"
            and incident.updated_at == "2026-11-14T09:02:00-08:00"
        )
    raise ValueError(f"Unknown {FAMILY_ID} assertion: {assertion_type}")


def golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return a deterministic successful write sequence for tests and review."""
    return [
        (
            "customer_gmail_send_message_v1",
            {
                "to": "priya.shah@northstar.example",
                "subject": "Update: EU data export delays",
                "body": (
                    "Priya, EU data exports are delayed and the incident remains "
                    "investigating. Other regions and ingestion are healthy. We will "
                    "provide the next update by 12:00 PT and apply a $400 service credit."
                ),
            },
        ),
        (
            "customer_salesforce_update_case_v1",
            {
                "case_id": "case_1042",
                "status": "Escalated - Monitoring",
                "priority": "High",
                "incident_id": "lin_incident_558",
                "external_message_id": "gmail_customer_001",
                "approved_credit_usd": 400,
                "resolution_summary": (
                    "Priya received an investigating update for EU data exports with "
                    "an approved $400 service credit."
                ),
            },
        ),
        (
            "customer_linear_create_followup_v1",
            {
                "title": "RCA follow-up: Northstar EU data exports",
                "state": "Todo",
                "assignee_email": "maya@atlas.example",
                "related_incident_id": "lin_incident_558",
                "due_date": "2026-11-18",
            },
        ),
        (
            "customer_slack_post_message_v1",
            {
                "channel": "customer-escalations",
                "text": (
                    "Northstar CASE-1042: EU data exports remain investigating. Priya "
                    "received the approved $400 credit update. RCA due 2026-11-18."
                ),
            },
        ),
    ]


def negative_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return a plausible but policy-violating external-send path."""
    return [
        (
            "customer_gmail_send_message_v1",
            {
                "to": "sam.lee@northstar-ops.example",
                "subject": "Northstar global outage resolved",
                "body": "Sam, the global outage is resolved. We approved a 20% credit.",
            },
        )
    ]
