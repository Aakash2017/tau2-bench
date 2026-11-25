"""Build vendor_invoice_005: the AP payment run learned from Slack history.

Derived from vendor_invoice_004 (run its builder first). There is no payment-run
procedure in the knowledge base. How runs are done lives in #ap-payments: four
past run threads by different people, each doing things slightly differently,
with later corrections that override earlier habits, mixed in with unrelated
chatter. Other channels add noise (including an engineering access request).
Compliance controls (approval matrix, duplicates, receipts, credits, discounts,
banking, FX) stay in the KB. The AP manager never teaches or corrects.

Grading is strict: exact payment and bill state, untouched bills unchanged,
exact counts of outbound emails and agent Slack posts, and exceptions rows in
the run's existing format.

Usage: python build_vendor_invoice_005.py data/tau2/domains/automation_workplace/interactive
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
TASK_ID = "vendor_invoice_005"
RUN = "2026-12-15"
KB_FILE = "knowledge/vendor_invoice_payment_run_v5.json"
SHEET = "sh_ap_exceptions_fy26"
DROPPED_DOCS = {
    "kb_ap_payment_run_procedure_2026_11",
    "kb_ap_payment_run_procedure_2025_03",
    "kb_ap_remittance_advice_2026_10",
}
UNTOUCHED = ["bill_1037", "bill_1102", "bill_1148", "bill_2212"]

base = json.loads((INTERACTIVE / "tasks/vendor_invoice_004.json").read_text())
kb = [
    d
    for d in json.loads((INTERACTIVE / base["knowledge_file"]).read_text())
    if d["document_id"] not in DROPPED_DOCS
]
task = deepcopy(base)
world = task["family_world"]
world["task_id"] = TASK_ID

# Obligations that 004 put in email move into Slack history.
del world["mailbox"]["msg_controller_exceptions"]
world["mailbox"]["msg_tr_1214"]["body"] = (
    "Revising Tuesday's release to $100,000 after the payroll true-up came in "
    "higher than forecast. Please keep the run inside this figure. Gwen"
)

# (channel, user, ts, text, replies[(user, ts, text)])
THREADS = [
    # ---- #ap-payments: superseded habit from September
    (
        "ap-payments",
        "tomas.reyes",
        "2026-09-15T08:31:00-07:00",
        "9/15 run going out. Release is tight so I'm paying half of the Halden "
        "facilities bill now and the other half next week.",
        [
            (
                "dana.okafor",
                "2026-09-15T09:02:00-07:00",
                "pls don't split bills across runs, it wrecks the aging and the vendor "
                "reconciliations. pay it in full or push the whole thing to next week.",
            ),
            ("tomas.reyes", "2026-09-15T09:05:00-07:00", "got it, pushed it whole."),
            (
                "tomas.reyes",
                "2026-09-15T11:48:00-07:00",
                "Out. Total posted in #ap-team.",
            ),
        ],
    ),
    (
        "ap-payments",
        "marco.diaz",
        "2026-11-19T14:12:00-08:00",
        "does anyone know if Quill's W-9 is on file? procurement is asking",
        [("lena.park", "2026-11-19T14:30:00-08:00", "yes, refreshed in October")],
    ),
    # ---- Run 1: ordering, and Treasury wants totals in #treasury-ops
    (
        "ap-payments",
        "tomas.reyes",
        "2026-11-17T08:40:00-08:00",
        "Starting the 11/17 run. Dana, any criticals this week?",
        [
            (
                "dana.okafor",
                "2026-11-17T08:52:00-08:00",
                "none this week. reminder for the new folks on order: suppliers I flag "
                "as critical for the run go first (I decide that each run, ask me if I "
                "haven't said), then anything past due, then bills whose early-pay "
                "discount closes before next tuesday, then everything else. inside each "
                "of those go by due date, earliest first, lower bill id on ties. walk "
                "the list once and if something doesn't fit what's left of the release "
                "skip it and keep going, a smaller one further down might fit",
            ),
            (
                "tomas.reyes",
                "2026-11-17T11:30:00-08:00",
                "Run's out: 6 bills, $118,240.00 of the $120k release.",
            ),
            (
                "gwen.harper",
                "2026-11-17T11:44:00-08:00",
                "Thanks Tomas. Going forward can AP post each run's total in "
                "#treasury-ops instead (release and total paid in USD)? That's where we "
                "match the bank file, I don't watch this channel.",
            ),
            ("tomas.reyes", "2026-11-17T11:46:00-08:00", "will do"),
        ],
    ),
    # ---- Run 2: stale release, remittance correction
    (
        "ap-payments",
        "tomas.reyes",
        "2026-11-24T08:35:00-08:00",
        "11/24 run. Using the $95k from Gwen's Friday email.",
        [
            (
                "lena.park",
                "2026-11-24T08:41:00-08:00",
                "Gwen sent a revision last night, it's $90k now. Her latest email for "
                "the run date is the one that counts.",
            ),
            ("tomas.reyes", "2026-11-24T08:43:00-08:00", "ugh missed it, using 90"),
            (
                "tomas.reyes",
                "2026-11-24T12:10:00-08:00",
                "Done, posted in #treasury-ops. Sent remittances to the remit-to emails "
                "printed on each invoice, and a heads-up to Sable that theirs slips a "
                "week.",
            ),
            (
                "renee.cho",
                "2026-11-24T13:02:00-08:00",
                "Tomas please don't use invoice addresses, one of those was a spoofed "
                "domain last quarter. Remittance advice goes only to the AR contact on "
                "the vendor master, or to the assignee when the vendor master records a "
                "notice of assignment. One email per vendor paid, with the invoice "
                "number(s) and the amount in the currency we paid. Vendors we didn't pay "
                "don't get emails from the run, Procurement handles those conversations.",
            ),
            ("tomas.reyes", "2026-11-24T13:05:00-08:00", "understood, sorry"),
        ],
    ),
    (
        "ap-payments",
        "sam.ortiz",
        "2026-11-26T10:03:00-08:00",
        "Concur is down for card reconciliations, vendor says ETA 2pm",
        [],
    ),
    # ---- Run 3: deferral convention and exceptions log
    (
        "ap-payments",
        "lena.park",
        "2026-12-01T08:30:00-08:00",
        "12/1 run thread",
        [
            (
                "lena.park",
                "2026-12-01T11:52:00-08:00",
                "Out, total's in #treasury-ops. Two didn't fit (Quill and Ridgeway): "
                "left both Approved and set their scheduled run date to next Tuesday's "
                "run so they're first in line. Held Sable's PO-5402 bill as "
                "RECEIPT_VARIANCE (pallets not received) and logged it.",
            ),
            (
                "renee.cho",
                "2026-12-01T12:06:00-08:00",
                "That's the format. For everyone: from December, every bill put on hold "
                "or rejected during a run gets one row in AP Exceptions FY26 (run date, "
                "bill, vendor, reason code, follow-up owner). Deferred bills aren't "
                "exceptions, don't log them. Audit samples from that sheet in January.",
            ),
            (
                "tomas.reyes",
                "2026-12-01T12:20:00-08:00",
                "should I add a row for the two deferrals too?",
            ),
            ("renee.cho", "2026-12-01T12:24:00-08:00", "no, see above"),
        ],
    ),
    (
        "ap-payments",
        "renee.cho",
        "2026-12-03T09:00:00-08:00",
        "Month-end reminder: accrue anything received-not-invoiced over $5k by WD3.",
        [],
    ),
    # ---- Run 4: duplicate, plan approval
    (
        "ap-payments",
        "lena.park",
        "2026-12-08T08:30:00-08:00",
        "12/8 run. Dana flagged no criticals.",
        [
            (
                "lena.park",
                "2026-12-08T09:14:00-08:00",
                "Ridgeway resent RS-7710 as RS7710, same date and amount as the one we "
                "paid 11/24. Rejected it as DUPLICATE and logged it.",
            ),
            (
                "dana.okafor",
                "2026-12-08T09:20:00-08:00",
                "nice catch. and show me the proposed run before anything goes out pls, "
                "same as always",
            ),
            (
                "lena.park",
                "2026-12-08T09:41:00-08:00",
                "Proposed: 9 bills, $141,902.55 of $150k (list in DM). ok?",
            ),
            ("dana.okafor", "2026-12-08T09:55:00-08:00", "go"),
            (
                "lena.park",
                "2026-12-08T12:02:00-08:00",
                "Out. Total posted in #treasury-ops, remittances to vendor-master "
                "contacts.",
            ),
        ],
    ),
    (
        "ap-payments",
        "tomas.reyes",
        "2026-12-09T15:10:00-08:00",
        "lunch for thursday's offsite? tacos or thai",
        [
            ("dana.okafor", "2026-12-09T15:12:00-08:00", "tacos"),
            ("lena.park", "2026-12-09T15:13:00-08:00", "tacos"),
        ],
    ),
    (
        "ap-payments",
        "tomas.reyes",
        "2026-12-10T10:20:00-08:00",
        "Ridgeway asked to move to monthly invoicing, forwarded to Procurement.",
        [],
    ),
    (
        "ap-payments",
        "lena.park",
        "2026-12-11T16:40:00-08:00",
        "I'm out 12/14-12/18, the AP bot is covering Tuesday's run.",
        [("dana.okafor", "2026-12-11T16:45:00-08:00", "enjoy!")],
    ),
    (
        "ap-payments",
        "sam.ortiz",
        "2026-12-14T09:15:00-08:00",
        "anyone have the Q4 audit PBC list? need it by thursday",
        [],
    ),
    # ---- #treasury-ops
    (
        "treasury-ops",
        "gwen.harper",
        "2026-11-30T07:05:00-08:00",
        "FX fixings now publish at 7am PT on run days.",
        [],
    ),
    (
        "treasury-ops",
        "lena.park",
        "2026-12-01T11:55:00-08:00",
        "12/1 AP run: release $130,000.00, paid $127,415.20 USD.",
        [],
    ),
    (
        "treasury-ops",
        "lena.park",
        "2026-12-08T12:04:00-08:00",
        "12/8 AP run: release $150,000.00, paid $141,902.55 USD.",
        [("gwen.harper", "2026-12-08T13:30:00-08:00", "matched, thanks")],
    ),
    (
        "treasury-ops",
        "gwen.harper",
        "2026-12-11T10:00:00-08:00",
        "Payroll true-up lands Monday, may affect next week's AP release.",
        [],
    ),
    # ---- #procurement
    (
        "procurement",
        "marco.diaz",
        "2026-12-02T09:30:00-08:00",
        "New PO approval thresholds take effect Jan 1, deck in Drive.",
        [],
    ),
    (
        "procurement",
        "marco.diaz",
        "2026-12-12T11:00:00-08:00",
        "Kicking off the Q1 SaaS renewal review, owners please update the tracker.",
        [],
    ),
    # ---- #eng-access: how engineering handles access (unrelated workflow)
    (
        "eng-access",
        "raj.mehta",
        "2026-12-07T10:12:00-08:00",
        "Need read access to the billing replica for INC-4471.",
        [
            (
                "it.helpdesk",
                "2026-12-07T10:20:00-08:00",
                "File it in Okta with the incident ID; your manager approves and it "
                "auto-expires in 7 days.",
            ),
            ("raj.mehta", "2026-12-07T10:31:00-08:00", "done, thanks"),
        ],
    ),
    (
        "eng-access",
        "ivy.chen",
        "2026-12-10T15:02:00-08:00",
        "Who approves prod admin for the payments service?",
        [
            (
                "it.helpdesk",
                "2026-12-10T15:09:00-08:00",
                "Service owner plus security on-call. Two approvals, max 24h.",
            )
        ],
    ),
    # ---- #general
    (
        "general",
        "people.team",
        "2026-12-04T12:00:00-08:00",
        "Holiday party is 12/18 at 5pm, RSVP in the form.",
        [],
    ),
    (
        "general",
        "it.helpdesk",
        "2026-12-14T08:00:00-08:00",
        "Laptop OS update rolls out tonight, please restart by Wednesday.",
        [],
    ),
]

slack = {}
for channel, user, ts, text, replies in THREADS:
    for u, t, body, thread in [(user, ts, text, "")] + [
        (u, t, b, ts) for u, t, b in replies
    ]:
        mid = f"sl_{len(slack) + 1:03d}"
        slack[mid] = {
            "message_id": mid,
            "channel": channel,
            "text": body,
            "user": u,
            "ts": t,
            "thread_ts": thread,
        }
world["slack_messages"] = slack

# Strict assertions on top of 004's.
seeded_bills = world["bills"]
assertions = []
for a in task["assertions"]:
    if a["type"] == "pay_sheet_rows":
        a["rows"] = {b: {**v, "run_date": RUN} for b, v in a["rows"].items()}
        a["message"] = (
            "Exactly one exceptions row per held or rejected bill, with run date "
            f"{RUN} and its reason code; none for paid or deferred bills."
        )
    assertions.append(a)
outbound = sum(1 for n, _ in task["golden_writes"] if n == "gmail_send_message_v1")
posts = sum(1 for n, _ in task["golden_writes"] if n == "slack_chat_post_message")
assertions += [
    {
        "type": "pay_outbound_email_count",
        "count": outbound,
        "message": f"Exactly {outbound} outbound emails: one remittance per paid "
        "vendor and one fresh-approval request.",
    },
    {
        "type": "pay_agent_slack_post_count",
        "count": posts,
        "message": f"Exactly {posts} Slack posts: the #treasury-ops total and the "
        "#procurement note.",
    },
] + [
    {
        "type": "pay_bill_unchanged",
        "bill_id": b,
        "bill": {k: v for k, v in seeded_bills[b].items() if k != "memo"},
        "message": f"{b} is outside the run and stays exactly as seeded.",
    }
    for b in UNTOUCHED
]

task["id"] = f"automation_workplace__interactive__{TASK_ID}"
task["knowledge_file"] = KB_FILE
task["knowledge_document_ids"] = [d["document_id"] for d in kb]
task["assertions"] = assertions
task["description"] = {
    **base["description"],
    "purpose": "AP payment run with no procedure document. Ordering, deferral, "
    "plan approval, remittance, exceptions-log and Treasury-summary practice must "
    "be inferred from four past #ap-payments threads that differ and correct each "
    "other, among unrelated chatter and other channels.",
    "notes": "The AP manager states the stale release and the invalid Lumen "
    "approval as fact, owns only the critical-supplier designation, and never "
    "teaches, corrects or asks for a summary.",
}
instructions = task["user_scenario"]["instructions"]
instructions["task_instructions"] = instructions["task_instructions"].replace(
    "never state policy,",
    "never state policy or explain how payment runs are done, never point the "
    "assistant to Slack, past runs or documents,",
)
assert "never point the assistant" in instructions["task_instructions"]

(INTERACTIVE / KB_FILE).write_text(json.dumps(kb, indent=2) + "\n")
(INTERACTIVE / f"tasks/{TASK_ID}.json").write_text(json.dumps(task, indent=2) + "\n")
print(
    f"{len(assertions)} assertions, {len(task['golden_writes'])} golden writes, "
    f"{len(kb)} docs, {len(slack)} slack messages"
)
