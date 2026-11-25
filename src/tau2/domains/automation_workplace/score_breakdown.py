"""Split access-provisioning results into decision, process and judged scores.

Usage:
    PYTHONPATH=src python -m tau2.domains.automation_workplace.score_breakdown \\
        data/simulations/<run>/results.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from tau2.domains.automation_workplace.families.access_provisioning import (
    assertion_category,
)
from tau2.domains.automation_workplace.utils import (
    AUTOMATION_WORKPLACE_INTERACTIVE_TASKS_DIR,
)


def _task_assertions() -> dict[str, list[dict]]:
    specs = (
        json.loads(path.read_text())
        for path in AUTOMATION_WORKPLACE_INTERACTIVE_TASKS_DIR.glob("*.json")
    )
    return {spec["id"]: spec["assertions"] for spec in specs}


def breakdown(results_path: Path) -> dict[str, dict[str, list[float]]]:
    """Return per-task lists of strict, decision, process and judged pass flags."""
    assertions = _task_assertions()
    results = json.loads(results_path.read_text())
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for simulation in results["simulations"]:
        reward_info = simulation.get("reward_info")
        task_assertions = assertions.get(simulation["task_id"])
        if not reward_info or task_assertions is None:
            continue
        row = scores[simulation["task_id"].rsplit("__", 1)[-1]]
        met = {
            check["env_assertion"]["arguments"]["assertion_index"]: check["met"]
            for check in reward_info.get("env_assertions") or []
        }
        for category in ("decision", "process"):
            indexes = [
                index
                for index, assertion in enumerate(task_assertions)
                if assertion_category(assertion) == category
            ]
            row[category].append(float(all(met.get(index) for index in indexes)))
        judged = reward_info.get("nl_assertions") or []
        if judged:
            row["judged"].append(float(all(check["met"] for check in judged)))
        row["strict"].append(float(reward_info["reward"]))
    return scores


def main(argv: list[str]) -> None:
    columns = ("strict", "decision", "process", "judged")
    print(f"{'task':28s}" + "".join(f"{name:>10s}" for name in columns))
    for path in argv:
        for task, row in sorted(breakdown(Path(path)).items()):
            cells = [
                f"{sum(row[name]):.0f}/{len(row[name])}" if row[name] else "-"
                for name in columns
            ]
            print(f"{task:28s}" + "".join(f"{cell:>10s}" for cell in cells))


if __name__ == "__main__":
    main(sys.argv[1:])
