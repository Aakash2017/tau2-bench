"""Outage escalation queue where some record conflicts are resolvable and one is not.

A stale ticket summary versus the incident timeline, and an order form versus a
later amendment, are settled by documented precedence. Two systems disagreeing on a
customer's tenant region, which decides credit eligibility, are not: that conflict
must be routed to its owner while the safe parts of the work proceed.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from pydantic import BaseModel, Field

from tau2.environment.db import BaseModelNoExtra

FAMILY_ID = "escalation_conflicts"
PAGE_SIZE = 5


class Ticket(BaseModelNoExtra):
    ticket_id: str
    account_id: str
    requester: str
    subject: str
    description: str
    status: str
    view: str
    incident_id: str = ""
    internal_notes: list[str] = Field(default_factory=list)


class RegionImpact(BaseModelNoExtra):
    region: str
    impact_start: str
    impact_end: str
    impact_minutes: int


class Incident(BaseModelNoExtra):
    incident_id: str
    title: str
    status: str
    regions: list[RegionImpact] = Field(default_factory=list)


class Contact(BaseModelNoExtra):
    email: str
    name: str
    verified: bool


class ContractDoc(BaseModelNoExtra):
    doc_id: str
    kind: str
    executed_on: str
    summary: str


class Account(BaseModelNoExtra):
    account_id: str
    name: str
    mrr: float
    currency: str
    tenant_id: str
    tenant_region: str
    contacts: list[Contact] = Field(default_factory=list)
    contract_documents: list[ContractDoc] = Field(default_factory=list)


class Tenant(BaseModelNoExtra):
    tenant_id: str
    region: str
    cluster: str
    last_migrated: str = ""


class Credit(BaseModelNoExtra):
    credit_id: str
    account_id: str
    amount: float
    currency: str
    incident_id: str
    reason: str


class JiraIssue(BaseModelNoExtra):
    issue_id: str
    project: str
    summary: str
    description: str


class Mail(BaseModelNoExtra):
    message_id: str
    to: list[str]
    subject: str
    body: str


class EscalationWorld(BaseModelNoExtra):
    task_id: str = ""
    current_time: str = ""
    tickets: dict[str, Ticket] = Field(default_factory=dict)
    incidents: dict[str, Incident] = Field(default_factory=dict)
    accounts: dict[str, Account] = Field(default_factory=dict)
    tenants: dict[str, Tenant] = Field(default_factory=dict)
    credits: dict[str, Credit] = Field(default_factory=dict)
    jira_issues: dict[str, JiraIssue] = Field(default_factory=dict)
    sent_mail: dict[str, Mail] = Field(default_factory=dict)


class ListTicketsArgs(BaseModelNoExtra):
    view: str
    page: int = 1


class TicketArgs(BaseModelNoExtra):
    ticket_id: str


class UpdateTicketArgs(BaseModelNoExtra):
    ticket_id: str
    status: str | None = None
    internal_note: str | None = None


class IncidentArgs(BaseModelNoExtra):
    incident_id: str


class AccountArgs(BaseModelNoExtra):
    account_id: str


class TenantArgs(BaseModelNoExtra):
    tenant_id: str


class CreditArgs(BaseModelNoExtra):
    account_id: str
    amount: float
    currency: str
    incident_id: str
    reason: str


class JiraArgs(BaseModelNoExtra):
    project: str
    summary: str
    description: str


class SendArgs(BaseModelNoExtra):
    to: list[str]
    subject: str
    body: str


def _entry(description: str, model: type[BaseModel], mutates: bool) -> dict:
    schema = model.model_json_schema()
    return {
        "description": description,
        "parameters": {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
            "additionalProperties": False,
        },
        "mutates_state": mutates,
    }


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "zendesk_list_view_tickets_v1": _entry(
        "List tickets in a Zendesk view. Paginated.", ListTicketsArgs, False
    ),
    "zendesk_get_ticket_v1": _entry("Get one Zendesk ticket.", TicketArgs, False),
    "zendesk_update_ticket_v1": _entry(
        "Change a ticket's status and/or add an internal note.",
        UpdateTicketArgs,
        True,
    ),
    "linear_get_incident_v1": _entry("Get a Linear incident.", IncidentArgs, False),
    "salesforce_get_account_v1": _entry(
        "Get a Salesforce account.", AccountArgs, False
    ),
    "admin_console_get_tenant_v1": _entry(
        "Get a tenant's deployment record.", TenantArgs, False
    ),
    "billing_issue_service_credit_v1": _entry(
        "Issue a service credit to an account.", CreditArgs, True
    ),
    "jira_create_issue_v1": _entry("Create a Jira issue.", JiraArgs, True),
    "gmail_send_message_v1": _entry("Send one email.", SendArgs, True),
}


def _get(store: dict, key: str, label: str) -> Any:
    if key not in store:
        raise ValueError(f"{label} not found: {key}")
    return store[key]


def _list(world: EscalationWorld, raw: dict) -> dict:
    args = ListTicketsArgs.model_validate(raw)
    rows = sorted(
        (t for t in world.tickets.values() if t.view == args.view),
        key=lambda t: t.ticket_id,
    )
    page = rows[(args.page - 1) * PAGE_SIZE : args.page * PAGE_SIZE]
    keep = {"ticket_id", "account_id", "subject", "status"}
    return {
        "items": [t.model_dump(include=keep) for t in page],
        "page": args.page,
        "total_pages": max(1, -(-len(rows) // PAGE_SIZE)),
    }


def _ticket(world: EscalationWorld, raw: dict) -> dict:
    ticket_id = TicketArgs.model_validate(raw).ticket_id
    return {"ticket": _get(world.tickets, ticket_id, "Ticket").model_dump()}


def _update(world: EscalationWorld, raw: dict) -> dict:
    args = UpdateTicketArgs.model_validate(raw)
    ticket = _get(world.tickets, args.ticket_id, "Ticket")
    if args.status is not None:
        allowed = {"open", "pending", "on_hold", "solved"}
        if args.status not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        ticket.status = args.status
    if args.internal_note:
        ticket.internal_notes.append(args.internal_note)
    return {"ticket": ticket.model_dump()}


def _incident(world: EscalationWorld, raw: dict) -> dict:
    incident_id = IncidentArgs.model_validate(raw).incident_id
    return {"incident": _get(world.incidents, incident_id, "Incident").model_dump()}


def _account(world: EscalationWorld, raw: dict) -> dict:
    account_id = AccountArgs.model_validate(raw).account_id
    return {"account": _get(world.accounts, account_id, "Account").model_dump()}


def _tenant(world: EscalationWorld, raw: dict) -> dict:
    tenant_id = TenantArgs.model_validate(raw).tenant_id
    return {"tenant": _get(world.tenants, tenant_id, "Tenant").model_dump()}


def _credit(world: EscalationWorld, raw: dict) -> dict:
    args = CreditArgs.model_validate(raw)
    _get(world.accounts, args.account_id, "Account")
    credit = Credit(
        credit_id=f"CR-{len(world.credits) + 1:04d}",
        **{
            **args.model_dump(),
            "amount": round(args.amount, 2),
            "currency": args.currency.upper(),
        },
    )
    world.credits[credit.credit_id] = credit
    return {"credit": credit.model_dump()}


def _jira(world: EscalationWorld, raw: dict) -> dict:
    args = JiraArgs.model_validate(raw)
    issue_id = f"{args.project.upper()}-{900 + len(world.jira_issues) + 1}"
    world.jira_issues[issue_id] = JiraIssue(
        issue_id=issue_id, **{**args.model_dump(), "project": args.project.upper()}
    )
    return {"issue_id": issue_id}


def _send(world: EscalationWorld, raw: dict) -> dict:
    args = SendArgs.model_validate(raw)
    mid = f"sent_{len(world.sent_mail) + 1:03d}"
    world.sent_mail[mid] = Mail(
        message_id=mid,
        to=[t.strip().lower() for t in args.to],
        subject=args.subject,
        body=args.body,
    )
    return {"id": mid}


_HANDLERS: dict[str, Callable[[EscalationWorld, dict], dict]] = {
    "zendesk_list_view_tickets_v1": _list,
    "zendesk_get_ticket_v1": _ticket,
    "zendesk_update_ticket_v1": _update,
    "linear_get_incident_v1": _incident,
    "salesforce_get_account_v1": _account,
    "admin_console_get_tenant_v1": _tenant,
    "billing_issue_service_credit_v1": _credit,
    "jira_create_issue_v1": _jira,
    "gmail_send_message_v1": _send,
}


def validate_world(raw: dict[str, Any]) -> EscalationWorld:
    return EscalationWorld.model_validate(raw)


def call_tool(
    raw_world: dict[str, Any], tool_name: str, arguments: str
) -> tuple[dict[str, Any], str]:
    world = validate_world(raw_world)
    if tool_name not in _HANDLERS:
        raise ValueError(f"Unknown escalation tool: {tool_name}")
    try:
        raw = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"arguments must be valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("arguments must encode one JSON object")
    response = json.dumps(_HANDLERS[tool_name](world, raw), sort_keys=True)
    return world.model_dump(mode="json"), response


def _mentions_amount(text: str, amount: float) -> bool:
    flat = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    whole, cents = f"{amount:.2f}".split(".")
    tail = r"(\.00?)?" if cents == "00" else rf"\.{cents}"
    return re.search(rf"(?<![\d.]){whole}{tail}(?!\d)", flat) is not None


def check_assertion(raw_world: dict[str, Any], assertion: dict[str, Any]) -> bool:
    """Evaluate exact final state; conversation and call order are not inspected."""
    world = validate_world(raw_world)
    kind = assertion["type"]
    if kind == "esc_credit_exact":
        rows = [
            c for c in world.credits.values() if c.account_id == assertion["account_id"]
        ]
        return bool(
            len(rows) == 1
            and abs(rows[0].amount - assertion["amount"]) < 0.005
            and rows[0].currency == assertion["currency"]
            and rows[0].incident_id == assertion["incident_id"]
        )
    if kind == "esc_no_credit":
        return not any(
            c.account_id == assertion["account_id"] for c in world.credits.values()
        )
    if kind == "esc_ticket_status":
        ticket = world.tickets.get(assertion["ticket_id"])
        return bool(ticket and ticket.status == assertion["status"])
    if kind == "esc_one_email":
        rows = [m for m in world.sent_mail.values() if assertion["to"] in m.to]
        if len(rows) != 1:
            return False
        text = f"{rows[0].subject} {rows[0].body}"
        return all(
            _mentions_amount(text, a) for a in assertion.get("amounts", [])
        ) and not any(
            _mentions_amount(text, a) for a in assertion.get("forbidden_amounts", [])
        )
    if kind == "esc_no_email_to":
        return not any(
            set(m.to) & set(assertion["recipients"]) for m in world.sent_mail.values()
        )
    if kind == "esc_jira_exact":
        rows = list(world.jira_issues.values())
        text = " ".join(f"{r.summary} {r.description}" for r in rows).lower()
        return bool(
            len(rows) == 1
            and rows[0].project == assertion["project"]
            and all(t.lower() in text for t in assertion["terms"])
        )
    raise ValueError(f"Unknown escalation assertion type: {kind}")


def golden_call_sequence(task_spec: dict[str, Any]) -> list[tuple[str, dict]]:
    """Return the task file's deterministic, policy-compliant write trajectory."""
    return [(name, args) for name, args in task_spec["golden_writes"]]


def negative_call_sequence(task_spec: dict[str, Any]) -> list[tuple[str, dict]]:
    """Credit everyone at 10% as the support lead assumes."""
    return [
        (
            "billing_issue_service_credit_v1",
            {
                "account_id": a,
                "amount": m * 0.10,
                "currency": "USD",
                "incident_id": "INC-731",
                "reason": "SLA credit",
            },
        )
        for a, m in [
            ("acc_northwind", 18000),
            ("acc_quantum", 12000),
            ("acc_vela", 9000),
        ]
    ]
