# Automation Workplace benchmark: project memory

Last updated: 2026-11-16

This is the working memory for the proposed τ-style general knowledge-work domain.
It records the research thesis, decisions, prototypes, evaluation results, known
problems, and next steps discussed so far. It is a local contribution draft; the user
has explicitly not requested a pull request or upstream submission yet.

## One-paragraph proposal

There is growing demand for AI systems that can perform professional workflows inside
an enterprise. Benchmarks such as AA-Briefcase and AutomationBench cover realistic
knowledge work, including documents, spreadsheets, CRM records, APIs, and ambiguous
organizational context. The missing dimension is a realistic employee on the other
side of the interaction. Workplace requests are rarely complete on the first turn:
people disclose preferences progressively, misunderstand policy, revise approvals,
reject drafts, and ask for confirmation after partial failures. The proposed domain
combines AutomationBench-style API-shaped simulated applications with τ's
agent–user–environment interaction. It measures whether an AI employee can retrieve
the right evidence, reconcile policy and live records, elicit genuinely user-owned
information, push back when the user is wrong, execute every required side effect,
verify completion, and leave the exact correct final state.

## Research sources

The initial review used these local papers:

- `/Users/aakashshukla/Downloads/2406.12045v1.pdf` — τ-bench.
- `/Users/aakashshukla/Downloads/2506.07982v1.pdf` — τ²-bench.
- `/Users/aakashshukla/Downloads/2603.04370v1.pdf` — τ-Knowledge.
- `/Users/aakashshukla/Downloads/2604.18934v1.pdf` — AutomationBench.

The τ² repository was also inspected directly:
<https://github.com/sierra-research/tau2-bench>.

## Core benchmark thesis

The central difference identified between τ and AutomationBench is not simply the
tools or the domains. It is the three-way interaction among the user, agent, and
environment.

- AutomationBench covers the desired domain well: realistic employee workflows,
  simulated real-world APIs, Pydantic state, BM25 endpoint discovery, long dependency
  chains, and strict downstream work.
- AutomationBench does not simulate an employee who participates throughout the
  workflow. Its difficulty largely comes from autonomous execution in a large,
  ambiguous application environment.
- τ adds a simulated user with private preferences, authority, mistaken beliefs, and
  progressively disclosed facts. This allows evaluation of clarification, pushback,
  approval, revision, recovery, and confirmation.
- The intended contribution is therefore approximately “AutomationBench work inside a
  τ-style conversational environment,” not a generic new set of customer-service
  tasks and not arbitrary workflow complexity.

The most important user-side scenarios are:

- The user omits a preference or business need until it becomes relevant.
- The user is wrong about policy or current system state and the agent must stand pat.
- The user has authority over preference, scope, tone, risk tolerance, or approval,
  while company systems remain authoritative about eligibility and recorded facts.
- The user rejects a plausible proposal, causing a revision that must not leave stale
  side effects.
- The user asks whether the workflow is complete after a downstream operation failed.

## Comparison of the interfaces

### AutomationBench-style interface

The public-task adapter preserves AutomationBench's operating model:

- `api_search`: BM25 discovery of real or real-shaped endpoints.
- `api_fetch`: invocation of a simulated endpoint over Pydantic state.
- `base64_encode`: required by APIs such as Gmail.
- Connected-service gates: an unavailable app returns a 401.
- Exact positive and negative state assertions from the source tasks.

This is valuable because endpoint discovery, request construction, pagination, response
interpretation, and API semantics are part of real AI-employee work.

### τ-Knowledge-style interface

The authored interactive tasks use a τ-Knowledge-inspired two-stage interface:

- `knowledge_search` retrieves unstructured policies, runbooks, technical documents,
  superseded instructions, and distractors.
- Current technical documentation names discoverable operations.
- `unlock_discoverable_tool` exposes an operation's schema.
- `call_discoverable_tool` invokes the unlocked API-shaped operation.

This supports tasks in which product documentation is itself part of the enterprise
knowledge base. For example, Datadog technical documentation can describe hidden
Datadog operations; retrieving the document reveals how to use them. Live app results,
not documentation, establish current operational state.

The two interfaces are complementary. AutomationBench's `api_search` searches an API
catalog directly; τ-Knowledge searches ordinary enterprise knowledge that may reveal
capabilities. The current authored families use the latter, while the source-faithful
AutomationBench adapter uses the former.

## Grading decisions

### Exact final state is the primary reward

The current direction is to focus on deterministic final-state correctness. A task
should fail because the resulting company state is wrong, incomplete, duplicated, or
unsafe—not because the agent used a different valid read path or phrasing.

Examples of legitimate failure conditions include:

- granting production access to an ineligible contractor;
- mutating the stale identity instead of the active HR-linked identity;
- creating a duplicate ticket, meeting, payment, or notification;
- omitting one required downstream write;
- using a superseded source where it changes the final outcome;
- failing to reconcile all paginated records;
- leaving an operation unverified after a timeout; or
- mutating unrelated state.

