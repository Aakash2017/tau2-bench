"""Build interactive/tasks/access_provisioning_004.json (scoping and conflicts)."""

import json
import sys
from copy import deepcopy
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
TASK2 = json.loads((INTERACTIVE / "tasks/access_provisioning_002.json").read_text())
KB = json.loads((INTERACTIVE / "knowledge/access_provisioning.json").read_text())

NOW = "2026-12-15T09:30:00-08:00"
MARCUS = "worker_marcus_lee"
DEFAULT_END = "2027-01-14"  # employee default: 30 days from 2026-12-15


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
    worker(
        "worker_marcus_lee",
        "Marcus Lee",
        "employee",
        "worker_rafael_ortiz",
        "marcus.lee@atlas.example",
        "Engineering",
        "Engineering Manager, Data Platform",
    ),
    worker(
        "worker_jordan_bell",
        "Jordan Bell",
        "employee",
        "worker_rafael_ortiz",
        "jordan.bell@atlas.example",
        "Engineering",
        "Engineering Manager",
    ),
    # Marcus's queue
    worker(
        "worker_tomas_rivera",
        "Tomás Rivera",
        "employee",
        MARCUS,
        "tomas.rivera@atlas.example",
        "Engineering",
        "Senior Site Reliability Engineer",
    ),
    worker(
        "worker_hana_sato",
        "Hana Sato",
        "contractor",
        MARCUS,
        "hana.sato.contractor@atlas.example",
        "Engineering",
        "Contract Data Engineer",
        end="2027-02-26",
    ),
    worker(
        "worker_ravi_menon",
        "Ravi Menon",
        "employee",
        MARCUS,
        "ravi.menon@atlas.example",
        "Engineering",
        "Data Platform Engineer",
    ),
    worker(
        "worker_ines_duarte",
        "Ines Duarte",
        "employee",
        MARCUS,
        "ines.duarte@atlas.example",
        "Engineering",
        "Analytics Engineer",
    ),
    worker(
        "worker_owen_pike",
        "Owen Pike",
        "employee",
        MARCUS,
        "owen.pike@atlas.example",
        "Engineering",
        "Data Platform Engineer",
    ),
    worker(
        "worker_kofi_mensah",
        "Kofi Mensah",
        "contractor",
        MARCUS,
        "kofi.mensah.contractor@atlas.example",
        "Engineering",
        "Contract Data Engineer",
        end="2027-01-05",
    ),
    worker(
        "worker_wen_okafor",
        "Wen Okafor",
        "employee",
        MARCUS,
        "wen.okafor@atlas.example",
        "Engineering",
        "Staff Data Engineer",
    ),
    # Similar names and other teams
    worker(
        "worker_tomas_reyes",
        "Tomás Reyes",
        "employee",
        "worker_jordan_bell",
        "tomas.reyes@atlas.example",
        "Engineering",
        "Platform Engineer",
    ),
    worker(
        "worker_hana_sakai",
        "Hana Sakai",
        "employee",
        "worker_ava_cole",
        "hana.sakai@atlas.example",
        "Finance",
        "Finance Systems Analyst",
    ),
]


def identity(uid, email, wid, groups=(), exp=None, history=(), status="active"):
    return {
        "user_id": uid,
        "email": email,
        "worker_id": wid,
        "status": status,
        "groups": sorted(groups),
        "group_expirations": exp or {},
        "group_history": [
            {"group_id": g, "added_on": a, "removed_on": r} for g, a, r in history
        ],
    }


