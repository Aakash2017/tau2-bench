"""Build interactive/evidence/access_provisioning.json: why each assertion is fair."""

import json
import sys
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])

TA = "kb_temporary_access_2026_09"
PS = "kb_production_access_standard_2026_10"
BG = "kb_employee_emergency_breakglass_2026_11"
RB = "kb_access_desk_runbook_2026_10"
Q = {
    "teammate": (TA, "the teammate's groups are context, not the request."),
    "least": (
        TA,
        "Grant the least-privileged group that covers the described work, "
        "which may be narrower than what was requested",
    ),
    "each": (TA, "Each requested group is decided on its own merits."),
    "serve": (
        TA,
        "A grant should enable the described work; access that doesn't "
        "serve it isn't granted.",
    ),
    "enddate": (
        TA,
        "30 days by default, extendable. Contractor and intern access also "
        "ends no later than the contract (or internship) end date, so the "
        "earlier of the two applies.",
    ),
    "contract_change": (
        TA,
        "When a contract changes, the worker record is updated "
        "first and the desk extends access after.",
    ),
    "account": (
        TA,
        "Grant to the account linked to the person's current worker record.",
    ),
    "old_account": (TA, "the old one stays suspended for audit."),
    "interim": (
        TA,
        "It is reviewed at closeout like any other grant and kept only if "
        "it meets this standard.",
    ),
    "other": (
        TA,
        "The desk doesn't change access a person holds under other requests "
        "unless someone asks for that change.",
    ),
    "elig_table": (
        PS,
        "| Contractor | Current training | Current training + role "
        "owner | Not eligible |",
    ),
    "training": (
        PS,
        "Holding a production role requires a current "
        "secure-production-access completion.",
    ),
    "approvals": (PS, "Approvals confirm need; they don't change eligibility."),
    "sod": (PS, "A request that would create an active pair is blocked as a conflict."),
    "bg_who": (
        BG,
        "Active employees, including those without current "
        "secure-production-access training, with written CTO approval.",
    ),
    "bg_inelig": (
        BG,
        "Contractors, vendors, interns and former workers are ineligible.",
    ),
    "bg_approval": (BG, "The CTO approves in writing for this incident"),
    "bg_grant": (
        BG,
        "adds the employee to grp_breakglass, expiring at the end of the "
        "approved window (72 hours at most), and records the approval on "
        "the access request.",
    ),
    "bg_standing": (
        BG,
        "Break-glass is temporary and does not fulfil a standing access "
        "request; that request stays open with whatever still blocks "
        "it.",
    ),
    "rb_manager": (
        RB,
        "The request is approved by the person's manager. Requests "
        "approved by someone else go back to the requester to "
        "reroute.",
    ),
    "rb_dup": (RB, "There is one open request per ask"),
    "rb_training": (RB, "Missing or expired training is assigned once"),
    "rb_granted": (
        RB,
        "| granted_groups | Groups added under this request that remain "
        "active at closeout |",
    ),
    "rb_exp": (
        RB,
        "| access_expiration | Expiry of the granted groups; null when none |",
    ),
    "st_training": (
        RB,
        "| Blocked - training | Requested access is still wanted but "
        "pending training |",
    ),
    "st_conflict": (RB, "| Blocked - conflict |"),
    "st_completed": (
        RB,
        "| Completed | Nothing on the request is still pending; a "
        "narrower role in the same environment may stand in for what "
        "was asked |",
    ),
    "st_declined": (RB, "| Declined | Not eligible, with no path to eligibility |"),
    "st_dup": (
        RB,
        "| Closed - duplicate | Superseded by an existing request (cite it) |",
    ),
    "rc_training": (RB, "| PRODUCTION_TRAINING_INCOMPLETE |"),
    "rc_sod": (RB, "| SOD_CONFLICT |"),
    "rc_notelig": (
        RB,
        "| NOT_ELIGIBLE | Worker cannot hold the role (worker type or "
        "inactive status) |",
    ),
    "announce": (
        RB,
        "Requests that result in new access get one update in the access "
        "requests channel",
    ),
    "no_access": (
        RB,
        "Outcomes with no new access are recorded on the request and "
        "reported back to the requester.",
    ),
    "jira_notify": (
        "tech_jira_access_requests_v1",
        "Every update emails the requester and the person the request is for",
    ),
    "lms_email": (
        "tech_lms_training_v1",
        "sends the learner the standard assignment email",
    ),
    "course": ("tech_lms_training_v1", "| secure-production-access-2026 |"),
    "staging_opens": (
        "tech_okta_engineering_groups_2026_10",
        "| grp_staging_readonly | Staging | Staging Argo apps, k8s "
        "namespaces, deploy manifests and config, logs (read-only) |",
    ),
    "deployer_prereq": (
        "tech_okta_engineering_groups_2026_10",
        "| grp_staging_deployer | Staging | Deploy and roll back in "
        "staging | Same as above | Staging readonly for 2 weeks |",
    ),
    "analytics_prereq": (
        "tech_okta_engineering_groups_2026_10",
        "| grp_analytics_readonly | Warehouse | Read analytics schemas "
        "| Pseudonymized | data-handling course |",
    ),
    "owner": ("kb_database_access_2026_10", "The owner approves in the thread"),
    "history": (
        "tech_okta_groups_v1",
        "group_history (one entry per membership: group_id, added_on, removed_on)",
    ),
    "emp_admin": (
        PS,
        "| Employee | Current training | Current training + role owner |",
    ),
    "rb_owner": (
        RB,
        "Roles that need a role owner have the owner's approval in "
        "writing. If that is the only thing missing, ask the owner once "
        "and hold the request as Blocked - approval",
    ),
    "rb_owner_other": (
        RB,
        "Requests blocked for another reason aren't sent to owners "
        "until that is resolved.",
    ),
    "owners": (
        "tech_okta_engineering_groups_2026_10",
        "Owner approvals come from prod-admin-owners@atlas.example",
    ),
    "sod_exception": (
        PS,
        "The pair is allowed only while the exception runs, and "
        "access that depends on it ends when the exception does.",
    ),
    "st_approval": (
        RB,
        "| Blocked - approval | Requested access is still wanted but "
        "pending a role-owner or CTO approval |",
    ),
    "rc_owner": (RB, "| ROLE_OWNER_APPROVAL_PENDING | Role owner has not approved |"),
    "review_mark": (
        "kb_quarterly_access_review_2026_q4",
        "For each person, mark Keep or Remove.",
    ),
    "review_unmarked": (
        "kb_quarterly_access_review_2026_q4",
        "Anything not marked by November 27 is removed on November 30.",
    ),
    "review_new": (
        "kb_quarterly_access_review_2026_q4",
        "Reviews cover existing "
        "memberships only. New access goes through the access desk as "
        "usual.",
    ),
    "boundary": (
        "kb_production_data_boundary_2026_11",
        "Live customer data and live deployment configuration exist only in "
        "production services and audited production sessions.",
    ),
}

