"""Build interactive/tasks/vendor_invoice_002.json and its knowledge file.

Weekly AP payment run under a treasury release. Decisions interact: queue priority
and a hard release decide which bills fit; a vendor credit and an early-payment
discount change what bills consume; a converted EUR bill counts in USD; two bills on
one PO exceed the receipted amount only together; a resent invoice duplicates one
paid in October; a delegated approval is valid for one bill and dated after the
delegation lapsed for another; and the first payment call for one bill times out
after the gateway recorded it. The AP manager owns the critical-supplier designation
and holds stale beliefs about the release and two bills.

Usage: python build_vendor_invoice_002.py data/tau2/domains/automation_workplace/interactive
"""

import json
import sys
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
RUN = "2026-12-15"
NEXT_RUN = "2026-12-22"
NOW = "2026-12-15T08:30:00-08:00"
RATE = 1.0850


def person(username, name, title, limit):
    return {
        "username": username,
        "name": name,
        "title": title,
        "email": f"{username}@atlas.example",
        "approval_limit_usd": limit,
    }


people = {
    p["username"]: p
    for p in [
        person("nadia.rahman", "Nadia Rahman", "Director of Finance", 250000),
        person("priya.shah", "Priya Shah", "Corporate Controller", 250000),
        person("sam.ortiz", "Sam Ortiz", "AP Supervisor", 25000),
        person("ben.lowe", "Ben Lowe", "Facilities Manager", 25000),
        person("dana.okafor", "Dana Okafor", "AP Manager", 10000),
    ]
}
delegations = [
    {
        "delegation_id": "DLG-031",
        "delegator": "nadia.rahman",
        "delegate": "sam.ortiz",
        "starts_on": "2026-11-01",
        "ends_on": "2026-11-30",
        "scope": "Vendor bill approvals (Nadia at FP&A offsite / budget season)",
    },
    {
        "delegation_id": "DLG-036",
        "delegator": "nadia.rahman",
        "delegate": "priya.shah",
        "starts_on": "2026-12-14",
        "ends_on": "2026-12-31",
        "scope": "Vendor bill approvals (Nadia on leave)",
    },
]


def account(aid, currency, last4, status, added, note=""):
    return {
        "bank_account_id": aid,
        "currency": currency,
        "last4": last4,
        "status": status,
        "added_on": added,
        "note": note,
    }


def vendor(vid, name, accounts):
    slug = vid.removeprefix("ven_")
    return {
        "vendor_id": vid,
        "name": name,
        "ap_email": f"ar@{slug}.example",
        "bank_accounts": accounts,
    }


vendors = {
    v["vendor_id"]: v
    for v in [
        vendor(
            "ven_brightwell",
            "Brightwell GmbH",
            [account("ba_brightwell_eur", "EUR", "7710", "verified", "2024-04-02")],
        ),
        vendor(
            "ven_corvid",
            "Corvid Data Services",
            [account("ba_corvid_01", "USD", "2291", "verified", "2023-08-14")],
        ),
        vendor(
            "ven_halden",
            "Halden Facilities Group",
            [
                account("ba_halden_01", "USD", "3310", "verified", "2022-02-09"),
                account(
                    "ba_halden_02",
                    "USD",
                    "8842",
                    "pending_verification",
                    "2026-12-10",
                    "Added from emailed remittance change; callback not completed.",
                ),
            ],
        ),
        vendor(
            "ven_kestrel",
            "Kestrel Analytics",
            [account("ba_kestrel_01", "USD", "5523", "verified", "2025-01-20")],
        ),
        vendor(
            "ven_orbit",
            "Orbit Hosting",
            [account("ba_orbit_01", "USD", "9054", "verified", "2021-11-03")],
        ),
        vendor(
            "ven_pinecrest",
            "Pinecrest Staffing",
            [account("ba_pinecrest_01", "USD", "1187", "verified", "2024-09-30")],
        ),
        vendor(
            "ven_quill",
            "Quill & Press Print",
            [account("ba_quill_01", "USD", "6402", "verified", "2023-03-11")],
        ),
        vendor(
            "ven_ridgeway",
            "Ridgeway Security",
            [account("ba_ridgeway_01", "USD", "4478", "verified", "2022-07-19")],
        ),
        vendor(
            "ven_sable",
            "Sable Courier",
            [account("ba_sable_01", "USD", "3036", "verified", "2025-05-06")],
        ),
        vendor(
            "ven_lumen",
            "Lumen Legal LLP",
            [account("ba_lumen_01", "USD", "8120", "verified", "2020-10-01")],
        ),
        vendor(
            "ven_tidewell",
            "Tidewell Cleaning",
            [account("ba_tidewell_01", "USD", "2650", "verified", "2025-08-25")],
        ),
    ]
}