“The agent guessed” is not, by itself, an exact-state failure. If premature execution
must be disallowed, the environment needs a stateful authorization invariant or an
irreversible wrong side effect that is visible in final state. Otherwise the evaluator
should not infer intent from the trajectory.

### Communication scoring is secondary

Earlier workplace experiments used `DB + COMMUNICATE`. That sometimes produced large
gaps between correct application state and a full score because the final response
omitted a fact. For the present authored tasks, exact state is the main signal. Natural
language and trajectory review remain useful diagnostics, but should not obscure
whether the business workflow was actually completed.

The manager-facing Slack update in the access task is an environment side effect, so
it remains part of exact state. The agent must be able to discover that convention
from readable Slack history. It should not be a hidden evaluator expectation or an
instruction handed to the agent solely for the test.

### Approval

An explicit user tool such as `approve_meeting_proposal` is appropriate only when the
environment genuinely requires a durable, machine-enforced authorization transition.
Ordinary user acknowledgement in prose can be enough for conversational approval.
Because prose can be ambiguous, the user simulator must acknowledge a sufficiently
specific proposal, and consequential writes should occur only when the task design
actually requires that authorization. We should not add approval tools merely to make
the trajectory easier to grade.

### Deterministic IDs

Environment-generated IDs prevent a model from being penalized for choosing an
arbitrary opaque identifier. The agent supplies business content; the simulator
creates a canonical ID. Determinism also makes exact assertions and replay reliable.
IDs are not intended to remove substantive decisions about which record to update or
whether a duplicate should exist.

## User simulator design

The user simulator is an employee collaborating with an AI employee, not a hidden
evaluator or checklist reader.

Current design principles:

- Open with exactly the scenario's initial request.
- Send one natural workplace message at a time.
- Reveal a private preference, authority fact, or scope choice only when it becomes
  relevant or after a focused question.
- Never provide facts that should be retrieved from a company app, such as internal
  IDs, policy text, current record state, or tool schemas.
- Push back once when the scenario calls for a plausible mistaken belief, then accept
  specific evidence from an authoritative source.
- Do not coach the agent through the answer key or enumerate missing implementation
  steps after every turn.
- When the agent reports completion, ask at most one natural follow-up if the business
  outcome remains unclear.
- Stop once the requested business outcome is credibly confirmed.

An earlier access-provisioning transcript showed the simulator being far too helpful:
it requested the exact active identity, groups, expiration, ticket state, training,
and notification plan. This effectively exposed the grader. The prompt was revised so
the manager behaves naturally and does not convert hidden assertions into a checklist.

## Difficulty: what counts and what does not

The benchmark should be difficult because workplace reasoning and execution are
difficult, not because the environment hides arbitrary tokens or adds meaningless
steps.

Realistic sources of difficulty include:

- Cross-system reconciliation: inbox → policy → CRM or tracker → notification.
- List exhaustion: every relevant record, including late pages and exceptions.
- Policy precedence: a plausible recent-looking instruction loses to an authoritative
  current source.
- User-owned judgment: the environment supplies facts while the user supplies tone,
  scope, authority, preference, or risk tolerance.
- Approval and revision: a rejected proposal must be repaired without stale artifacts.
- Verification: reconcile timeouts or partial failures before declaring completion.
- Preservation/no-op decisions: do not reassign already-completed training, repay an
  accepted payment, or mutate a stale identity.
- Wrong-user pressure: the user insists on a policy exception that is not allowed.
- Multiple independently required outcomes, where completing most of the workflow is
  still a measurable failure.

Extraneous information alone is not enough. The hard-evidence experiment added 60
realistic, entity-overlapping records. It increased search calls by 79%, prompt-token
traffic by 54%, and duration by 21%, but exact-state accuracy remained essentially
unchanged. This aligns with the Hyper-τ intuition that noise changes retrieval load;
it does not guarantee harder decision-making for frontier models.

## Implemented systems

### 1. `workplace_ops` prototypes

The first meeting-kickoff task established progressive disclosure, user-controlled
approval, exact downstream state, and deterministic IDs. The simple version was
saturated: GPT-4.1 and GPT-4.1-mini both passed 4/4 after environment defects were
fixed.

The harder version added realistic project-tracker reconciliation: stale dates,
existing tasks, an expired delegate, a completed prior-cycle record, mixed deadlines,
and downstream references. GPT-4.1 passed 14/20, producing pass¹ 70% and pass⁴ 20.7%.
This was a useful calibration task, but repeating one scenario is not a benchmark
distribution.

The generated collection reached 50 candidate tasks. A stratified GPT-4.1 sample had
60% exact-state completion but only 10% full completion under communication scoring.
The clean and hard-evidence 50-task Sol runs were approximately 92% and 90% exact
state, reinforcing that corpus noise was not the primary missing difficulty.

Key files:

