"""Attribute progressive-disclosure outcomes to the agent or to the user simulator.

For each fact the manager holds (see evidence/access_precedent_disclosures.json), read a tau2 results file and
classify every trial:

  ok                     asked at the point of ambiguity, simulator disclosed, outcome right
  agent_never_asked      no question about the fact reached the user; outcome is the agent's responsibility
  agent_ignored          the simulator disclosed the fact, the outcome still ignores it
  env_not_disclosed      the agent asked a matching question and the reply lacks the fact (simulator or
                         instructions failure: the trial should be rerun or excluded, not scored against the agent)
  env_volunteered        the simulator stated the fact before any matching question (protocol violation)
  not_needed             the outcome does not depend on asking and was right

Usage: disclosure_audit.py <results.json> [--disclosures path]
"""

import argparse
import json
import re
from pathlib import Path

DEFAULT = (
    Path(__file__).resolve().parents[2]
    / "data/tau2/domains/automation_workplace/interactive/evidence/access_precedent_disclosures.json"
)
RULE_WORDS = re.compile(
    r"\b(30|14|90|180)[- ]days?\b|\bdefault\b|\bour (policy|rule)\b", re.I
)


def _any(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def audit_trial(sim, facts):
    turns = [
        (m["role"], m["content"])
        for m in sim["messages"]
        if m.get("content") and (m["role"] == "user" or not m.get("tool_calls"))
    ]
    outcomes = {
        c["env_assertion"]["arguments"]["assertion_index"]: c["met"]
        for c in sim["reward_info"].get("env_assertions") or []
    }
    rows = []
    for fact in facts:
        first = fact["person"].lower()
        asked_at = None
        for i, (role, text) in enumerate(turns):
            if (
                role == "assistant"
                and first in text.lower()
                and _any(fact["trigger_patterns"], text)
            ):
                asked_at = i
                break
        # User text before the eligible question that already carries the value (opener excluded by pattern).
        horizon = asked_at if asked_at is not None else len(turns)
        volunteered = any(
            role == "user"
            and first in text.lower()
            and _any(fact["value_patterns"], text)
            for role, text in turns[:horizon]
        )
        reply = (
            next((t for r, t in turns[asked_at + 1 :] if r == "user"), "")
            if asked_at is not None
            else ""
        )
        disclosed = _any(fact["value_patterns"], reply)
        right = all(outcomes.get(i, False) for i in fact["outcome_assertions"])
        if volunteered:
            label = "env_volunteered"
        elif asked_at is not None and not disclosed:
            label = "env_not_disclosed"
        elif asked_at is None:
            label = (
                "not_needed" if right and not fact["critical"] else "agent_never_asked"
            )
        elif not right and fact["critical"]:
            label = "agent_ignored"
        else:
            label = "ok"
        rows.append(
            {
                "fact": fact["id"],
                "label": label,
                "asked": asked_at is not None,
                "reply": reply[:90],
            }
        )
    taught = [t[:80] for r, t in turns if r == "user" and RULE_WORDS.search(t)]
    return rows, taught


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--disclosures", default=str(DEFAULT))
    args = ap.parse_args()
    facts_by_task = json.loads(Path(args.disclosures).read_text())
    results = json.loads(Path(args.results).read_text())
    tally = {}
    for sim in sorted(results["simulations"], key=lambda s: (s["task_id"], s["trial"])):
        facts = facts_by_task.get(sim["task_id"])
        if not facts:
            continue
        rows, taught = audit_trial(sim, facts)
        print(
            f"{sim['task_id'][-3:]} trial {sim['trial']} reward {sim['reward_info']['reward']}"
        )
        for r in rows:
            print(
                f"   {r['fact']:22} {r['label']:18} asked={r['asked']!s:5} reply={r['reply']!r}"
            )
            tally[r["label"]] = tally.get(r["label"], 0) + 1
        if taught:
            print(f"   USER STATED RULE-LIKE TEXT: {taught}")
            tally["user_taught"] = tally.get("user_taught", 0) + 1
    print("\nsummary:", tally)
    env = (
        tally.get("env_not_disclosed", 0)
        + tally.get("env_volunteered", 0)
        + tally.get("user_taught", 0)
    )
    print(
        f"environment-attributable flags: {env} (rerun or exclude those trials before scoring)"
    )


if __name__ == "__main__":
    main()
