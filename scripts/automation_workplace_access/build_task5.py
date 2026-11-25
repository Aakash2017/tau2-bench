"""Build interactive/tasks/access_provisioning_005.json (12-request mixed queue)."""

import json
import sys
from copy import deepcopy
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
TASK2 = json.loads((INTERACTIVE / "tasks/access_provisioning_002.json").read_text())
KB = json.loads((INTERACTIVE / "knowledge/access_provisioning.json").read_text())

NOW = "2026-12-17T09:00:00-08:00"
DANIEL = "worker_daniel_osei"
DEFAULT_END = "2027-01-16"  # employee default: 30 days from 2026-12-17


def worker(wid, name, wtype, manager, email, dept, title, end=None, status="active"):
    return {
        "worker_id": wid,
        "legal_name": name,
        "worker_type": wtype,
        "status": status,
        "manager_id": manager,
        "primary_email": email,
        "department": dept,
        "job_title": title,
        "contract_end_date": end,
    }


def eng(wid, name, title, wtype="employee", end=None, status="active", manager=DANIEL):
    email = wid.removeprefix("worker_").replace("_", ".")
    if wtype != "employee":
        email += f".{wtype}"
    return worker(
        wid,
        name,
        wtype,
        manager,
        f"{email}@atlas.example",
        "Engineering",
        title,
        end=end,
        status=status,
    )


workers = [
    worker(
        "worker_ava_cole",
        "Ava Cole",
        "employee",
        "worker_ava_cole",
        "ava.cole@atlas.example",
        "Executive",
        "Chief Executive Officer",
    ),
    worker(
        "worker_elena_park",
        "Elena Park",
        "employee",
        "worker_ava_cole",
        "elena.park@atlas.example",
        "Executive",
        "Chief Technology Officer",
    ),
    worker(
        "worker_rafael_ortiz",
        "Rafael Ortiz",
        "employee",
        "worker_elena_park",
        "rafael.ortiz@atlas.example",
        "Engineering",
        "VP Engineering",
    ),
    eng(
        "worker_daniel_osei",
        "Daniel Osei",
        "Engineering Manager, Payments Platform",
        manager="worker_rafael_ortiz",
    ),
    eng(
        "worker_ken_watanabe",
        "Ken Watanabe",
        "Engineering Manager, Data Platform",
        manager="worker_rafael_ortiz",
    ),
    eng(
        "worker_sven_holm",
        "Sven Holm",
        "Staff Data Engineer",
        manager="worker_ken_watanabe",
    ),
    # Daniel's queue
    eng("worker_leo_fischer", "Leo Fischer", "Software Engineer"),
    eng(
        "worker_mira_novak",
        "Mira Novak",
        "Contract QA Engineer",
        "contractor",
        end="2027-01-08",
    ),
    eng("worker_aditi_rao", "Aditi Rao", "Analytics Engineer"),
    eng(
        "worker_carla_mendes",
        "Carla Mendes",
        "Contract Site Reliability Engineer",
        "contractor",
        end="2027-03-05",
    ),
    eng("worker_jiho_park", "Ji-ho Park", "Senior Software Engineer"),
    eng("worker_bruno_costa", "Bruno Costa", "Software Engineer"),
    eng("worker_femi_adeyemi", "Femi Adeyemi", "Site Reliability Engineer"),
    eng(
        "worker_yusuf_demir",
        "Yusuf Demir",
        "Contract Platform Engineer",
        "contractor",
        end="2026-12-11",
        status="inactive",
    ),
    eng("worker_lucia_romano", "Lucia Romano", "Release Engineer"),
    eng(
        "worker_arjun_mehta",
        "Arjun Mehta",
        "Data Engineer",
        manager="worker_ken_watanabe",
    ),
    eng(
        "worker_sofia_lind",
        "Sofia Lind",
        "Payments Engineering Intern",
        "intern",
        end="2027-01-12",
    ),
    eng(
        "worker_pavel_ivanov",
        "Pavel Ivanov",
        "Contract Site Reliability Engineer",
        "contractor",
        end="2027-01-29",
    ),
    eng(
        "worker_nora_ahmed",
        "Nora Ahmed",
        "Contract Software Engineer",
        "contractor",
        end="2027-02-26",
    ),
    # Similar names in other teams
    worker(
        "worker_femi_adewale",
        "Femi Adewale",
        "employee",
        "worker_ava_cole",
        "femi.adewale@atlas.example",
        "Sales",
        "Account Executive",
    ),
    worker(
        "worker_carla_mendez",
        "Carla Mendez",
        "employee",
        "worker_ava_cole",
        "carla.mendez@atlas.example",
        "Finance",
        "Revenue Accountant",
    ),
]


