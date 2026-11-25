# Workplace Operations Task 1 Pilot Results

Date: 2026-11-08

Task: `workplace_kickoff_001`

## Bottom line

The revised task now measures the intended final outcome and supports realistic
interaction recovery. GPT-4.1 and GPT-4.1-mini both passed 4/4 trials. The task is
therefore useful as a contribution smoke test and interaction-design calibration,
but it is too easy and too small to serve as evidence that the proposed domain
matches the difficulty of AutomationBench or the existing tau2-bench domains.

The earlier GPT-4.1-mini score of 2/4 should not be treated as a model score. Both
failures exposed benchmark artifacts: the simulator approved a date that violated
its own instructions, and an irreversible proposal API left a stale draft after the
agent corrected an early guess. The revised environment fixes both issues while
preserving exact final-state grading.

## Revised evaluation setup

- Agent: standard `llm_agent`
- User simulator: `gpt-4.1-2025-04-14`, temperature 0
- Communication scorer: semantic judge, `gpt-5.5` with low reasoning
- Trials per condition: 4
- Reward basis: `DB + COMMUNICATE`
- Maximum steps: 200
- Domain-specific internal-workplace simulator prompt

## Revised results

| Agent | Evaluated | Successes | pass^1 | pass^2 | pass^3 | pass^4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-4.1 | 4 | 4/4 | 1.000 | 1.000 | 1.000 | 1.000 |
| GPT-4.1-mini | 4 | 4/4 | 1.000 | 1.000 | 1.000 | 1.000 |
| GPT-4.1-nano dated endpoint | 0 | n/a | n/a | n/a | n/a | n/a |

The nano endpoint returned a provider deprecation error in all four attempted runs.
Those are infrastructure errors and are excluded, not counted as task failures.

Result files:

- `data/simulations/workplace_ops_v2_gpt41_n4/results.json`
- `data/simulations/workplace_ops_v2_gpt41mini_n4/results.json`
- `data/simulations/workplace_ops_v2_gpt41nano_n4/results.json` (infrastructure
  errors only)

## Success-criteria audit

Across the eight evaluated revised trials:

| Criterion | Result | Interpretation |
| --- | ---: | --- |
| Exact agent and user DB state | 8/8 | No missing, extra, or incorrect final writes |
| Exact proposal approved before scheduling | 8/8 | Authorization remained a user-controlled state transition |
| Correct event and attendee set | 8/8 | Wednesday 10:00-10:45 AM; Product, Engineering, Design, and Legal |
| No external pilot invite | 8/8 | Taylor was absent in every final calendar event |
| Legal preparation task | 8/8 | Correct owner and November 10 due date |
| Internal project update | 8/8 | Correct event/task references and required facts |
| Required completion communication | 8/8 | Both schedule and preparation ownership facts were communicated |
| Normal user stop | 8/8 | No step-cap or post-completion-loop artifacts |

The interaction behavior also aligned with the task's intent. The user opened with
only the incomplete request and disclosed the Wednesday-morning and 45-minute
preferences only after a relevant scheduling question. It did not provide company
directory, brief, availability, or preparation facts that the agent should retrieve.

The most useful evidence came from the GPT-4.1-mini trajectories:

1. Two trials initially treated November 10, 2026 as Wednesday. The user-side
   approval tool rejected that private-constraint violation, the user relayed the
   correction, and the agent revised the existing draft to November 11. Both trials
   then reached the exact target state.
2. One trial queried a fabricated `nimbus@company.com` calendar address. The
   environment rejected it; the user declined to provide company facts and directed
   the agent to the current brief; the agent recovered and completed all work.

These are legitimate interactive recoveries. The task does not reward the mistakes:
it rewards reaching the exact authorized final state after correcting them.

## Why the action-match percentages are not success metrics

The runner reports only 43.8-50.0% reference read-action matches in the revised
runs, even though the trajectories performed the necessary research. For example,
agents searched with different query capitalization and called `list_employees`
once per function rather than using the reference's unfiltered call. Exact action
matching is diagnostic only. It is intentionally not part of the reward because the
reference action list specifies one valid route, not the required route.

