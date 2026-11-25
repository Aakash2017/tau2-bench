"""Resume a half-finished renewal-notice batch from a previous session's handoff.

The handoff note is the agent's own earlier summary and is partly wrong: one notice
bounced, one CRM write never landed, one notice quoted the wrong price, a skipped
account's legal hold has since been released, and an in-scope account on a later
page was never reached. Remaining accounts need parent coverage, legal-hold and
currency-threshold decisions.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from pydantic import BaseModel, Field

from tau2.environment.db import BaseModelNoExtra

FAMILY_ID = "renewal_handoff"
PAGE_SIZE = 5


class Contact(BaseModelNoExtra):
    email: str
    name: str
    role: str
    verified: bool
    opted_out: bool = False
    active: bool = True
    updated_on: str = ""


class Contract(BaseModelNoExtra):
    contract_id: str
    master_agreement_id: str = ""
    uplift_cap_pct: float | None = None
    notes: str = ""


class Account(BaseModelNoExtra):
    account_id: str
    name: str
    parent_account_id: str = ""
    renewal_date: str
    currency: str
    arr: float
    contract: Contract
    contacts: list[Contact] = Field(default_factory=list)
    renewal_stage: str = "not_started"
    notice_sent_on: str = ""
    renewal_price: float | None = None


class LegalHold(BaseModelNoExtra):
    hold_id: str
    account_id: str
    scope: str
    status: str
    placed_on: str
    released_on: str = ""
    note: str = ""


class Mail(BaseModelNoExtra):
    message_id: str
    sender: str
    to: list[str]
    subject: str
    body: str
    sent_at: str
    folder: str
    session: str = "seed"


class SlackMessage(BaseModelNoExtra):
    message_id: str
    channel: str
    author: str
    text: str
    posted_at: str
    session: str = "seed"


class FxRate(BaseModelNoExtra):
    base_currency: str
    quote_currency: str
    rate_date: str
    rate: float


class RenewalWorld(BaseModelNoExtra):
    task_id: str = ""
    current_time: str = ""
    today: str = ""
    sender_email: str = "renewals@atlas.example"
    accounts: dict[str, Account] = Field(default_factory=dict)
    legal_holds: list[LegalHold] = Field(default_factory=list)
    mailbox: dict[str, Mail] = Field(default_factory=dict)
    slack_messages: dict[str, SlackMessage] = Field(default_factory=dict)
    fx_rates: list[FxRate] = Field(default_factory=list)


class ListRenewalsArgs(BaseModelNoExtra):
    renewal_from: str
    renewal_to: str
    page: int = 1


class AccountArgs(BaseModelNoExtra):
    account_id: str


class UpdateRenewalArgs(BaseModelNoExtra):
    account_id: str
    renewal_stage: str | None = None
    notice_sent_on: str | None = None
    renewal_price: float | None = None


class EmptyArgs(BaseModelNoExtra):
    pass


class MailSearchArgs(BaseModelNoExtra):
    query: str = ""
    folder: str | None = None


class SendArgs(BaseModelNoExtra):
    to: list[str]
    subject: str
    body: str


class SlackSearchArgs(BaseModelNoExtra):
    channel: str
    query: str = ""


class SlackPostArgs(BaseModelNoExtra):
    channel: str
    text: str


class FxArgs(BaseModelNoExtra):
    base_currency: str
    quote_currency: str
    rate_date: str


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
    "salesforce_list_renewals_v1": _entry(
        "List accounts by renewal date range. Paginated.", ListRenewalsArgs, False
    ),
    "salesforce_get_account_v1": _entry(
        "Get an account with contract terms, contacts and renewal fields.",
        AccountArgs,
        False,
    ),
    "salesforce_update_renewal_v1": _entry(
        "Update an account's renewal stage, notice date or renewal price.",
        UpdateRenewalArgs,
        True,
    ),
    "legal_list_holds_v1": _entry("List legal holds.", EmptyArgs, False),
    "gmail_search_v1": _entry(
        "Search the renewals mailbox (inbox and sent).", MailSearchArgs, False
    ),
    "gmail_send_message_v1": _entry("Send one email.", SendArgs, True),
    "slack_search_messages_v1": _entry(
        "Search messages in one Slack channel.", SlackSearchArgs, False
    ),
    "slack_chat_post_message": _entry("Post one Slack message.", SlackPostArgs, True),
    "treasury_get_fx_rate_v1": _entry(
        "Get the treasury FX rate for a date.", FxArgs, False
    ),
}


def _account(world: RenewalWorld, account_id: str) -> Account:
    if account_id not in world.accounts:
        raise ValueError(f"Account not found: {account_id}")
    return world.accounts[account_id]


def _list(world: RenewalWorld, raw: dict) -> dict:
    args = ListRenewalsArgs.model_validate(raw)
    rows = sorted(
        (
            a
            for a in world.accounts.values()
            if args.renewal_from <= a.renewal_date <= args.renewal_to
        ),
        key=lambda a: a.name,
    )
    pages = max(1, -(-len(rows) // PAGE_SIZE))
    page = rows[(args.page - 1) * PAGE_SIZE : args.page * PAGE_SIZE]
    keep = {"account_id", "name", "renewal_date", "currency", "arr", "renewal_stage"}
    return {
        "items": [a.model_dump(include=keep) for a in page],
        "page": args.page,
        "total_pages": pages,
    }


def _get(world: RenewalWorld, raw: dict) -> dict:
    account = _account(world, AccountArgs.model_validate(raw).account_id)
    return {"account": account.model_dump()}


def _update(world: RenewalWorld, raw: dict) -> dict:
    args = UpdateRenewalArgs.model_validate(raw)
    account = _account(world, args.account_id)
    stages = {"not_started", "notice_sent", "covered_by_parent", "legal_hold"}
    if args.renewal_stage is not None:
        if args.renewal_stage not in stages:
            raise ValueError(f"renewal_stage must be one of {sorted(stages)}")
        account.renewal_stage = args.renewal_stage
    if args.notice_sent_on is not None:
        account.notice_sent_on = args.notice_sent_on
    if args.renewal_price is not None:
        account.renewal_price = round(args.renewal_price, 2)
    return {"account": account.model_dump()}


def _holds(world: RenewalWorld, raw: dict) -> dict:
    EmptyArgs.model_validate(raw)
    return {"holds": [h.model_dump() for h in world.legal_holds]}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9@.]+", text.lower()))


def _search_mail(world: RenewalWorld, raw: dict) -> dict:
    args = MailSearchArgs.model_validate(raw)
    terms = _tokens(args.query)
    rows = []
    for m in world.mailbox.values():
        if args.folder and m.folder != args.folder:
            continue
        hay = _tokens(f"{m.sender} {' '.join(m.to)} {m.subject} {m.body}")
        if not terms or terms & hay:
            rows.append((-len(terms & hay), m.sent_at, m))
    rows.sort(key=lambda r: (r[0], r[1]))
    return {"messages": [r[2].model_dump(exclude={"session"}) for r in rows[:10]]}


def _send(world: RenewalWorld, raw: dict) -> dict:
    args = SendArgs.model_validate(raw)
    n = sum(m.session == "agent" for m in world.mailbox.values())
    mail = Mail(
        message_id=f"sent_new_{n + 1:03d}",
        sender=world.sender_email,
        to=[t.strip().lower() for t in args.to],
        subject=args.subject,
        body=args.body,
        sent_at=world.current_time,
        folder="sent",
        session="agent",
    )
    world.mailbox[mail.message_id] = mail
    return {"id": mail.message_id}


def _search_slack(world: RenewalWorld, raw: dict) -> dict:
    args = SlackSearchArgs.model_validate(raw)
    terms = _tokens(args.query)
    rows = [
        m.model_dump(exclude={"session"})
        for m in sorted(world.slack_messages.values(), key=lambda m: m.posted_at)
        if m.channel == args.channel.lstrip("#")
        and (not terms or terms & _tokens(m.text))
    ]
    return {"messages": rows}


def _post(world: RenewalWorld, raw: dict) -> dict:
    args = SlackPostArgs.model_validate(raw)
    mid = f"slack_new_{sum(m.session == 'agent' for m in world.slack_messages.values()) + 1:03d}"
    world.slack_messages[mid] = SlackMessage(
        message_id=mid,
        channel=args.channel.lstrip("#"),
        author="Renewals Assistant",
        text=args.text,
        posted_at=world.current_time,
        session="agent",
    )
    return {"ok": True, "message_id": mid}


def _fx(world: RenewalWorld, raw: dict) -> dict:
    args = FxArgs.model_validate(raw)
    for r in world.fx_rates:
        if (
            r.base_currency == args.base_currency.upper()
            and r.quote_currency == args.quote_currency.upper()
            and r.rate_date == args.rate_date
        ):
            return {"rate": r.model_dump()}
    raise ValueError("No treasury rate published for that pair and date")


_HANDLERS: dict[str, Callable[[RenewalWorld, dict], dict]] = {
    "salesforce_list_renewals_v1": _list,
    "salesforce_get_account_v1": _get,
    "salesforce_update_renewal_v1": _update,
    "legal_list_holds_v1": _holds,
    "gmail_search_v1": _search_mail,
    "gmail_send_message_v1": _send,
    "slack_search_messages_v1": _search_slack,
    "slack_chat_post_message": _post,
    "treasury_get_fx_rate_v1": _fx,
}


def validate_world(raw: dict[str, Any]) -> RenewalWorld:
    return RenewalWorld.model_validate(raw)


def call_tool(
    raw_world: dict[str, Any], tool_name: str, arguments: str
) -> tuple[dict[str, Any], str]:
    world = validate_world(raw_world)
    if tool_name not in _HANDLERS:
        raise ValueError(f"Unknown renewal tool: {tool_name}")
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


def _new_mail(world: RenewalWorld) -> list[Mail]:
    return [m for m in world.mailbox.values() if m.session == "agent"]


def check_assertion(raw_world: dict[str, Any], assertion: dict[str, Any]) -> bool:
    """Evaluate exact final state; conversation and call order are not inspected."""
    world = validate_world(raw_world)
    kind = assertion["type"]
    if kind == "renewal_crm_exact":
        a = world.accounts.get(assertion["account_id"])
        return bool(
            a
            and a.renewal_stage == assertion["renewal_stage"]
            and a.notice_sent_on == assertion.get("notice_sent_on", "")
            and a.renewal_price == assertion.get("renewal_price")
        )
    if kind == "renewal_one_notice":
        rows = [m for m in _new_mail(world) if assertion["to"] in m.to]
        return bool(
            len(rows) == 1
            and _mentions_amount(
                rows[0].subject + " " + rows[0].body, assertion["price"]
            )
            and not any(
                _mentions_amount(rows[0].body, wrong)
                for wrong in assertion.get("wrong_prices", [])
            )
        )
    if kind == "renewal_no_new_email":
        return not any(
            set(m.to) & set(assertion["recipients"]) for m in _new_mail(world)
        )
    if kind == "renewal_new_email_count":
        return len(_new_mail(world)) == assertion["count"]
    if kind == "renewal_one_slack_post":
        return (
            sum(
                m.session == "agent" and m.channel == assertion["channel"]
                for m in world.slack_messages.values()
            )
            == 1
        )
    raise ValueError(f"Unknown renewal assertion type: {kind}")


def golden_call_sequence(task_spec: dict[str, Any]) -> list[tuple[str, dict]]:
    """Return the task file's deterministic, policy-compliant write trajectory."""
    return [(name, args) for name, args in task_spec["golden_writes"]]


def negative_call_sequence(task_spec: dict[str, Any]) -> list[tuple[str, dict]]:
    """Trust the handoff note: only finish the accounts it lists as remaining."""
    return [
        step
        for step in golden_call_sequence(task_spec)
        if step[1].get("account_id") in {"acc_elmstead", "acc_fernhill", "acc_glenrock"}
        or any(t.endswith(("fernhill.example",)) for t in step[1].get("to", []))
    ]
