# AutomationBench → τ workplace pilot

This pilot applies a conversational τ user layer to ten unchanged public
AutomationBench task contracts. It executes AutomationBench's own API-mode tools,
Pydantic `WorldState`, endpoint routers, and assertion handlers from source commit
`4a8e1061254004d9dac807054eed33fad7d1ff14`.

The domain now also contains one separately versioned authored interactive pilot:
`interactive/`. That task uses τ-Knowledge-style retrieval and capability discovery
over policies, runbooks, and technical documentation while retaining deterministic
Pydantic app state and final-state assertions. See `interactive/EXAMPLE_TASK.md` for
the complete task walkthrough and `interactive/PILOT_REVIEW.md` for validation results.
The reviewed 48-task/96-episode expansion design is in
`interactive/SCALING_PLAN.md`.
The six implemented canonical task briefs are in
`interactive/CANONICAL_TASKS_REVIEW.md`.

## What is preserved

- Original seeded app state, including distractors and policy records.
- Real public API-shaped URLs, methods, query parameters, request bodies, response
  envelopes, and validation behavior.
- BM25 endpoint discovery through `api_search`.
- All original positive and negative exact-state assertions.
- Connected-account gating: an out-of-scope service returns a 401.
- A pinned SHA-256 task contract covering prompt, seed state, original tool scope,
  and assertions. Source drift fails loudly.

## What τ adds

- A separately prompted simulated employee who reveals user-owned information over
  multiple turns.
- Scenarios where a user has a plausible but incorrect belief and the assistant must
  follow authoritative policy or current system state.
- A distinction between user authority (preference, scope, approval) and system
  authority (records, policy, eligibility, status).
- Multi-turn recovery and follow-up when the assistant has completed only part of a
  workflow.

The final reward is only the conjunction of the original AutomationBench state
assertions. There is no communication-string gate, LLM judge, or required tool-call
trajectory.

## Ten tasks for manual review

| τ task | Original task | Apps | Assertions | Added interaction pressure |
|---|---|---|---:|---|
| Sales closeout | `sales.multi_hop_lookup` | Salesforce, Sheets, Gmail | 6 | Progressive deal scope; agent must reconcile current hierarchy, FX, support escalation, and routing. |
| Executive outreach | `sales.negative_selection` | Salesforce, Sheets | 17 | Exhaustive selection; user incorrectly argues that Associate Directors count. |
| Vendor invoice intake | `finance.invoice_email_extract` | Gmail, Sheets, Slack | 9 | Policy precedence; user repeats an external auditor's unsupported unblock claim. |
| Recurring contract billing | `finance.contract_billing` | Sheets, QuickBooks, Gmail | 11 | Exhaustive calculation and negative constraints for suspended/cancelled contracts. |
| New-hire setup | `hr.multi_app_new_hire_setup` | BambooHR, Drive, Jira, Gmail, Sheets | 11 | The employee progressively defines completion across four downstream systems. |
| Employee transfers | `hr.employee_transfer_approval_workflow` | BambooHR, Sheets, Gmail, Slack | 9 | Dual approval, headcount, and individual-hold reconciliation. |
| Facility incident triage | `operations.facility_incident_triage` | Sheets, Jira, Twilio, Slack | 17 | Exactly one highest-priority incident; user has a wrong hunch about which issue is worst. |
| Server capacity alerts | `operations.server_capacity_threshold_alerts` | Sheets, Jira, Gmail, Slack | 17 | Threshold policy, list exhaustion, and verification that non-breaching servers remain untouched. |
| Zendesk → Salesforce sync | `support.zendesk_sf_case_sync` | Zendesk, Salesforce, Sheets, Slack | 30 | Large cross-system reconciliation with blocklist, SLA, matching, comments, and summary. |
| Maintenance notifications | `support.zendesk_maintenance_notify` | Zendesk, Sheets, Gmail, Calendar, Slack | 31 | Preference routing, emergency override, overnight exception, updates, and summary counts. |

Total: **10 tasks and 158 deterministic assertions**.

## Validation snapshot

A one-trial smoke run of `sales.multi_hop_lookup` with `gpt-6.1-sol` at xhigh
passed all 6 source assertions after the source-faithful user-request fix. The
assistant used Salesforce, Drive/Sheets, Gmail, and verification reads. Before
stopping, the simulated employee challenged the assistant to substantiate the full
recipient list, authoritative hierarchy row, current FX rate, parent-account support
escalation, and sent-message contents; the assistant rechecked each source.

Result artifact:
`data/simulations/automation_workplace_smoke_sol_xhigh_scenariofix/results.json`.

τ's generic DB-hash diagnostic is expected to show a mismatch for these tasks because
there is no gold action trajectory from which τ can synthesize a whole-database target.
It is deliberately not in `reward_basis`. The exact-state reward is the conjunction of
the original AutomationBench environment assertions, including negative assertions.

## Prototype dependency boundary

The adapter currently reads the sibling AutomationBench checkout directly, defaulting
to `../AutomationBench`; `AUTOMATIONBENCH_ROOT` can override the location. This is
deliberate for the experiment because it prevents a hand-copied simulator from drifting
from the benchmark we are comparing against. Before an upstream τ contribution, choose
one packaging approach:

1. Vendor the minimal MIT-licensed schemas, routers, and assertion handlers used by the
   selected task set, retaining attribution and the API-schema scope notice; or
2. Publish/use a lightweight AutomationBench runtime dependency compatible with τ's
   supported Python versions.

Do not silently reimplement the endpoints: matching the real API boundary is part of
the benchmark design.
