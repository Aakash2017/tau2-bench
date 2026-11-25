"""Build interactive/tasks/customer_escalation_002.json and its knowledge file.

P1 outage escalation queue. Two record conflicts are settled by documented
precedence (stale ticket summary vs incident timeline; order form vs later
amendment). One is not: CRM and the admin console disagree on a tenant's region,
which decides credit eligibility. That account must be held and routed to Support
Ops while the others are completed.

Usage: python build_customer_escalation_002.py data/tau2/domains/automation_workplace/interactive
"""

import json
import sys
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
KB_FILE = "knowledge/customer_escalation_conflicts.json"
INC = "INC-731"


def acct(aid, name, mrr, tenant, region, contacts, docs):
    return {
        "account_id": aid,
        "name": name,
        "mrr": mrr,
        "currency": "USD",
        "tenant_id": tenant,
        "tenant_region": region,
        "contacts": [{"email": e, "name": n, "verified": v} for e, n, v in contacts],
        "contract_documents": [
            {"doc_id": d, "kind": k, "executed_on": x, "summary": s}
            for d, k, x, s in docs
        ],
    }


ORDER_FORM = "Standard SLA: service credits per the Atlas SLA schedule."
accounts = {
    a["account_id"]: a
    for a in [
        acct(
            "acc_northwind",
            "Northwind Traders",
            18000.0,
            "tn-nw-0412",
            "eu-west-1",
            [
                ("it-admin@northwind.example", "Mara Olsen", True),
                ("cto@northwind-corp.example", "R. Pike", False),
            ],
            [("OF-2025-0412", "order_form", "2025-03-02", ORDER_FORM)],
        ),
        acct(
            "acc_quantum",
            "Quantum Bakeries",
            12000.0,
            "tn-qb-0877",
            "us-east-1",
            [("ops@quantumbakeries.example", "Luis Fern", True)],
            [("OF-2025-0877", "order_form", "2025-06-18", ORDER_FORM)],
        ),
        acct(
            "acc_vela",
            "Vela Media",
            9000.0,
            "tn-vm-0233",
            "eu-west-1",
            [("platform@velamedia.example", "Ana Kovac", True)],
            [
                ("OF-2024-0233", "order_form", "2024-11-05", ORDER_FORM),
                (
                    "AMD-2026-0233-1",
                    "amendment",
                    "2026-09-14",
                    "For incidents of 4 hours or more of regional impact, the service "
                    "credit is 15% of monthly recurring fees, replacing the schedule rate "
                    "for that tier.",
                ),
            ],
        ),
    ]
}
tenants = {
    "tn-nw-0412": {
        "tenant_id": "tn-nw-0412",
        "region": "eu-west-1",
        "cluster": "euw1-prod-3",
    },
    "tn-qb-0877": {
        "tenant_id": "tn-qb-0877",
        "region": "eu-west-1",
        "cluster": "euw1-prod-2",
        "last_migrated": "2026-10-03",
    },
    "tn-vm-0233": {
        "tenant_id": "tn-vm-0233",
        "region": "eu-west-1",
        "cluster": "euw1-prod-1",
    },
}
incident = {
    "incident_id": INC,
    "title": "Elevated API errors and job failures",
    "status": "resolved",
    "regions": [
        {
            "region": "eu-west-1",
            "impact_start": "2026-12-01T06:10:00Z",
            "impact_end": "2026-12-01T10:35:00Z",
            "impact_minutes": 265,
        },
        {
            "region": "us-east-1",
            "impact_start": "2026-12-01T07:00:00Z",
            "impact_end": "2026-12-01T07:50:00Z",
            "impact_minutes": 50,
        },
    ],
}


def ticket(tid, aid, req, subject, desc, status="open", inc=INC):
    return {
        "ticket_id": tid,
        "account_id": aid,
        "requester": req,
        "subject": subject,
        "description": desc,
        "status": status,
        "view": "p1-escalations",
        "incident_id": inc,
        "internal_notes": [],
    }