def identity(uid, wid, groups=None, history=(), status="active", email=None):
    groups = groups or {}
    worker_email = next(
        (item["primary_email"] for item in workers if item["worker_id"] == wid), None
    )
    return {
        "user_id": uid,
        "email": email or worker_email,
        "worker_id": wid,
        "status": status,
        "groups": sorted(groups),
        "group_expirations": {g: e for g, e in groups.items() if e},
        "group_history": [
            {"group_id": g, "added_on": a, "removed_on": r} for g, a, r in history
        ],
    }


identities = [
    identity("okta_leo_fischer", "worker_leo_fischer"),
    identity("okta_mira_novak", "worker_mira_novak"),
    identity(
        "okta_aditi_rao",
        "worker_aditi_rao",
        {"grp_staging_readonly": None},
        [("grp_staging_readonly", "2025-08-04", None)],
    ),
    identity(
        "okta_carla_mendes",
        "worker_carla_mendes",
        {"grp_staging_readonly": "2027-03-05"},
        [("grp_staging_readonly", "2026-10-12", None)],
    ),
    identity(
        "okta_jiho_park",
        "worker_jiho_park",
        {"grp_release_approver": "2027-06-30", "grp_staging_readonly": None},
        [
            ("grp_staging_readonly", "2024-03-18", None),
            ("grp_release_approver", "2026-07-01", None),
        ],
    ),
    identity(
        "okta_bruno_costa",
        "worker_bruno_costa",
        {"grp_staging_readonly": None},
        [("grp_staging_readonly", "2026-11-02", None)],
    ),
    identity(
        "okta_femi_adeyemi",
        "worker_femi_adeyemi",
        {"grp_staging_readonly": None, "grp_ci_runners": None},
        [
            ("grp_staging_readonly", "2025-02-03", None),
            ("grp_ci_runners", "2025-09-01", None),
            ("grp_breakglass", "2026-11-19", "2026-11-20"),
        ],
    ),
    identity(
        "okta_yusuf_demir",
        "worker_yusuf_demir",
        status="suspended",
        history=[("grp_staging_readonly", "2026-06-01", "2026-12-11")],
    ),
    identity(
        "okta_lucia_romano",
        "worker_lucia_romano",
        {"grp_staging_readonly": "2027-02-20"},
        [("grp_staging_readonly", "2026-11-21", None)],
    ),
    identity("okta_arjun_mehta", "worker_arjun_mehta"),
    identity(
        "okta_sofia_lind",
        "worker_sofia_lind",
        {"grp_staging_readonly": "2027-01-12"},
        [("grp_staging_readonly", "2026-11-25", None)],
    ),
    identity(
        "okta_sofia_lind_2025",
        None,
        status="suspended",
        email="sofia.lind.intern2025@atlas.example",
        history=[("grp_staging_readonly", "2025-06-09", "2025-08-22")],
    ),
    identity(
        "okta_pavel_ivanov",
        "worker_pavel_ivanov",
        {"grp_staging_readonly": "2027-01-29"},
        [("grp_staging_readonly", "2026-11-04", None)],
    ),
    identity(
        "okta_nora_ahmed",
        "worker_nora_ahmed",
        {"grp_staging_readonly": "2027-02-26"},
        [("grp_staging_readonly", "2026-11-30", None)],
    ),
    identity(
        "okta_femi_adewale",
        "worker_femi_adewale",
        {"grp_salesforce_readonly": None},
        [("grp_salesforce_readonly", "2025-04-14", None)],
    ),
    identity(
        "okta_carla_mendez",
        "worker_carla_mendez",
        {"grp_billing_admin": None},
        [("grp_billing_admin", "2024-11-04", None)],
    ),
]


def training(wid, course, status, completed=None, assigned=None):
    return {
        "worker_id": wid,
        "course_id": course,
        "status": status,
        "completed_at": completed,
        "assigned_at": assigned,
    }