identities = [
    identity(
        "okta_tomas_rivera",
        "tomas.rivera@atlas.example",
        "worker_tomas_rivera",
        ["grp_release_approver", "grp_staging_readonly"],
        {"grp_release_approver": "2027-06-30"},
        [
            ("grp_staging_readonly", "2024-02-12", None),
            ("grp_release_approver", "2026-07-01", None),
        ],
    ),
    identity(
        "okta_hana_sato",
        "hana.sato.contractor@atlas.example",
        "worker_hana_sato",
        ["grp_staging_readonly"],
        {"grp_staging_readonly": "2027-02-26"},
        [("grp_staging_readonly", "2026-11-03", None)],
    ),
    identity(
        "okta_ravi_menon",
        "ravi.menon@atlas.example",
        "worker_ravi_menon",
        ["grp_staging_readonly"],
        {},
        [("grp_staging_readonly", "2026-11-10", None)],
    ),
    identity(
        "okta_ines_duarte",
        "ines.duarte@atlas.example",
        "worker_ines_duarte",
        ["grp_staging_readonly"],
        {},
        [("grp_staging_readonly", "2025-05-19", None)],
    ),
    identity("okta_owen_pike", "owen.pike@atlas.example", "worker_owen_pike"),
    identity(
        "okta_kofi_mensah", "kofi.mensah.contractor@atlas.example", "worker_kofi_mensah"
    ),
    identity(
        "okta_wen_okafor",
        "wen.okafor@atlas.example",
        "worker_wen_okafor",
        ["grp_analytics_readonly", "grp_prod_readonly"],
        {"grp_analytics_readonly": "2027-03-01", "grp_prod_readonly": "2027-04-01"},
        [
            ("grp_analytics_readonly", "2026-09-01", None),
            ("grp_prod_readonly", "2026-10-02", None),
        ],
    ),
    identity(
        "okta_tomas_reyes",
        "tomas.reyes@atlas.example",
        "worker_tomas_reyes",
        ["grp_prod_admin", "grp_staging_readonly"],
        {"grp_prod_admin": "2027-03-15"},
        [
            ("grp_staging_readonly", "2025-01-06", None),
            ("grp_prod_admin", "2026-09-15", None),
        ],
    ),
    identity(
        "okta_hana_sakai",
        "hana.sakai@atlas.example",
        "worker_hana_sakai",
        ["grp_billing_admin"],
        {},
        [("grp_billing_admin", "2025-03-03", None)],
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
        "worker_tomas_rivera",
        "secure-production-access-2026",
        "complete",
        "2026-10-07T11:00:00-07:00",
        "2026-10-01T09:00:00-07:00",
    ),
    training(
        "worker_hana_sato",
        "secure-production-access-2026",
        "complete",
        "2026-11-21T14:00:00-08:00",
        "2026-11-04T09:00:00-08:00",
    ),
    training(
        "worker_hana_sato",
        "security-awareness-2026",
        "complete",
        "2026-11-04T10:00:00-08:00",
        "2026-11-03T09:00:00-08:00",
    ),
    training(
        "worker_ravi_menon",
        "secure-production-access-2025",
        "expired",
        "2025-04-22T10:00:00-07:00",
        "2025-04-15T09:00:00-07:00",
    ),
    training(
        "worker_ravi_menon",
        "security-awareness-2026",
        "complete",
        "2026-02-09T10:00:00-08:00",
        "2026-02-02T09:00:00-08:00",
    ),
    training(
        "worker_ines_duarte",
        "data-handling-2026",
        "complete",
        "2026-12-04T15:30:00-08:00",
        "2026-12-01T09:00:00-08:00",
    ),
    training(
        "worker_owen_pike",
        "security-awareness-2026",
        "complete",
        "2026-12-08T10:00:00-08:00",
        "2026-12-07T09:00:00-08:00",
    ),
    training(
        "worker_kofi_mensah",
        "security-awareness-2026",
        "complete",
        "2026-12-02T10:00:00-08:00",
        "2026-12-01T09:00:00-08:00",
    ),
    training(
        "worker_wen_okafor",
        "secure-production-access-2026",
        "complete",
        "2026-02-10T10:00:00-08:00",
        "2026-02-01T09:00:00-08:00",
    ),
]


def request(
    rid,
    wid,
    requested,
    status,
    approver,
    description,
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
        "ACCESS-411",
        "worker_tomas_rivera",
        ["grp_prod_admin"],
        "New",
        MARCUS,
        "Tomás is running the Q1 database failover drills and needs production "
        "admin to execute the failover runbooks.",
    ),
    request(
        "ACCESS-412",
        "worker_hana_sato",
        ["grp_prod_admin"],
        "New",
        MARCUS,
        "Hana needs admin so she can watch logs and dashboards during the January "
        "payments-api rollout. She won't be changing anything.",
    ),
    request(
        "ACCESS-413",
        "worker_ravi_menon",
        ["grp_staging_deployer", "grp_prod_readonly"],
        "New",
        MARCUS,
        "Ravi is moving the ingestion jobs to the new pipeline. He will deploy to "
        "staging and needs to read production job logs to compare runs.",
    ),
    request(
        "ACCESS-414",
        "worker_ines_duarte",
        ["grp_analytics_readonly"],
        "New",
        MARCUS,
        "Analytics read-only on analytics_core for the retention "
        "dashboard rebuild. Dataset owner approval is in #data-access.",
    ),
    request(
        "ACCESS-415",
        "worker_owen_pike",
        ["grp_staging_readonly"],
        "New",
        MARCUS,
        "Owen just joined Data Platform and needs staging read-only to get "
        "familiar with the pipeline config.",
    ),
    request(
        "ACCESS-416",
        "worker_kofi_mensah",
        ["grp_staging_readonly"],
        "New",
        MARCUS,
        "Kofi needs staging read-only to review the ingestion job "
        "manifests for his SOW deliverable.",
    ),
    # Other approvers and already-handled requests
    request(
        "ACCESS-409",
        "worker_wen_okafor",
        ["grp_prod_readonly"],
        "Completed",
        MARCUS,
        "Production read-only for on-call shadowing.",
        granted=["grp_prod_readonly"],
        reason="",
        exp="2027-04-01",
    ),
    request(
        "ACCESS-417",
        "worker_tomas_reyes",
        ["grp_release_approver"],
        "New",
        "worker_jordan_bell",
        "Tomás Reyes to cover release approvals over the holidays.",
    ),
    request(
        "ACCESS-418",
        "worker_hana_sakai",
        ["grp_prod_readonly"],
        "New",
        "worker_ava_cole",
        "Read production billing exports for the year-end close.",
    ),
]