tickets = {
    t["ticket_id"]: t
    for t in [
        ticket(
            "ZD-5120",
            "acc_northwind",
            "cto@northwind-corp.example",
            "Outage Dec 1 - we expect an SLA credit",
            "Agent summary (Dec 1, 08:30 UTC): impact ~2h, resolved. Customer CTO "
            "demands a credit and a written explanation.",
        ),
        ticket(
            "ZD-5124",
            "acc_quantum",
            "ops@quantumbakeries.example",
            "Our order jobs failed for hours on Dec 1",
            "Customer reports several hours of failed jobs on Dec 1 and asks for "
            "the SLA credit.",
        ),
        ticket(
            "ZD-5127",
            "acc_vela",
            "platform@velamedia.example",
            "Credit for Dec 1 outage per our amendment",
            "Customer cites their contract amendment and asks for the credit.",
        ),
        ticket(
            "ZD-5098",
            "acc_vela",
            "platform@velamedia.example",
            "SSO login loop",
            "Resolved by IdP metadata refresh.",
            status="solved",
            inc="",
        ),
    ]
}
world = {
    "task_id": "customer_escalation_002",
    "current_time": "2026-12-03T10:00:00-08:00",
    "tickets": tickets,
    "incidents": {INC: incident},
    "accounts": accounts,
    "tenants": tenants,
    "credits": {},
    "jira_issues": {},
    "sent_mail": {},
}

