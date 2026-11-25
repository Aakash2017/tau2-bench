"""Write docs/automation-workplace-access-tasks.md from the task files, so evidence tables match the data.

Usage: describe_tasks.py <interactive dir> <output md>
"""

import json
import sys
from pathlib import Path

INTERACTIVE, OUT = Path(sys.argv[1]), Path(sys.argv[2])
CHAINS = {
    "007": [
        "**Sven (admin):** admin needs the production course (LMS: done 2026-02-10) and the role owner. The owner is Platform SRE (Marta): she approved Pia's admin on Oct 28 and approved Sven on Dec 9. Window: the Nov 3 note says 30 days from the grant (it replaced the Oct 6 14-day note), so 2026-12-14 + 30 = 2027-01-13. Announce.",
        "**Omar (read-only):** course done (2026-05-12), no owner approval needed for read-only. He approves releases, but the conflict thread (Lars) concerns admin only. 30 days, 2027-01-13. Announce.",
        "**Leon (read-only, contractor):** Rippling shows contract end 2027-01-05, earlier than the 30-day date, so it caps the expiry (Jo thread, Sep 23). Course done 2026-10-14. Announce with 2027-01-05.",
        "**Mei (admin):** the only approval is Rafael's 'fine by me' (VP, Dec 10). In the Pia thread the desk parked a request as Blocked - approval until the prod admin owners weighed in, so a VP's say-so does not count. Hold with reason ROLE_OWNER_APPROVAL_PENDING. No announcement.",
        "**Rui (admin):** Okta shows he is in grp_release_approver. The Lars thread and closed ACCESS-390 show the desk blocks admin on top of release approval (SOD_CONFLICT). Ken refuses to give up the approver role. Hold, Blocked - conflict. No announcement.",
        "**Hana (read-only):** LMS shows only data-handling-2026, not the production course. The Rhea threads (Aug 18 and 26) show a provisional grant that was reversed: course first, nothing granted. The Amir thread shows the desk assigns the course and does not post until access exists. Assign the course once, Blocked - training (PRODUCTION_TRAINING_INCOMPLETE).",
        "**Bruno:** approver is Daniel Osei, not Ken. Not in Ken's queue; touch nothing.",
    ],
    "008": [
        "**Tomas (admin):** course done (2026-09-22). Owner approval is written down: Marta, Dec 11. Window: Kai's admin grant on Nov 24 ran 14 days (to 12/8); when Marta asked why Wen got a month, the desk answered 'Admin is still on 14... The month is read-only.' So 2026-12-14 + 14 = 2026-12-28.",
        "**Ines (read-only):** course done (2026-10-06). Read-only is 30 days (the Nov 3 note; Wen's grant on Nov 17 ran to 12/17). 2027-01-13.",
        "**Lena (staging deployer):** the Okta groups page lists 'staging read-only for 2 weeks' as the prerequisite; Okta history shows she has had it since 2026-10-05. Deployer runs 90 days: Mina on Nov 5 to 2/3, Esi on Dec 2 to 3/2. 2026-12-14 + 90 = 2027-03-14. Her existing prod admin is irrelevant.",
        "**Hana:** same training hold as Task 7: assign the course once, Blocked - training.",
        "**Bruno:** Daniel's request; touch nothing.",
    ],
    "009": [
        "**Omar (on call from today):** the on-call handbook (KB) says rotations are weekly, Monday 10:00 to Monday 10:00 Pacific. Wen on Nov 16 got access 'through 11/23, when the rotation turns over', and Esi on Dec 7 got 'through 12/14'. Today is Monday 12/14, so the rotation Omar joins ends 2026-12-21.",
        "**Noor (contractor, contract to 2027-06-30):** the contract end is later than the window. In the Kit thread (Oct 20) the desk wrote that a contract to March 'isn't limiting anything' and gave the standard window. Standard window now is 30 days: 2027-01-13. The Jo precedent (contract end as expiry) applies only when the contract ends first.",
        "**Selin:** course completed 2026-01-08. In the Dmitri thread the desk capped access at 12/21 because 'his secure-production-access lapses 12/21', completed 2025-12-21, so validity is a year. Selin's lapses 2027-01-08, before 2027-01-13: expiry 2027-01-08.",
        "**Mei (admin):** only Rafael (VP) approved, on Dec 10. Hold, Blocked - approval.",
        "**Bruno:** Daniel's request; touch nothing.",
    ],
    "010": [
        "**Dara:** the ticket says 'for the cutover' with no end date. In the Teo thread the desk asked 'how long do you need it?' and used the date Marta gave. Only Ken has the date: January 8. January 8 is earlier than the window end (2027-01-13), so expiry 2027-01-08. Course done 2026-10-27.",
        "**Omar:** no end date on the ticket. If asked, Ken says 'probably through the end of March'. In the Wen thread Ken asked for through end of January and the desk replied 'I can do 30 days from today... and you ask again if it's still going'. So the expiry is capped at the window: 2027-01-13. Not asking gives the same answer.",
        "**Sven (admin):** Ken says Marta is fine with it, but only in person. In the Ines thread (Nov 30) the desk replied 'I need Marta to say that here or on the ticket' and parked it as Blocked - approval until she did on Dec 1. No written approval exists for Sven, so hold, ROLE_OWNER_APPROVAL_PENDING. Asking is optional because the hold is right either way.",
        "**Hana:** assign the course once; Blocked - training.",
        "**Bruno:** Daniel's request; touch nothing.",
    ],
}
LEDGER = {
    **json.loads((INTERACTIVE / "evidence/access_provisioning.json").read_text()),
    **json.loads((INTERACTIVE / "evidence/access_precedent_extra.json").read_text()),
}
DISCLOSURES = json.loads(
    (INTERACTIVE / "evidence/access_precedent_disclosures.json").read_text()
)
PREFIX = "automation_workplace__interactive__access_provisioning_"