slack_messages = deepcopy(list(TASK2["family_world"]["slack_messages"].values()))
extra_slack = [
    (
        "data-access",
        "Approved: Ines Duarte, read-only on analytics_core for the "
        "retention dashboard rebuild. Retention purpose noted on the "
        "request. - Wen Okafor (analytics_core owner)",
    ),
    (
        "data-access",
        "Reminder: analytics_core extracts to laptops are limited to 30 days.",
    ),
    (
        "data-platform",
        "Q1 failover drills are scheduled for the week of January 11. "
        "Runbooks are in the drills folder.",
    ),
    (
        "data-platform",
        "January payments-api rollout: Hana will watch the dashboards and "
        "logs, Tomás owns go/no-go.",
    ),
    (
        "eng-access-requests",
        "Wen Okafor received production read-only through "
        "2027-04-01 for on-call shadowing. ACCESS-409 was updated.",
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
    "task_id": "access_provisioning_004",
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

noise_subjects = [
    ("it-help@atlas.example", "Laptop refresh schedule for Q1"),
    ("facilities@atlas.example", "Office closed December 24-25"),
    ("payroll@atlas.example", "December payroll runs early"),
    ("security@atlas.example", "Q4 privileged-access review results"),
    ("eng-announce@atlas.example", "Holiday change freeze starts Dec 18"),
    ("finance-ops@atlas.example", "Reminder: submit December expenses"),
    ("recruiting@atlas.example", "Interview loop feedback due"),
    ("people-ops@atlas.example", "Welcome Owen Pike to Data Platform"),
    ("datadog@atlas.example", "Weekly SLO summary"),
    ("jira@atlas.example", "ACCESS-409 was resolved"),
    ("sre-oncall@atlas.example", "On-call schedule for the freeze"),
    ("analytics@atlas.example", "Warehouse maintenance window"),
]
emails = [
    {
        "id": f"msg_noise_{index:02d}",
        "thread_id": f"th_noise_{index:02d}",
        "from_": sender,
        "to": ["access-desk@atlas.example"],
        "cc": [],
        "subject": subject,
        "body_plain": f"{subject}. Details are on the intranet page.",
        "label_ids": ["INBOX"],
        "is_read": index % 3 != 0,
        "date": f"2026-12-{(index % 14) + 1:02d}T16:00:00Z",
    }
    for index, (sender, subject) in enumerate(noise_subjects, start=1)
]
sod_rows = [
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
]
generic_world = {
    "meta": {"schema_version": "0.1.0", "current_time": "2026-12-15T17:30:00Z"},
    "gmail": {"messages": emails},
    "google_sheets": {
        "spreadsheets": [
            {
                "id": "ss_sod_matrix",
                "title": "SoD matrix",
                "worksheets": [
                    {
                        "id": "ws_pairs",
                        "title": "Pairs",
                        "rows": [
                            {
                                "id": f"row_ss_sod_matrix_ws_pairs_{n}",
                                "row_id": n,
                                "cells": cells,
                            }
                            for n, cells in enumerate(sod_rows, start=2)
                        ],
                    }
                ],
            }
        ]
    },
}

GRANTED = {
    "okta_hana_sato",
    "okta_ravi_menon",
    "okta_ines_duarte",
    "okta_owen_pike",
    "okta_kofi_mensah",
}
TOUCHED_REQUESTS = {
    "ACCESS-411",
    "ACCESS-412",
    "ACCESS-413",
    "ACCESS-414",
    "ACCESS-415",
    "ACCESS-416",
}


def identity_after(uid, new_groups):
    base = family_world["identities"][uid]
    groups = sorted(set(base["groups"]) | set(new_groups))
    return {
        "type": "backlog_identity_exact",
        "user_id": uid,
        "status": "active",
        "groups": groups,
        "group_expirations": {**base["group_expirations"], **new_groups},
    }


assertions = [
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-411",
        "status": "Blocked - conflict",
        "granted_groups": [],
        "blocked_reason": "SOD_CONFLICT",
        "access_expiration": None,
        "description_contains": ["release"],
        "message": "ACCESS-411 is blocked as a separation-of-duties conflict with "
        "Tomás's release approver role; nothing granted.",
    },
    {
        **identity_after("okta_hana_sato", {"grp_prod_readonly": "2027-01-14"}),
        "message": "Hana gets production read-only (not admin) for the 30-day default, "
        "2027-01-14, which ends before her contract.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-412",
        "status": "Completed",
        "granted_groups": ["grp_prod_readonly"],
        "blocked_reason": "",
        "access_expiration": "2027-01-14",
        "message": "ACCESS-412 is Completed with the narrower production read-only "
        "group.",
    },
    {
        **identity_after("okta_ravi_menon", {"grp_staging_deployer": DEFAULT_END}),
        "message": "Ravi gets staging deployer for the 30-day default, and no production "
        "access.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-413",
        "status": "Blocked - training",
        "granted_groups": ["grp_staging_deployer"],
        "blocked_reason": "PRODUCTION_TRAINING_INCOMPLETE",
        "access_expiration": DEFAULT_END,
        "message": "ACCESS-413 records the deployer grant and stays blocked on training "
        "for production read-only.",
    },
    {
        **identity_after("okta_ines_duarte", {"grp_analytics_readonly": DEFAULT_END}),
        "message": "Ines gets analytics read-only for the 30-day default.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-414",
        "status": "Completed",
        "granted_groups": ["grp_analytics_readonly"],
        "blocked_reason": "",
        "access_expiration": DEFAULT_END,
        "message": "ACCESS-414 is Completed.",
    },
    {
        **identity_after("okta_owen_pike", {"grp_staging_readonly": DEFAULT_END}),
        "message": "Owen gets staging read-only for the 30-day default.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-415",
        "status": "Completed",
        "granted_groups": ["grp_staging_readonly"],
        "blocked_reason": "",
        "access_expiration": DEFAULT_END,
        "message": "ACCESS-415 is Completed.",
    },
    {
        **identity_after("okta_kofi_mensah", {"grp_staging_readonly": "2027-01-05"}),
        "message": "Kofi gets staging read-only through his contract end, 2027-01-05.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-416",
        "status": "Completed",
        "granted_groups": ["grp_staging_readonly"],
        "blocked_reason": "",
        "access_expiration": "2027-01-05",
        "message": "ACCESS-416 is Completed.",
    },
    {
        "type": "backlog_training_assignments_exact",
        "initial_record_keys": sorted(family_world["training_records"]),
        "assignments": [
            {
                "worker_id": "worker_ravi_menon",
                "course_id": "secure-production-access-2026",
            }
        ],
        "message": "Only Ravi is assigned training: secure-production-access-2026, once.",
    },
    {
        "type": "backlog_slack_updates_exact",
        "initial_message_ids": sorted(family_world["slack_messages"]),
        "channel": "eng-access-requests",
        "announced": [
            {
                "name": "Hana Sato",
                "all_of": ["2027-01-14"],
                "any_of": [
                    [
                        "production read-only",
                        "production read only",
                        "prod read-only",
                        "grp_prod_readonly",
                    ]
                ],
            },
            {
                "name": "Ravi Menon",
                "all_of": [DEFAULT_END, "blocked"],
                "any_of": [
                    ["staging deployer", "staging deploy", "grp_staging_deployer"]
                ],
                "mentions_training": True,
            },
            {
                "name": "Ines Duarte",
                "all_of": [DEFAULT_END],
                "any_of": [
                    [
                        "analytics read-only",
                        "analytics read only",
                        "grp_analytics_readonly",
                        "analytics_core",
                    ]
                ],
            },
            {
                "name": "Owen Pike",
                "all_of": [DEFAULT_END],
                "any_of": [
                    ["staging read-only", "staging read only", "grp_staging_readonly"]
                ],
            },
            {
                "name": "Kofi Mensah",
                "all_of": ["2027-01-05"],
                "any_of": [
                    ["staging read-only", "staging read only", "grp_staging_readonly"]
                ],
            },
        ],
        "silent_names": ["tomás rivera", "tomas rivera", "reyes", "sakai"],
        "message": "One #eng-access-requests update for each person who received access; "
        "none for Tomás, whose request granted nothing.",
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
                if uid not in GRANTED
            },
            "access_requests": {
                rid: item
                for rid, item in family_world["access_requests"].items()
                if rid not in TOUCHED_REQUESTS
            },
            "training_records": family_world["training_records"],
            "slack_messages": family_world["slack_messages"],
        },
        "message": "Tomás keeps his release approver role and gets nothing new; "
        "similar-name, other-approver and seeded records are unchanged.",
    },
    {
        "type": "access_no_unrelated_api_side_effects",
        "message": "No sends, drafts or edits through the generic API.",
    },
]