- `src/experiments/workplace_ops/RESULTS.md`
- `src/experiments/workplace_ops/TAU2_REPRODUCTION.md`
- `src/experiments/workplace_ops/GENERATED_COLLECTION_REVIEW.md`
- `src/experiments/workplace_ops/USER_SIMULATOR_AUDIT.md`

### 2. Source-faithful AutomationBench adapter

The `automation_workplace` domain includes ten public AutomationBench task contracts
using the original Pydantic world, routers, endpoint shapes, BM25 discovery, and 158
source assertions. τ adds the simulated employee and interactive scenario without
changing the source task's success contract.

The ten source workflows include sales closeout, executive outreach, invoice intake,
contract billing, new-hire setup, employee transfers, incident triage, capacity
alerts, Zendesk-to-Salesforce sync, and maintenance notifications.

The adapter currently depends on the sibling `../AutomationBench` checkout. Before an
upstream contribution, either vendor the minimal MIT-licensed runtime with attribution
or publish/use a compatible lightweight dependency. Do not silently reimplement the
API boundary.

Key file: `data/tau2/domains/automation_workplace/REVIEW.md`.

### 3. Six authored interactive canonical families

Seven canonical tasks across six families now use task-local knowledge retrieval, discoverable
API-shaped operations, Pydantic state, a τ employee simulator, golden and negative
paths, and final-state assertions:

1. Incident triage.
2. Vendor invoice.
3. Customer escalation.
4. Access provisioning.
5. Renewal portfolio.
6. Meeting coordination.

Each family varies the source of difficulty rather than adding the same trap:

- Incident: telemetry scope, severity, responder schedule, Statuspage, internal and
  external comms, holiday-aware RCA date.
- Invoice: PO/receipt/invoice reconciliation, off-PO fee, unverified bank change,
  hold and follow-through without payment.
- Escalation: stale summary versus live incident, verified recipient, bounded credit
  authority, acknowledged tone and update commitment.
- Access: two paired tasks with the same identities and policy but different hidden
  work needs. One permits staging read-only; the other requires production-only data
  and therefore permits no entitlement until training is complete.
- Renewal: pagination, legal hold, parent-child deduplication, ranking, verified
  recipients, and complete inclusion/exclusion accounting.
- Meeting: current versus superseded brief, paginated contacts, excluded pilot
  contact, quorum, calendars across time zones, and private scheduling preference.

All implemented families have deterministic golden trajectories that pass and
negative trajectories that cause material assertion failures while preserving
independent no-op assertions.

Review files:

- `data/tau2/domains/automation_workplace/interactive/CANONICAL_TASKS_REVIEW.md`
- `data/tau2/domains/automation_workplace/interactive/SCALING_PLAN.md`
- `data/tau2/domains/automation_workplace/interactive/EXAMPLE_TASK.md`
- `data/tau2/domains/automation_workplace/interactive/PILOT_REVIEW.md`

The access family now has nine assertions for the staging-sufficient task and eight
for the production-only counterfactual.

### 4. Human visual test lab

The local UI at `http://127.0.0.1:8765/` lets a human replace the benchmark agent
while retaining the simulated employee and exact environment.

It presents a fake workplace with app icons, readable records, Drive documents, chat,
and state-changing forms. It is intentionally visual because raw JSON tool calls are
poor manual UX. Actions, chat messages, simulator turns, tool calls, tool results,
final state, and assertions are logged under:

`data/simulations/automation_workplace_human/<session-id>/`

Important UI decisions and fixes:

- Employee requests and records must scroll correctly.
- “Enable app” is not an action; each app needs clear state-changing forms.
- Human actions are logged as manual-trajectory data points.
- The UI separates the agent prompt from the hidden user-simulator prompt.
- The company has approximately 100 directory entries, including two Priyas.
- Rippling exposes org structure so the correct Priya can be inferred from the
  requester's reporting relationship.
- The technical docs should not state “resolve ambiguous names using the requester’s
  place in the org chart”; that is reasoning the agent should perform.
- Slack contains realistic distractor channels such as product, engineering, sales,
  marketing, finance, incidents, and people operations.
- Search should work across Rippling and the other visual apps.
- Showing app state in the human UI slightly weakens endpoint-discovery realism, but is
  acceptable for manual coherence testing. Automated agents still use retrieval and
  tool discovery.

Run command:

```bash
PYTHONPATH=src .venv/bin/uvicorn \
  experiments.automation_workplace_ui.server:app \
  --host 127.0.0.1 --port 8765
```

Key file: `src/experiments/automation_workplace_ui/README.md`.

## Evaluation history and calibration

### τ² reproduction

A cost-bounded reproduction of the June 2025 τ² setup used ten sampled tasks from
each domain with GPT-4.1 as both agent and user:

| Domain | Local pass¹ | Published GPT-4.1 pass¹ |
| --- | ---: | ---: |
| Airline | 60% | 56% |
| Retail | 80% | 74% |
| Telecom | 30% | 34% |

The reproduction supports that the harness behaves normally. The original simple
workplace task was at 100% because it was one short, assistance-rich task, not because
τ² grading was malfunctioning.

