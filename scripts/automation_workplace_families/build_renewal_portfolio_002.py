"""Build interactive/tasks/renewal_portfolio_002.json and its knowledge file.

Second-session resume of a renewal-notice batch. The agent's own handoff note says
four accounts are done and three remain; the systems show a bounced notice, a CRM
write that never landed, a notice quoting a price above the contract cap, a legal
hold released after the note, and an in-scope account on page 2 the note omits.

Usage: python build_renewal_portfolio_002.py data/tau2/domains/automation_workplace/interactive
"""

import json
import sys
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
TODAY = "2027-01-11"
YDAY = "2027-01-10"
NOW = "2027-01-11T09:10:00-08:00"
KB_FILE = "knowledge/renewal_portfolio_handoff.json"


def contact(email, name, role="renewal_notice", verified=True, **kw):
    return {"email": email, "name": name, "role": role, "verified": verified, **kw}


def account(
    aid,
    name,
    renew,
    currency,
    arr,
    cap,
    contacts,
    parent="",
    msa="",
    notes="",
    stage="not_started",
    sent="",
    price=None,
):
    return {
        "account_id": aid,
        "name": name,
        "parent_account_id": parent,
        "renewal_date": renew,
        "currency": currency,
        "arr": arr,
        "contract": {
            "contract_id": f"CTR-{aid.removeprefix('acc_')[:4].upper()}-26",
            "master_agreement_id": msa,
            "uplift_cap_pct": cap,
            "notes": notes,
        },
        "contacts": contacts,
        "renewal_stage": stage,
        "notice_sent_on": sent,
        "renewal_price": price,
    }


accounts = [
    account(
        "acc_alder",
        "Alder Health",
        "2027-03-01",
        "USD",
        120000.0,
        None,
        [contact("ap@alderhealth.example", "Rhea Patel")],
        msa="MSA-ALDER-2024",
        stage="notice_sent",
        sent=YDAY,
        price=128400.0,
    ),
    account(
        "acc_birchline",
        "Birchline Logistics",
        "2027-03-15",
        "USD",
        80000.0,
        5.0,
        [
            contact(
                "jo.marsh@birchline.example",
                "Jo Marsh",
                verified=False,
                active=False,
                updated_on="2027-01-05",
            ),
            contact("kim.osei@birchline.example", "Kim Osei", updated_on="2027-01-05"),
        ],
        stage="notice_sent",
        sent=YDAY,
        price=84000.0,
    ),
    account(
        "acc_cobalt",
        "Cobalt Robotics",
        "2027-03-20",
        "USD",
        65000.0,
        3.0,
        [contact("finance@cobaltrobotics.example", "Ines Duarte")],
    ),
    account(
        "acc_dunmore",
        "Dunmore Insurance",
        "2027-04-01",
        "USD",
        200000.0,
        5.0,
        [contact("procurement@dunmore.example", "Aidan Kerr")],
        notes="Renewal uplift capped at 5% per Amendment 2 (2025).",
        stage="notice_sent",
        sent=YDAY,
        price=214000.0,
    ),
    account(
        "acc_elmstead",
        "Elmstead Clinics",
        "2027-04-05",
        "USD",
        90000.0,
        None,
        [contact("ops@elmsteadclinics.example", "Tom Reyes")],
        parent="acc_alder",
        msa="MSA-ALDER-2024",
        notes="Ordered under parent master agreement.",
    ),
    account(
        "acc_fernhill",
        "Fernhill Analytics Ltd",
        "2027-04-10",
        "GBP",
        41000.0,
        None,
        [contact("accounts@fernhill.example", "Grace Hale")],
    ),
    account(
        "acc_glenrock",
        "Glenrock Energy",
        "2027-04-12",
        "USD",
        150000.0,
        None,
        [contact("legal@glenrock.example", "Ward Lin")],
    ),
    account(
        "acc_harbor",
        "Harbor Freight Systems",
        "2027-04-18",
        "USD",
        70000.0,
        None,
        [contact("billing@harborfs.example", "Lena Ruiz")],
    ),
    account(
        "acc_ivory",
        "Ivory Dental Group",
        "2027-04-22",
        "USD",
        55000.0,
        4.0,
        [
            contact("ops@ivorydental.example", "Sara Moy", opted_out=True),
            contact("finance@ivorydental.example", "Raj Bose"),
        ],
    ),
    account(
        "acc_juniper",
        "Juniper Schools",
        "2027-04-25",
        "USD",
        45000.0,
        None,
        [contact("it@juniperschools.example", "Ola Berg")],
    ),
    account(
        "acc_larch",
        "Larch Outfitters",
        "2027-04-28",
        "CAD",
        60000.0,
        None,
        [contact("ap@larchoutfitters.example", "Ben Cho")],
    ),
    account(
        "acc_kiln",
        "Kiln Studios",
        "2027-05-15",
        "USD",
        95000.0,
        None,
        [contact("hello@kilnstudios.example", "Ana Diaz")],
    ),
]
accounts = {a["account_id"]: a for a in accounts}