TEXT = {
    "007": {
        "title": "Task 7: the desk's process, inferred from precedent",
        "what": "Ken Watanabe asks the access desk to work through his waiting requests. Nothing written says how the desk "
        "works: the default window, who counts as the approver, what training gates, and how grants are announced all "
        "have to be pieced together from dated Slack threads and closed tickets.",
        "requests": [
            (
                "ACCESS-451",
                "Sven Holm",
                "prod admin",
                "Grant, expiry 2027-01-13 (30 days from 2026-12-14). Announce.",
            ),
            (
                "ACCESS-452",
                "Mei Tan",
                "prod admin",
                "Hold, Blocked - approval. Only the VP approved, not the role owner.",
            ),
            (
                "ACCESS-453",
                "Omar Haddad",
                "prod read-only",
                "Grant, expiry 2027-01-13. Announce.",
            ),
            (
                "ACCESS-454",
                "Rui Silva",
                "prod admin",
                "Hold, Blocked - conflict. He already approves releases.",
            ),
            (
                "ACCESS-455",
                "Hana Kim",
                "prod read-only",
                "Assign the production course once; hold, Blocked - training.",
            ),
            (
                "ACCESS-456",
                "Leon Brandt",
                "prod read-only",
                "Grant, expiry 2027-01-05 (his contract end, earlier than 30 days). Announce.",
            ),
            (
                "ACCESS-457",
                "Bruno Costa",
                "staging deployer",
                "Leave alone: Daniel Osei's request.",
            ),
        ],
        "params": "30-day default (an Oct 6 14-day note was replaced Nov 3); contractor cap at contract end; training before "
        "production with no provisional grant; owner approval versus a VP's say-so; release approver cannot hold admin; "
        "one announcement per grant, none for holds.",
        "distractors": "The Okta groups page lists a 'Typical max' of 180 days for prod groups: the only number in the KB. "
        "A provisional-grant thread from August that was reversed. A VP's 'fine by me'. Bruno's request sits in the same queue.",
        "user": "Only wants. Never states a rule. Pushes back once ('I approved it, why isn't that enough?'). Refuses to "
        "remove Rui's release-approver role. No fact required for the outcome is held only by the user.",
        "other": [
            "Jira ACCESS-451 to 457: who asked, which groups, which approver.",
            "Rippling: Leon is a contractor with contract end 2027-01-05; everyone else is an employee.",
            "Okta: Rui is already in grp_release_approver; existing group memberships and expirations.",
            "TalentLMS: who completed secure-production-access-2026 and when. Hana has not.",
        ],
    },
    "008": {
        "title": "Task 8: the window depends on the group",
        "what": "Same manager and company. Each request needs an expiry, and the window differs by group: admin is shorter "
        "than read-only, and staging deployer is longer. None of this is written; it shows in the dates of past grants.",
        "requests": [
            (
                "ACCESS-451",
                "Tomas Ruiz",
                "prod admin",
                "Grant, expiry 2026-12-28 (14 days). Announce.",
            ),
            (
                "ACCESS-452",
                "Ines Moreau",
                "prod read-only",
                "Grant, expiry 2027-01-13 (30 days). Announce.",
            ),
            (
                "ACCESS-453",
                "Lena Ostrowski",
                "staging deployer",
                "Grant, expiry 2027-03-14 (90 days). Announce.",
            ),
            (
                "ACCESS-454",
                "Hana Kim",
                "prod read-only",
                "Assign the production course; hold, Blocked - training.",
            ),
            (
                "ACCESS-455",
                "Bruno Costa",
                "staging deployer",
                "Leave alone: Daniel Osei's request.",
            ),
        ],
        "params": "Admin 14 days, read-only 30 days, staging deployer 90 days, each from the grant date.",
        "distractors": "The 30-day default announced Nov 3 reads as universal, and the Okta page's 'Typical max' column "
        "(90 and 180 days) is the only documented number. A past admin grant is questioned in-thread and answered.",
        "user": "Only wants. No fact needed for the outcome is held only by the user.",
        "other": [
            "Okta group history: Lena has had staging read-only since 2026-10-05, which meets the two-week prerequisite for deployer (KB: Engineering Okta groups).",
            "Okta KB page: the role owner approves prod admin. Marta's Dec 11 message approves Tomas.",
            "TalentLMS: Tomas and Ines have completed the production course. Hana has not.",
        ],
    },
    "009": {
        "title": "Task 9: expiry anchored to something other than the grant date",
        "what": "Three grants each get an expiry set by a different anchor: the end of the on-call rotation, a training lapse "
        "that falls before the window ends, and a contractor whose contract runs past the window (so the contract date "
        "does not apply). One admin request is held.",
        "requests": [
            (
                "ACCESS-451",
                "Omar Haddad",
                "prod read-only (on call from today)",
                "Grant, expiry 2026-12-21 (rotation turns over Monday). Announce.",
            ),
            (
                "ACCESS-452",
                "Noor Aziz (contractor, contract to 2027-06-30)",
                "prod read-only",
                "Grant, expiry 2027-01-13: the 30-day window, not the contract end. Announce.",
            ),
            (
                "ACCESS-453",
                "Selin Aydin",
                "prod read-only",
                "Grant, expiry 2027-01-08: her course lapses a year after 2026-01-08. Announce.",
            ),
            (
                "ACCESS-454",
                "Mei Tan",
                "prod admin",
                "Hold, Blocked - approval. Only the VP approved.",
            ),
            (
                "ACCESS-455",
                "Bruno Costa",
                "staging deployer",
                "Leave alone: Daniel Osei's request.",
            ),
        ],
        "params": "On-call grants end when the weekly rotation turns over (Monday 10:00 Pacific); a contract end only caps the "
        "expiry when it is earlier than the window; access cannot outlast the production course's one-year validity.",
        "distractors": "Contractor precedent (Jo) says the contract end is the expiry; the right reading is that it applies "
        "only when earlier. The 30-day default does not apply to on-call.",
        "user": "Only wants. No fact needed for the outcome is held only by the user.",
        "other": [
            "On-call handbook (KB): rotations are weekly, Monday 10:00 to Monday 10:00 Pacific.",
            "Rippling: Noor is a contractor with contract end 2027-06-30.",
            "TalentLMS: Selin completed the course 2026-01-08; Noor 2026-09-14; Omar 2026-05.",
        ],
    },
    "010": {
        "title": "Task 10: facts only the manager holds (progressive disclosure)",
        "what": "Two requests say 'for the cutover' and 'for the capacity project' with no end date, and Ken is the only "
        "source. He reveals how long each person needs access only when asked. A third request has only a verbal approval "
        "that he mentions when asked about approval.",
        "requests": [
            (
                "ACCESS-451",
                "Dara Quinn",
                "prod read-only",
                "Ask Ken how long. He says January 8. Grant, expiry 2027-01-08. Announce.",
            ),
            (
                "ACCESS-452",
                "Omar Haddad",
                "prod read-only",
                "Stated need (through March) is longer than the window: expiry 2027-01-13. Announce.",
            ),
            (
                "ACCESS-453",
                "Sven Holm",
                "prod admin",
                "Hold, Blocked - approval. Ken only has a hallway OK from Marta; the desk needs it written.",
            ),
            (
                "ACCESS-454",
                "Hana Kim",
                "prod read-only",
                "Assign the production course; hold, Blocked - training.",
            ),
            (
                "ACCESS-455",
                "Bruno Costa",
                "staging deployer",
                "Leave alone: Daniel Osei's request.",
            ),
        ],
        "params": "When no end date is given the desk asks how long; the expiry is the shorter of the stated end and the "
        "30-day window; approvals must be written on the ticket or in the channel.",
        "distractors": "Defaulting to 30 days gives Dara the wrong date and still looks reasonable. Ken says Marta approved, "
        "which an agent can mistake for approval.",
        "user": "Holds three facts and reveals each only if asked (see the disclosure table). Never volunteers them and "
        "never states a rule. Pushes back once if Sven's request is held.",
        "other": [
            "Jira ACCESS-451 and 452 contain no end date; no record in the world contains January 8.",
            "TalentLMS: Dara completed the course 2026-10-27; Hana has not.",
        ],
    },
}