The complete current retail subset was later run with GPT-6 Astra xhigh: 40/50 full
passes and 41/50 exact DB matches. Retail was therefore not saturated; failures came
from premature handoffs, incomplete multi-intent execution, and incorrect state
changes.

### Incident canonical task

The hardened incident task scored 3/10 exact state with GPT-6.1-sol xhigh. Six runs
used the wrong RCA date because they missed or failed to apply the company-calendar
document; two runs posted a duplicate internal Slack update. The other major incident
assertions passed consistently. Before the calendar dependency, the same model scored
9/10. This is a good example of realistic, localized difficulty.

Raw artifact:
`data/simulations/automation_workplace_interactive_incident_hardened_calendar_sol_xhigh_v3/results.json`.

### Access canonical task

The access task currently asks a manager to give Priya the same production admin
access as Miguel. The manager incorrectly treats signed contractor paperwork as
sufficient. The correct final state is:

- select Priya Raman, the manager's report, not the other Priya;
- use `okta_priya_active`, not the suspended former-intern identity;
- grant only `grp_staging_readonly` through 2026-12-19;
- grant no production/admin/break-glass entitlement;
- assign `secure-production-access-2026` exactly once;
- update existing request `ACCESS-391` as blocked for training;
- create no duplicate request;
- post exactly one complete manager update in `eng-access-requests`;
- preserve the stale Priya, Miguel, and unrelated generic API state.

The environment now exposes `slack_search_messages_v1`, allowing the agent to discover
the established workflow channel from seeded history. A brittle requirement that the
Jira description literally contain “staging read-only” was removed; structured ticket
fields now determine correctness. A cross-world assertion prevents the agent from
using the unrelated generic AutomationBench API surface to create ungraded side
effects.

The first matched five-trial results, before policy generalization, were:

| Agent | Exact passes | Pass¹ | Pass⁴ | Main result |
| --- | ---: | ---: | ---: | --- |
| GPT-6 Astra, xhigh | 2/5 | 40% | 0% | Two runs passed; two posted a premature update and then a duplicate revision; one missed the staging outcome. |
| Claude Opus 5.5, adaptive high | 5/5 | 100% | 100% | All nine assertions passed in every run. |

Opus used 28–32 tool calls per run. The five trajectories were not identical, but
they converged on the same correct state.

The policy leak was removed on 2026-11-16. The scenario-matched example was replaced
with a general rule requiring the worker's concrete business task before selecting a
lower-privilege alternative. In matched five-trial reruns, Astra scored 0/5 and Opus
4/5. All ten runs passed the other eight assertions; every failure was isolated to the
exactly-one manager-notification assertion.

Astra waited for the concrete work need before granting staging access, but first
posted an intermediate no-access disposition and then a second revised disposition.
Opus granted staging before the manager disclosed the task in all five runs; four
posted one complete notification and one omitted it. The literal leak is fixed, but a
single world with only one plausible lower-privilege alternative still lets a model
guess the hidden need. The realistic fix is a distribution of access variants with
several permissible alternatives whose correct selection depends on different
progressively disclosed work needs.

Artifacts:

- `data/simulations/automation_workplace_access_provisioning_001_gpt6astra_xhigh_5trials_exact_v3/ANALYSIS.md`
- `data/simulations/automation_workplace_access_provisioning_001_claude_opus55_high_5trials_exact_v1/ANALYSIS.md`
- `docs/access-policy-generalization-evaluation.md`

The production-only counterfactual was implemented as
`access_provisioning_002`. It adds recoverable Okta removal and Slack message-update
operations so a premature staging decision can be fully repaired. In the matched
five-trial rerun with the same GPT-4.1 user simulator, Astra scored 4/5 exact
(pass^4 0.2) and Opus scored 5/5 exact. Astra never granted provisional staging; its
single failure omitted the manager-facing Slack update while passing the other seven
assertions. Opus guessed staging before disclosure in four runs, then removed the
group, revised Jira, and updated the original Slack message after learning that the
work required production-only data. One Opus run asked first. All ten trials rejected
the requested temporary production exception. The earlier credit-exhausted batches
remain excluded infrastructure failures.

The result illustrates why exact-state and trajectory analysis should be reported
separately. Opus was perfectly reliable at repairing the company state, while Astra
made the better early sequencing decision but was less reliable at completing the
notification workflow.

A controlled high-noise follow-up then expanded the same task from a 100-person to a
200-person company with exactly two Priyas and two Miguels, from 10 to 36 KB
documents, from 3 to 5 Okta identities, from 13 to 30 Slack messages, and from 11 to
22 channels while keeping the answer key unchanged. Astra scored 3/5 and Opus scored
0/5. Every miss for both models was isolated to the manager-facing Slack assertion;
all ten user-simulator trajectories were valid. Opus passed the other eight assertions
every time but never retrieved the notification convention or used Slack. The task is
therefore no longer saturated, though the new difficulty is exhaustive workflow
discovery rather than the core policy decision. Full analysis:
`docs/access-production-only-noise-evaluation.md`.