holds = [
    {
        "hold_id": "LH-2026-014",
        "account_id": "acc_glenrock",
        "scope": "All external commercial communications",
        "status": "active",
        "placed_on": "2026-11-02",
        "note": "Pending contract dispute.",
    },
    {
        "hold_id": "LH-2026-019",
        "account_id": "acc_harbor",
        "scope": "All external commercial communications",
        "status": "released",
        "placed_on": "2026-12-01",
        "released_on": YDAY,
        "note": "Released after settlement signed 2027-01-10 15:20 PT.",
    },
]


def mail(mid, sender, to, subject, body, sent_at, folder):
    return {
        "message_id": mid,
        "sender": sender,
        "to": to,
        "subject": subject,
        "body": body,
        "sent_at": sent_at,
        "folder": folder,
        "session": "seed",
    }


R = "renewals@atlas.example"


def notice(mid, to, name, date, price, t):
    return mail(
        mid,
        R,
        [to],
        f"Atlas renewal notice - {name}",
        f"Your Atlas subscription renews on {date}. Renewal price: "
        f"${price:,.2f} USD per year. Reply to this email with any questions.",
        f"{YDAY}T{t}:00-08:00",
        "sent",
    )


mailbox = [
    notice(
        "sent_0110_01",
        "ap@alderhealth.example",
        "Alder Health",
        "2027-03-01",
        128400,
        "16:02",
    ),
    notice(
        "sent_0110_02",
        "jo.marsh@birchline.example",
        "Birchline Logistics",
        "2027-03-15",
        84000,
        "16:05",
    ),
    notice(
        "sent_0110_03",
        "finance@cobaltrobotics.example",
        "Cobalt Robotics",
        "2027-03-20",
        66950,
        "16:09",
    ),
    notice(
        "sent_0110_04",
        "procurement@dunmore.example",
        "Dunmore Insurance",
        "2027-04-01",
        214000,
        "16:14",
    ),
    mail(
        "in_0110_bounce",
        "mailer-daemon@atlas.example",
        [R],
        "Undeliverable: Atlas renewal notice - Birchline Logistics",
        "Delivery to jo.marsh@birchline.example failed permanently: 550 5.1.1 "
        "mailbox does not exist.",
        f"{YDAY}T16:06:00-08:00",
        "inbox",
    ),
    mail(
        "in_0110_legal",
        "counsel@atlas.example",
        [R, "renewals-team@atlas.example"],
        "Harbor Freight Systems - legal hold released",
        "The settlement is signed; the hold on Harbor Freight Systems is lifted "
        "as of this afternoon. Normal commercial contact can resume.",
        f"{YDAY}T15:25:00-08:00",
        "inbox",
    ),
    mail(
        "in_0108_glen",
        "marcus.bell@atlas.example",
        [R],
        "Glenrock",
        "Glenrock's renewal is a big one, let's not let it slip. M",
        "2027-01-08T11:00:00-08:00",
        "inbox",
    ),
]
mailbox = {m["message_id"]: m for m in mailbox}

slack = {
    "slack_seed_001": {
        "message_id": "slack_seed_001",
        "channel": "renewals-ops",
        "author": "Marcus Bell",
        "text": "Kicking off the March/April renewal notices batch today.",
        "posted_at": f"{YDAY}T13:00:00-08:00",
        "session": "seed",
    },
    "slack_seed_002": {
        "message_id": "slack_seed_002",
        "channel": "renewals-ops",
        "author": "Renewals Assistant",
        "text": "Handoff (pausing for today): Mar/Apr notices batch. Sent + CRM "
        "updated: Alder Health, Birchline Logistics, Cobalt Robotics, Dunmore "
        "Insurance. Skipped Harbor Freight Systems (legal hold). Remaining: "
        "Elmstead Clinics, Fernhill Analytics, Glenrock Energy. Will pick up "
        "tomorrow.",
        "posted_at": f"{YDAY}T17:58:00-08:00",
        "session": "seed",
    },
}
fx = [
    {"base_currency": b, "quote_currency": "USD", "rate_date": d, "rate": r}
    for b, d, r in [
        ("GBP", YDAY, 1.2150),
        ("GBP", TODAY, 1.2700),
        ("CAD", YDAY, 0.7310),
        ("CAD", TODAY, 0.7300),
    ]
]
world = {
    "task_id": "renewal_portfolio_002",
    "current_time": NOW,
    "today": TODAY,
    "sender_email": R,
    "accounts": accounts,
    "legal_holds": holds,
    "mailbox": mailbox,
    "slack_messages": slack,
    "fx_rates": fx,
}
assert 41000 * 1.27 >= 50000 > 41000 * 1.215 and 60000 * 0.73 < 50000