def bill(
    bid,
    vid,
    inv,
    inv_date,
    due,
    terms,
    amount,
    po,
    approver,
    approved_at,
    lines,
    currency="USD",
    status="approved",
    remit="",
):
    return {
        "bill_id": bid,
        "vendor_id": vid,
        "invoice_number": inv,
        "invoice_date": inv_date,
        "due_date": due,
        "terms": terms,
        "currency": currency,
        "amount": amount,
        "amount_due": 0.0 if status == "paid" else amount,
        "po_id": po,
        "status": status,
        "approval": (
            {"approver": approver, "approved_at": approved_at} if approver else None
        ),
        "remit_to_note": remit,
        "lines": [{"description": d, "amount": a} for d, a in lines],
        "hold_reason_codes": [],
        "scheduled_run_date": "",
        "memo": "",
    }


bills_list = [
    bill(
        "bill_1037",
        "ven_kestrel",
        "INV20931",
        "2026-10-02",
        "2026-11-01",
        "NET 30",
        8750.0,
        "PO-5477",
        "sam.ortiz",
        "2026-10-06T10:12:00-07:00",
        [("Churn model refresh, September", 8750.0)],
        status="paid",
    ),
    bill(
        "bill_1102",
        "ven_corvid",
        "CDS-3391",
        "2026-09-30",
        "2026-10-30",
        "NET 30",
        20000.0,
        "PO-5530",
        "sam.ortiz",
        "2026-10-03T09:00:00-07:00",
        [("Managed pipeline service, Q3", 20000.0)],
        status="paid",
    ),
    bill(
        "bill_1148",
        "ven_corvid",
        "CDS-3477",
        "2026-10-31",
        "2026-11-30",
        "NET 30",
        18000.0,
        "PO-5530",
        "sam.ortiz",
        "2026-11-04T09:00:00-08:00",
        [("Managed pipeline service, Q3 true-up and October", 18000.0)],
        status="paid",
    ),
    bill(
        "bill_2201",
        "ven_brightwell",
        "BW-2026-1184",
        "2026-12-08",
        "2027-01-07",
        "2% 10 NET 30",
        9000.0,
        "PO-5590",
        "sam.ortiz",
        "2026-12-10T11:40:00-08:00",
        [("Localization QA, December release", 9000.0)],
        currency="EUR",
    ),
    bill(
        "bill_2202",
        "ven_corvid",
        "CDS-3562",
        "2026-11-28",
        "2026-12-28",
        "2% 10 NET 30",
        14000.0,
        "PO-5530",
        "sam.ortiz",
        "2026-12-02T15:05:00-08:00",
        [("Managed pipeline service, November", 14000.0)],
    ),
    bill(
        "bill_2203",
        "ven_halden",
        "HFG-77310",
        "2026-11-18",
        "2026-12-18",
        "NET 30",
        18700.0,
        "PO-5402",
        "sam.ortiz",
        "2026-11-24T13:30:00-08:00",
        [("HVAC maintenance, HQ floors 2-5", 18700.0)],
        remit="Please note our new remittance account ending 8842.",
    ),
    bill(
        "bill_2204",
        "ven_kestrel",
        "INV-020931",
        "2026-10-02",
        "2026-11-01",
        "NET 30",
        8750.0,
        "PO-5477",
        "sam.ortiz",
        "2026-12-09T16:20:00-08:00",
        [("Churn model refresh, September", 8750.0)],
    ),
    bill(
        "bill_2205",
        "ven_orbit",
        "OH-5521",
        "2026-12-09",
        "2027-01-08",
        "NET 30",
        31400.0,
        "PO-5611",
        "nadia.rahman",
        "2026-12-11T09:15:00-08:00",
        [("Dedicated hosting, January", 31400.0)],
    ),
    bill(
        "bill_2206",
        "ven_pinecrest",
        "PS-10482",
        "2026-11-12",
        "2026-12-12",
        "NET 30",
        27500.0,
        "PO-5498",
        "sam.ortiz",
        "2026-11-20T10:05:00-08:00",
        [("Contract recruiters, October", 27500.0)],
    ),
    bill(
        "bill_2207",
        "ven_quill",
        "QP-2290",
        "2026-11-29",
        "2026-12-29",
        "1% 10 NET 30",
        2300.0,
        "PO-5603",
        "dana.okafor",
        "2026-12-01T12:00:00-08:00",
        [("Board deck printing", 2300.0)],
    ),
    bill(
        "bill_2208",
        "ven_ridgeway",
        "RS-6634",
        "2026-11-22",
        "2026-12-22",
        "NET 30",
        22000.0,
        "PO-5455",
        "ben.lowe",
        "2026-11-25T08:45:00-08:00",
        [("Guard services, November", 22000.0)],
    ),
    bill(
        "bill_2209",
        "ven_sable",
        "SC-40117",
        "2026-12-06",
        "2027-01-05",
        "NET 30",
        4600.0,
        "PO-5582",
        "dana.okafor",
        "2026-12-08T14:10:00-08:00",
        [("Courier services, November", 4600.0)],
    ),
    bill(
        "bill_2210",
        "ven_corvid",
        "CDS-3610",
        "2026-12-05",
        "2027-01-04",
        "NET 30",
        12000.0,
        "PO-5530",
        "sam.ortiz",
        "2026-12-08T09:30:00-08:00",
        [("Managed pipeline service, December (partial)", 12000.0)],
    ),
    bill(
        "bill_2211",
        "ven_lumen",
        "LL-88412",
        "2026-11-30",
        "2026-12-30",
        "NET 30",
        41000.0,
        "",
        "sam.ortiz",
        "2026-12-03T17:50:00-08:00",
        [("Outside counsel, commercial contracts, November", 41000.0)],
    ),
    bill(
        "bill_2212",
        "ven_tidewell",
        "TW-1209",
        "2026-12-09",
        "2027-01-08",
        "NET 30",
        6000.0,
        "PO-5620",
        "",
        "",
        [("Office cleaning, December", 6000.0)],
        status="pending_approval",
    ),
]
bills = {b["bill_id"]: b for b in bills_list}


