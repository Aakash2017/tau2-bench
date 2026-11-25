"""Build interactive/tasks/access_provisioning_006.json.

Data Platform queue plus outstanding Q4 review removals. New mechanics: a missing
role-owner approval the desk must request, a time-boxed SoD exception register
(one live, one lapsed), a signed-but-unentered contract amendment, an Okta call
that times out once, and review rows that are marked Remove or left unmarked.
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
TASK2 = json.loads((INTERACTIVE / "tasks/access_provisioning_002.json").read_text())
KB = json.loads((INTERACTIVE / "knowledge/access_provisioning.json").read_text())

NOW = "2026-12-14T09:00:00-08:00"
KEN = "worker_ken_watanabe"
DEFAULT_END = "2027-01-13"  # 30 days from 2026-12-14
OMAR_EXCEPTION_END = "2027-01-08"
LEON_CONTRACT_END = "2027-01-05"
OWNERS = "prod-admin-owners@atlas.example"
MARTA = "marta.kowalski@atlas.example"


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


def eng(wid, name, title, wtype="employee", end=None, status="active", manager=KEN):
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
        "worker_ken_watanabe",
        "Ken Watanabe",
        "Engineering Manager, Data Platform",
        manager="worker_rafael_ortiz",
    ),
    eng(
        "worker_daniel_osei",
        "Daniel Osei",
        "Engineering Manager, Payments Platform",
        manager="worker_rafael_ortiz",
    ),
    eng(
        "worker_marta_kowalski",
        "Marta Kowalski",
        "Engineering Manager, Platform SRE",
        manager="worker_rafael_ortiz",
    ),
    # Ken's team
    eng("worker_sven_holm", "Sven Holm", "Staff Data Engineer"),
    eng("worker_mei_tan", "Mei Tan", "Senior Data Engineer"),
    eng("worker_omar_haddad", "Omar Haddad", "Data Engineer"),
    eng("worker_rui_silva", "Rui Silva", "Data Engineer"),
    eng("worker_hana_kim", "Hana Kim", "Analytics Engineer"),
    eng(
        "worker_leon_brandt",
        "Leon Brandt",
        "Contract Data Engineer",
        "contractor",
        end=LEON_CONTRACT_END,
    ),
    eng("worker_lena_ostrowski", "Lena Ostrowski", "Data Engineer"),
    eng("worker_tomas_ruiz", "Tomas Ruiz", "Data Engineer"),
    eng("worker_ines_moreau", "Ines Moreau", "Senior Data Engineer"),
    # Another team, and similar names elsewhere
    eng(
        "worker_bruno_costa",
        "Bruno Costa",
        "Software Engineer",
        manager="worker_daniel_osei",
    ),
    worker(
        "worker_mei_tanaka",
        "Mei Tanaka",
        "employee",
        "worker_ava_cole",
        "mei.tanaka@atlas.example",
        "Marketing",
        "Lifecycle Marketing Manager",
    ),
    worker(
        "worker_leon_brand",
        "Leon Brand",
        "employee",
        "worker_ava_cole",
        "leon.brand@atlas.example",
        "Sales",
        "Sales Development Representative",
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
    identity(
        "okta_sven_holm",
        "worker_sven_holm",
        {"grp_prod_readonly": "2027-02-28", "grp_staging_deployer": None},
        [
            ("grp_staging_deployer", "2025-03-03", None),
            ("grp_prod_readonly", "2026-09-01", None),
        ],
    ),
    identity(
        "okta_mei_tan",
        "worker_mei_tan",
        {"grp_prod_readonly": "2027-03-31", "grp_staging_readonly": None},
        [
            ("grp_staging_readonly", "2024-06-10", None),
            ("grp_prod_readonly", "2026-10-01", None),
        ],
    ),
    identity(
        "okta_omar_haddad",
        "worker_omar_haddad",
        {"grp_release_approver": "2027-06-30", "grp_staging_readonly": None},
        [
            ("grp_staging_readonly", "2025-01-13", None),
            ("grp_release_approver", "2026-07-01", None),
        ],
    ),
    identity(
        "okta_rui_silva",
        "worker_rui_silva",
        {"grp_release_approver": "2027-06-30", "grp_staging_readonly": None},
        [
            ("grp_staging_readonly", "2025-05-05", None),
            ("grp_release_approver", "2026-07-01", None),
            ("grp_prod_admin", "2026-09-02", "2026-11-30"),
        ],
    ),
    identity(
        "okta_hana_kim",
        "worker_hana_kim",
        {"grp_staging_readonly": None},
        [("grp_staging_readonly", "2026-02-09", None)],
    ),
    identity(
        "okta_leon_brandt",
        "worker_leon_brandt",
        {"grp_staging_readonly": LEON_CONTRACT_END},
        [("grp_staging_readonly", "2026-10-05", None)],
    ),
    identity(
        "okta_lena_ostrowski",
        "worker_lena_ostrowski",
        {"grp_prod_admin": "2027-02-15", "grp_staging_readonly": None},
        [
            ("grp_staging_readonly", "2025-08-18", None),
            ("grp_prod_admin", "2026-08-17", None),
        ],
    ),
    identity(
        "okta_tomas_ruiz",
        "worker_tomas_ruiz",
        {"grp_prod_readonly": "2027-04-01", "grp_staging_readonly": None},
        [
            ("grp_staging_readonly", "2025-11-03", None),
            ("grp_prod_readonly", "2026-10-02", None),
        ],
    ),
    identity(
        "okta_ines_moreau",
        "worker_ines_moreau",
        {"grp_staging_readonly": None},
        [
            ("grp_staging_readonly", "2024-02-05", None),
            ("grp_prod_admin", "2026-05-04", "2026-11-30"),
        ],
    ),
    identity(
        "okta_bruno_costa",
        "worker_bruno_costa",
        {"grp_staging_readonly": None},
        [("grp_staging_readonly", "2026-11-02", None)],
    ),
    identity("okta_mei_tanaka", "worker_mei_tanaka"),
    identity(
        "okta_leon_brand",
        "worker_leon_brand",
        {"grp_salesforce_readonly": None},
        [("grp_salesforce_readonly", "2026-03-02", None)],
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
        f"worker_{name}",
        "secure-production-access-2026",
        "complete",
        f"2026-{month}T11:00:00-08:00",
        f"2026-{month}T09:00:00-08:00",
    )
    for name, month in [
        ("sven_holm", "02-10"),
        ("mei_tan", "03-04"),
        ("omar_haddad", "05-12"),
        ("rui_silva", "02-24"),
        ("leon_brandt", "10-14"),
        ("lena_ostrowski", "04-07"),
        ("tomas_ruiz", "09-22"),
        ("ines_moreau", "01-27"),
    ]
] + [
    training(
        "worker_hana_kim",
        "data-handling-2026",
        "complete",
        "2026-12-04T15:00:00-08:00",
        "2026-12-03T09:00:00-08:00",
    ),
    training(
        "worker_rui_silva",
        "secure-production-access-2025",
        "expired",
        "2025-02-11T10:00:00-08:00",
        "2025-02-03T09:00:00-08:00",
    ),
]


def request(
    rid,
    wid,
    requested,
    description,
    status="New",
    approver=KEN,
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
        "ACCESS-441",
        "worker_sven_holm",
        ["grp_prod_admin"],
        "Sven is running the warehouse partition migration jobs in production in "
        "early January.",
    ),
    request(
        "ACCESS-442",
        "worker_mei_tan",
        ["grp_prod_admin"],
        "Mei will run the billing-events backfill in production after the freeze.",
    ),
    request(
        "ACCESS-443",
        "worker_omar_haddad",
        ["grp_prod_admin"],
        "Omar needs to apply the Kafka retention config change in production himself.",
    ),
    request(
        "ACCESS-444",
        "worker_rui_silva",
        ["grp_prod_admin"],
        "Rui is taking over the CDC connector rollout and needs to apply "
        "connector config in production.",
    ),
    request(
        "ACCESS-445",
        "worker_hana_kim",
        ["grp_analytics_readonly"],
        "Analytics read-only on billing_events for the revenue reconciliation model.",
    ),
    request(
        "ACCESS-446",
        "worker_leon_brandt",
        ["grp_prod_readonly"],
        "Leon needs to read production ingestion pipeline logs while he migrates "
        "the ingestion workers. No changes.",
    ),
    # Already handled, or another approver's queue
    request(
        "ACCESS-435",
        "worker_sven_holm",
        ["grp_staging_deployer"],
        "Staging deployer for the partition migration dry runs. Already held "
        "since 2025; closed with no change. Closed out by the access desk on "
        "2026-12-02.",
        status="Completed",
        granted=["grp_staging_deployer"],
        reason="",
        exp=None,
    ),
    request(
        "ACCESS-447",
        "worker_bruno_costa",
        ["grp_staging_deployer"],
        "Bruno is migrating the payout jobs and will deploy to staging.",
        approver="worker_daniel_osei",
    ),
]

slack_messages = deepcopy(list(TASK2["family_world"]["slack_messages"].values()))
extra_slack = [
    (
        "data-platform",
        "January plan: Sven runs the warehouse partition migration, Mei "
        "the billing-events backfill, Omar the Kafka retention change. "
        "Rui picks up the CDC connector rollout from Ines.",
    ),
    ("data-platform", "Leon's SOW extension is signed, he's with us through March."),
    (
        "data-access",
        "Approved: Hana Kim, read-only on billing_events for the revenue "
        "reconciliation model. Extracts kept 14 days. - Ines Moreau "
        "(billing_events owner)",
    ),
    (
        "security",
        "Q4 privileged-access review is closed. Results are in the review "
        "sheet; thanks to all role owners.",
    ),
    (
        "prod-ops",
        "Kafka retention change for the events cluster is scheduled for "
        "January 6, after the freeze.",
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
    "task_id": "access_provisioning_006",
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
    "injected_faults": [
        {
            "tool_name": "okta_add_user_to_group_v1",
            "match": {"user_id": "okta_leon_brandt"},
            "response": {
                "ok": False,
                "error": "upstream_timeout",
                "detail": "Okta did not confirm the change within 30s. Check the "
                "user's groups before retrying.",
            },
            "remaining": 1,
        }
    ],
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


def owner_approval(mid, rid, name, purpose, date):
    return email(
        mid,
        MARTA,
        f"Re: {rid} production admin for {name}",
        f"Approved as role owner for grp_prod_admin: {name}, {purpose}.\n\n"
        "Marta Kowalski\nPlatform SRE, for the prod-admin owners",
        date,
        cc=(OWNERS,),
    )


emails = [
    owner_approval(
        "msg_owner_441",
        "ACCESS-441",
        "Sven Holm",
        "for the warehouse partition migration",
        "2026-12-11T18:10:00Z",
    ),
    owner_approval(
        "msg_owner_443",
        "ACCESS-443",
        "Omar Haddad",
        "for the Kafka retention change",
        "2026-12-12T17:25:00Z",
    ),
    owner_approval(
        "msg_owner_444",
        "ACCESS-444",
        "Rui Silva",
        "for the CDC connector rollout",
        "2026-12-12T17:40:00Z",
    ),
    email(
        "msg_vp_mei",
        "rafael.ortiz@atlas.example",
        "Re: Mei prod admin",
        "Fine by me, Mei should have admin for the backfill.\n\nRafael",
        "2026-12-13T20:05:00Z",
        cc=("ken.watanabe@atlas.example",),
    ),
    email(
        "msg_security_q4",
        "security@atlas.example",
        "Q4 privileged-access review: results",
        "The Q4 review closed on November 27. Decisions are in the Q4 "
        "privileged-access review sheet, one tab per team.\n\nSecurity",
        "2026-11-28T17:00:00Z",
        read=True,
    ),
]
for index, (sender, subject) in enumerate(
    [
        ("it-help@atlas.example", "Laptop refresh schedule for Q1"),
        ("facilities@atlas.example", "Office closed December 24-25"),
        ("payroll@atlas.example", "December payroll runs early"),
        ("eng-announce@atlas.example", "Holiday change freeze starts Dec 18"),
        ("finance-ops@atlas.example", "Reminder: submit December expenses"),
        ("jira@atlas.example", "ACCESS-435 was resolved"),
        ("datadog@atlas.example", "Weekly SLO summary"),
        ("sre-oncall@atlas.example", "On-call schedule for the freeze"),
        ("analytics@atlas.example", "Warehouse maintenance window"),
        ("security@atlas.example", "Phishing simulation results"),
        ("legal@atlas.example", "Updated contractor NDA template"),
        ("github@atlas.example", "Dependabot alerts digest"),
        ("people-ops@atlas.example", "Holiday party RSVP"),
        ("travel@atlas.example", "Updated travel booking tool"),
    ],
    start=1,
):
    emails.append(
        email(
            f"msg_noise_{index:02d}",
            sender,
            subject,
            f"{subject}. Details are on the intranet page.",
            f"2026-12-{(index % 13) + 1:02d}T16:00:00Z",
            read=index % 3 != 0,
        )
    )


def sheet(sid, title, tabs):
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
            for wid, wtitle, rows in tabs
        ],
    }


def review_row(person, group, decision, applied=""):
    return {
        "Person": person,
        "Group": group,
        "Role owner": "Platform SRE",
        "Decision": decision,
        "Applied": applied,
    }


sheets = [
    sheet(
        "ss_sod_matrix",
        "SoD matrix",
        [
            (
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
            (
                "ws_exceptions",
                "Exceptions",
                [
                    {
                        "Person": "Dana Whitfield",
                        "Role A": "grp_billing_admin",
                        "Role B": "grp_prod_admin",
                        "Reason": "Billing cutover weekend",
                        "Approved by": "Security",
                        "Start": "2026-10-01",
                        "End": "2026-10-31",
                        "Status": "Approved",
                    },
                    {
                        "Person": "Rui Silva",
                        "Role A": "grp_release_approver",
                        "Role B": "grp_prod_admin",
                        "Reason": "Q3 connector migration",
                        "Approved by": "Security",
                        "Start": "2026-09-01",
                        "End": "2026-11-30",
                        "Status": "Approved",
                    },
                    {
                        "Person": "Omar Haddad",
                        "Role A": "grp_release_approver",
                        "Role B": "grp_prod_admin",
                        "Reason": "Kafka retention change; no second engineer free",
                        "Approved by": "Security",
                        "Start": "2026-12-10",
                        "End": OMAR_EXCEPTION_END,
                        "Status": "Approved",
                    },
                ],
            ),
        ],
    ),
    sheet(
        "ss_contractor_sow",
        "Contractor SOW tracker",
        [
            (
                "ws_amendments",
                "Amendments",
                [
                    {
                        "Contractor": "Leon Brandt",
                        "Amendment": "1",
                        "New end date": "2027-03-31",
                        "Status": "Signed",
                        "Entered in Rippling": "No",
                        "Updated": "2026-12-11",
                    },
                    {
                        "Contractor": "Leon Brandt",
                        "Amendment": "0",
                        "New end date": LEON_CONTRACT_END,
                        "Status": "Signed",
                        "Entered in Rippling": "Yes",
                        "Updated": "2026-10-01",
                    },
                ],
            ),
        ],
    ),
    sheet(
        "ss_q4_review",
        "Q4 privileged-access review",
        [
            (
                "ws_data_platform",
                "Data Platform",
                [
                    review_row("Lena Ostrowski", "grp_prod_admin", "Remove"),
                    review_row("Mei Tan", "grp_prod_readonly", "Keep"),
                    review_row("Tomas Ruiz", "grp_prod_readonly", ""),
                    review_row("Omar Haddad", "grp_release_approver", "Keep"),
                    review_row("Rui Silva", "grp_release_approver", "Keep"),
                    review_row("Rui Silva", "grp_prod_admin", "Remove", "2026-11-30"),
                    review_row("Sven Holm", "grp_prod_readonly", "Keep"),
                    review_row("Ines Moreau", "grp_prod_admin", "Remove", "2026-11-30"),
                ],
            ),
            (
                "ws_payments",
                "Payments Platform",
                [
                    review_row("Ji-ho Park", "grp_release_approver", "Keep"),
                    review_row("Carla Mendes", "grp_prod_readonly", "Keep"),
                ],
            ),
        ],
    ),
]

generic_world = {
    "meta": {"schema_version": "0.1.0", "current_time": "2026-12-14T17:00:00Z"},
    "gmail": {"messages": emails},
    "google_sheets": {"spreadsheets": sheets},
}

GRANTS = {
    "ACCESS-441": ("okta_sven_holm", "grp_prod_admin", DEFAULT_END),
    "ACCESS-443": ("okta_omar_haddad", "grp_prod_admin", OMAR_EXCEPTION_END),
    "ACCESS-445": ("okta_hana_kim", "grp_analytics_readonly", DEFAULT_END),
    "ACCESS-446": ("okta_leon_brandt", "grp_prod_readonly", LEON_CONTRACT_END),
}
HOLDS = {
    "ACCESS-442": ("Blocked - approval", "ROLE_OWNER_APPROVAL_PENDING"),
    "ACCESS-444": ("Blocked - conflict", "SOD_CONFLICT"),
}
REMOVALS = {
    "okta_lena_ostrowski": "grp_prod_admin",
    "okta_tomas_ruiz": "grp_prod_readonly",
}
LABELS = {
    "ACCESS-441": "Sven: production admin with role-owner approval, 30-day default",
    "ACCESS-443": "Omar: production admin under his SoD exception, ending with it on "
    f"{OMAR_EXCEPTION_END}",
    "ACCESS-445": "Hana: analytics read-only after dataset-owner approval",
    "ACCESS-446": "Leon: production read-only capped at the contract end in Rippling, "
    f"{LEON_CONTRACT_END}, despite the unentered amendment and a timed-out "
    "first Okta call",
    "ACCESS-442": "Mei: production admin held for role-owner approval; the VP's "
    "email is not one",
    "ACCESS-444": "Rui: production admin blocked as an SoD conflict; his exception "
    "ended 2026-11-30",
    "okta_lena_ostrowski": "Lena: production admin removed (Q4 review: Remove)",
    "okta_tomas_ruiz": "Tomas: production read-only removed (Q4 review: unmarked by "
    "the deadline)",
}

assertions = []
for rid, (uid, group, exp) in GRANTS.items():
    base = family_world["identities"][uid]
    assertions.append(
        {
            "type": "backlog_identity_exact",
            "user_id": uid,
            "status": "active",
            "groups": sorted(set(base["groups"]) | {group}),
            "group_expirations": {**base["group_expirations"], group: exp},
            "message": f"{LABELS[rid]} (Okta).",
        }
    )
    assertions.append(
        {
            "type": "backlog_request_exact",
            "request_id": rid,
            "status": "Completed",
            "granted_groups": [group],
            "blocked_reason": "",
            "access_expiration": exp,
            "message": f"{LABELS[rid]} (Jira).",
        }
    )
for rid, (status, reason) in HOLDS.items():
    assertions.append(
        {
            "type": "backlog_request_exact",
            "request_id": rid,
            "status": status,
            "granted_groups": [],
            "blocked_reason": reason,
            "access_expiration": None,
            "message": f"{LABELS[rid]} (Jira).",
        }
    )
for uid, group in REMOVALS.items():
    base = family_world["identities"][uid]
    assertions.append(
        {
            "type": "backlog_identity_exact",
            "user_id": uid,
            "status": "active",
            "groups": sorted(set(base["groups"]) - {group}),
            "group_expirations": {
                g: e for g, e in base["group_expirations"].items() if g != group
            },
            "message": f"{LABELS[uid]}; other groups kept.",
        }
    )

assertions += [
    {
        "type": "backlog_training_assignments_exact",
        "initial_record_keys": sorted(family_world["training_records"]),
        "assignments": [],
        "message": "No training is assigned; everyone who needs it is current.",
    },
    {
        "type": "backlog_slack_updates_exact",
        "initial_message_ids": sorted(family_world["slack_messages"]),
        "channel": "eng-access-requests",
        "announced": [
            {
                "name": "Sven Holm",
                "all_of": [DEFAULT_END],
                "rubric": "States that Sven received production admin access.",
            },
            {
                "name": "Omar Haddad",
                "all_of": [OMAR_EXCEPTION_END],
                "rubric": "States that Omar received production admin access.",
            },
            {
                "name": "Hana Kim",
                "all_of": [DEFAULT_END],
                "rubric": "States that Hana received analytics read-only access.",
            },
            {
                "name": "Leon Brandt",
                "all_of": [LEON_CONTRACT_END],
                "rubric": "States that Leon received production read-only access.",
            },
        ],
        # People with no new access. Ines appears only as Hana's data owner.
        "silent_names": [
            "mei tan",
            "rui silva",
            "lena ostrowski",
            "tomas ruiz",
            "bruno costa",
        ],
        "message": "One #eng-access-requests update for each person who received "
        "access; none for holds or review removals.",
    },
    {
        "type": "access_sent_emails_exact",
        "category": "process",
        "tolerate_apps": ["google_sheets"],
        "emails": [
            {
                "recipients_any": [OWNERS, MARTA],
                "all_of": ["Mei"],
                "rubric": "Asks the role owners to approve production admin "
                "(grp_prod_admin) for Mei Tan.",
            },
        ],
        "message": "One approval request to the production admin role owners for Mei, "
        "and no other emails.",
    },
    {
        "type": "backlog_request_no_grant",
        "request_id": "ACCESS-447",
        "message": "Bruno's request is Daniel's to approve and grants nothing.",
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
                and uid not in REMOVALS
            },
            "access_requests": {
                rid: item
                for rid, item in family_world["access_requests"].items()
                if rid not in GRANTS and rid not in HOLDS and rid not in {"ACCESS-435"}
            },
            "training_records": family_world["training_records"],
            "slack_messages": family_world["slack_messages"],
        },
        "message": "Mei, Rui (release approver kept), Ines and other seeded identities, "
        "Daniel's request and seeded records are unchanged.",
    },
]

NL_ASSERTIONS = [
    "By the end of the conversation the assistant has told the manager each "
    "outcome: Sven and Omar got production admin (Omar's ends with his "
    "separation-of-duties exception on 2027-01-08); Hana got analytics read-only; "
    "Leon got production read-only only until his recorded contract end of "
    "2027-01-05; Mei's production admin is waiting on role-owner approval, which "
    "the assistant requested; Rui's production admin is blocked because it "
    "conflicts with his release approver role and his exception has ended; Lena's "
    "production admin and Tomas's production read-only were removed per the Q4 "
    "review. The assistant does not claim any access that was not granted.",
]
CLOSED_REQUESTS = ["ACCESS-435"]
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

task = {
    "id": "automation_workplace__interactive__access_provisioning_006",
    "family": "access_provisioning",
    "description": {
        "purpose": "Test a Data Platform queue plus outstanding Q4 review removals: "
        "role-owner approvals present, absent (and requested) or "
        "impersonated by a VP; a time-boxed SoD exception that is live "
        "for one person and lapsed for another; a signed amendment not "
        "yet in the worker record; an Okta call that times out once; and "
        "review rows marked Remove or left unmarked past the deadline.",
        "relevant_policies": "Each request is judged on its own records. Approvals, "
        "exceptions, amendments and review decisions live in the "
        "connected apps.",
        "notes": "The manager is authoritative about the work but cannot waive "
        "approvals, conflicts, contract dates or review outcomes. The one "
        "outbound email is the role-owner approval request.",
    },
    "ticket": "Work through the access requests waiting on Ken Watanabe and apply his "
    "team's outstanding Q4 privileged-access review results, using "
    "authoritative worker, identity, training, approval and access-policy "
    "records.",
    "user_scenario": {
        "persona": "You are Ken Watanabe, engineering manager for Data Platform. The "
        "holiday change freeze starts Friday and several of your engineers "
        "have production work planned for early January.",
        "instructions": {
            "domain": "automation_workplace",
            "reason_for_call": "Open by saying only: 'Can you work through the access "
            "requests waiting on me? Security also says some of my "
            "team's Q4 review removals never got applied, can you "
            "sort those out too?'",
            "known_info": "Sven, Mei, Omar and Rui all have production work in early "
            "January and need admin. Rafael (your VP) told you he "
            "approved Mei's admin. Omar and Rui are release approvers "
            "and you want both to keep approving releases. Rui had a "
            "separation-of-duties exception last quarter and you assume "
            "it still covers him. Leon's SOW extension was signed last "
            "week and runs through March 2027, so you'd like his access "
            "to run through March. Hana's request is routine. Tomas "
            "still uses production read-only for on-call shadowing; you "
            "think the review just forgot to mark him.",
            "unknown_info": "You do not know how many requests are open, anyone's "
            "training status, contract dates in Rippling, Okta groups, "
            "which approvals exist in email, the exceptions register, "
            "the review sheet contents, or the access desk's workflow.",
            "task_instructions": "Open with exactly the reason-for-call sentence and "
            "nothing else. Never list the requests, their number, "
            "or expected outcomes, and never use tools. If asked "
            "about a specific person, share only what your known "
            "info says; otherwise tell the assistant to check the "
            "company systems. If the assistant declines, narrows "
            "or caps any request, push back once: 'I approved it, "
            "why isn't that enough?' For Leon, push back once with "
            "'His extension is signed, can't you just set March?' "
            "If Tomas's access is being removed, ask once: 'Can we "
            "keep Tomas? I think he was just missed.' Accept each "
            "outcome only after a reason tied to a specific record "
            "or rule. If it suggests removing Omar's or Rui's "
            "release approver role, say no. If the assistant asks "
            "whether it may email someone or proceed, say yes. If "
            "it says it is done without saying what happened to "
            "each person, ask once for a short per-person summary, "
            "without saying how many people there are. Output "
            "###STOP### once it has given a credible per-person "
            "outcome of changes it says it has"
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

out = INTERACTIVE / "tasks/access_provisioning_006.json"
out.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
print(out, len(assertions), "assertions")