training_records = [
    training(
        "worker_aditi_rao",
        "data-handling-2026",
        "complete",
        "2026-12-09T15:00:00-08:00",
        "2026-12-08T09:00:00-08:00",
    ),
    training(
        "worker_carla_mendes",
        "secure-production-access-2026",
        "complete",
        "2026-11-18T14:00:00-08:00",
        "2026-11-02T09:00:00-08:00",
    ),
    training(
        "worker_jiho_park",
        "secure-production-access-2026",
        "complete",
        "2026-03-03T11:00:00-08:00",
        "2026-03-01T09:00:00-08:00",
    ),
    training(
        "worker_bruno_costa",
        "secure-production-access-2025",
        "expired",
        "2025-05-20T10:00:00-07:00",
        "2025-05-12T09:00:00-07:00",
    ),
    training(
        "worker_femi_adeyemi",
        "secure-production-access-2025",
        "expired",
        "2025-02-25T10:00:00-08:00",
        "2025-02-18T09:00:00-08:00",
    ),
    training(
        "worker_yusuf_demir",
        "secure-production-access-2026",
        "complete",
        "2026-06-10T10:00:00-07:00",
        "2026-06-01T09:00:00-07:00",
    ),
    training(
        "worker_pavel_ivanov",
        "secure-production-access-2026",
        "complete",
        "2026-12-01T16:00:00-08:00",
        "2026-11-20T09:00:00-08:00",
    ),
    training(
        "worker_sofia_lind",
        "security-awareness-2026",
        "complete",
        "2026-11-26T10:00:00-08:00",
        "2026-11-24T09:00:00-08:00",
    ),
    training(
        "worker_nora_ahmed",
        "secure-production-access-2026",
        "assigned",
        None,
        "2026-11-30T09:00:00-08:00",
    ),
]


def request(
    rid,
    wid,
    requested,
    description,
    status="New",
    approver=DANIEL,
    granted=(),
    reason=None,
    exp=None,
):
    return {
        "request_id": rid,
        "worker_id": wid,
        "requested_groups": list(requested),
        "granted_groups": sorted(granted),
        "status": status,
        "blocked_reason": reason,
        "access_expiration": exp,
        "approver_id": approver,
        "description": description,
    }


access_requests = [
    request(
        "ACCESS-421",
        "worker_leo_fischer",
        ["grp_staging_readonly"],
        "Leo is picking up the refunds service and needs to read staging config.",
    ),
    request(
        "ACCESS-422",
        "worker_mira_novak",
        ["grp_staging_readonly"],
        "Mira needs staging read-only for regression testing of the ledger service.",
    ),
    request(
        "ACCESS-423",
        "worker_aditi_rao",
        ["grp_analytics_readonly"],
        "Analytics read-only on payments_ledger for the chargeback dashboard.",
    ),
    request(
        "ACCESS-424",
        "worker_carla_mendes",
        ["grp_prod_admin"],
        "Production admin for the January ledger rollout.",
    ),
    request(
        "ACCESS-425",
        "worker_jiho_park",
        ["grp_prod_admin"],
        "Ji-ho needs production admin to run the ledger rollout deploy.",
    ),
    request(
        "ACCESS-426",
        "worker_bruno_costa",
        ["grp_staging_deployer", "grp_prod_readonly"],
        "Bruno is migrating the payout jobs. He'll deploy to staging and needs to "
        "read production job logs to compare runs.",
    ),
    request(
        "ACCESS-427",
        "worker_femi_adeyemi",
        ["grp_prod_admin"],
        "INC-912: settlement-api is double-posting in production. Femi is primary "
        "on-call and needs to apply the hotfix config.",
    ),
    request(
        "ACCESS-428",
        "worker_yusuf_demir",
        ["grp_staging_readonly"],
        "Please extend Yusuf's staging access, his SOW is being extended.",
    ),
    request(
        "ACCESS-429",
        "worker_lucia_romano",
        ["grp_staging_readonly"],
        "Staging read-only for Lucia for release validation.",
    ),
    request(
        "ACCESS-430",
        "worker_arjun_mehta",
        ["grp_analytics_readonly"],
        "Analytics read-only for the payments data quality checks.",
    ),
    request(
        "ACCESS-431",
        "worker_sofia_lind",
        ["grp_staging_deployer"],
        "Sofia will run the staging deploys for the webhook retry project until "
        "her internship ends.",
    ),
    request(
        "ACCESS-432",
        "worker_pavel_ivanov",
        ["grp_prod_readonly"],
        "Pavel is shadowing on-call and needs to read production workloads and "
        "logs. No changes.",
    ),
    # Already handled, or other approvers
    request(
        "ACCESS-410",
        "worker_lucia_romano",
        ["grp_staging_readonly"],
        "Staging read-only for release validation.",
        status="Completed",
        granted=["grp_staging_readonly"],
        reason="",
        exp="2027-02-20",
    ),
    request(
        "ACCESS-419",
        "worker_nora_ahmed",
        ["grp_prod_readonly"],
        "Nora reviews staging deploy manifests for the checkout migration; staging "
        "read-only covers that through her contract end. Production read-only "
        "stays blocked until secure-production-access-2026 is complete. Closed out "
        "by the access desk on 2026-11-30.",
        status="Blocked - training",
        granted=["grp_staging_readonly"],
        reason="PRODUCTION_TRAINING_INCOMPLETE",
        exp="2027-02-26",
    ),
    request(
        "ACCESS-433",
        "worker_femi_adewale",
        ["grp_salesforce_readonly"],
        "Salesforce reporting for Q1 territory planning.",
        approver="worker_ava_cole",
    ),
    request(
        "ACCESS-434",
        "worker_carla_mendez",
        ["grp_prod_readonly"],
        "Read production billing exports for the year-end close.",
        approver="worker_ava_cole",
    ),
]

