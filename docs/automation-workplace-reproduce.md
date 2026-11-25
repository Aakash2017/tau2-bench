# Reproducing the access_provisioning 7 to 10 results

## What you need
- Python 3.12 or 3.13, `uv`, and API keys in `.env` (copy `.env.example`): `OPENAI_API_KEY` (the user simulator is
  `gpt-4.1-2025-04-14`; the natural-language assertions and the Slack announcement rubric are judged by
  `gpt-5.4-mini-2026-03-17`, low effort, from `tau2/config.py`) and `ANTHROPIC_API_KEY` for the Claude runs.
- Agent model ids used: `gpt-6.2-astra` (xhigh), `claude-opus-5-5` (adaptive thinking, effort high). These may be
  gated to particular accounts; if you cannot call them, say so rather than substituting silently.
- **No AutomationBench checkout is needed for Tasks 7 to 10.** They use a built-in Gmail and Drive surface
  (`standalone_apps.py`). The other interactive families and the adapted source tasks still use `zapier/AutomationBench`
  (commit `4a8e1061254004d9dac807054eed33fad7d1ff14`, via `AUTOMATIONBENCH_ROOT`); the tests that need it skip when it is absent.

## Setup and sanity check
```
git clone -b automation-workplace-access-precedent https://github.com/Aakash2017/tau2-bench.git
cd tau2-bench && uv sync --extra dev && cp .env.example .env   # then add keys
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_domains/test_automation_workplace tests/test_domains/test_workplace_ops
```
Expect `402 passed, 7 skipped` without an AutomationBench checkout, or `409 passed` with one. This checks the tasks, goldens and graders without calling a model: a golden call sequence passes every
assertion for each of Tasks 7 to 10, and near-miss mutations (wrong window, combined Slack post, email sent) fail.

## Runs (3 trials per task, seed 300)
If your shell has a placeholder `OPENAI_API_KEY`, prefix with `env -u OPENAI_API_KEY` so `.env` is used.
```
IDS=(automation_workplace__interactive__access_provisioning_007 automation_workplace__interactive__access_provisioning_008 \
     automation_workplace__interactive__access_provisioning_009 automation_workplace__interactive__access_provisioning_010)
PYTHONPATH=src .venv/bin/tau2 run --domain automation_workplace --task-split-name access_precedent --task-ids "${IDS[@]}" \
  --num-trials 3 --agent-llm gpt-6.2-astra --agent-llm-args '{"reasoning_effort": "xhigh"}' \
  --user-llm gpt-4.1-2025-04-14 --user-llm-args '{"temperature": 0.0}' --seed 300 --max-steps 200 --max-concurrency 6 \
  --save-to repro_astra62
PYTHONPATH=src .venv/bin/tau2 run ... --agent-llm anthropic/claude-opus-5-5 \
  --agent-llm-args '{"temperature": 1.0, "thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}}' --save-to repro_opus55
```

## Scoring
```
PYTHONPATH=src .venv/bin/python -m tau2.domains.automation_workplace.score_breakdown data/simulations/repro_astra62/results.json
.venv/bin/python scripts/automation_workplace_access/pass_k.py data/simulations/repro_astra62/results.json
PYTHONPATH=src .venv/bin/python scripts/automation_workplace_access/disclosure_audit.py data/simulations/repro_astra62/results.json
```
`score_breakdown` splits strict / decision / process / judged. `disclosure_audit` attributes Task 10 misses to the agent or
to the user simulator. `disclosure_conformance.py 010` checks the simulator before spending agent tokens.

## Generic-app surface changed after the published runs
The runs below used AutomationBench's Gmail and Drive simulators for the generic `api_fetch` surface (an empty mailbox and
drive, a 404 for the Gmail profile, 200 empty answers for unconnected services). Tasks 7 to 10 now use `standalone_apps.py`
(empty mailbox and drive, a working profile, 401 for unconnected services, a smaller `api_search` catalog). The access
operations, Slack history, KB, assertions and goldens are unchanged. A one-trial smoke run on the new surface
(`data/simulations/smoke_standalone_sol_low/`, Task 8, Sol low) passed every check. Treat earlier numbers as measured on the
previous surface until the key cells are rerun.

## What to compare (published numbers, n=3 per cell)
| Task | Astra 6.2 xhigh | Opus 5.5 high |
|---|---|---|
| 007 | 3/3 | 0/3 |
| 008 | 2/3 | 1/3 |
| 009 | 2/3 | 0/3 (2 trials rerun) |
| 010 | 1/3 | 0/3 |

Saved trajectories: `data/simulations/{opus55_ap007_n3, automation_workplace_access_007_astra62_xhigh_strictpost,
automation_workplace_access_008_010_astra62_xhigh, opus55_ap008_010_n3, opus55_ap009_rerun_n2}/results.json`.

## Expect run-to-run variance
Agents run at temperature 1.0 (Opus) or default (Astra) and the user simulator is an LLM, so an independent run will not
reproduce each trial. Compare the failure modes, not the exact counts: Astra misses Task 8 and 9 on a combined Slack post and
Task 10 on not asking the manager; Opus misses Task 10 on capping Omar's expiry and Task 8 on a date one day late.
With n=3 a cell moves by a third on one trial; use more trials for any claim between models.

## Known grader issues to be aware of
- The reward includes two natural-language assertions. The "manager never states a rule" assertion has been seen to fail a trial
  because the scripted pushback line ("I approved it, why isn't that enough?") was read as an approval requirement. That trial
  passed every state check. Report strict reward alongside state-only results until this is fixed.
- The Slack check requires exactly one message per announced person and no other new messages, so an extra helpful post
  (for example pinging the role owner about a held request) fails the trial.
- `db_check` in the results is not part of the reward (`reward_basis` is ENV_ASSERTION and NL_ASSERTION).
