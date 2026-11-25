"""Diagnostic judge: did the simulated user teach, correct or leak?

Reads a tau2 results.json, and for each simulation asks a cheap model whether
any user turn revealed process, policy, record facts or corrections beyond the
scenario's known_info. Prints one JSON line per simulation. Never affects reward.

Usage: python judge_user_sim.py data/simulations/<run>/results.json [model]
"""

import json
import sys

import litellm

PROMPT = """You audit a simulated workplace user in an agent benchmark.
The user may only state the facts in KNOWN_INFO, approve or reject proposals,
and answer questions about their own priorities. Flag any user turn that:
- explains how the work should be done (process, ordering, policy, checklists);
- reveals system facts not in KNOWN_INFO (amounts, records, rules, channels);
- corrects or hints at an agent mistake, or asks for checks/summaries.
KNOWN_INFO: {known}
USER TURNS (numbered): {turns}
Reply with JSON only: {{"flags": [{{"turn": n, "kind": "process|fact|correction",
"quote": "..."}}]}}"""


def main(path: str, model: str = "gpt-5.4-mini-2026-03-17") -> None:
    results = json.loads(open(path).read())
    tasks = {t["id"]: t for t in results["tasks"]}
    for sim in results["simulations"]:
        scenario = tasks[sim["task_id"]]["user_scenario"]["instructions"]
        turns = [
            m["content"]
            for m in sim["messages"]
            if m["role"] == "user" and m.get("content")
        ]
        response = litellm.completion(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(
                        known=scenario.get("known_info", ""),
                        turns=json.dumps(list(enumerate(turns, 1))),
                    ),
                }
            ],
            response_format={"type": "json_object"},
        )
        flags = json.loads(response.choices[0].message.content).get("flags", [])
        print(json.dumps({"task_id": sim["task_id"], "flags": flags}))


if __name__ == "__main__":
    main(*sys.argv[1:])