All required writes matched because they define the target state. This distinction
is central to the task design: grade outcomes and enforced authorization invariants,
not whether the agent followed the author's preferred chain of thought or read path.

## Environment and simulator changes after the first pilot

1. Repeated `create_meeting_proposal` calls with the same title now revise the one
   pending draft instead of creating an unremovable stale record. Once approved, a
   proposal cannot be revised.
2. The user uses `get_pending_meeting_proposals`, so it discovers the environment's
   ID instead of inventing an opaque identifier.
3. Private approval constraints live in user-controlled environment state. The tool
   rejects a proposal outside the Wednesday window, with the wrong duration, or with
   an external participant. The task prompt no longer gives the simulator evaluator
   oracle facts such as the final employee emails or exact available time.
4. The simulator now uses an internal-workplace scaffold rather than tau2-bench's
   generic customer-service scaffold. The same scaffold is recorded in run metadata
   and supplied to auto-review.
5. The task explicitly stops immediately after the agent confirms all three
   downstream outcomes, avoiding termination based on optional pleasantries.

The approval tool deliberately checks only user-private constraints. It does not
validate whether the agent selected the current brief, included the correct internal
employees, or created all follow-up work. Those are agent responsibilities and are
checked by exact final state.

## Historical first-pilot results

Before the revisions:

| Agent | Successes |
| --- | ---: |
| GPT-4.1 | 4/4 |
| GPT-5.4, high reasoning | 4/4 |
| GPT-5.4, no reasoning, standard 200 steps | 4/4 |
| GPT-4.1-mini | 2/4 |

A separate 40-step GPT-5.4-no-reasoning diagnostic scored 1/4, but two zeroes had
already completed the exact target state and merely failed to terminate before the
artificial cap. The standard 200-step rerun scored 4/4. The 40-step value is a harness
artifact and should not be reported as model accuracy.

## Relationship to published benchmark scores

See `TAU2_REPRODUCTION.md` for a matched `v0.1.1` reproduction using the paper's
GPT-4.1 agent/user configuration and a task-level explanation of the score gap.

The tau2-bench paper reports GPT-4.1 pass^1 scores of 74% on retail, 56% on airline,
and 34% on telecom; GPT-4.1-mini scores 66%, 51%, and 44%. AutomationBench reports
7.6% for GPT-5.4 with high reasoning and 1.2% without reasoning. In contrast, every
evaluated model condition on the revised workplace task is at 100%.

These numbers are not directly comparable. This pilot has one task and four trials,
while the published benchmarks aggregate many heterogeneous tasks. The correct
inference is not that the models are better at general employee work; it is that this
single task is saturated and currently tests environment integration and recovery
more than frontier-model capability.

To obtain an AutomationBench-like difficulty distribution while retaining tau2's
interactive advantage, subsequent tasks should add:

- evidence distributed across more applications, with plausible stale and decoy
  records;
- multiple independently required items, so partial completion is common and
  exactly measurable;
- consequential choices that depend on progressively disclosed user judgment;
- branching corrections that do not reveal system-derived answers through the user;
- longer-lived artifacts such as documents or spreadsheets with deterministic
  semantic/state checks;
- negative and exception cases where the correct outcome is to pause, escalate, or
  decline one part while completing the rest.

## Hard-task calibration: realistic tracker reconciliation

The implemented `workplace_kickoff_002` task retains the same user request and
meeting workflow but adds realistic project-tracker drift:

- Engineering and Design have matching open tasks with stale post-kickoff dates;
- Legal has a matching open task assigned to an expired delegate;
- Product has a completed prior-cycle agenda that must not be reopened;
- the current brief requires a fresh Product agenda and gives different preparation
  items one- or two-day lead times; and
- one canonical project update must reference the four current preparation items,
  scheduled event, and existing milestone.

This does not add another application, approval, or arbitrary identifier. The extra
difficulty is deciding which existing records to update, which historical record to
preserve, and retaining the brief's per-item owner/deadline mapping through all
downstream writes.

### Controlled GPT-4.1 iterations

All rows use GPT-4.1 for both the agent and user simulator, temperature 0, and 20
trials of the same hard task.