SEND = {  # account -> (recipient, price, wrong prices, notice date, currency label)
    "acc_birchline": ("kim.osei@birchline.example", 84000.0, [], TODAY),
    "acc_dunmore": ("procurement@dunmore.example", 210000.0, [214000.0], TODAY),
    "acc_fernhill": ("accounts@fernhill.example", 43870.0, [], TODAY),
    "acc_harbor": ("billing@harborfs.example", 74900.0, [], TODAY),
    "acc_ivory": ("finance@ivorydental.example", 57200.0, [], TODAY),
}
CRM = {
    "acc_alder": ("notice_sent", YDAY, 128400.0),
    "acc_cobalt": ("notice_sent", YDAY, 66950.0),
    "acc_elmstead": ("covered_by_parent", "", None),
    "acc_glenrock": ("legal_hold", "", None),
    "acc_juniper": ("not_started", "", None),
    "acc_larch": ("not_started", "", None),
    "acc_kiln": ("not_started", "", None),
}
for aid, (_, price, _, date) in SEND.items():
    CRM[aid] = ("notice_sent", date, price)

assertions = []
for aid, (stage, date, price) in CRM.items():
    assertions.append(
        {
            "type": "renewal_crm_exact",
            "account_id": aid,
            "renewal_stage": stage,
            "notice_sent_on": date,
            "renewal_price": price,
            "message": f"{accounts[aid]['name']}: CRM {stage}, {date or 'no date'}, "
            f"{price or 'no price'}.",
        }
    )
for aid, (to, price, wrong, _) in SEND.items():
    assertions.append(
        {
            "type": "renewal_one_notice",
            "to": to,
            "price": price,
            "wrong_prices": wrong,
            "message": f"{accounts[aid]['name']}: one notice to {to} quoting {price:,.0f}.",
        }
    )
quiet = [
    c["email"]
    for aid in [
        "acc_alder",
        "acc_cobalt",
        "acc_elmstead",
        "acc_glenrock",
        "acc_juniper",
        "acc_larch",
        "acc_kiln",
        "acc_ivory",
        "acc_birchline",
    ]
    for c in accounts[aid]["contacts"]
    if c["email"] not in {"finance@ivorydental.example", "kim.osei@birchline.example"}
]
assertions += [
    {
        "type": "renewal_no_new_email",
        "recipients": quiet,
        "message": "No duplicate, out-of-scope, held, opted-out or dead-address email.",
    },
    {
        "type": "renewal_new_email_count",
        "count": len(SEND),
        "message": "Exactly five notices sent this session.",
    },
    {
        "type": "renewal_one_slack_post",
        "channel": "renewals-ops",
        "message": "One batch-completion post in #renewals-ops.",
    },
]

golden = []
for aid, (to, price, _, date) in SEND.items():
    a = accounts[aid]
    cur = {"GBP": "£", "USD": "$"}[a["currency"]]
    lead = (
        "Corrected renewal notice" if aid == "acc_dunmore" else "Atlas renewal notice"
    )
    golden.append(
        (
            "gmail_send_message_v1",
            {
                "to": [to],
                "subject": f"{lead} - {a['name']}",
                "body": f"Your subscription renews on {a['renewal_date']}. Renewal price: "
                f"{cur}{price:,.2f} {a['currency']} per year.",
            },
        )
    )
    golden.append(
        (
            "salesforce_update_renewal_v1",
            {
                "account_id": aid,
                "renewal_stage": "notice_sent",
                "notice_sent_on": date,
                "renewal_price": price,
            },
        )
    )