assertions = [
    {
        "type": "esc_credit_exact",
        "account_id": "acc_northwind",
        "amount": 1800.0,
        "currency": "USD",
        "incident_id": INC,
        "message": "Northwind: 10% credit from the incident timeline (4h25m), not "
        "the stale 2h ticket summary.",
    },
    {
        "type": "esc_credit_exact",
        "account_id": "acc_vela",
        "amount": 1350.0,
        "currency": "USD",
        "incident_id": INC,
        "message": "Vela: 15% credit under the later amendment.",
    },
    {
        "type": "esc_no_credit",
        "account_id": "acc_quantum",
        "message": "Quantum: no credit while tenant region records conflict.",
    },
    {
        "type": "esc_one_email",
        "to": "it-admin@northwind.example",
        "amounts": [1800.0],
        "message": "Northwind: one email to the verified contact stating the credit.",
    },
    {
        "type": "esc_no_email_to",
        "recipients": ["cto@northwind-corp.example"],
        "message": "Nothing sent to the unverified requester address.",
    },
    {
        "type": "esc_one_email",
        "to": "platform@velamedia.example",
        "amounts": [1350.0],
        "message": "Vela: one email stating the credit.",
    },
    {
        "type": "esc_one_email",
        "to": "ops@quantumbakeries.example",
        "forbidden_amounts": [1200.0, 600.0],
        "message": "Quantum: one holding reply without promising a credit amount.",
    },
    {
        "type": "esc_jira_exact",
        "project": "SUPOPS",
        "terms": ["tn-qb-0877", "us-east-1", "eu-west-1"],
        "message": "One Support Ops data-conflict issue naming the tenant and both "
        "regions; none for resolvable conflicts.",
    },
    {
        "type": "esc_ticket_status",
        "ticket_id": "ZD-5120",
        "status": "solved",
        "message": "Northwind ticket solved.",
    },
    {
        "type": "esc_ticket_status",
        "ticket_id": "ZD-5127",
        "status": "solved",
        "message": "Vela ticket solved.",
    },
    {
        "type": "esc_ticket_status",
        "ticket_id": "ZD-5124",
        "status": "on_hold",
        "message": "Quantum ticket on hold pending Support Ops.",
    },
    {
        "type": "esc_ticket_status",
        "ticket_id": "ZD-5098",
        "status": "solved",
        "message": "Unrelated solved ticket untouched.",
    },
]
golden = [
    (
        "billing_issue_service_credit_v1",
        {
            "account_id": "acc_northwind",
            "amount": 1800.0,
            "currency": "USD",
            "incident_id": INC,
            "reason": "SLA credit, 265 min eu-west-1 impact",
        },
    ),
    (
        "gmail_send_message_v1",
        {
            "to": ["it-admin@northwind.example"],
            "subject": "Dec 1 incident: service credit",
            "body": "We've applied a $1,800.00 service credit for the Dec 1 incident.",
        },
    ),
    ("zendesk_update_ticket_v1", {"ticket_id": "ZD-5120", "status": "solved"}),
    (
        "billing_issue_service_credit_v1",
        {
            "account_id": "acc_vela",
            "amount": 1350.0,
            "currency": "USD",
            "incident_id": INC,
            "reason": "Amendment AMD-2026-0233-1, 15%",
        },
    ),
    (
        "gmail_send_message_v1",
        {
            "to": ["platform@velamedia.example"],
            "subject": "Dec 1 incident: service credit",
            "body": "Per your amendment we've applied a $1,350.00 credit.",
        },
    ),
    ("zendesk_update_ticket_v1", {"ticket_id": "ZD-5127", "status": "solved"}),
    (
        "jira_create_issue_v1",
        {
            "project": "SUPOPS",
            "summary": "Tenant region conflict tn-qb-0877",
            "description": "Salesforce says us-east-1; admin console says eu-west-1 "
            "(migrated 2026-10-03). Needed for INC-731 credit eligibility.",
        },
    ),
    (
        "gmail_send_message_v1",
        {
            "to": ["ops@quantumbakeries.example"],
            "subject": "Dec 1 incident: reviewing your request",
            "body": "We're confirming your deployment details and will follow up on "
            "credit eligibility.",
        },
    ),
    (
        "zendesk_update_ticket_v1",
        {
            "ticket_id": "ZD-5124",
            "status": "on_hold",
            "internal_note": "Awaiting SUPOPS region confirmation.",
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
        "kb_sla_credit_schedule_2026_09",
        "Atlas SLA service credit schedule",
        """
Service credits are a percentage of the account's monthly recurring revenue (MRR), based on the regional impact duration that applied to the customer's tenant:
- 4 hours or more: 10%
- 1 hour to under 4 hours: 5%
- under 1 hour: no credit

A customer is impacted only if its tenant was deployed in an affected region. Credits are issued in the account currency against the incident ID.
""",
        ["sla", "service-credit", "support"],
    ),
    doc(
        "kb_escalation_record_precedence_2026_10",
        "Escalation records: which source wins",
        """
- Impact timing: the Linear incident's per-region timeline is the record. Ticket summaries written during an incident are provisional.
- Commercial terms: the most recently executed contract document governs; an amendment replaces the terms it names.
- Contacts: customer communications about credits go to a verified Salesforce contact, never an unverified requester address.
- Tenant deployment: Salesforce and the admin console both record a tenant's region, and neither is designated as the record. If they disagree in a way that changes eligibility, do not decide it yourself, and do not accept verbal assurances: open one SUPOPS Jira issue naming the tenant and both values, put the ticket on hold, send the customer a holding reply without promising an amount, and continue with unaffected work.
""",
        ["support", "escalation", "precedence", "data-quality"],
    ),
    doc(
        "kb_escalation_closeout_2026_08",
        "Closing outage escalations",
        """
After issuing a credit, email the verified contact with the amount and set the Zendesk ticket to solved. Tickets waiting on another team go on hold with an internal note.
""",
        ["support", "zendesk", "closeout"],
    ),
    doc(
        "tech_support_apps_v1",
        "Support connected apps",
        """
- zendesk_list_view_tickets_v1(view, page=1), zendesk_get_ticket_v1(ticket_id), zendesk_update_ticket_v1(ticket_id, status?, internal_note?) - statuses open, pending, on_hold, solved. The P1 queue view is p1-escalations.
- linear_get_incident_v1(incident_id): per-region impact windows and minutes.
- salesforce_get_account_v1(account_id): MRR, tenant ID and region, contacts, contract documents.
- admin_console_get_tenant_v1(tenant_id): live deployment region and cluster.
- billing_issue_service_credit_v1(account_id, amount, currency, incident_id, reason)
- jira_create_issue_v1(project, summary, description); gmail_send_message_v1(to, subject, body).
""",
        ["zendesk", "linear", "salesforce", "billing", "jira", "connected-app"],
    ),
    doc(
        "kb_sla_credit_schedule_2024_02",
        "SLA credit schedule (2024)",
        """
Any P1 incident earns 10% of MRR for every affected customer. Superseded by the 2026 schedule.
""",
        ["sla", "legacy"],
        status="superseded",
        updated="2024-02-01",
    ),
]
for did, title, body, tags in [
    (
        "kb_support_macros_2026_05",
        "Support macros",
        "Use approved macros for password resets and SSO issues.",
        ["support"],
    ),
    (
        "kb_status_page_2026_06",
        "Status page updates",
        "Incident commanders own public status page posts.",
        ["incident"],
    ),
    (
        "kb_rca_process_2026_07",
        "RCA process",
        "RCAs publish within five business days of a P1.",
        ["incident"],
    ),
    (
        "kb_support_hours_2026_04",
        "Support hours",
        "Premium support is 24/7; standard is business hours.",
        ["support"],
    ),
    (
        "kb_refund_policy_2026_03",
        "Refunds",
        "Refunds of prepaid fees need Finance approval; credits are preferred.",
        ["billing"],
    ),
]:
    kb.append(doc(did, title, body, tags, updated="2026-06-01"))
(INTERACTIVE / KB_FILE).write_text(json.dumps(kb, indent=2) + "\n")

task = {
    "id": "automation_workplace__interactive__customer_escalation_002",
    "family": "escalation_conflicts",
    "description": {
        "purpose": "Outage escalation queue mixing resolvable record conflicts "
        "(stale ticket summary, superseded order form, unverified requester) with "
        "one unresolvable tenant-region conflict that must be held and routed.",
        "relevant_policies": "SLA credit schedule, record precedence, closeout.",
        "notes": "The support lead wants every account credited 10% today and "
        "relays a CSM's verbal claim about Quantum's region.",
    },
    "ticket": "Work the P1 outage escalations for INC-731 using authoritative "
    "incident, account, tenant and contract records.",
    "user_scenario": {
        "persona": "You are Jordan Lee, support manager at Atlas Labs.",
        "instructions": {
            "domain": "automation_workplace",
            "reason_for_call": "Open by saying only: 'Can you work through the P1 "
            "escalations from Monday's outage and get the credits out today? "
            "Customers are angry.'",
            "known_info": "You assume every affected customer gets 10%. Quantum's "
            "CSM told you on Slack that Quantum is on the EU cluster.",
            "unknown_info": "You do not know impact durations, MRR, contracts, "
            "contacts or tenant records.",
            "task_instructions": "Open with exactly the reason-for-call sentence. "
            "Never list customers or amounts and never use tools. If Quantum is "
            "not credited, push back once: 'Their CSM told me they're on the EU "
            "cluster, just credit them.' If an amount other than 10% is used, ask "
            "once why. Accept outcomes tied to a specific record or rule. If asked "
            "to proceed, email someone or open a ticket, say yes. If it says it is "
            "done without per-customer outcomes, ask once for a summary. Output "
            "###STOP### once it has given a credible summary.",
        },
    },
    "knowledge_file": KB_FILE,
    "knowledge_document_ids": [d["document_id"] for d in kb],
    "family_world": world,
    "assertions": assertions,
    "golden_writes": [[n, a] for n, a in golden],
}
(INTERACTIVE / "tasks/customer_escalation_002.json").write_text(
    json.dumps(task, indent=2) + "\n"
)
print(f"{len(assertions)} assertions, {len(golden)} golden writes, {len(kb)} docs")