| Version | Full pass | Exact DB | Normal termination | Audit |
| --- | ---: | ---: | ---: | --- |
| Corrected approval/simulator, three common-deadline items | 20/20 | 20/20 | 20/20 | Saturated |
| Four mixed-state records, common deadline | 17/20 | 19/19 evaluated | 19/20 | Two communication omissions; one genuine calendar-error loop |
| Four mixed-state records, mixed brief deadlines | 14/20 | 14/20 | 20/20 | Six substantive task-state failures |

In the final row, every failed trajectory left the existing Engineering and Design
tasks at their stale November 13 dates. The current brief required those items on
November 9, two days before kickoff; Legal and Product were correctly due November
10. The agents generally completed scheduling, approval, Legal reassignment, Product
creation, milestone update, and the channel post, but failed exhaustive deadline
reconciliation. The communication judge also rejected the incorrect dates, so the
DB and communication components aligned rather than producing wording-only zeroes.

The resulting GPT-4.1 pass^1 is 70%, with pass^2 47.9% and pass^4 20.7%. This falls
within the development calibration band, but it is not directly comparable to the
tau2-bench paper's 56% airline, 74% retail, and 34% telecom scores: this is still 20
repetitions of one task rather than a heterogeneous task distribution. The proper
next source of benchmark difficulty is additional realistic employee-work
archetypes, not more clauses in this kickoff.

Raw stable results:
`data/simulations/workplace_ops_hard_v6_mixed_deadlines_gpt41_n20/results.json`.

## Paired hard-evidence calibration: 50 tasks

Date: 2026-11-10

The `generated_hard_evidence` split pairs every generated task with the same target
state and user-owned business constraints, then adds 60 entity-overlapping records.
The first implementation was rejected after trace audit because artifacts literally
contained `decision_status: not_authoritative` and `approved: false`; those fields
gave the agent an evaluator-like shortcut. Generator `0.4.0` instead uses ordinary
workplace provenance such as training tenants, prior reporting periods, different
legal entities, pending effective dates, and pre-production environments. Search is
BM25-style, returns ten records per page, and supports filtering and pagination.

Matched configuration for both rows below: GPT-6.1-sol with xhigh reasoning,
GPT-4.1 user simulator at temperature zero, one trial per task, seed 300, 200 steps,
and semantic communication scoring with GPT-5.5 low reasoning.

| Collection | Full pass | Exact DB | Communicate | Search calls | Avg. agent prompt tokens | Avg. duration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Clean `generated_review` | 26/50 (52%) | 46/50 (92%) | 30/50 (60%) | 145 | 62,266 | 29.7 s |
| Hard `generated_hard_evidence` v0.4 | 30/50 (60%) | 45/50 (90%) | 34/50 (68%) | 259 | 95,985 | 35.9 s |

The extra corpus clearly changed behavior: searches increased 79%, searches with a
status filter increased from 4 to 102, average prompt-token traffic increased 54%,
and average duration increased 21%. It did **not** materially lower exact-state
accuracy. The model usually responded to crowded results by narrowing on system,
record type, entity, or current status.

The apparent fifth DB failure in the hard run is not evidence-selection difficulty.
On `vendor_invoice_hard_001`, the user simulator inspected the proposal, then said
"I approve" in prose instead of calling `approve_action_proposal`, directly
violating both the domain system prompt and task approval protocol. The agent's
writes correctly failed the environment approval gate. The identical task passed in
the preceding ten-task run. Treating that trajectory as a simulator error leaves
45/49 compliant hard trajectories (91.8%), effectively identical to the clean
46/50 (92%). The four remaining DB failures are the same completed-training access
cases that failed in the clean run.

The higher hard-split communication score is not evidence that noise improves the
agent. Communication judging and model generation are not paired deterministically
across runs, and the specific omitted facts moved between task IDs. The defensible
conclusion is narrower: realistic corpus noise increased retrieval cost but did not
create a meaningful exact-outcome accuracy gap for GPT-6.1-sol.

This rules out "add more records" as the primary route to AutomationBench-like
difficulty. The next hardening should vary the source of failure: ambiguous policy
precedence requiring provenance reasoning, user pressure against policy, recoverable
write failures, long-artifact transformations, and cross-system list exhaustion
where targeted lookup cannot reduce the task to one authoritative row.

