"""pass^k and pass@k per task from tau2 results files (strict reward = 1.0), unbiased estimators.

Usage: pass_k.py <results.json> [<results.json> ...]   (trials of the same task across files are pooled)
Trials without a reward (infrastructure errors) are excluded and reported.
"""

import json
import sys
from math import comb

per, lost = {}, {}
for path in sys.argv[1:]:
    for sim in json.load(open(path))["simulations"]:
        task = sim["task_id"].rsplit("_", 1)[-1]
        if sim["reward_info"] is None:
            lost[task] = lost.get(task, 0) + 1
            continue
        per.setdefault(task, []).append(int(sim["reward_info"]["reward"] >= 1.0))

for task, wins in sorted(per.items()):
    n, c = len(wins), sum(wins)
    cells = [
        f"k={k}: pass^k {comb(c, k) / comb(n, k):.2f} pass@k {1 - comb(n - c, k) / comb(n, k):.2f}"
        for k in (1, 2, 3)
        if k <= n
    ]
    note = f"  ({lost[task]} infra errors excluded)" if task in lost else ""
    print(f"{task}: {c}/{n}  " + "  ".join(cells) + note)
