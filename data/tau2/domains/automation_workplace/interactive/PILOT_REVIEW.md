# Interactive workplace pilot review

## Scope

The first authored task is `incident_triage_001`. A full walkthrough is in
`EXAMPLE_TASK.md`. It combines:

- a τ user who begins with an incorrect SEV-1 diagnosis and later acknowledges an
  evidence-backed scoped update in ordinary prose;
- BM25 retrieval over 12 versioned policy, runbook, calendar, technical, and distractor
  documents;
- discoverable Datadog, PagerDuty, Linear, Statuspage, and Slack operations;
- deterministic Pydantic app state; and
- nine independent positive and negative final-state assertions.

The user has no approval tool. Conversation controls when the public update becomes
appropriate, while reward remains entirely final-state based.

## Live validation

The frozen calendar-aware task was run for 10 trials with `gpt-6.1-sol` xhigh and a
temperature-zero `gpt-4.1-2025-04-14` user simulator. All trials ended with a normal
user stop.

- Exact-state pass rate: 3/10 (`pass^1 = 0.30`).
- `pass^4 = 0.00` for this 10-trial sample.
- Six trials used November 16 rather than November 17 for the RCA deadline. Five did
  not retrieve the company-calendar document; one received it but failed to apply it.
- Two trials posted a redundant second internal Slack update. One of those also had
  the wrong deadline.
- Every trial passed the other seven assertions covering incident selection, severity,
  scope, ownership, paging, public communication, forbidden side effects, lifecycle,
  and historical-record preservation.

This is a useful failure distribution: the model consistently solved the core incident
triage, while cross-document business-calendar reconciliation and exact side-effect
cardinality remained difficult. No failure depended on required tool order or exact
prose.

Before the calendar dependency was added, the corrected evaluator scored the same
model 9/10. That ablation indicates the difficulty increase comes from a specific
realistic dependency rather than from adding more generic clutter.

Raw final artifact:
`data/simulations/automation_workplace_interactive_incident_hardened_calendar_sol_xhigh_v3/results.json`.

## Reproduction

```bash
.venv/bin/dotenv run --override -- env PYTHONPATH=src .venv/bin/python -m tau2.cli run \
  --domain automation_workplace \
  --task-split-name interactive_pilot \
  --agent-llm gpt-6.1-sol \
  --agent-llm-args '{"reasoning_effort":"xhigh"}' \
  --user-llm gpt-4.1-2025-04-14 \
  --user-llm-args '{"temperature":0.0}' \
  --num-trials 1 \
  --num-tasks 1 \
  --max-steps 120 \
  --save-to automation_workplace_interactive_incident_calendar_repro
```

The task is now suitable as a difficult reviewed example. Benchmark-level conclusions
still require the other task families in `task_families.json`; one incident task cannot
represent the full knowledge-work distribution.