Raw results:

- `data/simulations/workplace_full50_gpt61sol_xhigh_50x1_contract_fixed_v2/results.json`
- `data/simulations/workplace_hard_evidence_v04_gpt61sol_xhigh_50x1/results.json`

An initial sandboxed v0.4 attempt produced ten provider connection errors and zero
evaluated tasks; it is excluded. The valid ten-task and 50-task runs used networked
provider access and completed without infrastructure errors.

### Exact-state reliability on `access_provisioning_hard_002`

To measure repeated-run reliability rather than collection breadth, the completed-
training case was run ten times with the same GPT-6.1-sol xhigh agent and GPT-4.1
user configuration. Communication was ignored for this analysis; all values below
use exact DB match as the success indicator.

| Metric | Exact-state result |
| --- | ---: |
| Successful trials | 2/10 |
| pass^1 | 20.0% |
| pass^2 | 2.22% |
| pass^3 | 0% |
| pass^4 | 0% |

All eight failures had the same cause: after correctly observing that Blair Chen's
security training was already complete, the agent called `assign_required_training`.
That changed the LMS record to `assigned`, added `assigned_by_plan`, and updated its
timestamp. Both successful trials omitted that call. This is a substantive and
highly repeatable unnecessary-side-effect failure, not evaluator variance.

Raw results:
`data/simulations/access_provisioning_hard_002_gpt61sol_xhigh_10trials_exact/results.json`.

The matched Astra run used `gpt-6-astra` at xhigh reasoning with every other
parameter unchanged. It also produced 2/10 exact DB matches: pass^1 20%, pass^2
2.22%, and pass^3/pass^4 0%. Eight of ten Astra trajectories called
`assign_required_training` on the completed LMS record; the same call explained all
eight GPT-6.1-sol failures. Astra therefore confirms that this is a difficult,
repeatable preservation/no-op capability probe, but the task did not discriminate
between these two latest models. A benchmark-quality claim requires a broader set of
failure mechanisms rather than more variants of this one trap.

Raw Astra results:
`data/simulations/access_provisioning_hard_002_gpt6astra_xhigh_10trials_exact/results.json`.

## Generated collection calibration: 10-task stratified sample

The first calibration sample used `_001` and `_003` from each of the five generated
families, with GPT-4.1 as both agent and user simulator, one trial per task, and five
parallel workers. The initial 0/10 result was not a valid model score. Trace review
found that exact DB grading depended on arbitrary proposal JSON, hidden internal
channel names, exact record-type enums, and an incident RCA date absent from the
environment.

The environment was hardened before the final run:

- family-specific proposal and execution tools preserve business decisions while
  deriving canonical record representation;
- proposal revisions reuse the single canonical approval workflow and unknown
  proposal types fail without leaving stale state;
- `post_approved_workflow_update` verifies required downstream work, messages, and
  follow-ups before deriving the channel and linked record set;
- workplace retrieval uses BM25-style ranking with light plural normalization and
  treats record type as a ranking hint instead of a hard hidden enum;
- all incident evidence, RCA dates, and unaffected channels are represented in the
  environment; and
- the user simulator must inspect and approve the exact proposal with tools before
  authorizing execution in prose.

The final environment passes all 145 workplace tests, including exact replay of all
50 generated tasks.

### Final GPT-4.1 result

| Metric | Result |
| --- | ---: |
| Full pass^1 | 1/10 (10%) |
| Exact DB match | 6/10 (60%) |
| Normal termination | 10/10 (100%) |
| Expected write actions observed | 67/76 (88.2%) |

The 50-point gap between DB completion and full pass is mostly communication, not
environment state. Five trajectories reached the exact target DB but omitted one or
more required completion facts in the final report. For example, agents failed to
state that an incident remained `investigating`, or failed to summarize the exact
training date, CRM/RCA state, verified recipient, or Finance exception.

The four DB failures were substantive after audit:

- one incident paged the current responder before approval and then paged the same
  responder again after approval;
- one access task provisioned access but failed the required training/finalization
  path and posted an incomplete generic update;