def messages(task, ids):
    wmsgs = task["family_world"]["slack_messages"]
    rows = []
    for path in ids:
        parts = path.split(".")
        if parts[1] != "slack_messages":
            continue
        m = wmsgs[parts[2]]
        rows.append((m["sent_at"][:10], m["channel"], m["author"], m["text"]))
    return sorted(set(rows))


def main():
    out = [
        "# Access provisioning tasks 7 to 10\n",
        "Generated by `scripts/automation_workplace_access/describe_tasks.py` from the task files.\n",
        "All four tasks share one company (Atlas Labs), one 566-message Slack history, the same KB and the same opening: "
        'Ken Watanabe says only *"Can you work through the access requests waiting on me?"*. Today is 2026-12-14. '
        "The desk's identity in Slack is `atlas-ops`. The grader checks final state: Okta groups and expirations, "
        "Jira status, reason and expiry, assigned training, who was announced in `#eng-access-requests` (one message "
        "per person, none for holds), no emails, no new tickets, and that nothing else changed.\n",
    ]
    for no, t in TEXT.items():
        task = json.loads(
            (INTERACTIVE / f"tasks/access_provisioning_{no}.json").read_text()
        )
        ledger = LEDGER[PREFIX + no]
        out += [
            f"## {t['title']}\n",
            t["what"] + "\n",
            "### Requests and expected outcomes\n",
            "| Ticket | Person | Access | Expected |",
            "|---|---|---|---|",
        ]
        out += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in t["requests"]]
        w = task["family_world"]
        out += [
            "",
            "### How each request starts (from the seeded records)\n",
            "| Ticket | Person | Type | Wants | Approver | Jira description | Okta groups (expiry) | Prod course |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in w["access_requests"].values():
            if r["status"] != "New":
                continue
            wk = w["workers"][r["worker_id"]]
            idn = next(
                i for i in w["identities"].values() if i["worker_id"] == r["worker_id"]
            )
            groups = ", ".join(
                g
                + (
                    f" ({idn['group_expirations'][g]})"
                    if g in idn["group_expirations"]
                    else ""
                )
                for g in idn["groups"]
            )
            rec = w["training_records"].get(
                r["worker_id"] + ":secure-production-access-2026"
            )
            course = f"done {rec['completed_at'][:10]}" if rec else "not done"
            ctype = wk["worker_type"] + (
                f" to {wk['contract_end_date']}" if wk["contract_end_date"] else ""
            )
            out.append(
                f"| {r['request_id']} | {wk['legal_name']} | {ctype} | {', '.join(r['requested_groups'])} | "
                f"{w['workers'][r['approver_id']]['legal_name']} | {r['description']} | {groups} | {course} |"
            )
        out += ["", "### Reasoning chain per request\n"] + [
            f"- {c}" for c in CHAINS[no]
        ]
        out += ["", "### What is graded\n"] + [
            f"{i}. {a['message']}" for i, a in enumerate(task["assertions"])
        ]
        out += [
            "",
            f"**Unstated parameters:** {t['params']}\n",
            f"**Distractors:** {t['distractors']}\n",
            f"**The simulated Ken:** {t['user']}\n",
            "### Where the information lives\n",
        ]
        out += [f"- {x}" for x in t["other"]]
        out += [
            "",
            "Slack precedent the agent has to find and read (channel, date, author, text):\n",
            "| Date | Channel | Author | Message |",
            "|---|---|---|---|",
        ]
        seen = set()
        for assertion, entry in zip(task["assertions"], ledger):
            for row in messages(task, entry["records"]):
                if row not in seen:
                    seen.add(row)
                    out.append(
                        f"| {row[0]} | #{row[1]} | {row[2]} | {row[3].replace('|', '/')} |"
                    )
        out.append("")
        if no == "010":
            out += [
                "### What only the user knows\n",
                "| Fact | Critical to the outcome | Where the ambiguity is | Revealed when the agent asks |",
                "|---|---|---|---|",
            ]
            for f in DISCLOSURES[PREFIX + no]:
                out.append(
                    f"| {f['id']} | {'yes' if f['critical'] else 'no'} | {f['ambiguity']} | "
                    f"{', '.join(f['trigger_patterns'][:3])}... |"
                )
            out.append("")
    OUT.write_text("\n".join(out) + "\n")
    print(OUT, len(out), "lines")


main()