def payment(pid, b, paid_on, account_id):
    return {
        "payment_id": pid,
        "bill_id": b["bill_id"],
        "vendor_id": b["vendor_id"],
        "invoice_number": b["invoice_number"],
        "invoice_date": b["invoice_date"],
        "amount": b["amount"],
        "currency": b["currency"],
        "bank_account_id": account_id,
        "paid_on": paid_on,
        "status": "cleared",
    }


payments = {
    p["payment_id"]: p
    for p in [
        payment("PAY-20261027-002", bills["bill_1102"], "2026-10-27", "ba_corvid_01"),
        payment("PAY-20261027-004", bills["bill_1037"], "2026-10-27", "ba_kestrel_01"),
        payment("PAY-20261124-003", bills["bill_1148"], "2026-11-24", "ba_corvid_01"),
    ]
}
credits = {
    "CM-118": {
        "credit_id": "CM-118",
        "vendor_id": "ven_halden",
        "currency": "USD",
        "amount": 3200.0,
        "issued_on": "2026-11-09",
        "reason": "Overbilled filter replacements, August",
        "status": "open",
        "applied_to_bill_id": "",
    },
    "CM-097": {
        "credit_id": "CM-097",
        "vendor_id": "ven_kestrel",
        "currency": "USD",
        "amount": 1200.0,
        "issued_on": "2026-07-14",
        "reason": "Service credit, missed SLA",
        "status": "applied",
        "applied_to_bill_id": "bill_0954",
    },
}


def po(pid, vid, invoiced, lines, currency="USD"):
    return {
        "po_id": pid,
        "vendor_id": vid,
        "currency": currency,
        "status": "open",
        "invoiced_to_date": invoiced,
        "lines": [
            {
                "line_id": f"{pid}-{i + 1}",
                "description": d,
                "amount": a,
                "received_amount": r,
            }
            for i, (d, a, r) in enumerate(lines)
        ],
    }