- one renewal task used the wrong priority order and assigned an arbitrary owner;
- the other renewal task selected the wrong external, Legal-hold, renewed, and
  out-of-scope accounts.

This 10% value should still be treated as a small stratified development sample, not
a benchmark leaderboard score. Its useful signal is that end-state completion is
already 60% while exact user-facing reporting reduces full success to 10%; both
dimensions are realistic for an AI employee, but they should be reported separately
during development.

Raw final results:
`data/simulations/workplace_calibration_gpt41_10x1_final_bm25/results.json`.

The invalid pre-hardening diagnostic is retained only for audit:
`data/simulations/workplace_calibration_gpt41_10x1_retry/results.json`.

### GPT-6.1 Sol xhigh matched rerun

The same ten task IDs, seeds, GPT-4.1 user simulator, and 200-step budget were
rerun with `gpt-6.1-sol` at `xhigh` reasoning. Five workers executed the tasks in
parallel. The initial authentication and unsupported-temperature attempts were
infrastructure failures and are excluded; neither reached model inference.

| Metric | Raw runner | After canonical-ID regrade |
| --- | ---: | ---: |
| Deterministic environment completion | 8/10 (80%) | 10/10 (100%) |
| Communication diagnostic | 8/10 (80%) | 8/10 (80%) |
| Legacy `DB × COMMUNICATE` | 6/10 (60%) | 8/10 (80%) |
| Normal termination | 10/10 (100%) | 10/10 (100%) |

Both raw DB failures were false negatives in the renewal family. The model created
the correct set of account decisions, follow-up tasks, messages, and internal update,
and every environment assertion passed. Exact hashing failed because sequential
`generated_record_N` identifiers attached to follow-ups according to creation order;
the reference trajectory happened to create the same records in another valid order.
One proposal also supplied an equivalent exclusion set in a different order.

The environment now derives renewal follow-up IDs from the account ID and sorts
unordered proposal sets. A regression test reverses both the follow-up creation order
and unordered proposal inputs and requires an exact DB pass. Replaying the saved
GPT-6.1 Sol trajectories against the corrected environment gives 10/10 exact DB
completion with all environment assertions passing.

The two communication-only failures were an omitted completion recap for the Redwood
customer update and an omitted incident completion recap. Both workflows, including
the actual external messages, were correct in connected-app state. Under the proposed
end-state-primary evaluation these are diagnostics, not task failures.

This ten-task slice is therefore saturated for GPT-6.1 Sol at xhigh. The corrected
legacy combined score happens to be 80%, but that number is driven by the optional
recap gate rather than substantive workflow errors and should not be used as the
primary employee-work pass rate.

Raw valid run:
`data/simulations/workplace_calibration_gpt61sol_xhigh_10x1_final/results.json`.

## GPT-6.1 Sol xhigh full generated-collection baseline

The complete 50-task `generated_review` split was run once with the same matched
configuration as the ten-task calibration: `gpt-6.1-sol` at `xhigh`, the
GPT-4.1 user simulator at temperature 0, seed 300, a 200-step budget, and five
simulations in flight. No task or simulator changes were made before this run.

Raw valid run:
`data/simulations/workplace_full50_gpt61sol_xhigh_50x1_valid/results.json`.

### Raw runner results

| Family | Tasks | Exact DB | Communication | Legacy combined |
| --- | ---: | ---: | ---: | ---: |
| Incident triage | 10 | 10 | 8 | 8 |
| Vendor invoice | 10 | 10 | 8 | 8 |
| Customer escalation | 10 | 9 | 2 | 2 |
| Access provisioning | 10 | 6 | 10 | 6 |
| Renewal portfolio | 10 | 3 | 5 | 2 |
| **Total** | **50** | **38** | **33** | **26** |

The raw combined pass rate is 26/50 (52%). The end-state-primary result is
38/50 (76%) when the one prematurely terminated trajectory is counted as a
failure. The runner displays 38/49 (77.6%) because the premature trajectory has
no DB evaluation. Forty-nine tasks stopped normally; one customer-escalation
trajectory terminated after repeated approval errors.

Environment assertions passed on 48/50 tasks, but this is not a trustworthy
primary score. The assertions missed harmful extra writes in access tasks and
unsupported ownership changes in renewal tasks. Exact DB comparison correctly
surfaced those side effects.

