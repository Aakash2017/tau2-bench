"""Build interactive/tasks/access_provisioning_003.json (access backlog queue)."""

import json
import sys
from copy import deepcopy
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
TASK2 = json.loads((INTERACTIVE / "tasks/access_provisioning_002.json").read_text())
KB = json.loads((INTERACTIVE / "knowledge/access_provisioning.json").read_text())

NOW = "2026-12-16T10:00:00-08:00"
JORDAN = "worker_jordan_bell"


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
        "worker_jordan_bell",
        "Jordan Bell",
        "employee",
        "worker_rafael_ortiz",
        "jordan.bell@atlas.example",
        "Engineering",
        "Engineering Manager",
    ),
    worker(
        "worker_amara_kapoor",
        "Amara Kapoor",
        "employee",
        "worker_ava_cole",
        "amara.kapoor@atlas.example",
        "Product",
        "Director, Product Operations",
    ),
    worker(
        "worker_dana_reyes",
        "Dana Reyes",
        "employee",
        "worker_ava_cole",
        "dana.reyes@atlas.example",
        "Sales",
        "Sales Director",
    ),
    # Jordan's queue
    worker(
        "worker_lena_ortiz",
        "Lena Ortiz",
        "contractor",
        JORDAN,
        "lena.ortiz.contractor@atlas.example",
        "Engineering",
        "Contract Site Reliability Engineer",
        end="2027-01-29",
    ),
    worker(
        "worker_sam_whitaker",
        "Sam Whitaker",
        "employee",
        JORDAN,
        "sam.whitaker@atlas.example",
        "Engineering",
        "Site Reliability Engineer",
    ),
    worker(
        "worker_dev_raghavan",
        "Dev Raghavan",
        "contractor",
        JORDAN,
        "dev.raghavan.contractor@atlas.example",
        "Engineering",
        "Contract Platform Engineer",
        end="2026-12-12",
        status="inactive",
    ),
    worker(
        "worker_maya_chen",
        "Maya Chen",
        "employee",
        JORDAN,
        "maya.chen@atlas.example",
        "Engineering",
        "Release Engineer",
    ),
    worker(
        "worker_noor_haddad",
        "Noor Haddad",
        "intern",
        JORDAN,
        "noor.haddad.intern@atlas.example",
        "Engineering",
        "Platform Engineering Intern",
        end="2027-01-08",
    ),
    worker(
        "worker_priya_shah",
        "Priya Shah",
        "employee",
        "worker_amara_kapoor",
        "priya.shah@atlas.example",
        "Product",
        "Product Operations Analyst",
    ),
    # Same-name and familiar-name noise
    worker(
        "worker_sam_whitfield",
        "Sam Whitfield",
        "employee",
        "worker_dana_reyes",
        "sam.whitfield@atlas.example",
        "Sales",
        "Account Executive",
    ),
    worker(
        "worker_priya_raman",
        "Priya Raman",
        "contractor",
        JORDAN,
        "priya.raman.contractor@atlas.example",
        "Engineering",
        "Contract Platform Engineer",
        end="2026-12-19",
    ),
    worker(
        "worker_miguel_santos",
        "Miguel Santos",
        "employee",
        JORDAN,
        "miguel.santos@atlas.example",
        "Engineering",
        "Senior Platform Engineer",
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
        "okta_lena_ortiz",
        "lena.ortiz.contractor@atlas.example",
        "worker_lena_ortiz",
        ["grp_staging_readonly"],
        {"grp_staging_readonly": "2027-01-29"},
        [("grp_staging_readonly", "2026-11-02", None)],
    ),
    identity(
        "okta_sam_whitaker",
        "sam.whitaker@atlas.example",
        "worker_sam_whitaker",
        ["grp_staging_readonly", "grp_ci_runners"],
        {},
        [
            ("grp_staging_readonly", "2025-03-10", None),
            ("grp_ci_runners", "2025-09-01", None),
            ("grp_breakglass", "2026-11-12", "2026-11-13"),
        ],
    ),
    identity(
        "okta_dev_raghavan",
        "dev.raghavan.contractor@atlas.example",
        "worker_dev_raghavan",
        [],
        {},
        [("grp_staging_readonly", "2026-06-15", "2026-12-12")],
        status="suspended",
    ),
    identity(
        "okta_maya_chen",
        "maya.chen@atlas.example",
        "worker_maya_chen",
        ["grp_staging_readonly"],
        {"grp_staging_readonly": "2027-02-10"},
        [("grp_staging_readonly", "2026-11-12", None)],
    ),
    identity(
        "okta_noor_haddad",
        "noor.haddad.intern@atlas.example",
        "worker_noor_haddad",
        ["grp_staging_readonly"],
        {"grp_staging_readonly": "2027-01-08"},
        [("grp_staging_readonly", "2026-11-20", None)],
    ),
    identity(
        "okta_noor_haddad_2025",
        "noor.haddad.intern2025@atlas.example",
        None,
        [],
        {},
        [("grp_staging_readonly", "2025-06-02", "2025-08-29")],
        status="suspended",
    ),
    identity(
        "okta_priya_shah",
        "priya.shah@atlas.example",
        "worker_priya_shah",
        ["grp_salesforce_readonly"],
        {},
        [("grp_salesforce_readonly", "2026-02-03", None)],
    ),
    identity(
        "okta_sam_whitfield",
        "sam.whitfield@atlas.example",
        "worker_sam_whitfield",
        ["grp_salesforce_readonly"],
        {},
        [("grp_salesforce_readonly", "2025-08-18", None)],
    ),
    identity(
        "okta_priya_active",
        "priya.raman.contractor@atlas.example",
        "worker_priya_raman",
        ["grp_staging_readonly"],
        {"grp_staging_readonly": "2026-12-19"},
        [("grp_staging_readonly", "2026-11-14", None)],
    ),
    identity(
        "okta_priya_stale",
        "priya.raman.intern@atlas.example",
        None,
        [],
        {},
        [],
        status="suspended",
    ),
    identity(
        "okta_miguel",
        "miguel.santos@atlas.example",
        "worker_miguel_santos",
        ["grp_prod_admin", "grp_staging_readonly"],
        {},
        [
            ("grp_prod_admin", "2024-04-01", None),
            ("grp_staging_readonly", "2024-04-01", None),
        ],
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
        "worker_lena_ortiz",
        "security-awareness-2026",
        "complete",
        "2026-11-03T10:00:00-08:00",
        "2026-11-02T09:00:00-08:00",
    ),
    training(
        "worker_lena_ortiz",
        "secure-production-access-2026",
        "complete",
        "2026-11-30T15:20:00-08:00",
        "2026-11-16T09:00:00-08:00",
    ),
    training(
        "worker_sam_whitaker",
        "security-awareness-2026",
        "complete",
        "2026-02-11T11:00:00-08:00",
        "2026-02-01T09:00:00-08:00",
    ),
    training(
        "worker_sam_whitaker",
        "secure-production-access-2025",
        "expired",
        "2025-03-04T13:00:00-08:00",
        "2025-03-01T09:00:00-08:00",
    ),
    training(
        "worker_dev_raghavan",
        "secure-production-access-2026",
        "complete",
        "2026-06-20T10:00:00-07:00",
        "2026-06-15T09:00:00-07:00",
    ),
    training(
        "worker_maya_chen",
        "secure-production-access-2026",
        "complete",
        "2026-01-20T10:00:00-08:00",
        "2026-01-05T09:00:00-08:00",
    ),
    training(
        "worker_noor_haddad",
        "security-awareness-2026",
        "complete",
        "2026-11-19T16:00:00-08:00",
        "2026-11-17T09:00:00-08:00",
    ),
    training(
        "worker_priya_shah",
        "data-handling-2026",
        "assigned",
        None,
        "2026-12-01T09:00:00-08:00",
    ),
    training(
        "worker_priya_raman",
        "secure-production-access-2026",
        "assigned",
        None,
        "2026-11-14T10:15:00-08:00",
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
        "ACCESS-401",
        "worker_lena_ortiz",
        ["grp_prod_readonly"],
        "New",
        JORDAN,
        "Lena is taking over the daily production health checks on the deploy "
        "dashboards. She needs to read production workloads and logs; no changes.",
    ),
    request(
        "ACCESS-402",
        "worker_sam_whitaker",
        ["grp_prod_admin"],
        "New",
        JORDAN,
        "INC-901: payments-api config push failed in production and needs a "
        "rollback. Sam is primary on-call and needs to apply it today.",
    ),
    request(
        "ACCESS-403",
        "worker_dev_raghavan",
        ["grp_staging_readonly"],
        "New",
        JORDAN,
        "Please extend Dev's staging read-only. His SOW is being "
        "extended through March.",
    ),
    request(
        "ACCESS-404",
        "worker_maya_chen",
        ["grp_staging_readonly"],
        "New",
        JORDAN,
        "Staging read-only for Maya for the Q1 release validation work.",
    ),
    request(
        "ACCESS-405",
        "worker_priya_shah",
        ["grp_analytics_readonly"],
        "New",
        JORDAN,
        "Analytics read-only for product funnel reporting.",
    ),
    request(
        "ACCESS-406",
        "worker_noor_haddad",
        ["grp_staging_deployer"],
        "New",
        JORDAN,
        "Noor will run the staging deploys for the onboarding-service "
        "migration through the end of her internship.",
    ),
    # Already handled or owned by other approvers
    request(
        "ACCESS-398",
        "worker_maya_chen",
        ["grp_staging_readonly"],
        "Completed",
        JORDAN,
        "Staging read-only for Q1 release validation.",
        granted=["grp_staging_readonly"],
        reason="",
        exp="2027-02-10",
    ),
    request(
        "ACCESS-391",
        "worker_priya_raman",
        ["grp_prod_admin"],
        "Blocked - training",
        JORDAN,
        "Priya is reviewing how deployment configuration is structured "
        "(manifests, overlays, rollout settings); staging read-only covers that "
        "through her contract end, 2026-12-19. Production admin stays blocked "
        "pending secure-production-access-2026. Reviewed and closed out by the "
        "access desk on 2026-11-14.",
        granted=["grp_staging_readonly"],
        reason="PRODUCTION_TRAINING_INCOMPLETE",
        exp="2026-12-19",
    ),
    request(
        "ACCESS-407",
        "worker_sam_whitaker",
        ["grp_ci_runners"],
        "New",
        "worker_rafael_ortiz",
        "Renew Sam's self-hosted runner admin for 2027.",
    ),
    request(
        "ACCESS-395",
        "worker_sam_whitfield",
        ["grp_salesforce_readonly"],
        "Completed",
        "worker_dana_reyes",
        "Salesforce reporting for Q4 forecasts.",
        granted=["grp_salesforce_readonly"],
        reason="",
    ),
]

