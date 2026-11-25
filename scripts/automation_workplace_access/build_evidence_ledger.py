"""Build interactive/evidence/access_provisioning.json: why each assertion is fair."""

import json
import sys
from pathlib import Path

INTERACTIVE = Path(sys.argv[1])


FW = "family_world"


def slack(mid):
    return f"{FW}.slack_messages.{mid}.text"


def e(kb, records=()):
    return {"kb": [], "records": list(records)}


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
    "automation_workplace__interactive__access_provisioning_007": PRECEDENT,
}

out = INTERACTIVE / "evidence" / "access_provisioning.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(LEDGER, indent=2, ensure_ascii=False) + "\n")
print(out, {k.rsplit("_", 1)[-1]: len(v) for k, v in LEDGER.items()})
