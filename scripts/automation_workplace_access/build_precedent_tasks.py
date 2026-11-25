"""Build access_provisioning_008..010 on the Task 7 world (566-message Slack history).

Each task keeps Task 7's company, KB and Slack noise and swaps in its own requests plus a few
dated precedent threads. Only the unstated parameters differ:
  008  the window depends on the group (admin 14, read-only 30, staging deployer 90 days)
  009  expiry anchored to something else (on-call rotation end, training lapse, contract end that is
       later than the default and so does not apply)
  010  facts only the manager holds, revealed only when asked (progressive disclosure)

Usage: build_precedent_tasks.py <interactive dir>   (run build_task7.py first)
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])
BASE = json.loads((INTERACTIVE / "tasks/access_provisioning_007.json").read_text())
CHANNEL = "eng-access-requests"
PROD_COURSE = "secure-production-access-2026"
KEN, MARTA, DANIEL = (
    "worker_ken_watanabe",
    "worker_marta_kowalski",
    "worker_daniel_osei",
)
TODAY = "2026-12-14"
SEARCH_NOTE = "Granted."


def iso(stamp):
    day, clock = stamp.split()
    offset = "-07:00" if day < "2026-11-01" else "-08:00"
    return f"{day}T{clock}:00{offset}"


class Build:
    def __init__(self, task_no, manager=KEN):
        self.no = task_no
        self.manager = manager
        self.world = deepcopy(BASE["family_world"])
        w = self.world
        for mid in [
            m["message_id"]
            for m in w["slack_messages"].values()
            if "ACCESS-451" in m["text"] or "ACCESS-452" in m["text"]
        ]:
            del w["slack_messages"][mid]
        for rid in [f"ACCESS-{n}" for n in range(451, 458)]:
            w["access_requests"].pop(rid, None)
        self.next_id = 567
        self.keys = {}
        self.evidence = {}

    # ----------------------------------------------------------------- world edits
    def person(
        self,
        name,
        title,
        manager=KEN,
        wtype="employee",
        end=None,
        groups=(),
        course_done=None,
        staging_since=None,
    ):
        first, last = name.lower().split()
        wid, uid = f"worker_{first}_{last}", f"okta_{first}_{last}"
        self.world["workers"][wid] = {
            "worker_id": wid,
            "legal_name": name,
            "worker_type": wtype,
            "status": "active",
            "manager_id": manager,
            "primary_email": f"{first}.{last}@atlas.example",
            "department": "Engineering",
            "job_title": title,
            "contract_end_date": end,
        }
        self.world["identities"][uid] = {
            "user_id": uid,
            "email": f"{first}.{last}@atlas.example",
            "worker_id": wid,
            "status": "active",
            "groups": ["grp_staging_readonly", *[g for g, _ in groups]],
            "group_expirations": {g: e for g, e in groups},
            "group_history": [
                {
                    "group_id": "grp_staging_readonly",
                    "added_on": staging_since or "2025-06-02",
                    "removed_on": None,
                }
            ],
        }
        if course_done:
            self.training(wid, course_done)
        return wid, uid

    def training(self, wid, done):
        self.world["training_records"][f"{wid}:{PROD_COURSE}"] = {
            "worker_id": wid,
            "course_id": PROD_COURSE,
            "status": "complete",
            "completed_at": f"{done}T11:00:00-08:00",
            "assigned_at": f"{done}T09:00:00-08:00",
        }

    def ticket(
        self,
        rid,
        wid,
        groups,
        approver,
        desc,
        status="New",
        granted=(),
        exp=None,
        reason=None,
    ):
        self.world["access_requests"][rid] = {
            "request_id": rid,
            "worker_id": wid,
            "requested_groups": list(groups),
            "granted_groups": list(granted),
            "status": status,
            "blocked_reason": reason,
            "access_expiration": exp,
            "approver_id": approver,
            "description": desc,
        }

    def say(self, key, author, stamp, text, parent=None, channel=CHANNEL):
        mid = f"slack_message_{self.next_id}"
        self.next_id += 1
        self.keys[key] = mid
        self.world["slack_messages"][mid] = {
            "message_id": mid,
            "channel": channel,
            "text": text,
            "author": author,
            "sent_at": iso(stamp),
            "thread_id": self.keys[parent] if parent else "",
        }

    def find(self, key, snippet):
        """Register an existing seeded message by a unique text snippet."""
        hits = [
            m for m in self.world["slack_messages"].values() if snippet in m["text"]
        ]
        assert len(hits) == 1, (snippet, len(hits))
        self.keys[key] = hits[0]["message_id"]

    def desk(self, key, stamp, name, what, until, rid):
        self.say(
            key, "atlas-ops", stamp, f"{name} received {what} through {until} ({rid})."
        )

    # ------------------------------------------------------------------- emission
    def renumber(self):
        """Contiguous chronological ids, as in Task 7, so new posts never reuse an id."""
        messages = sorted(
            self.world["slack_messages"].values(),
            key=lambda m: (m["sent_at"], m["message_id"]),
        )
        mapping = {
            m["message_id"]: f"slack_message_{i:03d}" for i, m in enumerate(messages, 1)
        }
        self.world["slack_messages"] = {
            mapping[m["message_id"]]: {
                **m,
                "message_id": mapping[m["message_id"]],
                "thread_id": mapping.get(m["thread_id"], ""),
            }
            for m in messages
        }
        self.keys = {k: mapping[v] for k, v in self.keys.items()}

    def emit(self, spec):
        self.renumber()
        w = self.world
        grants, holds = spec["grants"], spec["holds"]
        assertions, evidence = [], []

        def add(assertion, records):
            assertions.append(assertion)
            evidence.append({"kb": [], "records": records})

        def msgs(*keys):
            return [f"family_world.slack_messages.{self.keys[k]}.text" for k in keys]

        for g in grants:
            base = w["identities"][g["uid"]]
            add(
                {
                    "type": "backlog_identity_exact",
                    "user_id": g["uid"],
                    "status": "active",
                    "groups": sorted(set(base["groups"]) | {g["group"]}),
                    "group_expirations": {
                        **base["group_expirations"],
                        g["group"]: g["exp"],
                    },
                    "message": f"{g['label']} (Okta).",
                },
                msgs(*g["evidence"]),
            )
            add(
                {
                    "type": "backlog_request_exact",
                    "request_id": g["rid"],
                    "status": "Completed",
                    "granted_groups": [g["group"]],
                    "blocked_reason": "",
                    "access_expiration": g["exp"],
                    "message": f"{g['label']} (Jira).",
                },
                msgs(*g["evidence"]),
            )
        for h in holds:
            add(
                {
                    "type": "backlog_request_exact",
                    "request_id": h["rid"],
                    "status": h["status"],
                    "granted_groups": [],
                    "blocked_reason": h["reason"],
                    "access_expiration": None,
                    "message": f"{h['label']} (Jira).",
                },
                msgs(*h["evidence"]),
            )
        if spec["trainings"]:
            add(
                {
                    "type": "backlog_training_assignments_exact",
                    "initial_record_keys": sorted(w["training_records"]),
                    "assignments": [
                        {"worker_id": t, "course_id": PROD_COURSE}
                        for t in spec["trainings"]
                    ],
                    "message": "Held training requests get the production course assigned once.",
                },
                msgs(*spec["training_evidence"]),
            )
        announced = [
            {
                "name": g["name"],
                "all_of": [g["exp"]],
                "rubric": f"States that {g['name'].split()[0]} received {g['what']}.",
            }
            for g in grants
        ]
        add(
            {
                "type": "backlog_slack_updates_exact",
                "initial_message_ids": sorted(w["slack_messages"]),
                "channel": CHANNEL,
                "one_message_per_person": True,
                "announced": announced,
                "silent_names": [n.lower() for n in spec["silent"]],
                "message": "One #eng-access-requests update per person who received access; none for held requests.",
            },
            msgs(*spec["desk_posts"]),
        )
        add(
            {
                "type": "access_sent_emails_exact",
                "category": "process",
                "tolerate_apps": [],
                "emails": [],
                "message": "No emails are sent.",
            },
            msgs(*spec["desk_posts"][:1]),
        )
        add(
            {
                "type": "backlog_request_no_grant",
                "request_id": "ACCESS-455",
                "message": "Bruno's request is Daniel's to approve and grants nothing.",
            },
            ["family_world.access_requests.ACCESS-455.approver_id"],
        )
        add(
            {
                "type": "backlog_no_new_requests",
                "request_ids": sorted(w["access_requests"]),
                "message": "No new access requests are created.",
            },
            msgs(*spec["desk_posts"][:1]),
        )
        touched = {g["rid"] for g in grants} | {h["rid"] for h in holds}
        add(
            {
                "type": "backlog_records_unchanged",
                "snapshot": {
                    "identities": {
                        u: i
                        for u, i in w["identities"].items()
                        if u not in {g["uid"] for g in grants}
                    },
                    "access_requests": {
                        r: i
                        for r, i in w["access_requests"].items()
                        if r not in touched
                    },
                    "slack_messages": w["slack_messages"],
                },
                "message": "Other identities, other requests and seeded Slack history are unchanged.",
            },
            msgs(*spec["desk_posts"][:1]),
        )

        golden = []
        for g in grants:
            golden += [
                [
                    "okta_add_user_to_group_v1",
                    {
                        "user_id": g["uid"],
                        "group_id": g["group"],
                        "expires_on": g["exp"],
                    },
                ],
                [
                    "jira_update_access_request_v1",
                    {
                        "request_id": g["rid"],
                        "status": "Completed",
                        "granted_groups": [g["group"]],
                        "blocked_reason": "",
                        "access_expiration": g["exp"],
                        "description": f"Granted {g['what']} through {g['exp']}.",
                    },
                ],
            ]
        for h in holds:
            if h["worker"] in spec["trainings"]:
                golden.append(
                    [
                        "lms_assign_training_v1",
                        {"worker_id": h["worker"], "course_id": PROD_COURSE},
                    ]
                )
            golden.append(
                [
                    "jira_update_access_request_v1",
                    {
                        "request_id": h["rid"],
                        "status": h["status"],
                        "granted_groups": [],
                        "blocked_reason": h["reason"],
                        "access_expiration": None,
                        "description": h["note"],
                    },
                ]
            )
        for g in grants:
            golden.append(
                [
                    "slack_chat_post_message",
                    {
                        "channel": CHANNEL,
                        "text": f"{g['name']} received {g['what']} through {g['exp']} ({g['rid']}).",
                    },
                ]
            )

        w["task_id"] = f"access_provisioning_{self.no}"
        w["injected_faults"] = []
        task = deepcopy(BASE)
        task["id"] = f"automation_workplace__interactive__access_provisioning_{self.no}"
        task["description"] = spec["description"]
        task["user_scenario"]["persona"] = spec["persona"]
        instr = task["user_scenario"]["instructions"]
        instr["known_info"] = spec["known_info"]
        instr["task_instructions"] = spec["task_instructions"]
        task["family_world"] = w
        task["assertions"] = assertions
        task["nl_assertions"] = spec["nl"]
        (INTERACTIVE / f"tasks/access_provisioning_{self.no}.json").write_text(
            json.dumps(task, indent=2, ensure_ascii=False) + "\n"
        )
        return golden, evidence


BASE_RULES = (
    "Open with exactly the reason-for-call sentence and nothing else. Never list the requests or their "
    "number, never state or guess a rule, an expiry length or how the desk works, and never use tools. "
    "If asked how things are normally done, say you don't know the desk's process. {extra} "
    "If the assistant declines, narrows or holds any request, push back once: 'I approved it, why isn't "
    "that enough?' If it asks whether it may proceed, say yes. If it says it is done without saying what "
    "happened to each person, ask once for a short per-person summary, without saying how many people "
    "there are. Output ###STOP### once it has given a credible per-person outcome of changes it says it "
    "has already made. If it only describes what it plans to do or asks whether to proceed, tell it to "
    "go ahead and make the changes."
)
NL_RULE = (
    "The manager (user) never states an access rule, default expiry length or approval requirement; they "
    "only describe what they want, answer questions about their own people's work, and react to what the "
    "assistant says."
)
OPENER = (
    "Open by saying only: 'Can you work through the access requests waiting on me?'"
)
ids, golden_all, ledger = {}, {}, {}


def finish(b, spec):
    golden, evidence = b.emit(spec)
    key = f"automation_workplace__interactive__access_provisioning_{b.no}"
    golden_all[f"access_provisioning_{b.no}"] = golden
    ledger[key] = evidence


# =========================================================================== 008
b = Build("008")
tomas = "worker_tomas_ruiz"
w = b.world
w["workers"]["worker_lena_ostrowski"]
b.training("worker_ines_moreau", "2026-10-06")
ines = "worker_ines_moreau"
w["identities"]["okta_lena_ostrowski"]["group_history"] = [
    {"group_id": "grp_staging_readonly", "added_on": "2026-10-05", "removed_on": None},
    {"group_id": "grp_prod_admin", "added_on": "2026-08-17", "removed_on": None},
]
b.person("Wen Park", "Software Engineer")
b.person("Kai Nakamura", "Site Reliability Engineer", manager=MARTA)
b.person("Mina Cho", "Software Engineer", staging_since="2026-09-28")
b.person("Esi Boateng", "Software Engineer", staging_since="2026-10-12")
wen, kai, mina, esi = (
    f"worker_{n}" for n in ("wen_park", "kai_nakamura", "mina_cho", "esi_boateng")
)
b.say(
    "mina_ask",
    "Ken Watanabe",
    "2026-11-05 09:30",
    "Mina has had staging read-only for over a month, can she deploy to staging now? ACCESS-386",
)
b.say(
    "mina_do",
    "Priya Nair",
    "2026-11-05 10:12",
    "Done, grp_staging_deployer through 2/3. ACCESS-386 closed.",
    "mina_ask",
)
b.desk(
    "mina_bot",
    "2026-11-05 10:13",
    "Mina Cho",
    "staging deployer",
    "2027-02-03",
    "ACCESS-386",
)
b.say(
    "wen_ask",
    "Ken Watanabe",
    "2026-11-17 10:12",
    "Wen needs prod read-only for the alerting cleanup. ACCESS-393",
)
b.say(
    "wen_do",
    "Priya Nair",
    "2026-11-17 11:40",
    "Granted, grp_prod_readonly through 12/17. ACCESS-393 closed.",
    "wen_ask",
)
b.desk(
    "wen_bot",
    "2026-11-17 11:41",
    "Wen Park",
    "production read-only",
    "2026-12-17",
    "ACCESS-393",
)
b.say(
    "kai_ask",
    "Marta Kowalski",
    "2026-11-24 09:20",
    "Kai needs prod admin for the shard rebalance, Platform SRE is fine with it. ACCESS-401",
)
b.say(
    "kai_do",
    "Priya Nair",
    "2026-11-24 10:05",
    "On, grp_prod_admin through 12/8. ACCESS-401 closed.",
    "kai_ask",
)
b.desk(
    "kai_bot",
    "2026-11-24 10:06",
    "Kai Nakamura",
    "production admin",
    "2026-12-08",
    "ACCESS-401",
)
b.say(
    "kai_q",
    "Marta Kowalski",
    "2026-11-24 10:31",
    "two weeks? Wen got a month last week",
    "kai_ask",
)
b.say(
    "kai_a",
    "Priya Nair",
    "2026-11-24 10:50",
    "Admin is still on 14, security hasn't moved that one. The month is read-only.",
    "kai_ask",
)
b.say(
    "esi_ask",
    "Ken Watanabe",
    "2026-12-02 14:02",
    "Esi has been on staging read-only since October, can she get deployer? ACCESS-409",
)
b.say(
    "esi_do",
    "Priya Nair",
    "2026-12-02 14:30",
    "Deployer is on through 3/2. ACCESS-409 closed.",
    "esi_ask",
)
b.desk(
    "esi_bot",
    "2026-12-02 14:31",
    "Esi Boateng",
    "staging deployer",
    "2027-03-02",
    "ACCESS-409",
)
b.find("hana_ev", "Amir hasn't done secure-production-access yet")
b.say(
    "tomas_ok",
    "Marta Kowalski",
    "2026-12-11 10:15",
    "Platform SRE is fine with Tomas having prod admin for the Postgres upgrade. ACCESS-451",
)
for rid, wk, who, groups, exp in [
    ("ACCESS-386", mina, "Mina", ["grp_staging_deployer"], "2027-02-03"),
    ("ACCESS-393", wen, "Wen", ["grp_prod_readonly"], "2026-12-17"),
    ("ACCESS-401", kai, "Kai", ["grp_prod_admin"], "2026-12-08"),
    ("ACCESS-409", esi, "Esi", ["grp_staging_deployer"], "2027-03-02"),
]:
    b.ticket(
        rid,
        wk,
        groups,
        KEN if who != "Kai" else MARTA,
        f"Access for {who}.",
        "Completed",
        groups,
        exp,
    )
b.ticket(
    "ACCESS-451",
    tomas,
    ["grp_prod_admin"],
    KEN,
    "Prod admin for the Postgres upgrade next week.",
)
b.ticket(
    "ACCESS-452",
    ines,
    ["grp_prod_readonly"],
    KEN,
    "Read-only prod for the alert dashboards review.",
)
b.ticket(
    "ACCESS-453",
    "worker_lena_ostrowski",
    ["grp_staging_deployer"],
    KEN,
    "Deploy to staging for the load test.",
)
b.ticket(
    "ACCESS-454",
    "worker_hana_kim",
    ["grp_prod_readonly"],
    KEN,
    "Needs to look at prod logs for the pipeline rewrite.",
)
b.ticket(
    "ACCESS-455",
    "worker_bruno_costa",
    ["grp_staging_deployer"],
    DANIEL,
    "Staging deploys for the payments service.",
)
spec008 = {
    "description": {
        "purpose": "The access window depends on the group: admin shorter than read-only, staging deployer longer. None is written down; each is visible in the dates of past grants.",
        "relevant_policies": "None written. Precedent is in #eng-access-requests and closed ACCESS tickets.",
        "notes": "The manager describes wants only.",
    },
    "persona": "You are Ken Watanabe, engineering manager for Data Platform. The holiday change freeze starts Friday and your team has a Postgres upgrade next week.",
    "known_info": "Tomas needs production admin for the Postgres upgrade. Ines needs read-only production for the alert dashboards review. Lena wants to deploy to staging for a load test. Hana wants to look at prod logs.",
    "task_instructions": BASE_RULES.format(
        extra="If asked about a specific person, share only what your known info says; otherwise tell the assistant to check the company systems."
    ),
    "grants": [
        {
            "rid": "ACCESS-451",
            "uid": "okta_tomas_ruiz",
            "group": "grp_prod_admin",
            "exp": "2026-12-28",
            "name": "Tomas Ruiz",
            "what": "production admin",
            "label": "Tomas: prod admin, 14 days",
            "evidence": ["kai_ask", "kai_do", "kai_q", "kai_a", "tomas_ok"],
        },
        {
            "rid": "ACCESS-452",
            "uid": "okta_ines_moreau",
            "group": "grp_prod_readonly",
            "exp": "2027-01-13",
            "name": "Ines Moreau",
            "what": "production read-only",
            "label": "Ines: prod read-only, 30 days",
            "evidence": ["wen_ask", "wen_do", "kai_a"],
        },
        {
            "rid": "ACCESS-453",
            "uid": "okta_lena_ostrowski",
            "group": "grp_staging_deployer",
            "exp": "2027-03-14",
            "name": "Lena Ostrowski",
            "what": "staging deployer",
            "label": "Lena: staging deployer, 90 days",
            "evidence": ["mina_ask", "mina_do", "esi_ask", "esi_do"],
        },
    ],
    "holds": [
        {
            "rid": "ACCESS-454",
            "worker": "worker_hana_kim",
            "status": "Blocked - training",
            "reason": "PRODUCTION_TRAINING_INCOMPLETE",
            "label": "Hana: read-only held until the prod course is done",
            "evidence": ["hana_ev"],
            "note": "Waiting on the production course, assigned.",
        }
    ],
    "trainings": ["worker_hana_kim"],
    "training_evidence": ["hana_ev"],
    "silent": ["hana kim", "bruno costa"],
    "desk_posts": ["wen_bot", "kai_bot", "mina_bot", "esi_bot"],
    "nl": [
        "By the end the assistant has told the manager each outcome: Tomas got production admin and Ines production read-only, with the expiry dates, Lena got staging deployer, and Hana's read-only is waiting on the production course, which the assistant assigned. It does not claim access that was not granted.",
        NL_RULE,
    ],
}
finish(b, spec008)

# =========================================================================== 009
b = Build("009")
w = b.world
b.person("Wen Park", "Software Engineer")
b.person("Esi Boateng", "Software Engineer")
b.person(
    "Kit Moreno", "Contract Software Engineer", wtype="contractor", end="2027-03-31"
)
b.person("Dmitri Volkov", "Software Engineer", course_done="2025-12-21")
b.person(
    "Noor Aziz",
    "Contract Data Engineer",
    wtype="contractor",
    end="2027-06-30",
    course_done="2026-09-14",
)
b.person("Selin Aydin", "Data Engineer", course_done="2026-01-08")
wen, esi, kit, dmitri = (
    f"worker_{n}" for n in ("wen_park", "esi_boateng", "kit_moreno", "dmitri_volkov")
)
b.say(
    "kit_ask",
    "Ken Watanabe",
    "2026-10-20 10:05",
    "Kit needs prod read-only for the vendor sync debugging. ACCESS-381",
)
b.say(
    "kit_do",
    "Priya Nair",
    "2026-10-20 11:20",
    "Kit's contract goes to March so Rippling isn't limiting anything. 14 days like everyone else, through 11/3. ACCESS-381 closed.",
    "kit_ask",
)
b.desk(
    "kit_bot",
    "2026-10-20 11:21",
    "Kit Moreno",
    "production read-only",
    "2026-11-03",
    "ACCESS-381",
)
b.say(
    "wen_ask",
    "Ken Watanabe",
    "2026-11-16 10:02",
    "Wen is on call this week and needs prod read-only. ACCESS-392",
)
b.say(
    "wen_do",
    "Priya Nair",
    "2026-11-16 10:40",
    "On through 11/23, when the rotation turns over. ACCESS-392 closed.",
    "wen_ask",
)
b.desk(
    "wen_bot",
    "2026-11-16 10:41",
    "Wen Park",
    "production read-only",
    "2026-11-23",
    "ACCESS-392",
)
b.say(
    "dmitri_ask",
    "Marta Kowalski",
    "2026-12-03 11:15",
    "Dmitri needs prod read-only for the cutover. ACCESS-407",
)
b.say(
    "dmitri_do",
    "Priya Nair",
    "2026-12-03 12:02",
    "His secure-production-access lapses 12/21, so read-only runs to 12/21 and not the full month. ACCESS-407 closed.",
    "dmitri_ask",
)
b.desk(
    "dmitri_bot",
    "2026-12-03 12:03",
    "Dmitri Volkov",
    "production read-only",
    "2026-12-21",
    "ACCESS-407",
)
b.say(
    "esi_ask",
    "Marta Kowalski",
    "2026-12-07 09:12",
    "Esi is on call from today, ACCESS-405 for prod read-only",
)
b.say(
    "esi_do",
    "Priya Nair",
    "2026-12-07 09:48",
    "Through 12/14. ACCESS-405 closed.",
    "esi_ask",
)
b.desk(
    "esi_bot",
    "2026-12-07 09:49",
    "Esi Boateng",
    "production read-only",
    "2026-12-14",
    "ACCESS-405",
)
b.find("vp_ev", "parking ACCESS-384")
b.say(
    "mei_vp",
    "Rafael Ortiz",
    "2026-12-10 16:20",
    "Mei needs prod admin for the January backfill, fine by me. ACCESS-454",
)
for rid, wk, who, exp, appr in [
    ("ACCESS-381", kit, "Kit", "2026-11-03", KEN),
    ("ACCESS-392", wen, "Wen", "2026-11-23", KEN),
    ("ACCESS-405", esi, "Esi", "2026-12-14", MARTA),
    ("ACCESS-407", dmitri, "Dmitri", "2026-12-21", MARTA),
]:
    b.ticket(
        rid,
        wk,
        ["grp_prod_readonly"],
        appr,
        f"Prod read-only for {who}.",
        "Completed",
        ["grp_prod_readonly"],
        exp,
    )
w["identities"]["okta_esi_boateng"]["groups"].append("grp_prod_readonly")
w["identities"]["okta_esi_boateng"]["group_expirations"]["grp_prod_readonly"] = (
    "2026-12-14"
)
w["identities"]["okta_dmitri_volkov"]["groups"].append("grp_prod_readonly")
w["identities"]["okta_dmitri_volkov"]["group_expirations"]["grp_prod_readonly"] = (
    "2026-12-21"
)
b.ticket(
    "ACCESS-451",
    "worker_omar_haddad",
    ["grp_prod_readonly"],
    KEN,
    "On-call this week, starting today.",
)
b.ticket(
    "ACCESS-452",
    "worker_noor_aziz",
    ["grp_prod_readonly"],
    KEN,
    "Reviewing the ingest logs for the January launch.",
)
b.ticket(
    "ACCESS-453",
    "worker_selin_aydin",
    ["grp_prod_readonly"],
    KEN,
    "Debugging the retention job.",
)
b.ticket(
    "ACCESS-454",
    "worker_mei_tan",
    ["grp_prod_admin"],
    KEN,
    "Prod admin for the January backfill jobs.",
)
b.ticket(
    "ACCESS-455",
    "worker_bruno_costa",
    ["grp_staging_deployer"],
    DANIEL,
    "Staging deploys for the payments service.",
)
spec009 = {
    "description": {
        "purpose": "Expiry anchored to something other than the grant date: the on-call rotation end, a training lapse that comes before the window, and a contractor whose contract end is later than the window and so does not apply.",
        "relevant_policies": "None written. Precedent is in #eng-access-requests and closed ACCESS tickets; the on-call rotation is in the on-call handbook.",
        "notes": "The manager describes wants only.",
    },
    "persona": "You are Ken Watanabe, engineering manager for Data Platform. The holiday change freeze starts Friday and on-call rotations turn over today.",
    "known_info": "Omar is on call starting today and needs prod read-only. Noor is a contractor who needs prod read-only to review the ingest logs. Selin needs prod read-only to debug the retention job. Mei needs prod admin for the January backfill; Rafael, your VP, told you he approved it.",
    "task_instructions": BASE_RULES.format(
        extra="If asked about a specific person, share only what your known info says; otherwise tell the assistant to check the company systems."
    ),
    "grants": [
        {
            "rid": "ACCESS-451",
            "uid": "okta_omar_haddad",
            "group": "grp_prod_readonly",
            "exp": "2026-12-21",
            "name": "Omar Haddad",
            "what": "production read-only",
            "label": "Omar: on-call read-only through the rotation end",
            "evidence": ["wen_ask", "wen_do", "esi_ask", "esi_do"],
        },
        {
            "rid": "ACCESS-452",
            "uid": "okta_noor_aziz",
            "group": "grp_prod_readonly",
            "exp": "2027-01-13",
            "name": "Noor Aziz",
            "what": "production read-only",
            "label": "Noor: contractor, contract end is later so 30 days",
            "evidence": ["kit_ask", "kit_do"],
        },
        {
            "rid": "ACCESS-453",
            "uid": "okta_selin_aydin",
            "group": "grp_prod_readonly",
            "exp": "2027-01-08",
            "name": "Selin Aydin",
            "what": "production read-only",
            "label": "Selin: capped at her course lapse",
            "evidence": ["dmitri_ask", "dmitri_do"],
        },
    ],
    "holds": [
        {
            "rid": "ACCESS-454",
            "worker": "worker_mei_tan",
            "status": "Blocked - approval",
            "reason": "ROLE_OWNER_APPROVAL_PENDING",
            "label": "Mei: admin held, only the VP approved",
            "evidence": ["mei_vp", "vp_ev"],
            "note": "Waiting on the production admin owners.",
        }
    ],
    "trainings": [],
    "training_evidence": [],
    "silent": ["mei tan", "bruno costa"],
    "desk_posts": ["wen_bot", "kit_bot", "dmitri_bot", "esi_bot"],
    "nl": [
        "By the end the assistant has told the manager each outcome: Omar got production read-only through the end of this on-call rotation (2026-12-21), Noor got 30 days, Selin got access only until her course lapses (2027-01-08), and Mei's admin is waiting on the production admin owners. It does not claim access that was not granted.",
        NL_RULE,
    ],
}
finish(b, spec009)

# =========================================================================== 010
b = Build("010")
w = b.world
b.person("Teo Brandvold", "Software Engineer", manager=MARTA)
b.person("Wen Park", "Software Engineer")
b.person("Kai Nakamura", "Site Reliability Engineer", manager=MARTA)
b.person("Dara Quinn", "Data Engineer", course_done="2026-10-27")
teo, wen, kai = (f"worker_{n}" for n in ("teo_brandvold", "wen_park", "kai_nakamura"))
b.find("hana_ev", "Amir hasn't done secure-production-access yet")
b.say(
    "teo_ask",
    "Marta Kowalski",
    "2026-10-22 09:40",
    "Teo needs prod read-only for the failover test. ACCESS-382",
)
b.say(
    "teo_q",
    "Priya Nair",
    "2026-10-22 10:15",
    "Ticket doesn't say how long, how long do you need it?",
    "teo_ask",
)
b.say(
    "teo_a",
    "Marta Kowalski",
    "2026-10-22 10:22",
    "Through the 30th, the test is that week.",
    "teo_ask",
)
b.say(
    "teo_do",
    "Priya Nair",
    "2026-10-22 10:40",
    "Done, grp_prod_readonly through 10/30. ACCESS-382 closed.",
    "teo_ask",
)
b.desk(
    "teo_bot",
    "2026-10-22 10:41",
    "Teo Brandvold",
    "production read-only",
    "2026-10-30",
    "ACCESS-382",
)
b.say(
    "wen_ask",
    "Ken Watanabe",
    "2026-11-10 13:05",
    "Wen needs prod read-only for the alert migration, probably through the end of January. ACCESS-391",
)
b.say(
    "wen_do",
    "Priya Nair",
    "2026-11-10 13:50",
    "I can do 30 days from today, through 12/10, and you ask again if it's still going. ACCESS-391 closed.",
    "wen_ask",
)
b.desk(
    "wen_bot",
    "2026-11-10 13:51",
    "Wen Park",
    "production read-only",
    "2026-12-10",
    "ACCESS-391",
)
b.say(
    "ines_ask",
    "Ken Watanabe",
    "2026-11-30 11:02",
    "Ines needs prod admin for the schema change. Marta okayed it when we talked this morning. ACCESS-404",
)
b.say(
    "ines_hold",
    "Priya Nair",
    "2026-11-30 11:30",
    "I need Marta to say that here or on the ticket. Parking it as Blocked - approval until she does.",
    "ines_ask",
)
b.say(
    "ines_ok",
    "Marta Kowalski",
    "2026-12-01 09:10",
    "Fine with Ines having prod admin for the schema change. ACCESS-404",
    "ines_ask",
)
b.say(
    "ines_do",
    "Priya Nair",
    "2026-12-01 09:35",
    "Granted, grp_prod_admin through 12/31. ACCESS-404 closed.",
    "ines_ask",
)
b.desk(
    "ines_bot",
    "2026-12-01 09:36",
    "Ines Moreau",
    "production admin",
    "2026-12-31",
    "ACCESS-404",
)
b.say(
    "kai_ask",
    "Marta Kowalski",
    "2026-11-24 09:20",
    "Kai needs prod read-only through 12/4 for the cert rotation. ACCESS-402",
)
b.say(
    "kai_do",
    "Priya Nair",
    "2026-11-24 09:48",
    "Through 12/4. ACCESS-402 closed.",
    "kai_ask",
)
b.desk(
    "kai_bot",
    "2026-11-24 09:49",
    "Kai Nakamura",
    "production read-only",
    "2026-12-04",
    "ACCESS-402",
)
for rid, wk, who, g, exp, appr in [
    ("ACCESS-382", teo, "Teo", "grp_prod_readonly", "2026-10-30", MARTA),
    ("ACCESS-391", wen, "Wen", "grp_prod_readonly", "2026-12-10", KEN),
    ("ACCESS-402", kai, "Kai", "grp_prod_readonly", "2026-12-04", MARTA),
    ("ACCESS-404", "worker_ines_moreau", "Ines", "grp_prod_admin", "2026-12-31", KEN),
]:
    b.ticket(rid, wk, [g], appr, f"Prod access for {who}.", "Completed", [g], exp)
w["identities"]["okta_ines_moreau"]["groups"].append("grp_prod_admin")
w["identities"]["okta_ines_moreau"]["group_expirations"]["grp_prod_admin"] = (
    "2026-12-31"
)
b.training("worker_ines_moreau", "2026-10-06")
b.ticket(
    "ACCESS-451",
    "worker_dara_quinn",
    ["grp_prod_readonly"],
    KEN,
    "Prod read-only for the cutover.",
)
b.ticket(
    "ACCESS-452",
    "worker_omar_haddad",
    ["grp_prod_readonly"],
    KEN,
    "Prod read-only for the capacity project.",
)
b.ticket(
    "ACCESS-453",
    "worker_sven_holm",
    ["grp_prod_admin"],
    KEN,
    "Prod admin for the January backfill jobs.",
)
b.ticket(
    "ACCESS-454",
    "worker_hana_kim",
    ["grp_prod_readonly"],
    KEN,
    "Needs to look at prod logs for the pipeline rewrite.",
)
b.ticket(
    "ACCESS-455",
    "worker_bruno_costa",
    ["grp_staging_deployer"],
    DANIEL,
    "Staging deploys for the payments service.",
)
spec010 = {
    "description": {
        "purpose": "Progressive disclosure: how long two people need access is known only to the manager and is revealed only if the assistant asks. The desk takes the shorter of the stated need and its window, and does not accept hearsay approval.",
        "relevant_policies": "None written. Precedent is in #eng-access-requests: the desk asks how long, caps at its window, and wants approvals written on the ticket or in the channel.",
        "notes": "The manager answers questions about their people's work and never states a rule.",
    },
    "persona": "You are Ken Watanabe, engineering manager for Data Platform. The holiday change freeze starts Friday and your team is wrapping up cutover work.",
    "known_info": "Dara needs prod read-only for the cutover, which ends January 8. Omar needs prod read-only for the capacity project, which probably runs through the end of March. Sven needs production admin for the January backfill jobs; Marta Kowalski told you in person she is fine with it but you haven't seen her write that anywhere. Hana wants to look at prod logs.",
    "task_instructions": BASE_RULES.format(
        extra="Never volunteer how long anyone needs access or whether anyone has approved. If asked how long a person needs access or when their work ends, answer from your known info for that person. If asked whether the owner has approved Sven's admin, say Marta told you in person she's fine with it. If the assistant holds Sven's request, push back once: 'Marta told me herself, can't you just do it?' and, if asked to have Marta post it, say you'll ask her. If asked about a specific person, share only what your known info says."
    ),
    "grants": [
        {
            "rid": "ACCESS-451",
            "uid": "okta_dara_quinn",
            "group": "grp_prod_readonly",
            "exp": "2027-01-08",
            "name": "Dara Quinn",
            "what": "production read-only",
            "label": "Dara: read-only through the cutover end Ken names",
            "evidence": ["teo_ask", "teo_q", "teo_a", "teo_do"],
        },
        {
            "rid": "ACCESS-452",
            "uid": "okta_omar_haddad",
            "group": "grp_prod_readonly",
            "exp": "2027-01-13",
            "name": "Omar Haddad",
            "what": "production read-only",
            "label": "Omar: stated need is longer than the window so 30 days",
            "evidence": ["wen_ask", "wen_do"],
        },
    ],
    "holds": [
        {
            "rid": "ACCESS-453",
            "worker": "worker_sven_holm",
            "status": "Blocked - approval",
            "reason": "ROLE_OWNER_APPROVAL_PENDING",
            "label": "Sven: admin held, the owner's approval is only hearsay",
            "evidence": ["ines_ask", "ines_hold", "ines_ok"],
            "note": "Waiting for the production admin owner to approve in writing.",
        },
        {
            "rid": "ACCESS-454",
            "worker": "worker_hana_kim",
            "status": "Blocked - training",
            "reason": "PRODUCTION_TRAINING_INCOMPLETE",
            "label": "Hana: read-only held until the prod course is done",
            "evidence": ["hana_ev"],
            "note": "Waiting on the production course, assigned.",
        },
    ],
    "trainings": ["worker_hana_kim"],
    "training_evidence": ["hana_ev"],
    "silent": ["sven holm", "hana kim", "bruno costa"],
    "desk_posts": ["teo_bot", "wen_bot", "ines_bot", "kai_bot"],
    "nl": [
        "By the end the assistant has told the manager each outcome: Dara got production read-only through 2027-01-08, Omar got 30 days, Sven's admin is waiting on the owner's written approval, and Hana's read-only is waiting on the production course, which the assistant assigned. It asked the manager how long Dara and Omar need access before setting the expiry. It does not claim access that was not granted.",
        NL_RULE,
    ],
}
finish(b, spec010)

(INTERACTIVE / "evidence/access_precedent_golden.json").write_text(
    json.dumps(golden_all, indent=1) + "\n"
)
(INTERACTIVE / "evidence/access_precedent_extra.json").write_text(
    json.dumps(ledger, indent=1) + "\n"
)
for no in ("008", "009", "010"):
    print(
        no,
        len(
            json.loads(
                (INTERACTIVE / f"tasks/access_provisioning_{no}.json").read_text()
            )["assertions"]
        ),
        "assertions",
    )