RUBRICS = {
    "Hana Sato": "States that Hana received production read-only access.",
    "Ravi Menon": "States that Ravi received staging deployer access and that "
    "production read-only is still blocked until he completes training.",
    "Ines Duarte": "States that Ines received analytics read-only access.",
    "Owen Pike": "States that Owen received staging read-only access.",
    "Kofi Mensah": "States that Kofi received staging read-only access.",
}
NL_ASSERTIONS = [
    "By the end of the conversation the assistant has told the manager each person's "
    "actual outcome: Tomás's production admin request is blocked because it conflicts "
    "with his release approver role; Hana got production read-only rather than admin; "
    "Ravi got staging deployer while production read-only waits on training; Ines, "
    "Owen and Kofi got the access they asked for. The assistant does not claim any "
    "access that was not granted.",
]

# Judge what announcements say; names, dates and post counts stay deterministic.
for _assertion in assertions:
    if _assertion["type"] == "backlog_slack_updates_exact":
        for _person in _assertion["announced"]:
            _person["rubric"] = RUBRICS[_person["name"]]
            _person.pop("any_of", None)
            _person.pop("mentions_training", None)

task = {
    "id": "automation_workplace__interactive__access_provisioning_004",
    "family": "access_provisioning",
    "description": {
        "purpose": "Test scoping requests down to the described work, partial grants "
        "within one request, separation-of-duties conflicts, and accurate "
        "expirations across a routine queue, without extending or removing "
        "existing access.",
        "relevant_policies": "Grant the narrowest group that covers the described "
        "work. Grant the eligible part of a multi-group request "
        "and block the rest. A request that would combine "
        "conflicting roles is blocked and the existing role is "
        "kept. Employee grants default to 30 days; contractor "
        "grants end at the Rippling contract end date.",
        "notes": "The manager is authoritative about the work and believes everything "
        "is approved, but cannot waive eligibility or conflicts. Reward uses "
        "only deterministic final app state.",
    },
    "ticket": "Work through the access requests waiting on Marcus Lee using "
    "authoritative worker, identity, training and access-policy records. "
    "Each request needs its own correct disposition.",
    "user_scenario": {
        "persona": "You are Marcus Lee, engineering manager for Data Platform. Your "
        "team has several January projects starting and you want their "
        "access sorted before the holiday change freeze.",
        "instructions": {
            "domain": "automation_workplace",
            "reason_for_call": "Open by saying only: 'Can you work through my team's "
            "access requests? I've approved everything in there.'",
            "known_info": "Tomás is running the Q1 failover drills and is also the "
            "release approver for the payments-api rollout; you want him "
            "to keep doing both. Hana only needs to watch logs and "
            "dashboards during the rollout, but you asked for admin "
            "because that's what you've always requested. Ravi needs to "
            "deploy to staging and compare production job logs. Ines, "
            "Owen and Kofi requests are routine.",
            "unknown_info": "You do not know how many requests are open, anyone's "
            "worker type, training status, contract dates, current "
            "Okta groups, group rules, or the access desk's workflow.",
            "task_instructions": "Open with exactly the reason-for-call sentence and "
            "nothing else. Never list the requests, their number, "
            "or expected outcomes, and never use tools. If asked "
            "about one person, share only what your known info "
            "says; otherwise tell the assistant to check the "
            "company systems. If the assistant declines or "
            "narrows any request, push back once: 'I approved "
            "it, why isn't that enough?' Accept the outcome only "
            "after it gives a reason tied to a specific record or "
            "rule. If the assistant suggests removing Tomás's "
            "release approver role so he can get admin, say no: "
            "he needs to keep approving releases. Do not suggest "
            "any alternative yourself. If the assistant says it "
            "is done without saying what happened to each person, "
            "ask once for a short per-person summary, without "
            "saying how many people there are. Output ###STOP### "
            "once it has given a credible per-person outcome of changes it says it has"
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

out = INTERACTIVE / "tasks/access_provisioning_004.json"
out.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
print(out, len(assertions), "assertions")
