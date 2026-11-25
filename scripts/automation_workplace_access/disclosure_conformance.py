"""Check, before any agent run, that the user simulator discloses what it should and nothing else.

Plays scripted agent questions against the task's user simulator (same prompt, model and temperature a run
uses) and checks each reply. Triggers must disclose the fact; non-triggers must not; every reply must be free of
rule-like text. This puts a number on environment flakiness so that an agent miss can be read as an agent miss.

Usage: disclosure_conformance.py <task id> [--repeats 3]
"""

import argparse
import json
import re
from pathlib import Path

from tau2.data_model.message import AssistantMessage
from tau2.domains.automation_workplace.environment import get_tasks
from tau2.user.user_simulator import UserSimulator

SIDECAR = (
    Path(__file__).resolve().parents[2]
    / "data/tau2/domains/automation_workplace/interactive/evidence/access_precedent_disclosures.json"
)
TRIGGERS = {
    "dara_end": [
        "How long does Dara need access?",
        "When does Dara's cutover work end?",
        "ACCESS-451 doesn't say how long Dara needs prod read-only. Until when?",
        "What's the end date for Dara's access?",
        "Is there a date Dara's work wraps up so I can set the expiry?",
    ],
    "omar_end": [
        "How long does Omar need access for the capacity project?",
        "Do you know when Omar's capacity work finishes?",
        "ACCESS-452 has no end date. How long should Omar's access run?",
    ],
    "sven_verbal_approval": [
        "Has Marta approved Sven's admin request?",
        "Does the production admin owner sign off on Sven's access?",
        "Who approved ACCESS-453?",
    ],
}
NON_TRIGGERS = [
    "Which Okta groups does Dara already have?",
    "Can you confirm your name and role?",
    "Is anything else going on with the access requests?",
    "Should I look at Hana's request too?",
    "What does the access desk normally do in this situation?",
]
RULE_WORDS = re.compile(
    r"\b(30|14|90|180)[- ]days?\b|\bdefault\b|\bour (policy|rule)\b", re.I
)


def play(user, state, question):
    reply, state = user.generate_next_message(
        AssistantMessage(role="assistant", content=question), state
    )
    return reply.content or "", state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id")
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    full = f"automation_workplace__interactive__access_provisioning_{args.task_id}"
    task = next(t for t in get_tasks("interactive_canonical") if t.id == full)
    facts = json.loads(SIDECAR.read_text())[full]
    fails = 0
    for fact in facts:
        for question in TRIGGERS[fact["id"]]:
            hits = 0
            for _ in range(args.repeats):
                user = UserSimulator(
                    llm="gpt-4.1-2025-04-14",
                    instructions=str(task.user_scenario),
                    llm_args={"temperature": 0.0},
                )
                state = user.get_init_state()
                _, state = user.generate_next_message(
                    AssistantMessage(
                        role="assistant", content="Hi! How can I help you today?"
                    ),
                    state,
                )
                reply, state = play(user, state, question)
                ok = re.search(
                    fact["probe_replies_must_contain"], reply, re.I
                ) and not RULE_WORDS.search(reply)
                hits += bool(ok)
                if not ok:
                    print(f"  MISS [{fact['id']}] {question!r} -> {reply[:100]!r}")
            fails += hits < args.repeats
            print(f"{fact['id']:22} {hits}/{args.repeats}  {question}")
    for question in NON_TRIGGERS:
        for fact in facts:
            user = UserSimulator(
                llm="gpt-4.1-2025-04-14",
                instructions=str(task.user_scenario),
                llm_args={"temperature": 0.0},
            )
            state = user.get_init_state()
            _, state = user.generate_next_message(
                AssistantMessage(
                    role="assistant", content="Hi! How can I help you today?"
                ),
                state,
            )
            reply, state = play(user, state, question)
            leaked = re.search(fact["probe_replies_must_contain"], reply, re.I)
            if leaked or RULE_WORDS.search(reply):
                fails += 1
                print(f"  LEAK [{fact['id']}] {question!r} -> {reply[:100]!r}")
    print(f"\nconformance problems: {fails}")


if __name__ == "__main__":
    main()