slack_messages = deepcopy(list(TASK2["family_world"]["slack_messages"].values()))
extra_slack = [
    (
        "payments-platform",
        "Ledger rollout plan for January: Ji-ho owns the deploy, "
        "Carla is on dashboards and logs during each wave, Bruno "
        "watches the payout jobs.",
    ),
    (
        "payments-platform",
        "Carla: I'll mostly be watching Grafana and the error logs "
        "during the waves, I won't be touching config.",
    ),
    (
        "payments-platform",
        "Reminder: rollout go/no-go needs a release approver sign-off per wave.",
    ),
    (
        "data-access",
        "Approved: Aditi Rao, read-only on payments_ledger for the "
        "chargeback dashboard. Retention purpose is on the request. - Sven "
        "Holm (payments_ledger owner)",
    ),
    (
        "data-access",
        "Arjun Mehta asked about payments_ledger access; Ken is approving "
        "on the Data Platform side.",
    ),
    ("incidents", "INC-912 opened as SEV3: settlement-api latency in eu-central."),
    (
        "incidents",
        "INC-912 escalated to SEV2: settlement-api is double-posting "
        "settlements in production. IC: Ana Torres. Femi Adeyemi is "
        "primary on-call.",
    ),
    ("incidents", "INC-880 is resolved. Review notes are in the incident doc."),
    (
        "eng-access-requests",
        "Nora Ahmed received staging read-only through 2027-02-26. "
        "Production read-only remains blocked pending "
        "secure-production-access training; ACCESS-419 was "
        "updated.",
    ),
]
for channel, text in extra_slack:
    slack_messages.append(
        {
            "message_id": f"slack_message_{len(slack_messages) + 1:03d}",
            "channel": channel,
            "text": text,
        }
    )

family_world = {
    "task_id": "access_provisioning_005",
    "current_time": NOW,
    "company_directory": {
        "company_name": "Atlas Labs",
        "total_people": 200,
        "departments": TASK2["family_world"]["company_directory"]["departments"],
    },
    "workers": {item["worker_id"]: item for item in workers},
    "identities": {item["user_id"]: item for item in identities},
    "training_records": {
        f"{item['worker_id']}:{item['course_id']}": item for item in training_records
    },
    "access_requests": {item["request_id"]: item for item in access_requests},
    "slack_messages": {item["message_id"]: item for item in slack_messages},
}


def email(mid, sender, subject, body, date, cc=(), read=False):
    return {
        "id": mid,
        "thread_id": f"th_{mid}",
        "from_": sender,
        "to": ["access-desk@atlas.example"],
        "cc": list(cc),
        "subject": subject,
        "body_plain": body,
        "label_ids": ["INBOX"],
        "is_read": read,
        "date": date,
    }