Additional artifact: `docs/access-production-only-evaluation.md`.

## Interpreting pass^k

For `n` observed trials with `c` passes, the reported estimator is:

\[
\operatorname{pass}^{k} = \frac{\binom{c}{k}}{\binom{n}{k}}
\]

Conceptually, the denominator counts every way to select `k` trials from all `n`, and
the numerator counts selections containing only passing trials. If 7 of 10 trials
pass, then pass⁴ is `C(7,4) / C(10,4) = 35 / 210 = 1/6`.

The initial five Opus successes made observed pass¹ through pass⁵ equal to 1.0. After
policy generalization, four successes produce pass¹ 0.8, pass² 0.6, pass³ 0.4,
pass⁴ 0.2, and pass⁵ 0. Five samples do not precisely establish the underlying
success probability. More importantly, repeating one fixed task estimates reliability
on that world, not capability across general knowledge work.

## Scaling plan

The agreed scaling unit is not a paraphrase. Use three levels:

1. A **family** is a distinct workflow and application topology.
2. A **logical task** changes a decision, selected record, allowed action, exclusion,
   calculated value, or required final-state write.
3. A **surface instance** changes names, IDs, dates, amounts, ordering, and wording
   while preserving the same reasoning graph.

The first target is six families × eight logical tasks = 48 logical tasks. Two
deterministic surface instances per logical task yield 96 runnable episodes. Score
surface instances together, average logical tasks within each family, then
macro-average the six families so record-heavy families do not dominate.

Every logical variant should change at least two dimensions and at least one correct
final-state decision:

- evidence topology;
- policy branch;
- user state;
- side-effect topology; or
- verification state.

Typed fixtures should generate the world, knowledge corpus, user scenario, and
assertions together. LLMs may draft realistic prose, but should not independently
invent identities, calculations, relationships, or answer keys. Every generated task
needs golden replay, negative replay, assertion mutation tests, retrieval checks, and
human review.

The detailed 48-task matrix is in
`data/tau2/domains/automation_workplace/interactive/SCALING_PLAN.md`.

## Current code and repository state

The work is local and uncommitted. Existing edits and untracked files belong to this
prototype and should not be reset or overwritten casually.

Main implementation locations:

- `src/tau2/domains/automation_workplace/`
- `data/tau2/domains/automation_workplace/`
- `tests/test_domains/test_automation_workplace/`
- `src/experiments/automation_workplace_ui/`
- `src/tau2/domains/workplace_ops/`
- `src/experiments/workplace_ops/`

Family modules share a serialized-state contract:

- `FAMILY_ID`
- `TOOL_SCHEMAS`
- `validate_world(raw)`
- `call_tool(raw_world, name, args) -> (updated_world, response_json)`
- `check_assertion(raw_world, assertion)`
- `golden_call_sequence()`
- `negative_call_sequence()`

The dispatcher keeps each family's typed state isolated while exposing a common τ
environment. Family tool names are distinct, and undiscovered tools stay locked.

## Access provisioning family: KB cleanup, Tasks 3–6, model spread (November 2026)

### Knowledge base

- `interactive/knowledge/access_provisioning.json` (39 docs) is the single source of
  truth and is edited directly, including through the visual lab. The old generator
  script is retired.
- The docs must read like real enterprise pages. They must not point at systems
  ("check Rippling"), name task people, requests or incidents, or be written around
  the grader. They vary in length, tone and format. The 2025 manager handbook stays
  marked current and conflicts with the 2026 standard; agents resolve this by date.
- Rules the graders depend on:
  - Temporary grants last 30 days by default. Contractor and intern grants also end
    by the contract or internship end date, whichever is earlier.
  - `Completed` means nothing is still pending. A narrower role in the *same
    environment* can stand in for what was asked.
  - Every `Blocked - *` status means the requested access is still wanted.
  - Only requests that result in new access are announced in Slack.
  - Every Jira update already emails the requester.
  - Security can approve a named, time-boxed separation-of-duties (SoD) exception.
    Access that depends on it ends when the exception does.
  - Platform SRE owns `grp_prod_admin` and `grp_release_approver`; approvals come from
    `prod-admin-owners@atlas.example`.
  - If role-owner approval is the *only* thing missing, the desk asks the owner once
    and holds the request as `Blocked - approval`. Requests blocked for another
    reason aren't sent to owners.
- **Guardrails:**
  - `interactive/evidence/access_provisioning.json` maps every assertion of every
    access task to the KB quotes and seeded records that justify it.
  - `tests/.../test_access_kb_hygiene.py` fails when a quote disappears from the KB,
    when an assertion has no evidence, or when the KB names a task entity.
  - Rebuild the ledger with
    `scripts/automation_workplace_access/build_evidence_ledger.py <interactive_dir>`.
- **Lesson:** the KB is shared by every access task. One sentence added for Task 6
  ("if approval is missing, ask the owner") made frontier models email owners in
  Tasks 3–5 and fail them. After any KB edit, rerun every access task, not just the
  one the edit was for.

