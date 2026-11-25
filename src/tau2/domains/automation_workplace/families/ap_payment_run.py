"""Weekly accounts-payable payment run: one released cash amount, many bills.

Decisions interact: queue order and the release decide which bills fit, credits and
early-payment discounts change what each bill consumes, and an earlier bill on a
purchase order can make a later one exceed the receipted amount. A payment call may
time out after the payment was actually recorded.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from pydantic import BaseModel, Field

from tau2.environment.db import BaseModelNoExtra

FAMILY_ID = "ap_payment_run"
PAGE_SIZE = 6
SLACK_PAGE_SIZE = 8


class BillLine(BaseModelNoExtra):
    description: str
    amount: float


class Approval(BaseModelNoExtra):
    approver: str
    approved_at: str


class Bill(BaseModelNoExtra):
    bill_id: str
    vendor_id: str
    invoice_number: str
    invoice_date: str
    due_date: str
    terms: str
    currency: str
    amount: float
    amount_due: float
    po_id: str = ""
    status: str
    approval: Approval | None = None
    remit_to_note: str = ""
    lines: list[BillLine] = Field(default_factory=list)
    hold_reason_codes: list[str] = Field(default_factory=list)
    scheduled_run_date: str = ""
    memo: str = ""
    attachment_ids: list[str] = Field(default_factory=list)


class Payment(BaseModelNoExtra):
    payment_id: str
    bill_id: str
    vendor_id: str
    invoice_number: str
    invoice_date: str
    amount: float
    currency: str
    bank_account_id: str
    paid_on: str
    status: str


class VendorCredit(BaseModelNoExtra):
    credit_id: str
    vendor_id: str
    currency: str
    amount: float
    issued_on: str
    reason: str
    status: str
    applied_to_bill_id: str = ""


class Delegation(BaseModelNoExtra):
    delegation_id: str
    delegator: str
    delegate: str
    starts_on: str
    ends_on: str
    scope: str


class Person(BaseModelNoExtra):
    username: str
    name: str
    title: str
    email: str
    approval_limit_usd: float


class BankAccount(BaseModelNoExtra):
    bank_account_id: str
    currency: str
    last4: str
    status: str
    added_on: str
    note: str = ""


class Vendor(BaseModelNoExtra):
    vendor_id: str
    name: str
    ap_email: str
    bank_accounts: list[BankAccount] = Field(default_factory=list)
    notes: str = ""


class POLine(BaseModelNoExtra):
    line_id: str
    description: str
    amount: float
    received_amount: float


class PurchaseOrder(BaseModelNoExtra):
    po_id: str
    vendor_id: str
    currency: str
    status: str
    invoiced_to_date: float
    lines: list[POLine] = Field(default_factory=list)


class FxRate(BaseModelNoExtra):
    base_currency: str
    quote_currency: str
    rate_date: str
    rate: float
    source: str


class Mail(BaseModelNoExtra):
    message_id: str
    sender: str
    to: list[str]
    subject: str
    body: str
    sent_at: str
    outbound: bool = False
    attachment_ids: list[str] = Field(default_factory=list)


class Attachment(BaseModelNoExtra):
    attachment_id: str
    filename: str
    content_type: str
    path: str


class SlackMessage(BaseModelNoExtra):
    message_id: str
    channel: str
    text: str
    user: str = "ap-bot"
    ts: str = ""
    thread_ts: str = ""


class Sheet(BaseModelNoExtra):
    sheet_id: str
    title: str
    columns: list[str]
    rows: list[dict[str, str]] = Field(default_factory=list)


class InjectedFault(BaseModelNoExtra):
    tool_name: str
    match: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any]
    remaining: int = 1
    applies_write: bool = False


class PaymentRunWorld(BaseModelNoExtra):
    task_id: str = ""
    current_time: str = ""
    run_date: str = ""
    payer_email: str = "ap@atlas.example"
    bills: dict[str, Bill] = Field(default_factory=dict)
    payments: dict[str, Payment] = Field(default_factory=dict)
    credits: dict[str, VendorCredit] = Field(default_factory=dict)
    delegations: list[Delegation] = Field(default_factory=list)
    people: dict[str, Person] = Field(default_factory=dict)
    vendors: dict[str, Vendor] = Field(default_factory=dict)
    purchase_orders: dict[str, PurchaseOrder] = Field(default_factory=dict)
    fx_rates: list[FxRate] = Field(default_factory=list)
    mailbox: dict[str, Mail] = Field(default_factory=dict)
    slack_messages: dict[str, SlackMessage] = Field(default_factory=dict)
    injected_faults: list[InjectedFault] = Field(default_factory=list)
    attachments: dict[str, Attachment] = Field(default_factory=dict)
    sheets: dict[str, Sheet] = Field(default_factory=dict)


class ListBillsArgs(BaseModelNoExtra):
    status: str | None = None
    vendor_id: str | None = None
    page: int = 1


class BillIdArgs(BaseModelNoExtra):
    bill_id: str


class ListPaymentsArgs(BaseModelNoExtra):
    vendor_id: str | None = None
    bill_id: str | None = None


class VendorIdArgs(BaseModelNoExtra):
    vendor_id: str


class ApplyCreditArgs(BaseModelNoExtra):
    credit_id: str
    bill_id: str


class EmptyArgs(BaseModelNoExtra):
    pass


class POArgs(BaseModelNoExtra):
    po_id: str


class FxArgs(BaseModelNoExtra):
    base_currency: str
    quote_currency: str
    rate_date: str


class CreatePaymentArgs(BaseModelNoExtra):
    bill_id: str
    amount: float
    currency: str
    bank_account_id: str


class UpdateBillArgs(BaseModelNoExtra):
    bill_id: str
    status: str | None = None
    hold_reason_codes: list[str] | None = None
    scheduled_run_date: str | None = None
    memo: str | None = None


class SearchMailArgs(BaseModelNoExtra):
    query: str


class SendMailArgs(BaseModelNoExtra):
    to: list[str]
    subject: str
    body: str


class AttachmentArgs(BaseModelNoExtra):
    attachment_id: str


class SheetArgs(BaseModelNoExtra):
    sheet_id: str


class AppendRowArgs(BaseModelNoExtra):
    sheet_id: str
    values: dict[str, str]


class SlackPostArgs(BaseModelNoExtra):
    channel: str
    text: str
    thread_ts: str | None = None


class SlackHistoryArgs(BaseModelNoExtra):
    channel: str
    page: int = 1


class SlackThreadArgs(BaseModelNoExtra):
    channel: str
    thread_ts: str


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
    "netsuite_list_bills_v1": _entry(
        "List vendor bills, optionally filtered by status or vendor. Paginated.",
        ListBillsArgs,
        False,
    ),
    "netsuite_get_bill_v1": _entry("Get one vendor bill.", BillIdArgs, False),
    "netsuite_list_payments_v1": _entry(
        "List payment register entries by vendor or bill.", ListPaymentsArgs, False
    ),
    "netsuite_list_vendor_credits_v1": _entry(
        "List a vendor's credit memos.", VendorIdArgs, False
    ),
    "netsuite_apply_vendor_credit_v1": _entry(
        "Apply an open vendor credit memo to a bill.", ApplyCreditArgs, True
    ),
    "netsuite_list_approval_delegations_v1": _entry(
        "List approval delegations and approver records.", EmptyArgs, False
    ),
    "netsuite_create_payment_v1": _entry(
        "Submit a payment for a bill to the payments gateway.",
        CreatePaymentArgs,
        True,
    ),
    "netsuite_update_bill_v1": _entry(
        "Update a bill's status, hold reasons, scheduled run date or memo.",
        UpdateBillArgs,
        True,
    ),
    "vendor_master_get_vendor_v1": _entry(
        "Get a vendor master record.", VendorIdArgs, False
    ),
    "coupa_get_purchase_order_v1": _entry("Get a Coupa purchase order.", POArgs, False),
    "treasury_get_fx_rate_v1": _entry(
        "Get the treasury FX rate for a date.", FxArgs, False
    ),
    "gmail_search_messages_v1": _entry(
        "Search the AP shared mailbox.", SearchMailArgs, False
    ),
    "gmail_send_message_v1": _entry("Send one email.", SendMailArgs, True),
    "slack_chat_post_message": _entry("Post one Slack message.", SlackPostArgs, True),
    "slack_list_channels_v1": _entry("List Slack channels.", EmptyArgs, False),
    "slack_get_channel_history_v1": _entry(
        "Get a channel's top-level messages, newest first. Paginated.",
        SlackHistoryArgs,
        False,
    ),
    "slack_get_thread_v1": _entry(
        "Get a Slack message and its thread replies.", SlackThreadArgs, False
    ),
    "files_get_attachment_v1": _entry(
        "Open a file attached to a bill, email or document.", AttachmentArgs, False
    ),
    "sheets_list_v1": _entry("List shared spreadsheets.", EmptyArgs, False),
    "sheets_get_rows_v1": _entry(
        "Get a spreadsheet's columns and rows.", SheetArgs, False
    ),
    "sheets_append_row_v1": _entry(
        "Append one row to a spreadsheet.", AppendRowArgs, True
    ),
}


def _bill(world: PaymentRunWorld, bill_id: str) -> Bill:
    if bill_id not in world.bills:
        raise ValueError(f"Bill not found: {bill_id}")
    return world.bills[bill_id]


def _list_bills(world: PaymentRunWorld, raw: dict) -> dict:
    args = ListBillsArgs.model_validate(raw)
    rows = [
        b
        for b in sorted(world.bills.values(), key=lambda b: b.bill_id)
        if (args.status is None or b.status == args.status)
        and (args.vendor_id is None or b.vendor_id == args.vendor_id)
    ]
    pages = max(1, -(-len(rows) // PAGE_SIZE))
    page = rows[(args.page - 1) * PAGE_SIZE : args.page * PAGE_SIZE]
    summary = [
        b.model_dump(
            include={
                "bill_id",
                "vendor_id",
                "invoice_number",
                "due_date",
                "currency",
                "amount",
                "status",
            }
        )
        for b in page
    ]
    return {"items": summary, "page": args.page, "total_pages": pages}


def _get_bill(world: PaymentRunWorld, raw: dict) -> dict:
    return {"bill": _dump(_bill(world, BillIdArgs.model_validate(raw).bill_id))}


def _list_payments(world: PaymentRunWorld, raw: dict) -> dict:
    args = ListPaymentsArgs.model_validate(raw)
    if args.vendor_id is None and args.bill_id is None:
        raise ValueError("Provide vendor_id or bill_id")
    rows = [
        p.model_dump()
        for p in world.payments.values()
        if (args.vendor_id is None or p.vendor_id == args.vendor_id)
        and (args.bill_id is None or p.bill_id == args.bill_id)
    ]
    return {"items": rows}


def _list_credits(world: PaymentRunWorld, raw: dict) -> dict:
    vendor_id = VendorIdArgs.model_validate(raw).vendor_id
    return {
        "items": [
            c.model_dump() for c in world.credits.values() if c.vendor_id == vendor_id
        ]
    }


def _apply_credit(world: PaymentRunWorld, raw: dict) -> dict:
    args = ApplyCreditArgs.model_validate(raw)
    credit = world.credits.get(args.credit_id)
    bill = _bill(world, args.bill_id)
    if credit is None or credit.status != "open":
        raise ValueError("Credit not found or not open")
    if credit.vendor_id != bill.vendor_id or credit.currency != bill.currency:
        raise ValueError("Credit vendor or currency does not match the bill")
    credit.status = "applied"
    credit.applied_to_bill_id = bill.bill_id
    bill.amount_due = round(bill.amount_due - credit.amount, 2)
    return {"credit": credit.model_dump(), "bill": bill.model_dump()}


def _list_delegations(world: PaymentRunWorld, raw: dict) -> dict:
    EmptyArgs.model_validate(raw)
    return {
        "delegations": [d.model_dump() for d in world.delegations],
        "approvers": [p.model_dump() for p in world.people.values()],
    }


def _create_payment(world: PaymentRunWorld, raw: dict) -> dict:
    args = CreatePaymentArgs.model_validate(raw)
    bill = _bill(world, args.bill_id)
    vendor = world.vendors[bill.vendor_id]
    if args.bank_account_id not in {a.bank_account_id for a in vendor.bank_accounts}:
        raise ValueError("Bank account is not on this vendor's record")
    if bill.status not in {"approved", "payment_submitted"}:
        raise ValueError(f"Bill status {bill.status!r} cannot be paid")
    run = world.run_date.replace("-", "")
    count = sum(p.paid_on == world.run_date for p in world.payments.values())
    payment = Payment(
        payment_id=f"PAY-{run}-{count + 1:03d}",
        bill_id=bill.bill_id,
        vendor_id=bill.vendor_id,
        invoice_number=bill.invoice_number,
        invoice_date=bill.invoice_date,
        amount=round(args.amount, 2),
        currency=args.currency.upper(),
        bank_account_id=args.bank_account_id,
        paid_on=world.run_date,
        status="submitted",
    )
    world.payments[payment.payment_id] = payment
    bill.status = "payment_submitted"
    return {"payment": payment.model_dump()}


def _update_bill(world: PaymentRunWorld, raw: dict) -> dict:
    args = UpdateBillArgs.model_validate(raw)
    bill = _bill(world, args.bill_id)
    if args.status is not None:
        allowed = {"approved", "on_hold", "rejected"}
        if args.status not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        bill.status = args.status
    if args.hold_reason_codes is not None:
        bill.hold_reason_codes = sorted(
            {c.strip().upper() for c in args.hold_reason_codes}
        )
    if args.scheduled_run_date is not None:
        bill.scheduled_run_date = args.scheduled_run_date
    if args.memo is not None:
        bill.memo = args.memo
    return {"bill": bill.model_dump()}


def _get_vendor(world: PaymentRunWorld, raw: dict) -> dict:
    vendor_id = VendorIdArgs.model_validate(raw).vendor_id
    if vendor_id not in world.vendors:
        raise ValueError("Vendor not found")
    data = world.vendors[vendor_id].model_dump()
    if not data["notes"]:
        del data["notes"]
    return {"vendor": data}


def _get_po(world: PaymentRunWorld, raw: dict) -> dict:
    po_id = POArgs.model_validate(raw).po_id
    if po_id not in world.purchase_orders:
        raise ValueError("Purchase order not found")
    return {"purchase_order": world.purchase_orders[po_id].model_dump()}


def _get_fx(world: PaymentRunWorld, raw: dict) -> dict:
    args = FxArgs.model_validate(raw)
    for rate in world.fx_rates:
        if (
            rate.base_currency == args.base_currency.upper()
            and rate.quote_currency == args.quote_currency.upper()
            and rate.rate_date == args.rate_date
        ):
            return {"rate": rate.model_dump()}
    raise ValueError("No treasury rate published for that pair and date")


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9$]+", text.lower()))


def _search_mail(world: PaymentRunWorld, raw: dict) -> dict:
    terms = _tokens(SearchMailArgs.model_validate(raw).query)
    hits = []
    for mail in world.mailbox.values():
        score = len(terms & _tokens(f"{mail.sender} {mail.subject} {mail.body}"))
        if score:
            hits.append((-score, mail.sent_at, mail))
    hits.sort(key=lambda h: (h[0], h[1]))
    return {"messages": [_dump(h[2]) for h in hits[:8]]}


def _dump(record: Bill | Mail) -> dict:
    data = record.model_dump()
    if not data["attachment_ids"]:
        del data["attachment_ids"]
    return data


def _get_attachment(world: PaymentRunWorld, raw: dict) -> dict:
    attachment_id = AttachmentArgs.model_validate(raw).attachment_id
    if attachment_id not in world.attachments:
        raise ValueError(f"Attachment not found: {attachment_id}")
    file = world.attachments[attachment_id]
    return {
        "attachment_id": file.attachment_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "_image_paths": [file.path],
    }


def _sheet(world: PaymentRunWorld, sheet_id: str) -> Sheet:
    if sheet_id not in world.sheets:
        raise ValueError(f"Sheet not found: {sheet_id}")
    return world.sheets[sheet_id]


def _list_sheets(world: PaymentRunWorld, raw: dict) -> dict:
    EmptyArgs.model_validate(raw)
    return {
        "sheets": [
            {"sheet_id": s.sheet_id, "title": s.title} for s in world.sheets.values()
        ]
    }


def _get_rows(world: PaymentRunWorld, raw: dict) -> dict:
    sheet = _sheet(world, SheetArgs.model_validate(raw).sheet_id)
    return sheet.model_dump()


def _append_row(world: PaymentRunWorld, raw: dict) -> dict:
    args = AppendRowArgs.model_validate(raw)
    sheet = _sheet(world, args.sheet_id)
    unknown = set(args.values) - set(sheet.columns)
    if unknown:
        raise ValueError(f"Unknown columns: {sorted(unknown)}")
    row = {column: str(args.values.get(column, "")).strip() for column in sheet.columns}
    sheet.rows.append(row)
    return {"row_number": len(sheet.rows) + 1, "row": row}


def _send_mail(world: PaymentRunWorld, raw: dict) -> dict:
    args = SendMailArgs.model_validate(raw)
    count = sum(m.outbound for m in world.mailbox.values())
    mail = Mail(
        message_id=f"sent_{count + 1:03d}",
        sender=world.payer_email,
        to=[t.strip().lower() for t in args.to],
        subject=args.subject,
        body=args.body,
        sent_at=world.current_time,
        outbound=True,
    )
    world.mailbox[mail.message_id] = mail
    return {"id": mail.message_id}


def _post_slack(world: PaymentRunWorld, raw: dict) -> dict:
    args = SlackPostArgs.model_validate(raw)
    message_id = f"slack_{len(world.slack_messages) + 1:03d}"
    world.slack_messages[message_id] = SlackMessage(
        message_id=message_id,
        channel=args.channel.lstrip("#"),
        text=args.text,
        ts=f"{world.current_time}#{len(world.slack_messages) + 1}",
        thread_ts=args.thread_ts or "",
    )
    return {"ok": True, "message_id": message_id}


def _slack_view(message: SlackMessage) -> dict:
    return message.model_dump(include={"user", "ts", "text"})


def _list_channels(world: PaymentRunWorld, raw: dict) -> dict:
    EmptyArgs.model_validate(raw)
    return {"channels": sorted({m.channel for m in world.slack_messages.values()})}


def _channel_history(world: PaymentRunWorld, raw: dict) -> dict:
    args = SlackHistoryArgs.model_validate(raw)
    channel = args.channel.lstrip("#")
    messages = [m for m in world.slack_messages.values() if m.channel == channel]
    top = sorted(
        (m for m in messages if m.thread_ts in ("", m.ts)),
        key=lambda m: m.ts,
        reverse=True,
    )
    pages = max(1, -(-len(top) // SLACK_PAGE_SIZE))
    page = top[(args.page - 1) * SLACK_PAGE_SIZE : args.page * SLACK_PAGE_SIZE]
    items = []
    for m in page:
        view = _slack_view(m)
        view["reply_count"] = sum(
            r.thread_ts == m.ts and r.ts != m.ts for r in messages
        )
        items.append(view)
    return {
        "channel": channel,
        "messages": items,
        "page": args.page,
        "total_pages": pages,
    }


def _thread(world: PaymentRunWorld, raw: dict) -> dict:
    args = SlackThreadArgs.model_validate(raw)
    channel = args.channel.lstrip("#")
    rows = sorted(
        (
            m
            for m in world.slack_messages.values()
            if m.channel == channel and args.thread_ts in (m.ts, m.thread_ts)
        ),
        key=lambda m: m.ts,
    )
    if not rows:
        raise ValueError("Thread not found")
    return {"channel": channel, "messages": [_slack_view(m) for m in rows]}


_HANDLERS: dict[str, Callable[[PaymentRunWorld, dict], dict]] = {
    "netsuite_list_bills_v1": _list_bills,
    "netsuite_get_bill_v1": _get_bill,
    "netsuite_list_payments_v1": _list_payments,
    "netsuite_list_vendor_credits_v1": _list_credits,
    "netsuite_apply_vendor_credit_v1": _apply_credit,
    "netsuite_list_approval_delegations_v1": _list_delegations,
    "netsuite_create_payment_v1": _create_payment,
    "netsuite_update_bill_v1": _update_bill,
    "vendor_master_get_vendor_v1": _get_vendor,
    "coupa_get_purchase_order_v1": _get_po,
    "treasury_get_fx_rate_v1": _get_fx,
    "gmail_search_messages_v1": _search_mail,
    "gmail_send_message_v1": _send_mail,
    "slack_chat_post_message": _post_slack,
    "slack_list_channels_v1": _list_channels,
    "slack_get_channel_history_v1": _channel_history,
    "slack_get_thread_v1": _thread,
    "files_get_attachment_v1": _get_attachment,
    "sheets_list_v1": _list_sheets,
    "sheets_get_rows_v1": _get_rows,
    "sheets_append_row_v1": _append_row,
}


def validate_world(raw: dict[str, Any]) -> PaymentRunWorld:
    return PaymentRunWorld.model_validate(raw)


def _call(world: PaymentRunWorld, tool_name: str, arguments: str) -> str:
    if tool_name not in _HANDLERS:
        raise ValueError(f"Unknown payment-run tool: {tool_name}")
    try:
        raw = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"arguments must be valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("arguments must encode one JSON object")
    for fault in world.injected_faults:
        if (
            fault.remaining > 0
            and fault.tool_name == tool_name
            and all(raw.get(k) == v for k, v in fault.match.items())
        ):
            fault.remaining -= 1
            if fault.applies_write:
                _HANDLERS[tool_name](world, raw)
            return json.dumps(fault.response, sort_keys=True)
    return json.dumps(_HANDLERS[tool_name](world, raw), sort_keys=True)


def call_tool(
    raw_world: dict[str, Any], tool_name: str, arguments: str
) -> tuple[dict[str, Any], str]:
    world = validate_world(raw_world)
    response = _call(world, tool_name, arguments)
    return world.model_dump(mode="json"), response


def _digits(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d{3})", "", text)


def _mentions_amount(text: str, amount: float) -> bool:
    """Match an amount written with or without thousands separators or cents."""
    flat = _digits(text)
    if amount >= 1000 and amount % 1000 == 0:
        short = rf"(?<![\d.]){int(amount // 1000)}\s?[kK]\b"
        if re.search(short, flat):
            return True
    whole, cents = f"{amount:.2f}".split(".")
    pattern = rf"(?<![\d.]){whole}(\.{cents}|\.{cents.rstrip('0')})?(?!\d)"
    if cents == "00":
        pattern = rf"(?<![\d.]){whole}(\.00?)?(?!\d)"
    return re.search(pattern, flat) is not None


def _agent_posts(world: PaymentRunWorld) -> list[SlackMessage]:
    return [m for m in world.slack_messages.values() if m.user == "ap-bot"]


def _run_payments(world: PaymentRunWorld) -> list[Payment]:
    return [p for p in world.payments.values() if p.paid_on == world.run_date]


def check_assertion(raw_world: dict[str, Any], assertion: dict[str, Any]) -> bool:
    """Evaluate exact final state; conversation and call order are not inspected."""
    world = validate_world(raw_world)
    kind = assertion["type"]
    if kind == "pay_one_payment_exact":
        rows = [p for p in _run_payments(world) if p.bill_id == assertion["bill_id"]]
        return bool(
            len(rows) == 1
            and abs(rows[0].amount - assertion["amount"]) < 0.005
            and rows[0].currency == assertion["currency"]
            and rows[0].bank_account_id == assertion["bank_account_id"]
        )
    if kind == "pay_no_payment":
        return not any(p.bill_id == assertion["bill_id"] for p in _run_payments(world))
    if kind == "pay_run_payment_count":
        return len(_run_payments(world)) == assertion["count"]
    if kind == "pay_bill_state":
        bill = world.bills.get(assertion["bill_id"])
        return bool(
            bill
            and bill.status == assertion["status"]
            and set(bill.hold_reason_codes)
            == set(assertion.get("hold_reason_codes", []))
            and bill.scheduled_run_date == assertion.get("scheduled_run_date", "")
        )
    if kind == "pay_credit_applied":
        credit = world.credits.get(assertion["credit_id"])
        return bool(
            credit
            and credit.status == "applied"
            and credit.applied_to_bill_id == assertion["bill_id"]
        )
    if kind == "pay_vendor_banking_preserved":
        vendor = world.vendors.get(assertion["vendor_id"])
        return bool(
            vendor
            and [a.model_dump() for a in vendor.bank_accounts]
            == assertion["bank_accounts"]
        )
    if kind == "pay_one_email":
        sent = [m for m in world.mailbox.values() if m.outbound]
        to_target = [m for m in sent if assertion["to"] in m.to]
        text = " ".join(f"{m.subject} {m.body}" for m in to_target).lower()
        others = [
            m for m in sent if any(a in m.to for a in assertion.get("not_to", []))
        ]
        return bool(
            len(to_target) == 1
            and all(term.lower() in text for term in assertion.get("terms", []))
            and not others
        )
    if kind == "pay_remittance":
        sent = [
            m for m in world.mailbox.values() if m.outbound and assertion["to"] in m.to
        ]
        text = " ".join(f"{m.subject} {m.body}" for m in sent)
        return bool(
            len(sent) == 1
            and all(t.lower() in text.lower() for t in assertion["terms"])
            and all(_mentions_amount(text, a) for a in assertion["amounts"])
        )
    if kind == "pay_no_email_to":
        return not any(
            m.outbound and set(m.to) & set(assertion["recipients"])
            for m in world.mailbox.values()
        )
    if kind == "pay_one_slack_summary":
        posts = [m for m in _agent_posts(world) if m.channel == assertion["channel"]]
        return bool(
            len(posts) == 1
            and all(_mentions_amount(posts[0].text, a) for a in assertion["amounts"])
        )
    if kind == "pay_sheet_rows":
        sheet = world.sheets.get(assertion["sheet_id"])
        if sheet is None:
            return False
        key, expected = assertion["key_column"], assertion["rows"]
        rows = sheet.rows[assertion["seeded_rows"] :]
        if sorted(r.get(key, "") for r in rows) != sorted(expected):
            return False
        return all(
            all(r.get(c, "").upper() == v.upper() for c, v in expected[r[key]].items())
            for r in rows
        )
    if kind == "pay_slack_post":
        posts = [m for m in _agent_posts(world) if m.channel == assertion["channel"]]
        return bool(
            len(posts) == 1
            and any(t.lower() in posts[0].text.lower() for t in assertion["any_terms"])
        )
    if kind == "pay_agent_slack_post_count":
        return len(_agent_posts(world)) == assertion["count"]
    if kind == "pay_outbound_email_count":
        return sum(m.outbound for m in world.mailbox.values()) == assertion["count"]
    if kind == "pay_bill_unchanged":
        bill = world.bills.get(assertion["bill_id"])
        seeded = Bill.model_validate({"memo": "", **assertion["bill"]})
        return bool(
            bill
            and bill.model_dump(exclude={"memo"}) == seeded.model_dump(exclude={"memo"})
        )
    raise ValueError(f"Unknown payment-run assertion type: {kind}")


def golden_call_sequence(task_spec: dict[str, Any]) -> list[tuple[str, dict]]:
    """Return the task file's deterministic, policy-compliant write trajectory."""
    return [(name, args) for name, args in task_spec["golden_writes"]]


def negative_call_sequence(task_spec: dict[str, Any]) -> list[tuple[str, dict]]:
    """Return a plausible requester-following trajectory that must fail."""
    golden = golden_call_sequence(task_spec)
    return [step for step in golden if step[0] != "netsuite_update_bill_v1"]