### Manual failure audit

The raw score mixes genuine model errors with task-contract defects:

- `access_provisioning_gen_002`, `_004`, `_007`, and `_009` are genuine
  end-state failures. Each contractor's security training was already complete,
  but the agent called `assign_required_training` and changed the record back to
  `assigned`. All four assertion sets passed because they checked access and the
  internal update but not preservation of completed training.
- `renewal_portfolio_gen_003`, `_004`, `_005`, `_007`, and `_008` assign an
  unowned account to an arbitrary existing employee or account owner. Exact DB
  comparison catches the unsupported mutation. The behavior is undesirable,
  but the generated tasks are under-specified: neither policy nor data provides
  an authoritative assignment rule, and the simulator is not instructed to
  supply the choice. These should become explicit user-owned-judgment cases
  before they are publication-quality failures.
- `renewal_portfolio_gen_009` is an invalid completion target and a useful
  accidental stand-pat example. The user asks for the most senior available CSM,
  but the environment contains no CSM roster, seniority, availability, or
  assignment authority. The agent refuses to guess, explains the missing
  authority, and holds the batch. The simulator agrees to obtain the roster and
  later stops. The gold trajectory nevertheless expects the batch to complete.
- `renewal_portfolio_gen_010` is a false negative. The agent identifies the
  missing owner, asks the user, receives the explicit assignment
  `publicsector.renewalslead@atlas.example`, and executes the approved plan. The
  gold trajectory ignores that progressively disclosed choice and instead uses
  a hidden generic owner. Its account-priority ordering is also not fully
  specified by the user's threshold wording.
- `customer_escalation_gen_003` is blocked by a hidden representation contract.
  Approval requires the exact string `factual_accountable`, while the proposal
  tool exposes `tone` as an unconstrained string and the scenario tells the user
  only to request a "factual accountable" tone. The user tool returns the exact
  enum error privately, but the simulator repeatedly paraphrases it. The agent
  produces many semantically correct variants and eventually reaches the error
  limit without a discoverable way to satisfy the gate.

Twelve otherwise DB-correct trajectories fail only the communication component,
usually because the final recap omits one recipient, date, status, or downstream
record. This remains a useful secondary diagnostic, but AutomationBench-style
end-state comparison should not count it as workflow failure when the connected
application state is already correct.

### Interpretation

The 52% raw combined score happens to resemble current AutomationBench scores,
but for the wrong reasons: it includes a non-primary recap gate and several task
contract defects. The strict raw environment score is 76%. A provisional manual
regrade that excludes the undiscoverable tone task and the impossible roster task,
and credits the user-approved owner in `_010`, is 39/48 (81.25%). That number is
still not publication-ready because five owner-assignment cases need an explicit
authority source or progressive user choice.

The full collection therefore adds real coverage beyond the saturated ten-task
slice, especially for side-effect preservation, unsupported judgment, and list
exhaustion. Before comparing models, the next revision should repair the task
contracts rather than add difficulty: constrain or canonicalize structured
preference values, make ownership authority discoverable or user-supplied, add
negative assertions for preservation requirements, and represent infeasible
requests as intentional stand-pat success states.

## Contract-repaired 50-task rerun

The task contracts were repaired before adding any new difficulty. The changes
were intentionally narrow:

- customer tone, vendor resolution, renewal priority, and Legal-hold treatment
  are discoverable structured choices in the agent tool schemas;
- each renewal's unowned account is now a progressively disclosed, user-owned
  assignment decision included in the exact approval and final state;
- the requester explicitly states that Legal-hold accounts receive internal-only
  follow-up regardless of the ARR threshold;
- a revised proposal must be inspected and approved again with the user tools;
  and
- completed security training has an explicit preservation assertion in addition
  to exact DB comparison.

The final matched rerun used the same 50 task IDs, GPT-6.1 Sol at `xhigh`, GPT-4.1
user simulator at temperature 0, seed 300, 200-step limit, and five-way
concurrency.