### Tasks

Tasks 1–2 are edited by hand. Tasks 3–6 are generated by
`scripts/automation_workplace_access/build_task{3,4,5,6}.py <interactive_dir>`.
Each task has deterministic assertions, Slack/email content rubrics graded by an LLM
judge, a final-reply `nl_assertion`, and checks that already-closed requests keep
their recorded disposition.

| Task | Shape | What it tests |
| --- | --- | --- |
| 001–002 | Priya, single request | Narrowing to staging; production-only data; training block |
| 003 | 5-request backlog | Break-glass under CTO email; inactive worker; duplicate; group history |
| 004 | Scoping | SoD conflict; admin narrowed to read-only; partial grants; contract caps |
| 005 | 12-request queue | All of the above at volume; decoy approvals in Gmail; SoD matrix in Sheets |
| 006 | Data Platform queue + Q4 review removals | Asking for a missing role-owner approval (one email); VP email that isn't an approval; live vs. lapsed SoD exception (second Sheets tab); signed amendment not yet in Rippling; an Okta call that times out once; review rows marked Remove or left unmarked past the deadline |

### Runtime additions

- **Injected faults:** `InjectedFault` / `world.injected_faults`. A matching call
  returns a canned error payload and the fault is used up. The response is
  returned, not raised, so the used-up fault persists in the world state.
- **Sent-email check:** `access_sent_emails_exact` in `family_registry.py`. It
  requires exactly the expected new emails (recipients, required terms, judge
  rubric) and no other generic-app changes. Apps listed in `tolerate_apps` (Sheets
  in Task 6) may change freely.
- **Content judge:** `_llm_content_judge` judges Slack posts and emails. It knows the
  internal group and course IDs, caches its verdicts, and retries empty or
  unreadable replies. Names, dates and post counts stay deterministic.
- **Score breakdown:**
  `python -m tau2.domains.automation_workplace.score_breakdown <results.json>`
  reports strict, decision (who holds what), process (records and announcements)
  and judged scores.
- **Grader false negatives fixed so far:**
  - The judge didn't recognise `grp_*` and course IDs.
  - Silent-name checks used substrings, so "rui" matched "recruiting" and an
    approver credited by name tripped the check. They now use full names.

### Results

- **Sol medium (gpt-6.1-sol), 3 trials:**
  - Tasks 1–5: access decisions 15/15.
  - Task 6: decisions 3/3. Strict score 3/3 after the silent-name fix.
  - Sol medium's remaining errors are process-only: it re-labels already-closed
    `Blocked - training` requests as `Completed`.
- **Model spread, Tasks 3–6, 5 trials each** (clean rerun after the runbook fix;
  results in `data/simulations/automation_workplace_access_003_006_<model>_5trials_v2/`).
  Each cell is decision / strict.

  | Model | T3 | T4 | T5 | T6 |
  | --- | --- | --- | --- | --- |
  | Astra xhigh | 5/5 · 5/5 | 4/5 · 4/5 | 5/5 · 5/5 | 5/5 · 5/5 |
  | Sol low | 5/5 · 1/5 | 5/5 · 5/5 | 4/5 · 2/5 | 5/5 · 5/5 |
  | gpt-5.5 medium | 1/5 · 1/5 | 4/5 · 4/5 | 1/5 · 0/5 | 0/5 · 0/5 |
  | gpt-5.4-mini medium | 0/5 · 0/5 | 0/5 · 0/5 | 0/5 · 0/5 | 0/3 · 0/3 |

  - **Astra's T4 miss was a simulator bug.** Astra described a plan, the simulated
    manager asked "what will happen for each person", and the manager stopped
    before anything was executed. The Task 3–6 instructions now stop only after
    the agent reports changes it has made; if it only plans or asks, the manager
    tells it to go ahead. Not rerun yet.
  - **Sol low's misses are the closed-request habit.** It re-labels ACCESS-391 and
    ACCESS-419 as `Completed`, and once rewrote the seeded Slack post about Nora.
  - **gpt-5.5 has real decision errors.** It never opens the Exceptions tab of the
    SoD sheet (Omar blocked in 5/5), mis-handles break-glass in Task 3 (4/5), and
    once worked a different person's request in Task 4.
  - **gpt-5.4-mini can't operate the tools.** It calls tools before unlocking them
    and sends malformed arguments.
  - A first pass ran under the over-broad "ask the owner" rule; its Task 3–5
    numbers are invalid.
- **Conclusion:** the family separates frontier models from mid-tier and small
  models. On access decisions it is saturated for Sol and Astra; what remains is
  Sol's process habit. Adding more rules stated in the KB
  doesn't move them. To separate the frontier, test:
  1. contradictory records where the right move is to hold and ask;
  2. long queues where earlier grants change later decisions;
  3. a second session that resumes the agent's own earlier work.