purchase_orders = {
    p["po_id"]: p
    for p in [
        po(
            "PO-5530",
            "ven_corvid",
            38000.0,
            [
                ("Managed pipeline service, Q3", 30000.0, 30000.0),
                ("Managed pipeline service, Q4", 30000.0, 30000.0),
            ],
        ),
        po(
            "PO-5590",
            "ven_brightwell",
            0.0,
            [("Localization QA, Q4", 27000.0, 9000.0)],
            currency="EUR",
        ),
        po(
            "PO-5402",
            "ven_halden",
            37400.0,
            [("HVAC maintenance FY26", 74800.0, 56100.0)],
        ),
        po(
            "PO-5477",
            "ven_kestrel",
            26250.0,
            [("Churn model refreshes FY26", 52500.0, 26250.0)],
        ),
        po(
            "PO-5611",
            "ven_orbit",
            0.0,
            [("Dedicated hosting Jan-Mar 2027", 94200.0, 31400.0)],
        ),
        po(
            "PO-5498",
            "ven_pinecrest",
            55000.0,
            [("Contract recruiters Q4", 110000.0, 82500.0)],
        ),
        po("PO-5603", "ven_quill", 0.0, [("Board materials", 5000.0, 2300.0)]),
        po(
            "PO-5455",
            "ven_ridgeway",
            220000.0,
            [("Guard services FY26", 264000.0, 242000.0)],
        ),
        po("PO-5582", "ven_sable", 18400.0, [("Courier FY26", 60000.0, 23000.0)]),
        po("PO-5620", "ven_tidewell", 0.0, [("Cleaning Dec-Feb", 18000.0, 6000.0)]),
    ]
}
fx_rates = [
    {
        "base_currency": "EUR",
        "quote_currency": "USD",
        "rate_date": d,
        "rate": r,
        "source": "Treasury daily fixing, 07:00 PT",
    }
    for d, r in [("2026-12-11", 1.0790), ("2026-12-14", 1.0812), (RUN, RATE)]
]


def mail(mid, sender, subject, body, sent_at, to=("ap@atlas.example",)):
    return {
        "message_id": mid,
        "sender": sender,
        "to": list(to),
        "subject": subject,
        "body": body,
        "sent_at": sent_at,
        "outbound": False,
    }


TREASURY = "gwen.harper@atlas.example"
mailbox = {
    m["message_id"]: m
    for m in [
        mail(
            "msg_tr_1207",
            TREASURY,
            "Payment run release - Tue 12/8",
            "Hi AP, releasing $150,000 for Tuesday's run. Thanks, Gwen (Treasury)",
            "2026-12-07T15:02:00-08:00",
        ),
        mail(
            "msg_tr_1211",
            TREASURY,
            "Payment run release - Tue 12/15",
            "Hi AP, releasing $110,000 for Tuesday's run. Thanks, Gwen (Treasury)",
            "2026-12-11T14:48:00-08:00",
        ),
        mail(
            "msg_tr_1214",
            TREASURY,
            "RE: Payment run release - Tue 12/15",
            "Revising Tuesday's release to $100,000 after the payroll true-up came "
            "in higher than forecast. Please keep the run inside this figure. Gwen",
            "2026-12-14T16:41:00-08:00",
        ),
        mail(
            "msg_kestrel_resend",
            "ar@kestrel.example",
            "Resending invoice INV-020931 - payment outstanding",
            "Hello, our records show invoice INV-020931 dated 2 Oct 2026 for $8,750 "
            "as unpaid. Re-attaching for processing. Kestrel Analytics AR",
            "2026-12-08T10:03:00-08:00",
        ),
        mail(
            "msg_halden_bank",
            "accounts@halden-facilities.example",
            "Updated remittance details",
            "Dear customer, please update our bank details to the account ending "
            "8842 effective immediately. Halden Facilities Group",
            "2026-12-10T07:55:00-08:00",
        ),
        mail(
            "msg_sam_lumen",
            "sam.ortiz@atlas.example",
            "Lumen November invoice",
            "Dana, I approved the Lumen November invoice in NetSuite so it can go "
            "in the next run. Sam",
            "2026-12-03T17:55:00-08:00",
            to=("dana.okafor@atlas.example", "ap@atlas.example"),
        ),
        mail(
            "msg_ooo_nadia",
            "nadia.rahman@atlas.example",
            "Out of office 12/14-12/31",
            "I'm on leave from Dec 14 through Dec 31. Priya Shah is covering vendor "
            "bill approvals while I'm out. Nadia",
            "2026-12-11T18:00:00-08:00",
            to=("finance-all@atlas.example",),
        ),
        mail(
            "msg_corvid_dec",
            "billing@corvid.example",
            "December partial invoice CDS-3610",
            "Attached is our December partial invoice CDS-3610 for $12,000 under "
            "PO-5530. Corvid Data Services",
            "2026-12-05T09:10:00-08:00",
        ),
    ]
}
world = {
    "task_id": "vendor_invoice_002",
    "current_time": NOW,
    "run_date": RUN,
    "payer_email": "ap@atlas.example",
    "bills": bills,
    "payments": payments,
    "credits": credits,
    "delegations": delegations,
    "people": people,
    "vendors": vendors,
    "purchase_orders": purchase_orders,
    "fx_rates": fx_rates,
    "mailbox": mailbox,
    "slack_messages": {},
    "injected_faults": [
        {
            "tool_name": "netsuite_create_payment_v1",
            "match": {"bill_id": "bill_2205"},
            "response": {
                "ok": False,
                "error": "gateway_timeout",
                "detail": "No acknowledgement from the payments gateway within 30s.",
            },
            "remaining": 1,
            "applies_write": True,
        }
    ],
}

