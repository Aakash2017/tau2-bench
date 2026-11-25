"""Build vendor_invoice_004: the AP payment run without a checklist.

Derived from vendor_invoice_002 (run its builder first). Difficulty moves from
evaluating spelled-out checks to finding obligations in the records:

- the procedure no longer lists the eligibility checks or the closing steps;
- Treasury's revision email, not the KB, asks for the #treasury-ops total;
- a Controller email requires an exceptions-log row for every held or rejected bill;
- a Procurement email asks for a #procurement note if Corvid's invoice is paid;
- Pinecrest has a notice of assignment, so payment and remittance go to the factor;
- the AP manager's opening request carries the stale release and the Lumen belief,
  and she never asks for a summary.

Usage: python build_vendor_invoice_004.py data/tau2/domains/automation_workplace/interactive
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
TASK_ID = "vendor_invoice_004"
RUN = "2026-12-15"
KB_FILE = "knowledge/vendor_invoice_payment_run_v4.json"
SHEET = "sh_ap_exceptions_fy26"
FACTOR_ACCOUNT = "ba_pinecrest_harbor"
FACTOR_EMAIL = "cash@harborfunding.example"

base = json.loads((INTERACTIVE / "tasks/vendor_invoice_002.json").read_text())
kb = deepcopy(json.loads((INTERACTIVE / base["knowledge_file"]).read_text()))
task = deepcopy(base)
world = task["family_world"]
world["task_id"] = TASK_ID

# Knowledge: policy stays, checklist and closing steps go.
docs = {d["document_id"]: d for d in kb}
procedure = docs["kb_ap_payment_run_procedure_2026_11"]
content = procedure["content"]
checklist = (
    "Before a candidate is paid it must pass every eligibility check in the AP "
    "standards (approval authority, duplicate review, receipt matching, vendor "
    "credits, banking). A bill that fails a check is handled under that standard "
    "and is not part of the run."
)
assert checklist in content
content = content.replace(
    checklist,
    "A candidate is paid only if it is eligible under the AP standards; an "
    "ineligible bill is handled under the standard it fails.",
)
remit_start = content.index("## Remittance advice")
remittance = content[remit_start : content.index("## Closing the run")].strip()
content = content[:remit_start].rstrip()
procedure["content"] = content
kb.insert(
    kb.index(docs["kb_treasury_fx_2026_06"]) + 1,
    {
        "document_id": "kb_ap_remittance_advice_2026_10",
        "title": "Remittance advice",
        "status": "current",
        "updated_at": "2026-10-12T09:00:00-07:00",
        "content": remittance.removeprefix("## Remittance advice").strip(),
        "tags": ["ap", "remittance", "vendor-communication"],
    },
)
banking = docs["kb_ap_vendor_banking_2026_09"]
banking["content"] += (
    "\n\nNotices of assignment: when a vendor has assigned its receivables to a "
    "factor, the vendor master records the notice. Covered invoices are paid to "
    "the assignee's verified account and remittance advice goes to the assignee "
    "contact named in the notice instead of the vendor."
)

# Records: obligations that live only in the data.
pinecrest = world["vendors"]["ven_pinecrest"]
pinecrest["bank_accounts"].append(
    {
        "bank_account_id": FACTOR_ACCOUNT,
        "currency": "USD",
        "last4": "4410",
        "status": "verified",
        "added_on": "2026-10-06",
        "note": "Harbor Funding LLC (assignee).",
    }
)
pinecrest["notes"] = (
    "Notice of assignment received 2026-10-02; Vendor Management callback "
    "completed 2026-10-06. Pinecrest Staffing has assigned receivables to Harbor "
    "Funding LLC. Invoices dated on or after 2026-10-01: pay to "
    f"{FACTOR_ACCOUNT}; remittance advice to {FACTOR_EMAIL}."
)
assert world["bills"]["bill_2206"]["invoice_date"] >= "2026-10-01"

world["mailbox"]["msg_tr_1214"]["body"] = (
    "Revising Tuesday's release to $100,000 after the payroll true-up came in "
    "higher than forecast. Please keep the run inside this figure and post the "
    "final USD total in #treasury-ops once it's out so we can match the bank "
    "file. Gwen"
)
world["mailbox"]["msg_controller_exceptions"] = {
    "message_id": "msg_controller_exceptions",
    "sender": "renee.cho@atlas.example",
    "to": ["ap@atlas.example", "dana.okafor@atlas.example"],
    "subject": "Payment runs: exceptions log for audit",
    "body": "Team, starting with the December payment runs, every bill that is "
    "put on hold or rejected during a run needs one row in the 'AP Exceptions "
    "FY26' sheet (run date, bill, vendor, reason code, follow-up owner). Bills "
    "that are only deferred and stay approved don't go in the log. External "
    "audit will sample from it in January. Thanks, Renee (Controller)",
    "sent_at": "2026-11-30T11:20:00-08:00",
    "outbound": False,
}
world["mailbox"]["msg_marco_corvid"] = {
    "message_id": "msg_marco_corvid",
    "sender": "marco.diaz@atlas.example",
    "to": ["ap@atlas.example"],
    "subject": "Corvid - November invoice",
    "body": "Hi AP, Corvid says they'll pause our data feed if the November "
    "invoice isn't paid this week. If it goes out in Tuesday's run, can you drop "
    "a note in #procurement so I can let their account team know? Thanks, Marco "
    "(Procurement)",
    "sent_at": "2026-12-14T10:05:00-08:00",
    "outbound": False,
}
SEEDED_ROWS = [
    {
        "run_date": "2026-12-01",
        "bill_id": "bill_2171",
        "vendor": "Sable Courier",
        "reason_code": "RECEIPT_VARIANCE",
        "owner": "receiving@atlas.example",
        "note": "Two pallets not received against PO-5402.",
    },
    {
        "run_date": "2026-12-08",
        "bill_id": "bill_2189",
        "vendor": "Ridgeway Security",
        "reason_code": "DUPLICATE",
        "owner": "ap@atlas.example",
        "note": "Resend of RS-7710, paid 11/24.",
    },
]
world["sheets"] = {
    SHEET: {
        "sheet_id": SHEET,
        "title": "AP Exceptions FY26",
        "columns": ["run_date", "bill_id", "vendor", "reason_code", "owner", "note"],
        "rows": SEEDED_ROWS,
    },
    "sh_ap_run_calendar_fy26": {
        "sheet_id": "sh_ap_run_calendar_fy26",
        "title": "AP Run Calendar FY26",
        "columns": ["run_date", "cutoff", "approver"],
        "rows": [
            {"run_date": d, "cutoff": c, "approver": "dana.okafor"}
            for d, c in [
                ("2026-12-15", "2026-12-14"),
                ("2026-12-22", "2026-12-21"),
                ("2026-12-29", "2026-12-28"),
            ]
        ],
    },
}

# Assertions and golden writes.
HELD = {
    "bill_2204": "DUPLICATE",
    "bill_2210": "RECEIPT_VARIANCE",
    "bill_2211": "APPROVAL_INVALID",
}
assertions = []
for a in task["assertions"]:
    if a["type"] == "pay_one_payment_exact" and a["bill_id"] == "bill_2206":
        a["bank_account_id"] = FACTOR_ACCOUNT
        a["message"] = (
            f"Pinecrest PS-10482 paid exactly once: 27,500.00 USD to the "
            f"assignee account {FACTOR_ACCOUNT}."
        )
    if a["type"] == "pay_remittance" and a["to"] == "ar@pinecrest.example":
        a["to"] = FACTOR_EMAIL
        a["message"] = f"One remittance for PS-10482 to the assignee {FACTOR_EMAIL}."
    if a["type"] == "pay_no_email_to":
        a["recipients"] = sorted(set(a["recipients"]) | {"ar@pinecrest.example"})
    assertions.append(a)
assertions += [
    {
        "type": "pay_sheet_rows",
        "sheet_id": SHEET,
        "seeded_rows": len(SEEDED_ROWS),
        "key_column": "bill_id",
        "rows": {b: {"reason_code": code} for b, code in HELD.items()},
        "message": "Exactly one exceptions-log row per held or rejected bill, "
        "with its reason code, and none for paid or deferred bills.",
    },
    {
        "type": "pay_slack_post",
        "channel": "procurement",
        "any_terms": ["CDS-3562", "Corvid"],
        "message": "One #procurement note that Corvid's November invoice was paid.",
    },
]

golden = []
for name, args in task["golden_writes"]:
    if name == "netsuite_create_payment_v1" and args["bill_id"] == "bill_2206":
        args = {**args, "bank_account_id": FACTOR_ACCOUNT}
    if name == "gmail_send_message_v1" and args["to"] == ["ar@pinecrest.example"]:
        args = {**args, "to": [FACTOR_EMAIL]}
    golden.append([name, args])
bills = world["bills"]
golden += [
    [
        "sheets_append_row_v1",
        {
            "sheet_id": SHEET,
            "values": {
                "run_date": RUN,
                "bill_id": b,
                "vendor": world["vendors"][bills[b]["vendor_id"]]["name"],
                "reason_code": code,
                "owner": "ap@atlas.example",
            },
        },
    ]
    for b, code in HELD.items()
]
golden.append(
    [
        "slack_chat_post_message",
        {
            "channel": "procurement",
            "text": "Corvid CDS-3562 ($14,000) went out in today's run.",
        },
    ]
)

task["id"] = f"automation_workplace__interactive__{TASK_ID}"
task["knowledge_file"] = KB_FILE
task["knowledge_document_ids"] = [d["document_id"] for d in kb]
task["assertions"] = assertions
task["golden_writes"] = golden
task["description"] = {
    **base["description"],
    "purpose": base["description"]["purpose"]
    + " The procedure no longer lists the checks or closing steps; an "
    "exceptions log, a Procurement notification, the Treasury summary and a "
    "factoring assignment are found only in records.",
    "notes": "The AP manager's opening request states the stale release and the "
    "invalid Lumen approval as fact. She owns the critical-supplier designation "
    "and never asks for a summary.",
}
task["user_scenario"] = {
    "persona": base["user_scenario"]["persona"],
    "instructions": {
        **base["user_scenario"]["instructions"],
        "reason_for_call": "Open by saying only: 'hey can you get today's payment "
        "run out? treasury gave us 110k, and sam approved the lumen invoice so make "
        "sure lumen goes. in meetings all morning'",
        "task_instructions": "Open with exactly the reason-for-call sentence. "
        "Never list bills or amounts, never name vendors outside your known info, "
        "never state policy, never mention spreadsheets, logs, Slack channels or "
        "other teams' requests, and never use tools. You own one decision: which "
        "suppliers are critical this run. Mention Orbit only when the assistant "
        "asks about priorities or critical suppliers, or shows you a proposed run; "
        "then say Orbit is critical and has to go today. When shown a proposed "
        "run: if Orbit is missing, say so; if Quill is not being paid, ask once "
        "'any way to squeeze Quill in?'; otherwise reply 'ok go ahead'. If the "
        "assistant asks permission to proceed, reply 'ok go ahead'. If it pays "
        "without showing you a plan, don't object. If it says the release, Lumen "
        "or Kestrel is different from what you thought, reply briefly ('ah ok') and "
        "don't argue or ask why. For any other question reply 'just follow AP "
        "policy'. If asked to email someone or post an update, say 'sure'. Never "
        "ask for a summary or for anything to be checked. Output ###STOP### as "
        "soon as the assistant says the run is done or submitted, however brief.",
    },
}

(INTERACTIVE / KB_FILE).write_text(json.dumps(kb, indent=2) + "\n")
(INTERACTIVE / f"tasks/{TASK_ID}.json").write_text(json.dumps(task, indent=2) + "\n")
print(f"{len(assertions)} assertions, {len(golden)} golden writes, {len(kb)} docs")