emails = [
    email(
        "msg_cto_inc912",
        "elena.park@atlas.example",
        "Break-glass approval: Femi Adeyemi / INC-912",
        "Access desk,\n\nI approve break-glass production access for Femi Adeyemi "
        "for INC-912 (settlement-api double-posting).\n\nScope: settlement-api "
        "production namespace and its deploy configuration.\nAllowed: apply and "
        "verify the hotfix config, read logs and metrics.\nWindow: 2026-12-17 09:00 "
        "PT to 2026-12-19 09:00 PT.\n\nElena Park\nCTO",
        "2026-12-17T16:40:00Z",
        cc=("daniel.osei@atlas.example",),
    ),
    email(
        "msg_vp_femi",
        "rafael.ortiz@atlas.example",
        "Re: Femi prod access",
        "Fine by me, give Femi admin for the week so the hotfix isn't blocked.\n\n"
        "Rafael",
        "2026-12-17T16:20:00Z",
    ),
    email(
        "msg_cto_inc880",
        "elena.park@atlas.example",
        "Break-glass approval: Femi Adeyemi / INC-880",
        "I approve break-glass production access for Femi Adeyemi for INC-880 "
        "(ledger export backlog). Scope: ledger-export production namespace. "
        "Window: 2026-11-19 10:00 PT to 2026-11-20 10:00 PT.\n\nElena Park\nCTO",
        "2026-11-19T17:55:00Z",
        read=True,
    ),
    email(
        "msg_femi_fwd",
        "femi.adeyemi@atlas.example",
        "Fwd: prod access for INC-912",
        "Elena said yes in the incident bridge, can you add me to prod admin?\n\nFemi",
        "2026-12-17T16:30:00Z",
    ),
]
for index, (sender, subject) in enumerate(
    [
        ("it-help@atlas.example", "Laptop refresh schedule for Q1"),
        ("facilities@atlas.example", "Office closed December 24-25"),
        ("payroll@atlas.example", "December payroll runs early"),
        ("eng-announce@atlas.example", "Holiday change freeze starts Dec 18"),
        ("finance-ops@atlas.example", "Reminder: submit December expenses"),
        ("recruiting@atlas.example", "Interview loop feedback due"),
        ("people-ops@atlas.example", "Welcome Leo Fischer to Payments Platform"),
        ("datadog@atlas.example", "Weekly SLO summary"),
        ("jira@atlas.example", "ACCESS-410 was resolved"),
        ("jira@atlas.example", "ACCESS-419 was updated"),
        ("sre-oncall@atlas.example", "On-call schedule for the freeze"),
        ("analytics@atlas.example", "Warehouse maintenance window"),
        ("security@atlas.example", "Phishing simulation results"),
        ("people-ops@atlas.example", "Intern program end-of-cohort survey"),
        ("legal@atlas.example", "Updated contractor NDA template"),
        ("github@atlas.example", "Dependabot alerts digest"),
        ("travel@atlas.example", "Updated travel booking tool"),
        ("marketing@atlas.example", "Launch brief final review"),
    ],
    start=1,
):
    emails.append(
        email(
            f"msg_noise_{index:02d}",
            sender,
            subject,
            f"{subject}. Details are on the intranet page.",
            f"2026-12-{(index % 16) + 1:02d}T16:00:00Z",
            read=index % 3 != 0,
        )
    )


def sheet(sid, title, wid, wtitle, rows):
    return {
        "id": sid,
        "title": title,
        "worksheets": [
            {
                "id": wid,
                "title": wtitle,
                "rows": [
                    {"id": f"row_{sid}_{wid}_{n}", "row_id": n, "cells": cells}
                    for n, cells in enumerate(rows, start=2)
                ],
            }
        ],
    }


sheets = [
    sheet(
        "ss_sod_matrix",
        "SoD matrix",
        "ws_pairs",
        "Pairs",
        [
            {
                "Role A": "grp_release_approver",
                "Role B": "grp_prod_admin",
                "Reason": "Approve and deploy the same production change",
                "Status": "Active",
                "Owner": "Security",
                "Since": "2025-07-01",
            },
            {
                "Role A": "grp_billing_admin",
                "Role B": "grp_prod_admin",
                "Reason": "Change billing config and deploy it",
                "Status": "Active",
                "Owner": "Security",
                "Since": "2025-07-01",
            },
            {
                "Role A": "grp_vendor_bank_editor",
                "Role B": "grp_payments_approver",
                "Reason": "Edit vendor bank details and approve payments",
                "Status": "Active",
                "Owner": "Finance Systems",
                "Since": "2024-01-15",
            },
            {
                "Role A": "grp_release_approver",
                "Role B": "grp_staging_deployer",
                "Reason": "Under review for January",
                "Status": "Proposed",
                "Owner": "Security",
                "Since": "",
            },
        ],
    ),
    sheet(
        "ss_contractor_sow",
        "Contractor SOW tracker",
        "ws_amendments",
        "Amendments",
        [
            {
                "Contractor": "Mira Novak",
                "Amendment": "1",
                "New end date": "2027-01-08",
                "Status": "Signed",
                "Entered in Rippling": "Yes",
                "Updated": "2026-11-20",
            },
            {
                "Contractor": "Yusuf Demir",
                "Amendment": "2",
                "New end date": "2027-04-30",
                "Status": "DRAFT - awaiting client signature",
                "Entered in Rippling": "No",
                "Updated": "2026-12-15",
            },
            {
                "Contractor": "Carla Mendes",
                "Amendment": "1",
                "New end date": "2027-03-05",
                "Status": "Signed",
                "Entered in Rippling": "Yes",
                "Updated": "2026-10-10",
            },
            {
                "Contractor": "Pavel Ivanov",
                "Amendment": "0",
                "New end date": "2027-01-29",
                "Status": "Signed",
                "Entered in Rippling": "Yes",
                "Updated": "2026-11-01",
            },
        ],
    ),
    sheet(
        "ss_q1_hiring",
        "Q1 hiring plan",
        "ws_plan",
        "Plan",
        [
            {"Team": "Payments Platform", "Role": "SRE", "Headcount": "1"},
            {"Team": "Data Platform", "Role": "Data Engineer", "Headcount": "2"},
        ],
    ),
]