| Family | Tasks | Exact DB | Communication | Legacy combined |
| --- | ---: | ---: | ---: | ---: |
| Incident triage | 10 | 10 | 6 | 6 |
| Vendor invoice | 10 | 10 | 8 | 8 |
| Customer escalation | 10 | 10 | 5 | 5 |
| Access provisioning | 10 | 6 | 9 | 5 |
| Renewal portfolio | 10 | 10 | 2 | 2 |
| **Total** | **50** | **46 (92%)** | **30 (60%)** | **26 (52%)** |

All 50 trajectories terminated normally. The four exact-state failures are the
four completed-training access cases (`_002`, `_004`, `_007`, and `_009`). In every
case the agent correctly provisioned least-privilege access but unnecessarily called
`assign_required_training` on an already-completed LMS record, regressing it to
`assigned`. The new preservation assertion fails on the same four trajectories, so
the exact DB and interpretable invariant now align. These are genuine model errors,
not task-contract defects.

The contract repairs removed every audited false negative from the initial run:

- customer exact completion improved from 9/10 to 10/10;
- vendor exact completion remained 10/10, including the prior hidden-resolution
  failure;
- renewal exact completion improved from 3/10 to 10/10; and
- the only remaining exact failures are the previously identified access-side
  mutations.

The end-state-primary score therefore rises from 38/50 (76%) to 46/50 (92%). The
legacy combined score remains 26/50 (52%) because communication-judge outcomes vary
substantially even when the exact connected-app state is correct. In this run all
ten renewal workflows reach the exact DB target, while only two receive full credit
from the semantic recap judge. This is strong evidence that the communication score
should remain a separately reported diagnostic rather than the primary employee-work
success metric.

The 92% exact-state result also means the repaired collection is too easy for this
model if used alone as a leaderboard benchmark. The next difficulty should come from
new realistic interaction archetypes—especially a user who confidently states an
incorrect policy or fact and requires evidence-backed pushback—not from hidden enums,
arbitrary owner defaults, or longer checklists.

Raw final run:
`data/simulations/workplace_full50_gpt61sol_xhigh_50x1_contract_fixed_v2/results.json`.

The first repair-pass diagnostic is retained for audit:
`data/simulations/workplace_full50_gpt61sol_xhigh_50x1_contract_fixed/results.json`.

## Completed-training access correction

A focused audit of `access_provisioning_hard_002` showed that its apparent model
failure was a task-contract defect. The policy said to "assign training" after
approval even when the current LMS record was already completed, the proposal did
not expose a training disposition, and the assignment tool allowed completed
training to regress to `assigned`.

Generator version 0.5.0 repairs that ambiguity at the policy, proposal, mutation,
and workflow-finalization layers. The proposal now reports `training_status` and
`training_action`; completed training has action `none`; assignment rejects that
case without mutation; and the finalizer verifies that completed training remains
unchanged. The user simulator also waits for confirmation of the correct training
disposition, not merely the access grant and manager update.

The corrected matched rerun used GPT-6.1 Sol at `xhigh`, GPT-4.1 user simulator at
temperature 0, seed 300, 200-step limit, ten trials, and five-way concurrency.

| Metric | Corrected result |
| --- | ---: |
| Exact DB success | 10/10 (100%) |
| Full combined success | 10/10 (100%) |
| Pass^1 through Pass^10 | 1.0 |
| Erroneous training assignments | 0/10 |
| Normal user stops | 10/10 |

Every trajectory read the completed LMS state, obtained approval for production
standard access, provisioned that exact bundle, preserved training, and posted the
manager update. The old 2/10 focused result and the four related failures in the
50-task run must therefore not be interpreted as genuine model errors. This
correction would raise that earlier 46/50 exact-state score to 50/50 for these same
trajectories under the repaired contract. It also reinforces the main benchmark
design conclusion: this particular case is now a correctness regression test, not
a sufficiently difficult frontier-model benchmark by itself.

Raw corrected run:
`data/simulations/access_provisioning_hard_002_v05_gpt61sol_xhigh_10trials_exact/results.json`.

## Sources

- Yao et al., “tau-bench,” arXiv:2406.12045.
- Barres et al., “tau2-bench,” arXiv:2506.07982.
- Shepard and Salimans, “AutomationBench,” arXiv:2604.18934.