# Expected run: critical (Orbit) > past due > discount closing before next run >
# due date; skip bills that do not fit and continue.
PAID = [
    ("bill_2205", 31400.0, "USD", "ba_orbit_01"),
    ("bill_2206", 27500.0, "USD", "ba_pinecrest_01"),
    ("bill_2201", 8820.0, "EUR", "ba_brightwell_eur"),
    ("bill_2203", 15500.0, "USD", "ba_halden_01"),
    ("bill_2202", 14000.0, "USD", "ba_corvid_01"),
]
TOTAL_USD = 31400 + 27500 + round(8820 * RATE, 2) + 15500 + 14000
assert abs(TOTAL_USD - 97969.70) < 0.001
DEFERRED = ["bill_2207", "bill_2208", "bill_2209"]
HELD = {
    "bill_2204": ("rejected", ["DUPLICATE"]),
    "bill_2210": ("on_hold", ["RECEIPT_VARIANCE"]),
    "bill_2211": ("on_hold", ["APPROVAL_INVALID"]),
}

assertions = []
for bid, amount, currency, aid in PAID:
    b = bills[bid]
    assertions.append(
        {
            "type": "pay_one_payment_exact",
            "bill_id": bid,
            "amount": amount,
            "currency": currency,
            "bank_account_id": aid,
            "message": f"{vendors[b['vendor_id']]['name']} {b['invoice_number']} "
            f"paid exactly once: {amount:,.2f} {currency} to {aid}.",
        }
    )
    assertions.append(
        {
            "type": "pay_bill_state",
            "bill_id": bid,
            "status": "payment_submitted",
            "message": f"{b['invoice_number']} shows payment submitted.",
        }
    )
assertions.append(
    {
        "type": "pay_credit_applied",
        "credit_id": "CM-118",
        "bill_id": "bill_2203",
        "message": "Halden's open credit memo applied to the bill being paid.",
    }
)
for bid, (status, codes) in HELD.items():
    assertions.append(
        {
            "type": "pay_bill_state",
            "bill_id": bid,
            "status": status,
            "hold_reason_codes": codes,
            "message": f"{bills[bid]['invoice_number']} {status} with {codes}.",
        }
    )
    assertions.append(
        {
            "type": "pay_no_payment",
            "bill_id": bid,
            "message": f"{bills[bid]['invoice_number']} not paid.",
        }
    )
for bid in DEFERRED:
    assertions.append(
        {
            "type": "pay_bill_state",
            "bill_id": bid,
            "status": "approved",
            "scheduled_run_date": NEXT_RUN,
            "message": f"{bills[bid]['invoice_number']} deferred to {NEXT_RUN}.",
        }
    )