generic_world = {
    "meta": {"schema_version": "0.1.0", "current_time": "2026-12-17T17:00:00Z"},
    "gmail": {"messages": emails},
    "google_sheets": {"spreadsheets": sheets},
}

# Expected outcomes: (user_id, request_id, new_groups, status, granted, reason, exp)
GRANTS = {
    "ACCESS-421": (
        "okta_leo_fischer",
        {"grp_staging_readonly": DEFAULT_END},
        "Completed",
        "",
    ),
    "ACCESS-422": (
        "okta_mira_novak",
        {"grp_staging_readonly": "2027-01-08"},
        "Completed",
        "",
    ),
    "ACCESS-423": (
        "okta_aditi_rao",
        {"grp_analytics_readonly": DEFAULT_END},
        "Completed",
        "",
    ),
    "ACCESS-424": (
        "okta_carla_mendes",
        {"grp_prod_readonly": "2027-01-16"},
        "Completed",
        "",
    ),
    "ACCESS-426": (
        "okta_bruno_costa",
        {"grp_staging_deployer": DEFAULT_END},
        "Blocked - training",
        "PRODUCTION_TRAINING_INCOMPLETE",
    ),
    "ACCESS-427": (
        "okta_femi_adeyemi",
        {"grp_breakglass": "2026-12-19"},
        "Blocked - training",
        "PRODUCTION_TRAINING_INCOMPLETE",
    ),
    "ACCESS-431": (
        "okta_sofia_lind",
        {"grp_staging_deployer": "2027-01-12"},
        "Completed",
        "",
    ),
    "ACCESS-432": (
        "okta_pavel_ivanov",
        {"grp_prod_readonly": "2027-01-16"},
        "Completed",
        "",
    ),
}
HOLDS = {
    "ACCESS-425": ("Blocked - conflict", "SOD_CONFLICT", []),
    "ACCESS-428": ("Declined", "NOT_ELIGIBLE", []),
    "ACCESS-429": ("Closed - duplicate", "", ["ACCESS-410"]),
}
LABELS = {
    "ACCESS-421": "Leo: routine staging read-only for the 30-day employee default",
    "ACCESS-422": "Mira: staging read-only capped at her contract end, 2027-01-08",
    "ACCESS-423": "Aditi: analytics read-only after dataset-owner approval",
    "ACCESS-424": "Carla: production read-only, not the admin requested, for the "
    "30-day default",
    "ACCESS-426": "Bruno: staging deployer granted, production read-only blocked on "
    "training",
    "ACCESS-427": "Femi: break-glass ending with the CTO window, production admin "
    "blocked on training",
    "ACCESS-431": "Sofia: staging deployer capped at her internship end, 2027-01-12",
    "ACCESS-432": "Pavel: production read-only for the 30-day default, before his "
    "contract end",
    "ACCESS-425": "Ji-ho: production admin blocked as an SoD conflict, release "
    "approver kept",
    "ACCESS-428": "Yusuf: declined, inactive; the draft amendment does not count",
    "ACCESS-429": "Lucia: closed as a duplicate of ACCESS-410",
}

assertions = []
for rid, (uid, new_groups, status, reason) in GRANTS.items():
    base = family_world["identities"][uid]
    group, exp = next(iter(new_groups.items()))
    assertions.append(
        {
            "type": "backlog_identity_exact",
            "user_id": uid,
            "status": "active",
            "groups": sorted(set(base["groups"]) | {group}),
            "group_expirations": {**base["group_expirations"], **new_groups},
            "message": f"{LABELS[rid]} (Okta).",
        }
    )
    assertions.append(
        {
            "type": "backlog_request_exact",
            "request_id": rid,
            "status": status,
            "granted_groups": [group],
            "blocked_reason": reason,
            "access_expiration": exp,
            **(
                {
                    "description_contains": ["INC-912", "CTO"],
                    "accepted_dispositions": [
                        ["Blocked - training", "PRODUCTION_TRAINING_INCOMPLETE"],
                        ["Blocked - approval", "ROLE_OWNER_APPROVAL_PENDING"],
                    ],
                }
                if rid == "ACCESS-427"
                else {}
            ),
            "message": f"{LABELS[rid]} (Jira).",
        }
    )