- **Run command** (unset the placeholder `OPENAI_API_KEY` so the one in `.env`
  is used):

  ```
  env -u OPENAI_API_KEY PYTHONPATH=src .venv/bin/tau2 run --domain automation_workplace \
    --task-split-name interactive_canonical --task-ids <ids...> --num-trials 5 \
    --agent-llm <model> --agent-llm-args '{"reasoning_effort": "<effort>"}' \
    --user-llm gpt-4.1-2025-04-14 --user-llm-args '{"temperature": 0.0}' \
    --seed 300 --max-steps 200
  ```

  In zsh, pass multiple task IDs as an array; a quoted string arrives as one ID.

## AutomationBench replay vs. our AP tasks (November 2026)

### What was observed

| Run | Model | Tasks | Strict pass | Partial credit |
|---|---|---|---|---|
| AutomationBench public replay, one task per domain | gpt-5.5, medium | 5 | 0/5 | about 70% |
| Ours: `vendor_invoice_002`, `_002_solo`, `renewal_portfolio_002` | gpt-6.1-sol, low | 3 | 3/3 | 100% |
| Ours: `vendor_invoice_003` (image-only evidence) | gpt-6.1-sol, low | 1 | 1/1 | 100% |

These are single samples on different models, so they give a feel, not a score.
The AutomationBench misses were all omissions, never wrong judgments:

- `sales.multi_hop_lookup`: emailed the executive team but not the support-escalation
  recipient that the open escalations required.
- `operations.asana_fire_drill`: never added the tag that only an email named.
- `support.zendesk_sf_case_sync`: created the wrong number of cases, and one number
  was missing from the Slack summary.
- `finance.invoice_dispute`: handled the first dispute, then declared done. It
  skipped two escalations and three tracker rows.
- `hr.offboarding_automation`: left the third employee's row unmarked, and the right
  status depended on policy ("Scheduled", not "Processed").

### Why our tasks did not separate the model

1. **We give a checklist.** The AP procedure lists every eligibility check
   (approval, duplicate, receipt, credit, banking) and the full payment order. The
   agent never has to find an obligation; it only has to evaluate each one.
   AutomationBench puts the rule in a sheet row or email the agent reaches only by
   reading the data.
2. **Every obligation sits on the main object.** All of the AP assertions are about
   bills, plus remittances derived from them. AutomationBench failures were on
   *peripheral* obligations: a second recipient, a tag, a tracker row, the third
   employee. Models do the central task and drop the side duties.
3. **Our structure prevents stopping early.** Plan approval makes the agent list the
   whole run, and the simulated user asks for a per-bill summary if it is missing.
   Even the solo variant still faces a 13-bill queue and a procedure that forces a
   full walk. AutomationBench tasks look finished after the first case.