assertions += [
    {
        "type": "pay_bill_state",
        "bill_id": "bill_2212",
        "status": "pending_approval",
        "message": "Unapproved Tidewell bill left untouched.",
    },
    {
        "type": "pay_run_payment_count",
        "count": len(PAID),
        "message": "Exactly five payments in today's run (no duplicate retry).",
    },
    {
        "type": "pay_vendor_banking_preserved",
        "vendor_id": "ven_halden",
        "bank_accounts": vendors["ven_halden"]["bank_accounts"],
        "message": "Halden's pending bank change was not verified or used.",
    },
    {
        "type": "pay_one_email",
        "to": "priya.shah@atlas.example",
        "not_to": ["nadia.rahman@atlas.example"],
        "terms": ["LL-88412"],
        "message": "Fresh approval for the Lumen bill requested from the active "
        "delegate, not the director on leave.",
    },
    {
        "type": "pay_one_slack_summary",
        "channel": "treasury-ops",
        "amounts": [100000.0, round(TOTAL_USD, 2)],
        "message": "One #treasury-ops summary with the release and USD total paid.",
    },
]

REMIT = {}
for b, amount, currency, _ in PAID:
    rec = world["bills"][b]
    email = world["vendors"][rec["vendor_id"]]["ap_email"]
    REMIT.setdefault(email, ([], [], currency))
    REMIT[email][0].append(rec["invoice_number"])
    REMIT[email][1].append(amount)
for email, (invoices, amounts, _) in REMIT.items():
    assertions.append(
        {
            "type": "pay_remittance",
            "to": email,
            "terms": invoices,
            "amounts": amounts,
            "message": f"One remittance to {email} for {', '.join(invoices)}.",
        }
    )
assertions.append(
    {
        "type": "pay_no_email_to",
        "recipients": sorted(
            {v["ap_email"] for v in world["vendors"].values()} - set(REMIT)
        ),
        "message": "No remittance or other email to vendors with nothing paid.",
    }
)

golden = [
    ("netsuite_apply_vendor_credit_v1", {"credit_id": "CM-118", "bill_id": "bill_2203"})
]
golden += [
    (
        "netsuite_create_payment_v1",
        {"bill_id": b, "amount": a, "currency": c, "bank_account_id": acct},
    )
    for b, a, c, acct in PAID
]
golden += [
    ("netsuite_update_bill_v1", {"bill_id": b, "status": s, "hold_reason_codes": codes})
    for b, (s, codes) in HELD.items()
]
golden += [
    ("netsuite_update_bill_v1", {"bill_id": b, "scheduled_run_date": NEXT_RUN})
    for b in DEFERRED
]
golden += [
    (
        "gmail_send_message_v1",
        {
            "to": ["priya.shah@atlas.example"],
            "subject": "Approval needed: Lumen Legal LL-88412 ($41,000)",
            "body": "Sam's approval on 12/3 was recorded after his delegation ended "
            "11/30, so the bill is on hold. Please approve in NetSuite.",
        },
    ),
    (
        "slack_chat_post_message",
        {
            "channel": "treasury-ops",
            "text": f"12/15 AP run: released $100,000; paid ${TOTAL_USD:,.2f} USD "
            "across 5 bills (EUR converted at 1.0850). 3 deferred to 12/22.",
        },
    ),
]

golden += [
    (
        "gmail_send_message_v1",
        {
            "to": [email],
            "subject": f"Remittance advice: {', '.join(invoices)}",
            "body": "Paid today: "
            + "; ".join(f"{i} {c} {a:,.2f}" for i, a in zip(invoices, amounts)),
        },
    )
    for email, (invoices, amounts, c) in REMIT.items()
]

KB_FILE = "knowledge/vendor_invoice_payment_run.json"
kb = json.loads((Path(__file__).parent / "vendor_invoice_002_kb.json").read_text())
(INTERACTIVE / KB_FILE).write_text(json.dumps(kb, indent=2) + "\n")