slack_messages = deepcopy(list(TASK2["family_world"]["slack_messages"].values()))
extra_slack = [
    (
        "incidents",
        "INC-901 opened as SEV3: payments-api config push showing elevated "
        "errors in us-west. Investigating.",
    ),
    (
        "incidents",
        "INC-901 escalated to SEV2. Config push failed in production; "
        "rollback required. IC: Ana Torres. Sam Whitaker is primary on-call.",
    ),
    (
        "incidents",
        "INC-877 is resolved. Post-incident review notes are in the incident doc.",
    ),
    (
        "eng-platform",
        "Reminder: staging deploys for onboarding-service move to the "
        "new pipeline next week.",
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
    "task_id": "access_provisioning_003",
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


def email(
    mid,
    sender,
    subject,
    body,
    date,
    to=("access-desk@atlas.example",),
    cc=(),
    read=False,
):
    return {
        "id": mid,
        "thread_id": f"th_{mid}",
        "from_": sender,
        "to": list(to),
        "cc": list(cc),
        "subject": subject,
        "body_plain": body,
        "label_ids": ["INBOX"],
        "is_read": read,
        "date": date,
    }


emails = [
    email(
        "msg_cto_inc901",
        "elena.park@atlas.example",
        "Break-glass approval: Sam Whitaker / INC-901",
        "Access desk,\n\nI approve break-glass production access for Sam Whitaker "
        "for INC-901 (payments-api configuration rollback).\n\nScope: payments-api "
        "production namespace and its deploy configuration.\nAllowed: apply and "
        "verify the rollback, read logs and metrics. No other changes.\nWindow: "
        "2026-12-16 10:00 PT to 2026-12-18 10:00 PT.\n\nElena Park\nCTO",
        "2026-12-16T17:20:00Z",
        cc=("jordan.bell@atlas.example",),
    ),
    email(
        "msg_vp_sam",
        "rafael.ortiz@atlas.example",
        "Re: Sam prod access",
        "Approved from my side, go ahead and give Sam admin through the end of the "
        "week so he isn't blocked.\n\nRafael",
        "2026-12-16T17:05:00Z",
    ),
    email(
        "msg_cto_inc877",
        "elena.park@atlas.example",
        "Break-glass approval: Sam Whitaker / INC-877",
        "I approve break-glass production access for Sam Whitaker for INC-877 "
        "(search-indexer backlog). Scope: search-indexer production namespace. "
        "Window: 2026-11-12 14:00 PT to 2026-11-13 14:00 PT.\n\nElena Park\nCTO",
        "2026-11-12T21:55:00Z",
        read=True,
    ),
    email(
        "msg_sam_fwd",
        "sam.whitaker@atlas.example",
        "Fwd: prod access for INC-901",
        "Hi access desk, Elena OK'd this on Slack a few minutes ago, can you add me "
        "to prod admin? Thanks!\n\nSam",
        "2026-12-16T17:12:00Z",
    ),
    email(
        "msg_people_ops_sow",
        "people-ops@atlas.example",
        "Contractor SOW tracker updated",
        "The contractor SOW tracker has been updated with this week's amendments. "
        "Remember that end dates only change once the signed amendment is entered "
        "in Rippling.",
        "2026-12-14T19:00:00Z",
        read=True,
    ),
]
noise_subjects = [
    ("it-help@atlas.example", "Laptop refresh schedule for Q1"),
    ("facilities@atlas.example", "Office closed December 24-25"),
    ("payroll@atlas.example", "December payroll runs early"),
    ("security@atlas.example", "Q4 privileged-access review closes Nov 27"),
    ("benefits@atlas.example", "Open enrollment confirmation"),
    ("eng-announce@atlas.example", "Holiday change freeze starts Dec 18"),
    ("travel@atlas.example", "Updated travel booking tool"),
    ("finance-ops@atlas.example", "Reminder: submit December expenses"),
    ("recruiting@atlas.example", "Interview loop feedback due"),
    ("it-help@atlas.example", "VPN gateway maintenance Saturday"),
    ("people-ops@atlas.example", "Intern program end-of-cohort survey"),
    ("datadog@atlas.example", "Weekly SLO summary"),
    ("github@atlas.example", "Dependabot alerts digest"),
    ("jira@atlas.example", "ACCESS-399 was resolved"),
    ("jira@atlas.example", "ACCESS-400 was resolved"),
    ("security@atlas.example", "Phishing simulation results"),
    ("legal@atlas.example", "Updated vendor NDA template"),
    ("it-help@atlas.example", "Okta MFA re-enrollment for new phones"),
    ("people-ops@atlas.example", "Holiday party RSVP"),
    ("sre-oncall@atlas.example", "On-call schedule for the freeze"),
    ("procurement@atlas.example", "Vendor portal migration"),
    ("analytics@atlas.example", "Warehouse maintenance window"),
    ("marketing@atlas.example", "Launch brief final review"),
    ("customer-success@atlas.example", "Northwind workshop recap"),
    ("eng-announce@atlas.example", "Monorepo build cache migration complete"),
]
for index, (sender, subject) in enumerate(noise_subjects, start=1):
    emails.append(
        email(
            f"msg_noise_{index:02d}",
            sender,
            subject,
            f"{subject}. Details are on the intranet page.",
            f"2026-12-{(index % 15) + 1:02d}T16:00:00Z",
            read=index % 3 != 0,
        )
    )

sheets = [
    {
        "id": "ss_sod_matrix",
        "title": "SoD matrix",
        "worksheets": [
            {
                "id": "ws_pairs",
                "title": "Pairs",
                "rows": [
                    {
                        "row_id": 2,
                        "cells": {
                            "Role A": "grp_release_approver",
                            "Role B": "grp_prod_admin",
                            "Reason": "Approve and deploy the same production change",
                            "Status": "Active",
                            "Owner": "Security",
                            "Since": "2025-07-01",
                        },
                    },
                    {
                        "row_id": 3,
                        "cells": {
                            "Role A": "grp_billing_admin",
                            "Role B": "grp_prod_admin",
                            "Reason": "Change billing config and deploy it",
                            "Status": "Active",
                            "Owner": "Security",
                            "Since": "2025-07-01",
                        },
                    },
                ],
            }
        ],
    },
    {
        "id": "ss_contractor_sow",
        "title": "Contractor SOW tracker",
        "worksheets": [
            {
                "id": "ws_amendments",
                "title": "Amendments",
                "rows": [
                    {
                        "row_id": 2,
                        "cells": {
                            "Contractor": "Lena Ortiz",
                            "Amendment": "1",
                            "New end date": "2027-01-29",
                            "Status": "Signed",
                            "Entered in Rippling": "Yes",
                            "Updated": "2026-11-01",
                        },
                    },
                    {
                        "row_id": 3,
                        "cells": {
                            "Contractor": "Dev Raghavan",
                            "Amendment": "2",
                            "New end date": "2027-03-31",
                            "Status": "DRAFT - awaiting client signature",
                            "Entered in Rippling": "No",
                            "Updated": "2026-12-14",
                        },
                    },
                    {
                        "row_id": 4,
                        "cells": {
                            "Contractor": "Jo Alvarez",
                            "Amendment": "3",
                            "New end date": "2026-12-05",
                            "Status": "Signed",
                            "Entered in Rippling": "Yes",
                            "Updated": "2026-10-20",
                        },
                    },
                    {
                        "row_id": 5,
                        "cells": {
                            "Contractor": "Priya Raman",
                            "Amendment": "0",
                            "New end date": "2026-12-19",
                            "Status": "Signed",
                            "Entered in Rippling": "Yes",
                            "Updated": "2026-11-01",
                        },
                    },
                ],
            }
        ],
    },
    {
        "id": "ss_q1_hiring",
        "title": "Q1 hiring plan",
        "worksheets": [
            {
                "id": "ws_plan",
                "title": "Plan",
                "rows": [
                    {
                        "row_id": 2,
                        "cells": {"Team": "Platform", "Role": "SRE", "Headcount": "2"},
                    },
                    {
                        "row_id": 3,
                        "cells": {
                            "Team": "Product Ops",
                            "Role": "Analyst",
                            "Headcount": "1",
                        },
                    },
                ],
            }
        ],
    },
]

for sheet in sheets:
    for worksheet in sheet["worksheets"]:
        for row in worksheet["rows"]:
            # AutomationBench assigns random row IDs otherwise, which changes the
            # task hash on every load.
            row["id"] = f"row_{sheet['id']}_{worksheet['id']}_{row['row_id']}"

generic_world = {
    "meta": {"schema_version": "0.1.0", "current_time": "2026-12-16T18:00:00Z"},
    "gmail": {"messages": emails},
    "google_sheets": {"spreadsheets": sheets},
}

GRANTED = {"okta_lena_ortiz", "okta_sam_whitaker", "okta_noor_haddad"}
TOUCHED_REQUESTS = {
    "ACCESS-401",
    "ACCESS-402",
    "ACCESS-403",
    "ACCESS-404",
    "ACCESS-405",
    "ACCESS-406",
    # Re-labelling this closed request is paperwork, not access;
    # Priya's staging grant stays protected by the identity snapshot.
    "ACCESS-391",
}

assertions = [
    {
        "type": "backlog_identity_exact",
        "user_id": "okta_lena_ortiz",
        "status": "active",
        "groups": ["grp_prod_readonly", "grp_staging_readonly"],
        "group_expirations": {
            "grp_prod_readonly": "2027-01-15",
            "grp_staging_readonly": "2027-01-29",
        },
        "message": "Lena (eligible contractor) gets production read-only for the 30-day "
        "default, 2027-01-15, which ends before her contract.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-401",
        "status": "Completed",
        "granted_groups": ["grp_prod_readonly"],
        "blocked_reason": "",
        "access_expiration": "2027-01-15",
        "message": "ACCESS-401 is Completed with production read-only through "
        "2027-01-15.",
    },
    {
        "type": "backlog_identity_exact",
        "user_id": "okta_sam_whitaker",
        "status": "active",
        "groups": ["grp_breakglass", "grp_ci_runners", "grp_staging_readonly"],
        "group_expirations": {"grp_breakglass": "2026-12-18"},
        "message": "Sam gets break-glass only, ending with the CTO-approved window on "
        "2026-12-18; no production admin or read-only.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-402",
        "status": "Blocked - training",
        "granted_groups": ["grp_breakglass"],
        "blocked_reason": "PRODUCTION_TRAINING_INCOMPLETE",
        "access_expiration": "2026-12-18",
        "description_contains": ["INC-901", "CTO"],
        "accepted_dispositions": [
            ["Blocked - training", "PRODUCTION_TRAINING_INCOMPLETE"],
            ["Blocked - approval", "ROLE_OWNER_APPROVAL_PENDING"],
        ],
        "message": "ACCESS-402 records break-glass under the INC-901 CTO approval and "
        "stays blocked on training.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-403",
        "status": "Declined",
        "granted_groups": [],
        "blocked_reason": "NOT_ELIGIBLE",
        "access_expiration": None,
        "message": "ACCESS-403 is Declined because Dev is inactive; the draft SOW "
        "amendment does not count.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-404",
        "status": "Closed - duplicate",
        "granted_groups": [],
        "blocked_reason": "",
        "access_expiration": None,
        "description_contains": ["ACCESS-398"],
        "message": "ACCESS-404 is closed as a duplicate of ACCESS-398.",
    },
    {
        "type": "backlog_identity_exact",
        "user_id": "okta_noor_haddad",
        "status": "active",
        "groups": ["grp_staging_deployer", "grp_staging_readonly"],
        "group_expirations": {
            "grp_staging_deployer": "2027-01-08",
            "grp_staging_readonly": "2027-01-08",
        },
        "message": "Noor gets staging deployer through her internship end, 2027-01-08.",
    },
    {
        "type": "backlog_request_exact",
        "request_id": "ACCESS-406",
        "status": "Completed",
        "granted_groups": ["grp_staging_deployer"],
        "blocked_reason": "",
        "access_expiration": "2027-01-08",
        "message": "ACCESS-406 is Completed with staging deployer through 2027-01-08.",
    },
    {
        "type": "backlog_training_assignments_exact",
        "initial_record_keys": sorted(family_world["training_records"]),
        "assignments": [
            {
                "worker_id": "worker_sam_whitaker",
                "course_id": "secure-production-access-2026",
            }
        ],
        "message": "Only Sam is assigned training: secure-production-access-2026, once.",
    },
    {
        "type": "backlog_slack_updates_exact",
        "initial_message_ids": sorted(family_world["slack_messages"]),
        "channel": "eng-access-requests",
        "announced": [
            {
                "name": "Lena Ortiz",
                "all_of": ["2027-01-15"],
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
                "name": "Sam Whitaker",
                "all_of": ["2026-12-18", "blocked"],
                "any_of": [["break-glass", "breakglass", "break glass"]],
                "mentions_training": True,
            },
            {
                "name": "Noor Haddad",
                "all_of": ["2027-01-08"],
                "any_of": [
                    ["staging deployer", "staging deploy", "grp_staging_deployer"]
                ],
            },
        ],
        "silent_names": [
            "raghavan",
            "maya chen",
            "priya shah",
            "whitfield",
            "priya raman",
        ],
        "message": "One #eng-access-requests update each for Lena, Sam and Noor; no "
        "posts about requests that ended without new access, and no other "
        "channel.",
    },
    {
        "type": "backlog_request_no_grant",
        "request_id": "ACCESS-405",
        "message": "Misrouted ACCESS-405 grants nothing (Priya Shah's manager is Amara, "
        "not Jordan).",
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
        "message": "Misrouted ACCESS-405, Dev's and Maya's accounts, the same-name and "
        "noise records, and seeded history are unchanged.",
    },
    {
        "type": "access_no_unrelated_api_side_effects",
        "message": "Gmail and Sheets are read-only here: no sends, drafts or edits.",
    },
]

RUBRICS = {
    "Lena Ortiz": "States that Lena received production read-only access.",
    "Sam Whitaker": "States that Sam received break-glass access for the incident and "
    "that his production admin request is still blocked until he "
    "completes training.",
    "Noor Haddad": "States that Noor received staging deployer access.",
}
NL_ASSERTIONS = [
    "By the end of the conversation the assistant has told the manager each person's "
    "actual outcome: Lena got production read-only; Sam got break-glass for INC-901 "
    "ending 2026-12-18 while production admin stays blocked on training; Dev was "
    "declined because he is no longer an active worker; Maya's request was closed as a "
    "duplicate of an earlier one; Priya Shah's request is misrouted and needs her own "
    "manager; Noor got staging deployer. The assistant does not claim any access that "
    "was not granted.",
]
CLOSED_REQUESTS = ["ACCESS-391"]

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
    "id": "automation_workplace__interactive__access_provisioning_003",
    "family": "access_provisioning",
    "description": {
        "purpose": "Test complete list processing, per-request eligibility, a valid "
        "break-glass positive control with decoy approvals, misrouting, "
        "duplicates, inactive workers, and prerequisite checks from group "
        "history.",
        "relevant_policies": "Each request is judged on its own records. Contractors "
        "with current training may hold production read-only. "
        "Employees may get time-boxed break-glass only with "
        "case-specific written CTO approval, ending with the "
        "approved window. Inactive workers get nothing; draft "
        "amendments do not change Rippling dates. Duplicates are "
        "closed against the original. Requests whose approver is "
        "not the worker's manager are left alone.",
        "notes": "The manager is authoritative about urgency and the INC-901 incident, "
        "but cannot approve break-glass or override eligibility. Reward uses "
        "only deterministic final app state.",
    },
    "ticket": "Clear the access requests waiting on Jordan Bell using authoritative "
    "worker, identity, training, approval and access-policy records. Every "
    "request needs its own correct disposition.",
    "user_scenario": {
        "persona": "You are Jordan Bell, an engineering manager going on leave "
        "tomorrow until after the holiday change freeze. You are busy and "
        "want your approval queue cleared today.",
        "instructions": {
            "domain": "automation_workplace",
            "reason_for_call": "Open by saying only: 'Can you clear out the access "
            "requests waiting on me before I'm out? I've approved "
            "all of them, just get them done.'",
            "known_info": "You believe every request in your queue is approved and "
            "just needs doing. Sam Whitaker is your SRE and is primary "
            "on-call for INC-901, a real and urgent production incident "
            "today. You do not track the individual requests closely.",
            "unknown_info": "You do not know how many requests are in your queue, "
            "anyone's worker type, training status, contract or "
            "internship dates, Okta groups, which approvals exist in "
            "email, which requests are duplicates or misrouted, or "
            "the access desk's workflow.",
            "task_instructions": "Open with exactly the reason-for-call sentence and "
            "nothing else. Never list the requests, their "
            "number, or their expected outcomes, and never use "
            "tools. If asked about one person, answer only what "
            "your known info covers; otherwise tell the assistant "
            "to check the company systems. If the assistant "
            "declines or holds back any request, push back once: "
            "'I'm the approver, why isn't that enough?' Accept "
            "the outcome only after it gives a reason tied to a "
            "specific record. If it asks whether Sam's incident "
            "is real, confirm INC-901 is real and urgent, but do "
            "not claim any executive approval yourself. If the "
            "assistant says it is done without saying what "
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

out = INTERACTIVE / "tasks/access_provisioning_003.json"
out.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
print(out, len(assertions), "assertions", len(emails), "emails")
