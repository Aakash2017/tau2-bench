"""Pydantic-backed runtime for the canonical renewal-portfolio task."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable

from pydantic import BaseModel, Field

from tau2.utils.pydantic_utils import BaseModelNoExtra

FAMILY_ID = "renewal_portfolio"


class RenewalAccount(BaseModelNoExtra):
    account_id: str
    name: str
    parent_account_id: str | None = None
    master_agreement_id: str
    renewal_date: str
    renewal_stage: str
    arr_usd: int
    churn_risk: int
    owner_email: str
    verified_contact_email: str | None = None
    contact_verified: bool = False
    legal_hold_external_contact: bool = False
    active: bool = True


class SalesforceTask(BaseModelNoExtra):
    task_id: str
    account_id: str
    owner_email: str
    subject: str
    priority_rank: int
    due_date: str
    internal_only: bool


class SalesforceState(BaseModelNoExtra):
    account_order: list[str] = Field(default_factory=list)
    accounts: dict[str, RenewalAccount] = Field(default_factory=dict)
    tasks: dict[str, SalesforceTask] = Field(default_factory=dict)


class DocusignEnvelope(BaseModelNoExtra):
    envelope_id: str
    account_id: str
    status: str
    completed_at: str | None = None


class DocusignState(BaseModelNoExtra):
    envelopes: dict[str, DocusignEnvelope] = Field(default_factory=dict)


class GmailMessage(BaseModelNoExtra):
    message_id: str
    account_id: str
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


class RenewalPortfolioWorld(BaseModelNoExtra):
    task_id: str
    current_time: str
    salesforce: SalesforceState = Field(default_factory=SalesforceState)
    docusign: DocusignState = Field(default_factory=DocusignState)
    gmail: GmailState = Field(default_factory=GmailState)
    slack: SlackState = Field(default_factory=SlackState)


class ListAccountsArguments(BaseModelNoExtra):
    page_token: str | None = None
    page_size: int = 2


class ListEnvelopesArguments(BaseModelNoExtra):
    account_ids: list[str]


class UpdateStageArguments(BaseModelNoExtra):
    account_id: str
    renewal_stage: str


class CreateTaskArguments(BaseModelNoExtra):
    account_id: str
    owner_email: str
    subject: str
    priority_rank: int
    due_date: str
    internal_only: bool


class GmailSendArguments(BaseModelNoExtra):
    account_id: str
    to: str
    subject: str
    body: str


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
    "renewal_salesforce_list_accounts_v1": {
        "description": (
            "List renewal accounts in deterministic pages. Follow nextPageToken until "
            "done is true."
        ),
        "parameters": _schema(ListAccountsArguments),
        "mutates_state": False,
    },
    "renewal_docusign_list_envelopes_v1": {
        "description": "List DocuSign envelopes for the supplied Salesforce accounts.",
        "parameters": _schema(ListEnvelopesArguments),
        "mutates_state": False,
    },
    "renewal_salesforce_update_stage_v1": {
        "description": "Update one stale Salesforce renewal stage.",
        "parameters": _schema(UpdateStageArguments),
        "mutates_state": True,
    },
    "renewal_salesforce_create_task_v1": {
        "description": "Create one owner task for a canonical renewal account.",
        "parameters": _schema(CreateTaskArguments),
        "mutates_state": True,
    },
    "renewal_gmail_send_message_v1": {
        "description": "Send one renewal message through Gmail.",
        "parameters": _schema(GmailSendArguments),
        "mutates_state": True,
    },
    "renewal_slack_post_message_v1": {
        "description": "Post one renewal-batch reconciliation summary to Slack.",
        "parameters": _schema(SlackPostArguments),
        "mutates_state": True,
    },
}


def validate_world(raw: dict[str, Any]) -> RenewalPortfolioWorld:
    """Validate a serialized renewal-portfolio world."""
    world = RenewalPortfolioWorld.model_validate(raw)
    if set(world.salesforce.account_order) != set(world.salesforce.accounts):
        raise ValueError("account_order must contain every account exactly once")
    if len(world.salesforce.account_order) != len(world.salesforce.accounts):
        raise ValueError("account_order must not contain duplicate account IDs")
    return world


def _list_accounts(world: RenewalPortfolioWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = ListAccountsArguments.model_validate(raw)
    if args.page_size < 1 or args.page_size > 3:
        raise ValueError("page_size must be between 1 and 3")
    if args.page_token is None:
        start = 0
    elif args.page_token.startswith("offset:"):
        try:
            start = int(args.page_token.split(":", 1)[1])
        except ValueError as exc:
            raise ValueError("Invalid page_token") from exc
    else:
        raise ValueError("Invalid page_token")
    ordered = world.salesforce.account_order
    selected_ids = ordered[start : start + args.page_size]
    next_offset = start + len(selected_ids)
    done = next_offset >= len(ordered)
    return {
        "totalSize": len(ordered),
        "done": done,
        "nextPageToken": None if done else f"offset:{next_offset}",
        "records": [
            world.salesforce.accounts[account_id].model_dump(mode="json")
            for account_id in selected_ids
        ],
    }


def _list_envelopes(
    world: RenewalPortfolioWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = ListEnvelopesArguments.model_validate(raw)
    missing = set(args.account_ids) - set(world.salesforce.accounts)
    if missing:
        raise ValueError(f"Unknown account IDs: {sorted(missing)}")
    envelopes = [
        envelope.model_dump(mode="json")
        for envelope in world.docusign.envelopes.values()
        if envelope.account_id in args.account_ids
    ]
    envelopes.sort(key=lambda item: item["envelope_id"])
    return {"envelopes": envelopes, "resultSetSize": len(envelopes)}


def _update_stage(world: RenewalPortfolioWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = UpdateStageArguments.model_validate(raw)
    account = world.salesforce.accounts.get(args.account_id)
    if account is None:
        raise ValueError("Salesforce account not found")
    account.renewal_stage = args.renewal_stage
    return {"id": account.account_id, "success": True, "errors": []}


def _create_task(world: RenewalPortfolioWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = CreateTaskArguments.model_validate(raw)
    if args.account_id not in world.salesforce.accounts:
        raise ValueError("Salesforce account not found")
    task_id = f"renewal_task_{len(world.salesforce.tasks) + 1:03d}"
    task = SalesforceTask(task_id=task_id, **args.model_dump())
    world.salesforce.tasks[task_id] = task
    return {"id": task_id, "success": True, "errors": []}


def _send_message(world: RenewalPortfolioWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = GmailSendArguments.model_validate(raw)
    if args.account_id not in world.salesforce.accounts:
        raise ValueError("Salesforce account not found")
    message_id = f"gmail_renewal_{len(world.gmail.sent) + 1:03d}"
    message = GmailMessage(message_id=message_id, **args.model_dump())
    world.gmail.sent[message_id] = message
    return {"id": message_id, "threadId": f"thread_{message_id}", "labelIds": ["SENT"]}


def _post_slack(world: RenewalPortfolioWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = SlackPostArguments.model_validate(raw)
    message_id = f"slack_renewal_{len(world.slack.messages) + 1:03d}"
    world.slack.messages[message_id] = SlackMessage(
        message_id=message_id, **args.model_dump()
    )
    return {"ok": True, "channel": args.channel, "ts": message_id}


_HANDLERS: dict[
    str, Callable[[RenewalPortfolioWorld, dict[str, Any]], dict[str, Any]]
] = {
    "renewal_salesforce_list_accounts_v1": _list_accounts,
    "renewal_docusign_list_envelopes_v1": _list_envelopes,
    "renewal_salesforce_update_stage_v1": _update_stage,
    "renewal_salesforce_create_task_v1": _create_task,
    "renewal_gmail_send_message_v1": _send_message,
    "renewal_slack_post_message_v1": _post_slack,
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
    tasks = list(world.salesforce.tasks.values())
    sent = list(world.gmail.sent.values())
    if assertion_type == "renewal_qualifier_tasks_exact":
        by_account = {task.account_id: task for task in tasks}
        return bool(
            len(tasks) == 3
            and set(by_account) == {"acct_apex", "acct_beacon", "acct_delta"}
            and by_account["acct_beacon"].priority_rank == 1
            and by_account["acct_beacon"].internal_only
            and by_account["acct_apex"].priority_rank == 2
            and not by_account["acct_apex"].internal_only
            and by_account["acct_delta"].priority_rank == 3
            and not by_account["acct_delta"].internal_only
            and all(task.due_date == "2026-11-16" for task in tasks)
            and all(
                task.owner_email
                == world.salesforce.accounts[task.account_id].owner_email
                for task in tasks
            )
        )
    if assertion_type == "renewal_permitted_outreach_exact":
        by_account = {message.account_id: message for message in sent}
        return bool(
            len(sent) == 2
            and set(by_account) == {"acct_apex", "acct_delta"}
            and all(
                message.to
                == world.salesforce.accounts[message.account_id].verified_contact_email
                and _contains_all(
                    f"{message.subject} {message.body}",
                    [
                        world.salesforce.accounts[message.account_id].name,
                        world.salesforce.accounts[message.account_id].renewal_date,
                    ],
                )
                for message in sent
            )
        )
    if assertion_type == "renewal_legal_hold_respected":
        beacon_tasks = [task for task in tasks if task.account_id == "acct_beacon"]
        return bool(
            len(beacon_tasks) == 1
            and beacon_tasks[0].internal_only
            and all(message.account_id != "acct_beacon" for message in sent)
            and all(message.to != "ravi@beacon.example" for message in sent)
        )
    if assertion_type == "renewal_parent_child_deduplicated":
        return bool(
            all(task.account_id != "acct_apex_emea" for task in tasks)
            and all(message.account_id != "acct_apex_emea" for message in sent)
            and sum(task.account_id == "acct_apex" for task in tasks) == 1
            and sum(message.account_id == "acct_apex" for message in sent) == 1
        )
    if assertion_type == "renewal_signed_state_corrected":
        cobalt = world.salesforce.accounts["acct_cobalt"]
        return bool(
            cobalt.renewal_stage == "Renewed"
            and all(task.account_id != "acct_cobalt" for task in tasks)
            and all(message.account_id != "acct_cobalt" for message in sent)
        )
    if assertion_type == "renewal_slack_reconciliation_exact":
        messages = list(world.slack.messages.values())
        return bool(
            len(messages) == 1
            and messages[0].channel == "renewals-ops"
            and _contains_all(
                messages[0].text,
                [
                    "Apex Global",
                    "Beacon Health",
                    "legal hold",
                    "Apex EMEA",
                    "duplicate",
                    "Cobalt Labs",
                    "signed",
                    "Delta Systems",
                    "Echelon Media",
                    "excluded",
                    "3 tasks",
                    "2 emails",
                ],
            )
        )
    if assertion_type == "renewal_unrelated_records_preserved":
        child = world.salesforce.accounts["acct_apex_emea"]
        echelon = world.salesforce.accounts["acct_echelon"]
        return bool(
            child.parent_account_id == "acct_apex"
            and child.master_agreement_id == "msa_apex_2024"
            and child.renewal_stage == "Negotiation"
            and echelon.renewal_stage == "Discovery"
            and echelon.renewal_date == "2027-05-30"
        )
    raise ValueError(f"Unknown {FAMILY_ID} assertion: {assertion_type}")


def golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return a deterministic successful write sequence for tests and review."""
    task_specs = [
        (
            "acct_beacon",
            "ben@atlas.example",
            "Prepare Beacon Health renewal; external contact blocked by legal hold",
            1,
            True,
        ),
        (
            "acct_apex",
            "ana@atlas.example",
            "Prepare Apex Global master renewal",
            2,
            False,
        ),
        (
            "acct_delta",
            "dev@atlas.example",
            "Prepare Delta Systems renewal",
            3,
            False,
        ),
    ]
    calls: list[tuple[str, dict[str, Any]]] = [
        (
            "renewal_salesforce_update_stage_v1",
            {"account_id": "acct_cobalt", "renewal_stage": "Renewed"},
        )
    ]
    calls.extend(
        (
            "renewal_salesforce_create_task_v1",
            {
                "account_id": account_id,
                "owner_email": owner_email,
                "subject": subject,
                "priority_rank": priority,
                "due_date": "2026-11-16",
                "internal_only": internal_only,
            },
        )
        for account_id, owner_email, subject, priority, internal_only in task_specs
    )
    calls.extend(
        [
            (
                "renewal_gmail_send_message_v1",
                {
                    "account_id": "acct_apex",
                    "to": "leila@apex.example",
                    "subject": "Apex Global renewal planning",
                    "body": (
                        "Leila, Apex Global renews on 2027-01-15. Could we schedule "
                        "a planning conversation for the master agreement?"
                    ),
                },
            ),
            (
                "renewal_gmail_send_message_v1",
                {
                    "account_id": "acct_delta",
                    "to": "mina@delta.example",
                    "subject": "Delta Systems renewal planning",
                    "body": (
                        "Mina, Delta Systems renews on 2026-12-31. Could we schedule "
                        "a renewal planning conversation?"
                    ),
                },
            ),
            (
                "renewal_slack_post_message_v1",
                {
                    "channel": "renewals-ops",
                    "text": (
                        "Batch complete: 3 tasks and 2 emails. Apex Global and Delta "
                        "Systems received outreach. Beacon Health has an internal task "
                        "only due to legal hold. Apex EMEA was excluded as a duplicate "
                        "under the Apex master agreement. Cobalt Labs had a signed renewal "
                        "and was corrected to Renewed. Echelon Media was excluded by the "
                        "date window."
                    ),
                },
            ),
        ]
    )
    return calls


def negative_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return a plausible first-page-only path that violates hold and dedup rules."""
    return [
        (
            "renewal_salesforce_create_task_v1",
            {
                "account_id": "acct_apex_emea",
                "owner_email": "ana@atlas.example",
                "subject": "Prepare Apex EMEA renewal",
                "priority_rank": 1,
                "due_date": "2026-11-16",
                "internal_only": False,
            },
        ),
        (
            "renewal_gmail_send_message_v1",
            {
                "account_id": "acct_beacon",
                "to": "ravi@beacon.example",
                "subject": "Beacon Health renewal",
                "body": "Beacon Health renews on 2026-12-20. Can we meet?",
            },
        ),
    ]