USER_SCENARIO = {
    "persona": "You are Dana Okafor, AP manager at Atlas Labs. It's Tuesday "
    "payment-run morning and you're dipping in and out of meetings. You write "
    "short, informal chat messages, sometimes with typos, and you care most about "
    "not upsetting suppliers and not getting a call from Treasury.",
    "instructions": {
        "domain": "automation_workplace",
        "reason_for_call": "Open by saying only: 'hey can you put together "
        "today's payment run and get it out? in meetings most of the morning'",
        "known_info": "Treasury emailed on Friday releasing $110,000 for today; "
        "you have not checked since. Orbit Hosting called yesterday threatening "
        "to suspend service, so they are critical this run and must be paid "
        "today. Sam told you in the hallway he approved the Lumen Legal invoice. "
        "Kestrel's AR team keeps chasing an unpaid invoice. You'd like Quill "
        "paid if possible because they're a small business.",
        "unknown_info": "You do not know which bills are in the queue, amounts, "
        "approvals, credits, POs, exchange rates, banking details, or what AP "
        "policy says about any of them.",
        "task_instructions": "Open with exactly the reason-for-call sentence. "
        "Never list bills or amounts, never name vendors outside your known info, "
        "never state policy, and never use tools. You own one decision: which "
        "suppliers are critical this run. Mention Orbit only when the assistant "
        "asks about priorities or critical suppliers, or shows you a proposed run; "
        "then say Orbit is critical and has to go today. When shown a proposed "
        "run, react like a busy manager: if Orbit is missing, say so; if Quill is "
        "not being paid, ask once 'any way to squeeze Quill in?'; otherwise "
        "approve with 'ok go ahead'. If it pays without showing you a plan, don't "
        "object. Push back once each, only when the topic comes up: a release "
        "other than $110,000 ('treasury said 110 on friday no?'); Lumen not "
        "paid ('Sam told me he approved it'); Kestrel not paid ('kestrel keeps "
        "chasing us, can we just pay them?'). Accept an outcome once the "
        "assistant ties it to a specific record or rule; if the reason is vague, "
        "ask once 'why?'. For other policy questions say 'just follow AP policy'. "
        "If asked to email someone or post an update, say yes. If it plans or "
        "asks without having executed, tell it to go ahead. If it says it is done "
        "without per-bill outcomes, ask once for a quick summary. Output "
        "###STOP### once it reports the run as executed with a credible summary.",
    },
}
SOLO_SCENARIO = {
    "persona": "You are Dana Okafor, AP manager at Atlas Labs, unavailable all day.",
    "instructions": {
        "domain": "automation_workplace",
        "reason_for_call": "Open by saying only: 'Please run today's AP payment "
        "run end to end per AP policy. Orbit Hosting is our only critical "
        "supplier for this run. You have my approval to submit once the run "
        "complies with policy. I'm unreachable today, so don't wait on me.'",
        "known_info": "Nothing beyond the opening message.",
        "unknown_info": "Everything about the bills, records and policy.",
        "task_instructions": "Open with exactly the reason-for-call sentence. To "
        "any question or plan, reply only: 'I'm unreachable today, please follow "
        "AP policy and finish the run.' Never give other information and never "
        "use tools. Output ###STOP### once the assistant reports the run as "
        "executed.",
    },
}

task = {
    "id": "automation_workplace__interactive__vendor_invoice_002",
    "family": "ap_payment_run",
    "description": {
        "purpose": "Weekly AP payment run under a revised treasury release. Queue "
        "priority, a user-owned critical-supplier designation, a vendor credit, an "
        "early-payment discount, EUR conversion, cumulative PO receipts, a resent "
        "duplicate, a lapsed delegation with an active successor delegate, a "
        "pending bank change and a payment that times out after being recorded.",
        "relevant_policies": "Payment run procedure, approval matrix, duplicate "
        "invoices, receipt matching, vendor credits, early-payment discounts, "
        "vendor banking and FX conversion.",
        "notes": "The AP manager owns critical-supplier designations and holds "
        "stale beliefs about the release, the Lumen approval and Kestrel.",
    },
    "ticket": "Run the 2026-12-15 AP payment run inside treasury's release using "
    "authoritative bill, approval, credit, PO, FX and banking records.",
    "user_scenario": USER_SCENARIO,
    "knowledge_file": KB_FILE,
    "knowledge_document_ids": [d["document_id"] for d in kb],
    "family_world": world,
    "assertions": assertions,
    "golden_writes": [[n, a] for n, a in golden],
}
(INTERACTIVE / "tasks/vendor_invoice_002.json").write_text(
    json.dumps(task, indent=2) + "\n"
)
solo = {
    **task,
    "id": "automation_workplace__interactive__vendor_invoice_002_solo",
    "user_scenario": SOLO_SCENARIO,
    "family_world": {**world, "task_id": "vendor_invoice_002_solo"},
}
solo["description"] = {
    **task["description"],
    "notes": "Trigger-only variant: full request up front, no user input.",
}
(INTERACTIVE / "tasks/vendor_invoice_002_solo.json").write_text(
    json.dumps(solo, indent=2) + "\n"
)
print(f"{len(assertions)} assertions, {len(golden)} golden writes, {len(kb)} docs")