FW = "family_world"
NOW = f"{FW}.current_time"
KNOWN = "user_scenario.instructions.known_info"


def w(worker, field):
    return f"{FW}.workers.worker_{worker}.{field}"


def ident(user, field):
    return f"{FW}.identities.okta_{user}.{field}"


def req(rid, field="status"):
    return f"{FW}.access_requests.{rid}.{field}"


def slack(mid):
    return f"{FW}.slack_messages.{mid}.text"


def gmail(mid):
    return f"generic_world.gmail.messages.{mid}"


def sheet(sid):
    return f"generic_world.google_sheets.spreadsheets.{sid}"


def e(kb, records=()):
    return {"kb": [list(Q[k]) for k in kb], "records": list(records)}


SIDE = e(["jira_notify", "lms_email", "rb_owner_other"])
PRIYA = [
    e(
        [
            "teammate",
            "least",
            "staging_opens",
            "enddate",
            "account",
            "elig_table",
            "training",
        ],
        [
            w("priya_raman", "worker_type"),
            w("priya_raman", "contract_end_date"),
            ident("priya_active", "worker_id"),
            NOW,
            KNOWN,
        ],
    ),
    e(
        ["elig_table", "training", "approvals", "bg_inelig"],
        [
            w("priya_raman", "worker_type"),
            f"{FW}.training_records.worker_priya_raman:secure-production-access-2025.status",
        ],
    ),
    e(
        ["rb_training", "course", "training"],
        [
            f"{FW}.training_records.worker_priya_raman:secure-production-access-2025.status"
        ],
    ),
    e(
        ["st_training", "rc_training", "rb_granted", "rb_exp"],
        [
            req("ACCESS-391", "requested_groups"),
            "user_scenario.instructions.task_instructions",
        ],
    ),
    e(["rb_dup"], [req("ACCESS-391")]),
    e(["announce"], [slack("slack_message_001")]),
    e(["account", "old_account"], [ident("priya_stale", "status")]),
    e(["teammate", "other"], [ident("miguel", "groups")]),
    SIDE,
]
PRIYA_PROD_ONLY = [
    e(
        ["serve", "interim", "boundary"],
        [ident("priya_active", "groups"), req("ACCESS-391", "description"), KNOWN],
    ),
    PRIYA[2],
    e(
        ["st_training", "rc_training", "rb_granted", "rb_exp", "interim"],
        [req("ACCESS-391", "granted_groups"), KNOWN],
    ),
    PRIYA[4],
    e(["announce", "no_access"]),
    PRIYA[6],
    PRIYA[7],
    SIDE,
    e(["other"]),
]
BACKLOG = [
    e(
        ["elig_table", "training", "enddate"],
        [
            w("lena_ortiz", "worker_type"),
            w("lena_ortiz", "contract_end_date"),
            NOW,
            f"{FW}.training_records.worker_lena_ortiz:secure-production-access-2026.status",
        ],
    ),
    e(["st_completed", "rb_exp"], [req("ACCESS-401", "requested_groups")]),
    e(
        ["bg_who", "bg_approval", "bg_grant"],
        [gmail("msg_cto_inc901"), w("sam_whitaker", "worker_type")],
    ),
    e(
        ["bg_standing", "st_training", "rc_training", "bg_grant"],
        [
            req("ACCESS-402", "requested_groups"),
            f"{FW}.training_records.worker_sam_whitaker:secure-production-access-2025.status",
        ],
    ),
    e(
        ["st_declined", "rc_notelig", "contract_change"],
        [w("dev_raghavan", "status"), sheet("ss_contractor_sow")],
    ),
    e(["st_dup", "rb_granted", "rb_exp"], [req("ACCESS-398")]),
    e(
        ["deployer_prereq", "history", "enddate"],
        [
            ident("noor_haddad", "group_history"),
            w("noor_haddad", "contract_end_date"),
            NOW,
        ],
    ),
    e(["st_completed", "rb_exp"], [req("ACCESS-406", "requested_groups")]),
    e(
        ["rb_training", "course"],
        [
            f"{FW}.training_records.worker_sam_whitaker:secure-production-access-2025.status"
        ],
    ),
    e(["announce", "no_access"], [slack("slack_message_001")]),
    e(
        ["rb_manager"],
        [w("priya_shah", "manager_id"), req("ACCESS-405", "approver_id")],
    ),
    e(["rb_dup"]),
    e(["other", "account", "old_account"], [ident("noor_haddad_2025", "status")]),
    SIDE,
    e(["other", "st_training"], [req("ACCESS-391")]),
]
SCOPING = [
    e(
        ["sod", "st_conflict", "rc_sod", "other"],
        [ident("tomas_rivera", "groups"), sheet("ss_sod_matrix")],
    ),
    e(
        ["least", "elig_table", "enddate"],
        [req("ACCESS-412", "description"), w("hana_sato", "contract_end_date"), NOW],
    ),
    e(["st_completed", "least"], [req("ACCESS-412", "requested_groups")]),
    e(
        ["each", "deployer_prereq", "history", "enddate", "training"],
        [
            ident("ravi_menon", "group_history"),
            f"{FW}.training_records.worker_ravi_menon:secure-production-access-2025.status",
        ],
    ),
    e(["st_training", "rc_training", "each"], [req("ACCESS-413", "requested_groups")]),
    e(
        ["analytics_prereq", "owner", "enddate"],
        [
            slack("slack_message_031"),
            f"{FW}.training_records.worker_ines_duarte:data-handling-2026.status",
        ],
    ),
    e(["st_completed"]),
    e(["staging_opens", "enddate"], [NOW]),
    e(["st_completed"]),
    e(["enddate"], [w("kofi_mensah", "contract_end_date")]),
    e(["st_completed"]),
    e(["rb_training", "course"]),
    e(["announce", "no_access"]),
    e(["rb_dup"]),
    e(["other", "sod"]),
    SIDE,
]
QUEUE = [
    e(["staging_opens", "enddate"], [NOW]),
    e(["st_completed"]),
    e(["enddate"], [w("mira_novak", "contract_end_date")]),
    e(["st_completed"]),
    e(
        ["analytics_prereq", "owner"],
        [
            slack("slack_message_034"),
            f"{FW}.training_records.worker_aditi_rao:data-handling-2026.status",
        ],
    ),
    e(["st_completed"]),
    e(
        ["least", "elig_table", "enddate"],
        [slack("slack_message_032"), w("carla_mendes", "contract_end_date")],
    ),
    e(["st_completed", "least"]),
    e(
        ["each", "deployer_prereq", "history", "enddate"],
        [ident("bruno_costa", "group_history")],
    ),
    e(["st_training", "rc_training", "each"]),
    e(["bg_who", "bg_approval", "bg_grant"], [gmail("msg_cto_inc912")]),
    e(["bg_standing", "st_training", "rc_training"]),
    e(
        ["deployer_prereq", "history", "enddate"],
        [ident("sofia_lind", "group_history"), w("sofia_lind", "contract_end_date")],
    ),
    e(["st_completed"]),
    e(
        ["elig_table", "training", "enddate"],
        [
            w("pavel_ivanov", "contract_end_date"),
            f"{FW}.training_records.worker_pavel_ivanov:secure-production-access-2026.status",
        ],
    ),
    e(["st_completed"]),
    e(
        ["sod", "st_conflict", "rc_sod", "other"],
        [ident("jiho_park", "groups"), sheet("ss_sod_matrix")],
    ),
    e(
        ["st_declined", "rc_notelig", "contract_change"],
        [w("yusuf_demir", "status"), sheet("ss_contractor_sow")],
    ),
    e(["st_dup"], [req("ACCESS-410")]),
    e(["rb_training", "course"]),
    e(["announce", "no_access"]),
    e(
        ["rb_manager"],
        [w("arjun_mehta", "manager_id"), req("ACCESS-430", "approver_id")],
    ),
    e(["rb_dup"]),
    e(["other", "account", "old_account"], [ident("sofia_lind_2025", "status")]),
    SIDE,
    e(["other", "st_training"], [req("ACCESS-419")]),
]