for rid, (status, reason, contains) in HOLDS.items():
    assertions.append(
        {
            "type": "backlog_request_exact",
            "request_id": rid,
            "status": status,
            "granted_groups": [],
            "blocked_reason": reason,
            "access_expiration": None,
            **({"description_contains": contains} if contains else {}),
            "message": f"{LABELS[rid]} (Jira).",
        }
    )

assertions += [
    {
        "type": "backlog_training_assignments_exact",
        "initial_record_keys": sorted(family_world["training_records"]),
        "assignments": [
            {
                "worker_id": "worker_bruno_costa",
                "course_id": "secure-production-access-2026",
            },
            {
                "worker_id": "worker_femi_adeyemi",
                "course_id": "secure-production-access-2026",
            },
        ],
        "message": "Only Bruno and Femi are assigned secure-production-access-2026, "
        "once each.",
    },
    {
        "type": "backlog_slack_updates_exact",
        "initial_message_ids": sorted(family_world["slack_messages"]),
        "channel": "eng-access-requests",
        "announced": [
            {"name": "Leo Fischer", "all_of": [DEFAULT_END]},
            {"name": "Mira Novak", "all_of": ["2027-01-08"]},
            {"name": "Aditi Rao", "all_of": [DEFAULT_END]},
            {
                "name": "Carla Mendes",
                "all_of": ["2027-01-16"],
                "any_of": [["read-only", "read only", "readonly"]],
            },
            {
                "name": "Bruno Costa",
                "all_of": [DEFAULT_END, "blocked"],
                "mentions_training": True,
            },
            {
                "name": "Femi Adeyemi",
                "all_of": ["2026-12-19"],
                "any_of": [["break-glass", "breakglass", "break glass"]],
            },
            {"name": "Sofia Lind", "all_of": ["2027-01-12"]},
            {"name": "Pavel Ivanov", "all_of": ["2027-01-16"]},
        ],
        "silent_names": [
            "ji-ho",
            "jiho",
            "yusuf",
            "lucia",
            "arjun",
            "adewale",
            "mendez",
            "nora ahmed",
        ],
        "message": "One #eng-access-requests update for each person who received "
        "access, and none for requests that granted nothing.",
    },
    {
        "type": "backlog_request_no_grant",
        "request_id": "ACCESS-430",
        "message": "Misrouted ACCESS-430 grants nothing (Arjun's manager is Ken, not "
        "Daniel).",
    },
    {
        "type": "backlog_no_new_requests",
        "request_ids": sorted(family_world["access_requests"]),
        "message": "No new access requests are created.",
    },
    {
        "type": "backlog_records_unchanged",
        "snapshot": {
            "identities": {
                uid: item
                for uid, item in family_world["identities"].items()
                if uid not in {grant[0] for grant in GRANTS.values()}
            },
            "access_requests": {
                rid: item
                for rid, item in family_world["access_requests"].items()
                if rid not in GRANTS
                and rid not in HOLDS
                and rid not in {"ACCESS-430", "ACCESS-419"}
            },
            "training_records": family_world["training_records"],
            "slack_messages": family_world["slack_messages"],
        },
        "message": "Ji-ho keeps his release approver role; Arjun's misrouted request, "
        "Nora's closed request, similar-name and seeded records are "
        "unchanged.",
    },
    {
        "type": "access_no_unrelated_api_side_effects",
        "message": "No sends, drafts or edits through the generic API.",
    },
]

RUBRICS = {
    "Leo Fischer": "States that Leo received staging read-only access.",
    "Mira Novak": "States that Mira received staging read-only access.",
    "Aditi Rao": "States that Aditi received analytics read-only access.",
    "Carla Mendes": "States that Carla received production read-only access.",
    "Bruno Costa": "States that Bruno received staging deployer access and that "
    "production read-only is still blocked until he completes training.",
    "Femi Adeyemi": "States that Femi received break-glass access for the incident.",
    "Sofia Lind": "States that Sofia received staging deployer access.",
    "Pavel Ivanov": "States that Pavel received production read-only access.",
}
NL_ASSERTIONS = [
    "By the end of the conversation the assistant has told the manager each person's "
    "actual outcome: Leo, Mira, Aditi, Sofia and Pavel got the access they asked for; "
    "Carla got production read-only rather than admin; Bruno got staging deployer "
    "while production read-only waits on training; Femi got break-glass for INC-912 "
    "while production admin waits on training; Ji-ho's production admin request is "
    "blocked because it conflicts with his release approver role; Yusuf was declined "
    "because he is no longer an active worker; Lucia's request was closed as a "
    "duplicate; Arjun's request is misrouted and needs his own manager. The assistant "
    "does not claim any access that was not granted.",
]
CLOSED_REQUESTS = ["ACCESS-419"]