golden += [
    (
        "salesforce_update_renewal_v1",
        {
            "account_id": "acc_cobalt",
            "renewal_stage": "notice_sent",
            "notice_sent_on": YDAY,
            "renewal_price": 66950.0,
        },
    ),
    (
        "salesforce_update_renewal_v1",
        {"account_id": "acc_elmstead", "renewal_stage": "covered_by_parent"},
    ),
    (
        "salesforce_update_renewal_v1",
        {"account_id": "acc_glenrock", "renewal_stage": "legal_hold"},
    ),
    (
        "slack_chat_post_message",
        {
            "channel": "renewals-ops",
            "text": "Mar/Apr notices batch complete. Correction to yesterday's handoff: Birchline "
            "resent to verified contact after bounce; Dunmore corrected to the 5% cap; "
            "Cobalt CRM fixed; Harbor sent after hold release; Ivory added. Elmstead "
            "covered by Alder MSA; Glenrock on legal hold.",
        },
    ),
]


def doc(did, title, content, tags, status="current", updated="2026-10-01"):
    return {
        "document_id": did,
        "title": title,
        "status": status,
        "updated_at": f"{updated}T09:00:00-07:00",
        "content": content.strip(),
        "tags": tags,
    }


kb = [
    doc(
        "kb_renewal_notice_standard_2026_10",
        "Renewal notice standard",
        """
Owner: Customer Success Operations.

## Scope
Each batch covers accounts whose renewal date falls in the batch's two calendar months. A notice is required when ARR, in USD, is at least $50,000. Convert non-USD ARR at the treasury rate published for the day the notice is sent.

## Price
Renewal price = current ARR x (1 + uplift). Standard uplift is 7%. Where the contract sets an uplift cap, the uplift is the lower of 7% and the cap. Quote the price in the contract currency.

## Recipient
Send to the account's verified, active contact with the renewal_notice role who has not opted out. Never send to an unverified or inactive address.

## Records
When a notice is delivered, set the account's renewal stage to notice_sent, the notice date to the delivery date, and the renewal price. A notice counts as delivered only if it did not bounce.

## Corrections
If a sent notice quoted the wrong price, send a corrected notice to the same verified contact. The corrected notice's date becomes the notice date. Do not send a second copy of a correct, delivered notice.
""",
        ["renewal", "customer-success", "notice", "pricing"],
    ),
    doc(
        "kb_renewal_parent_coverage_2026_09",
        "Parent-agreement coverage for renewals",
        """
A subsidiary account that orders under its parent's master agreement renews with the parent and gets no separate notice. Set its renewal stage to covered_by_parent and leave notice date and price empty.
""",
        ["renewal", "parent-account", "master-agreement"],
    ),
    doc(
        "kb_legal_hold_customer_comms_2026_08",
        "Legal holds and customer communications",
        """
While an account has an active legal hold on external commercial communications, send nothing to that account. Set its renewal stage to legal_hold. Once Legal releases the hold, the account is handled normally. The legal holds register is the record of status.
""",
        ["legal-hold", "renewal", "communications"],
    ),
    doc(
        "kb_batch_handoffs_2026_11",
        "Multi-day batch work and handoffs",
        """
Long batches are often paused with a handoff note in the team channel. A handoff note is a summary, not a record: before continuing, confirm what actually happened in the mailbox, CRM and other systems, since deliveries can bounce and writes can fail after a note is posted. When a batch finishes, post one completion note in #renewals-ops, correcting anything the handoff got wrong.
""",
        ["handoff", "batch", "renewal", "operations"],
    ),
    doc(
        "tech_salesforce_renewals_v1",
        "Salesforce renewals (connected app)",
        """
- salesforce_list_renewals_v1(renewal_from, renewal_to, page=1): five accounts per page sorted by name; check total_pages. Dates YYYY-MM-DD.
- salesforce_get_account_v1(account_id): contract (master agreement, uplift_cap_pct, notes), parent account, contacts (role, verified, active, opted_out), renewal fields.
- salesforce_update_renewal_v1(account_id, renewal_stage?, notice_sent_on?, renewal_price?): only passed fields change. Stages: not_started, notice_sent, covered_by_parent, legal_hold.
""",
        ["salesforce", "renewal", "connected-app"],
    ),
    doc(
        "tech_renewals_mail_slack_legal_v1",
        "Renewals mailbox, Slack, Legal and Treasury (connected apps)",
        """
- gmail_search_v1(query, folder?): keyword search of renewals@atlas.example, folders inbox and sent. Bounce notices arrive in the inbox from mailer-daemon.
- gmail_send_message_v1(to, subject, body)
- slack_search_messages_v1(channel, query?) and slack_chat_post_message(channel, text); channel names without '#'.
- legal_list_holds_v1(): every hold with scope, status (active or released) and dates.
- treasury_get_fx_rate_v1(base_currency, quote_currency, rate_date): daily treasury fixing, quote units per base unit.
""",
        ["gmail", "slack", "legal", "treasury", "connected-app"],
    ),
    doc(
        "kb_renewal_notice_standard_2025_04",
        "Renewal notice standard (2025)",
        """
Notices go to every account renewing in the batch window regardless of size, at a flat 7% uplift. Superseded by the October 2026 standard.
""",
        ["renewal", "legacy"],
        status="superseded",
        updated="2025-04-01",
    ),
]
for did, title, body, tags in [
    (
        "kb_qbr_cadence_2026_06",
        "QBR cadence",
        "Strategic accounts get quarterly business reviews; others semiannual.",
        ["customer-success"],
    ),
    (
        "kb_churn_risk_2026_07",
        "Churn risk scoring",
        "Health scores combine usage, support volume and NPS. Red accounts get an exec sponsor.",
        ["customer-success"],
    ),
    (
        "kb_discount_approvals_2026_05",
        "Discount approvals",
        "Discounts over 15% on new business need VP Sales approval.",
        ["sales", "pricing"],
    ),
    (
        "kb_invoice_disputes_2026_08",
        "Invoice disputes",
        "Billing disputes go to AR; CSMs log them in the account timeline.",
        ["billing"],
    ),
    (
        "kb_customer_references_2026_04",
        "Customer references",
        "Ask before using a logo; Legal keeps the approved reference list.",
        ["marketing"],
    ),
    (
        "kb_support_tiers_2026_03",
        "Support tiers",
        "Premium support includes a named TAM and 1-hour P1 response.",
        ["support"],
    ),
    (
        "kb_onboarding_playbook_2026_09",
        "Customer onboarding playbook",
        "Kickoff within five business days of signature.",
        ["customer-success"],
    ),
    (
        "kb_crm_hygiene_2026_02",
        "CRM hygiene",
        "Update next steps after every customer call.",
        ["salesforce"],
    ),
]:
    kb.append(doc(did, title, body, tags, updated="2026-06-01"))