REVIEW = [
    e(
        ["emp_admin", "training", "owners", "enddate"],
        [
            gmail("msg_owner_441"),
            NOW,
            f"{FW}.training_records.worker_sven_holm:secure-production-access-2026.status",
        ],
    ),
    e(["st_completed", "rb_exp"]),
    e(
        ["sod", "sod_exception", "owners", "other"],
        [
            ident("omar_haddad", "groups"),
            sheet("ss_sod_matrix"),
            gmail("msg_owner_443"),
        ],
    ),
    e(["st_completed", "rb_exp", "sod_exception"]),
    e(
        ["analytics_prereq", "owner", "enddate"],
        [
            slack("slack_message_033"),
            f"{FW}.training_records.worker_hana_kim:data-handling-2026.status",
        ],
    ),
    e(["st_completed"]),
    e(
        ["elig_table", "enddate", "contract_change"],
        [w("leon_brandt", "contract_end_date"), sheet("ss_contractor_sow")],
    ),
    e(["st_completed", "rb_exp"]),
    e(
        ["rb_owner", "st_approval", "rc_owner", "approvals", "owners"],
        [gmail("msg_vp_mei"), w("rafael_ortiz", "job_title")],
    ),
    e(
        ["sod", "st_conflict", "rc_sod", "sod_exception", "approvals"],
        [ident("rui_silva", "groups"), sheet("ss_sod_matrix"), gmail("msg_owner_444")],
    ),
    e(["review_mark"], [sheet("ss_q4_review")]),
    e(["review_unmarked", "review_new"], [sheet("ss_q4_review"), NOW]),
    e(["rb_training"]),
    e(["announce", "no_access"]),
    e(["rb_owner", "owners", "jira_notify", "lms_email"]),
    e(
        ["rb_manager"],
        [w("bruno_costa", "manager_id"), req("ACCESS-447", "approver_id")],
    ),
    e(["rb_dup"]),
    e(["other", "sod"], [ident("rui_silva", "groups")]),
    e(["other", "st_completed"], [req("ACCESS-435")]),
]