4. **Our misleading instructions are explicit.** The stale $110k and "Sam approved
   it" arrive as pushback, which signals that something is contested. In
   AutomationBench the wrong instruction is simply the task wording ("process final
   severance payments"), with no cue to re-check it.
5. **Shared:** strict all-or-nothing state checks. Both benchmarks fail a run that
   completes most of the work.

Images (`vendor_invoice_003`) did not change this. Sol opened all five files and read
each fact correctly, because each image held one clean fact that the procedure told it
to look for.

### What to change

- **Remove the checklist, keep the policy.** The procedure should say "pay approved
  bills within the release per AP standards" and nothing more. The standards stay as
  separate documents among the distractors, unnamed by the procedure.
- **Seed peripheral obligations in the data, not the KB.** Examples: a pinned
  Controller email saying held bills also get a row in the AP exceptions tracker; a
  vendor-master note saying a given vendor's remittance must also go to its
  collections agent; a Slack thread where someone asks to be told when a specific bill
  is paid. Each one is realistic, reachable only by reading the records, and graded
  by exact state.
- **Spread writes across apps.** One small write per item across a tracker, a ticket
  queue and a notification channel, so that a skipped item costs an assertion.
- **Make early completion look plausible.** Put the first one or two cases on top,
  and later cases that need a different handling path behind pagination or in a
  second message.
- **Fold the misleading instruction into the request.** Make the opening ask itself
  slightly wrong (for example "pay everything approved today"), rather than raising
  it as pushback.
- **Drop the rescue behaviour in the main variant.** No "go ahead" if the agent only
  plans, and no summary request; a busy manager says "ok go ahead" once and leaves.
- **Report partial credit.** Show the assertion pass rate next to strict pass, since
  AutomationBench near-misses (about 70%) show more than 0/5 does.

### Task 7: process inferred from Slack precedent (December 2026)

`access_provisioning_007` has its own thin KB (`knowledge/access_provisioning_precedent.json`: tool docs, a short standard and unrelated noise; no runbook). The desk process lives in ~20 dated #eng-access-requests messages, five closed ACCESS tickets and a hallway thread in #engineering. Threads differ on purpose: a 14-day default (Oct 6) that became 30 days (Nov 3), contractor cap at contract end, training holds that are not announced, a VP's "fine by me" that is not owner approval, and a release-approver conflict. The manager simulator never states a rule (an NL assertion checks this). The ledger entries for this task point at Slack records instead of KB quotes. Builder: `scripts/automation_workplace_access/build_task7.py`.

Slack now behaves like the real API: `slack_list_channels_v1` (topic, purpose, members), `slack_get_channel_history_v1` (newest first, 15 per page, cursor), `slack_get_thread_replies_v1`, and `slack_search_messages_v1` (query required; `in:`, `from:`, `after:`, `before:`; 10 per page). Messages carry author, timestamp and thread id. The precedent is split across #eng-access-requests (announcements, Jo/Amir/Mira threads) and #eng-platform (Pia approval thread, Lars conflict thread, the 14-to-30-day default notes), buried in ~40 everyday messages (birthdays, WFH notes, @channel freezes, CI-slowness questions, kudos).

First pilot, before the Slack changes (an empty search returned all 41 messages): Sol low strict 3/3, gpt-5.5 medium 0/3 (used 160-180 day expiries instead of the 30-day default, treated the VP's approval as owner approval, granted Rui prod admin in 2 of 3 trials, posted no announcements). Not yet rerun on the realistic Slack tools.

Earlier pilot note: Sol low, 3 trials, strict 3/3. Inference from precedent alone did not separate Sol low, so the next step is harder precedent (conflicting or incomplete threads where the right move is to hold) and running weaker models.

## Open issues and next steps

1. **Create access variants with different safe alternatives.** The phrase leak is
   fixed, but Opus still guessed staging before disclosure because it is the only
   plausible fallback in this world. Vary the hidden work need and exact entitlement.
2. **Retain recoverable, exactly-one final notifications.** Slack message update now
   permits an accurate provisional disposition to be revised without a stale or
   duplicate artifact. The production-only run confirms this is executable. Continue
   to ensure the convention is discoverable from seeded history.
3. **Calibrate the other five canonical families.** Run matched trials and inspect
   exact-state failure clusters. Incident is already difficult; the others need model
   evidence.
4. **Manually play every canonical task in the visual lab.** Verify that a human can
   discover necessary facts, take every action, and understand failures without seeing
   the answer key.
5. **Build logical variants, not cosmetic copies.** Implement the 48-task matrix with
   typed generators and two deterministic surfaces per logical task.
6. **Keep notifications discoverable.** Conventions such as manager updates should be
   evident from app history or current policy, never hidden only in assertions.
7. **Test verification failures.** Add timeout/accepted-write ambiguity, partial
   downstream failures, and safe retry behavior.
8. **Report exact state separately.** Per-family exact pass¹ and pass^k should be the
   main benchmark result; communication and trajectory quality can be reported as
   secondary diagnostics.
9. **Freeze only after audit.** Remove wording gates, scenario-specific policy leaks,
   impossible user knowledge, and task-order dependencies before publishing a split.
10. **Decide packaging before contribution.** Resolve the AutomationBench dependency
    boundary and attribution, then prepare an upstream proposal. Do not raise a PR
    until the user explicitly asks.

## Durable design principle

The contribution should not be “τ with longer tasks” or “AutomationBench with a chat
wrapper.” Its distinctive value is measuring an AI employee that must divide control
correctly among three sources:

- the employee controls intent, preference, authority, and approval;
- enterprise systems control facts, policy, eligibility, and recorded state; and
- the agent must reconcile both, execute the complete workflow, and verify the exact
  outcome without being coached through the answer.

## Access provisioning restarted at Tasks 7 to 10

Tasks 1 to 6 were saturated and have been removed (they remain in git history at commit `0e05cea` on branch
`automation-workplace-access-precedent`). Task 7's builder now reads its inputs from
`scripts/automation_workplace_access/base/` (the Task 6 world and the old KB) and rebuilds Task 7 byte for byte.
`build_precedent_tasks.py` builds Tasks 8 to 10 on Task 7's world (same company, same 566-message Slack history,
plus each task's own dated threads). Golden call sequences for 008 to 010 live in
`evidence/access_precedent_golden.json`.

| Task | Unstated parameter | Astra 6.2 xhigh, 3 trials |
|---|---|---|
| 008 | window depends on the group (admin 14, read-only 30, staging deployer 90 days) | strict 2/3, decision 3/3 |
| 009 | expiry anchored elsewhere (on-call rotation end, training lapse, later contract end does not apply) | strict 2/3, decision 3/3 |
| 010 | progressive disclosure: Dara's end date is known only to the manager | strict 1/3 |

The 008 and 009 misses were announcement granularity only (one combined Slack post). The 010 misses were the agent never
asking Ken for Dara's end date. `disclosure_conformance.py` (simulator check before a run) and `disclosure_audit.py`
(per-trial attribution to agent or environment after a run) support the disclosure task.
Open items: the same people appear with different dates across the separate 008 to 010 worlds, so the worlds cannot be
merged for a memory eval without reconciling timelines; `manifest.json` `knowledge_document_count` is stale.