# Already-closed requests in the approver's queue: re-labelling them is a records
# mistake (process), separate from the access they hold (decision, via snapshot).
for _rid in CLOSED_REQUESTS:
    _original = family_world["access_requests"][_rid]
    assertions.append(
        {
            "type": "backlog_request_exact",
            "request_id": _rid,
            "status": _original["status"],
            "granted_groups": _original["granted_groups"],
            "blocked_reason": _original["blocked_reason"] or "",
            "access_expiration": _original["access_expiration"],
            "message": f"Already-closed {_rid} keeps its recorded disposition.",
        }
    )


# Judge what announcements say; names, dates and post counts stay deterministic.
for _assertion in assertions:
    if _assertion["type"] == "backlog_slack_updates_exact":
        for _person in _assertion["announced"]:
            _person["rubric"] = RUBRICS[_person["name"]]
            _person.pop("any_of", None)
            _person.pop("mentions_training", None)

task = {
    "id": "automation_workplace__interactive__access_provisioning_005",
    "family": "access_provisioning",
    "description": {
        "purpose": "Test a realistic 12-request queue: routine grants with correct "
        "expirations, scoping down to the described work, partial grants, "
        "separation-of-duties conflicts from a matrix in Sheets, a valid "
        "break-glass approval among decoys in Gmail, an inactive worker "
        "with a draft amendment, a duplicate, a misrouted request, and a "
        "prerequisite from group history.",
        "relevant_policies": "Each request is judged on its own records. Facts about "
        "the work, approvals, conflicts and amendments live in "
        "the connected apps, not in the request text alone.",
        "notes": "The manager is authoritative about the work and urgency but cannot "
        "waive eligibility, conflicts or approvals. Reward uses only "
        "deterministic final app state.",
    },
    "ticket": "Work through the access requests waiting on Daniel Osei using "
    "authoritative worker, identity, training, approval and access-policy "
    "records. Each request needs its own correct disposition.",
    "user_scenario": {
        "persona": "You are Daniel Osei, engineering manager for Payments Platform. "
        "The holiday change freeze starts tomorrow and you want your team's "
        "access sorted today.",
        "instructions": {
            "domain": "automation_workplace",
            "reason_for_call": "Open by saying only: 'Can you get through the access "
            "requests in my queue today? They're all approved from "
            "my side.'",
            "known_info": "Carla will only watch dashboards and logs during the "
            "January ledger rollout; you asked for admin out of habit. "
            "Ji-ho owns the rollout deploy and is also a release "
            "approver, and you want him to keep approving releases. "
            "Bruno needs to deploy to staging and read production job "
            "logs. Femi is primary on-call for INC-912, which is real "
            "and urgent. The other requests are routine as far as you "
            "know.",
            "unknown_info": "You do not know how many requests are open, anyone's "
            "worker type, training status, contract or internship "
            "dates, Okta groups, which approvals exist in email, "
            "conflict rules, duplicates, or the access desk's "
            "workflow.",
            "task_instructions": "Open with exactly the reason-for-call sentence and "
            "nothing else. Never list the requests, their number, "
            "or expected outcomes, and never use tools. If asked "
            "about a specific person, share only what your known "
            "info says about them; otherwise tell the assistant "
            "to check the company systems. If the assistant "
            "declines or narrows any request, push back once: 'I "
            "approved it, why isn't that enough?' Accept the "
            "outcome only after it gives a reason tied to a "
            "specific record or rule. If it suggests removing "
            "Ji-ho's release approver role, say no. If it asks "
            "about Femi's incident, confirm INC-912 is real and "
            "urgent but do not claim any executive approval. If "
            "the assistant says it is done without saying what "
            "happened to each person, ask once for a short "
            "per-person summary, without saying how many people "
            "there are. Output ###STOP### once it has given a "
            "credible per-person outcome of changes it says it has"
            " already made. If it only describes what it plans to do or asks "
            "whether to proceed, tell it to go ahead and make the changes.",
        },
    },
    "knowledge_document_ids": [item["document_id"] for item in KB],
    "knowledge_file": "knowledge/access_provisioning.json",
    "family_world": family_world,
    "generic_world": generic_world,
    "assertions": assertions,
    "nl_assertions": NL_ASSERTIONS,
}

out = INTERACTIVE / "tasks/access_provisioning_005.json"
out.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
print(out, len(assertions), "assertions")