_T7 = json.loads((INTERACTIVE / "tasks/access_provisioning_007.json").read_text())


def s7(*needles):
    """Point at the seeded Slack messages that contain each snippet, once."""
    ids = []
    for needle in needles:
        hits = [
            mid
            for mid, m in _T7["family_world"]["slack_messages"].items()
            if needle in m["text"]
        ]
        assert len(hits) == 1, (needle, hits)
        ids.append(slack(hits[0]))
    return e([], ids)


D30 = "Default is 30 days"
OWNER = "good with Pia"
VP = "parking ACCESS-384"
CAP = "Jo's end date"
JOA = "Jo Alvarez received"
TRAIN = "hasn't done secure-production-access"
CONFLICT = "Lars already approves"
COURSE = "They made me do the prod course"
ANNOUNCE = "Pia Lund received"

# Task 7 has no written workflow; precedent lives in Slack and closed tickets.
PRECEDENT = [
    s7(D30, OWNER, "Sven having prod admin"),  # Sven: owner approval, 30 days
    s7(D30, OWNER, ANNOUNCE),
    s7(D30, COURSE),  # Omar: read-only, course already done
    s7(D30, "Mira Soto received"),
    s7(CAP, JOA),  # Leon: capped at the contract end
    s7(CAP, JOA),
    s7("Mei needs prod admin", VP, OWNER),  # Mei: VP approval is not owner approval
    s7(VP, OWNER),
    s7(CONFLICT),  # Rui: release approver conflict
    s7(CONFLICT),
    s7(TRAIN, COURSE, "Provisional isn't a thing"),  # Hana: assign course, block
    s7("Provisional isn't a thing", "Amir finished"),
    s7(TRAIN, "Amir Chen - production", ANNOUNCE),  # announcements for grants only
    s7("Provisional isn't a thing", "Amir finished"),
    s7("Amir needs prod read-only", TRAIN),
]

LEDGER = {
    "automation_workplace__interactive__access_provisioning_001": PRIYA,
    "automation_workplace__interactive__access_provisioning_002": PRIYA_PROD_ONLY,
    "automation_workplace__interactive__access_provisioning_003": BACKLOG,
    "automation_workplace__interactive__access_provisioning_004": SCOPING,
    "automation_workplace__interactive__access_provisioning_005": QUEUE,
    "automation_workplace__interactive__access_provisioning_006": REVIEW,
    "automation_workplace__interactive__access_provisioning_007": PRECEDENT,
}

out = INTERACTIVE / "evidence" / "access_provisioning.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(LEDGER, indent=2, ensure_ascii=False) + "\n")
print(out, {k.rsplit("_", 1)[-1]: len(v) for k, v in LEDGER.items()})