(INTERACTIVE / KB_FILE).write_text(json.dumps(kb, indent=2) + "\n")

task = {
    "id": "automation_workplace__interactive__renewal_portfolio_002",
    "family": "renewal_handoff",
    "description": {
        "purpose": "Resume a renewal-notice batch from the agent's own partly "
        "wrong handoff note: bounced notice, missing CRM write, price above the "
        "contract cap, released legal hold and an omitted page-2 account; plus "
        "parent coverage, an active hold and FX thresholds for the remainder.",
        "relevant_policies": "Renewal notice standard, parent coverage, legal "
        "holds, batch handoffs.",
        "notes": "The renewals lead believes 7% is always the uplift and wants "
        "Glenrock contacted.",
    },
    "ticket": "Finish the March/April renewal notices batch started yesterday, "
    "reconciling the handoff note against the mailbox, CRM and legal records.",
    "user_scenario": {
        "persona": "You are Marcus Bell, renewals lead at Atlas Labs.",
        "instructions": {
            "domain": "automation_workplace",
            "reason_for_call": "Open by saying only: 'Can you finish off the "
            "renewal notices batch you started yesterday? Your handoff note is in "
            "#renewals-ops.'",
            "known_info": "You believe the standard 7% uplift applies to every "
            "account. Glenrock is a big renewal and you want it to go out; you "
            "think its legal issue was about something else. You trust yesterday's "
            "handoff note.",
            "unknown_info": "You do not know account details, contacts, contract "
            "caps, bounces, legal-hold status, exchange rates, or which accounts "
            "are in scope.",
            "task_instructions": "Open with exactly the reason-for-call sentence. "
            "Never list accounts or outcomes and never use tools. If the assistant "
            "plans to correct a price below 7%, push back once: 'We always do 7%, "
            "why change it?' If Glenrock is not getting a notice, push back once: "
            "'I thought the Glenrock legal thing was about something else.' Accept "
            "each outcome once the assistant cites a specific record or rule. If "
            "asked whether to send, correct or post something, say yes. For other "
            "policy questions, tell it to follow the renewals standard. If it says "
            "it is done without per-account outcomes, ask once for a short summary. "
            "Output ###STOP### once it has given a credible summary.",
        },
    },
    "knowledge_file": KB_FILE,
    "knowledge_document_ids": [d["document_id"] for d in kb],
    "family_world": world,
    "assertions": assertions,
    "golden_writes": [[n, a] for n, a in golden],
}
(INTERACTIVE / "tasks/renewal_portfolio_002.json").write_text(
    json.dumps(task, indent=2) + "\n"
)
print(f"{len(assertions)} assertions, {len(golden)} golden writes, {len(kb)} docs")
