# Tau2-Bench Reproduction and Workplace Task Comparison

Date: 2026-11-08

## Question

Why does `workplace_kickoff_001` score 100% while published tau2-bench pass^1
scores are materially lower, including roughly the high 80s for some newer
leaderboard models?

## Reproduction protocol

The current repository `main` branch is tau-bench 2.0. Its README explicitly says
that its English inputs are not identical to the 1.x benchmark and should not be
compared directly with the earlier leaderboard. The June 2025 tau2-bench paper is
matched by tag `v0.1.1`, released immediately after the paper and differing from
`v0.1.0` only in the domain viewer.

The paper configuration was reproduced from an isolated archive of `v0.1.1`:

- agent: `gpt-4.1-2025-04-14`;
- user simulator: `gpt-4.1-2025-04-14`;
- temperature: 0 for both;
- standard `llm_agent` and `user_simulator`;
- maximum steps: 200;
- seed: 300; and
- original airline, retail, and telecom task data and evaluator.

The complete paper run contains 278 tasks (50 airline, 114 retail, and 114
telecom), each run four times: 1,112 conversations. The paper reports approximately
$40 for one trial over all domains, or about $160 for the complete four-trial run.

For a cost-bounded reproduction, ten tasks were sampled without replacement from
each domain using seed 300 and run once. This gives an unbiased but high-variance
pass^1 check over 30 conversations. It is not an exact full-paper replication.

## Results

| Domain | Local successes | Local pass^1 | 95% Wilson interval | Paper GPT-4.1 pass^1 |
| --- | ---: | ---: | ---: | ---: |
| Airline | 6/10 | 60% | 31-83% | 56% |
| Retail | 8/10 | 80% | 49-94% | 74% |
| Telecom | 3/10 | 30% | 11-60% | 34% |
| Combined sample | 17/30 | 56.7% | 39-73% | Not reported as one pooled score |

All three reported paper values fall inside their local sample intervals. The local
ordering also matches the paper: retail is easiest, airline is intermediate, and
telecom is hardest. This is strong evidence that the benchmark harness is behaving
as expected.

Actual cost for the 30 conversations was approximately $3.10:

| Domain | Agent cost | User cost | Total |
| --- | ---: | ---: | ---: |
| Airline | $0.35 | $0.12 | $0.46 |
| Retail | $0.57 | $0.14 | $0.71 |
| Telecom | $1.01 | $0.91 | $1.93 |

Raw results:

- `data/simulations/tau2_v011_repro_airline_gpt41_n10.json`
- `data/simulations/tau2_v011_repro_retail_gpt41_n10.json`
- `data/simulations/tau2_v011_repro_telecom_gpt41_n10.json`

## The apparent “high 80s” discrepancy

There are two different comparisons being mixed together:

1. The tau2-bench paper does not report high-80s pass^1 for GPT-4.1. It reports
   74% retail, 56% airline, and 34% telecom. The local reproduction matches those
   numbers closely.
2. The current leaderboard includes much newer models and later benchmark releases.
   For example, the checked-out leaderboard shows GPT-5.2 at 89.7% on one telecom
   text entry. The current README warns that 2.0 English runs are not input-identical
   to 1.x. Model and benchmark revision must therefore be fixed before comparing
   scores.

Even an 89.7% benchmark score means roughly one in ten task-trials fails across a
large, heterogeneous population. It is fully compatible with passing one easy task
four times.

## Why the workplace task is currently 100%

### 1. One task is not a benchmark distribution

The workplace result is four trials of one task. Tau2-bench evaluates 278 distinct
tasks covering many goals, policies, and failure modes. Four successful repetitions
show that Task 1 is stable; they do not estimate performance over general employee
work.

### 2. Task 1 is a short, mostly linear workflow

Task 1 has five consequential state transitions:

1. create or revise the proposal;
2. record user approval;
3. schedule the event;
4. create one preparation task; and
5. post one project update.

The information-gathering path can vary without affecting the score, and the write
sequence has no genuine branching after the correct proposal is known.

The sampled tau2-bench tasks were more heterogeneous:

- sampled retail tasks required up to 12 reference actions and often modified
  several products, orders, addresses, returns, or payments;
- sampled telecom tasks required up to 11 reference actions and generated 14-26
  actual tool calls because diagnosis is interactive; and
- airline mixed positive actions with policy-sensitive refusals, partial approvals,
  and compensation calculations.

### 3. Tau2 errors compound across independent requirements

The retail failures illustrate strict exhaustive completion. The two failed sampled
tasks had 10 and 12 reference actions. The agent successfully completed much of each
conversation but missed or incorrectly executed one required order modification, so
the final DB did not match.

The airline failures included:

- cancelling a reservation that policy required leaving untouched;
- issuing $100 instead of $50 compensation;
- completing a flight change but getting baggage state wrong; and
- handling one of several reservations incorrectly.

These are not user-simulator artifacts. They are agent reasoning and exhaustive
follow-through errors that exact-state evaluation correctly catches.

### 4. Telecom has real decentralized diagnostic branching

Seven of ten sampled telecom tasks failed. In a representative two-issue failure,
the agent fixed the network preference but never diagnosed the required roaming
state. It performed many plausible checks, reset APN settings, rebooted the device,
and eventually transferred the user. The final mobile-data and speed assertions
therefore failed.

Longer MMS tasks often completed most repairs but omitted data refueling, roaming,
or another user-side correction. This is the paper's central dual-control challenge:
the agent must choose the next diagnostic question, guide a user action, observe the
result, update its hypothesis, and continue until every hidden issue is resolved.

The workplace user currently holds a preference and approval authority, but does not
hold a partially observable operational state that must be diagnosed over several
rounds.

### 5. The workplace environment is intentionally assistance-rich

Task 1 currently provides several useful guardrails:

- the policy names the exact meeting-title format, downstream task template,
  channel, and due-date rule;
- there is one employee per required function;
- availability contains a single clean common slot;
- proposal creation rejects conflicts and unknown attendees;
- the user approval tool rejects the wrong private date, duration, or external
  attendee and returns an actionable correction;
- a wrong pending proposal can be revised in place; and
- deterministic IDs make downstream references straightforward.

These are good properties for a first environment test because they isolate whether
the interaction and grading machinery works. Together, however, they make the
correct path easy to recover once any model gets close.

### 6. Evaluator strictness is not the main difference

The workplace task uses strict `DB + COMMUNICATE` grading. The reproduction includes
strict DB equality in airline/retail and final-state assertions in telecom. Both
evaluators reject partial completion.

The score gap remains after matching the original evaluator and model. The dominant
difference is the task population and its reasoning horizon, not lenient workplace
grading.

## Implications for the contribution

`workplace_kickoff_001` should remain a smoke/calibration task. It demonstrates:

- progressive disclosure;
- user-controlled authorization;
- correction of a bad proposal without path-based punishment;
- policy-grounded research; and
- exact multi-application final-state grading.

It should not be used as evidence of model-level employee-work accuracy.

The domain needs enough additional tasks that failures can arise from substantive
employee-work complexity rather than simulator ambiguity. The next tasks should
include several of the following at once:

- three or more independently required items;
- evidence split across several applications;
- stale and plausible decoy records;
- a policy exception where one requested action must not be performed;
- a user-private decision revealed only after the agent presents tradeoffs;
- an approval that covers only one consequential artifact;
- partial completion that leaves a visibly incorrect final state; and
- recovery paths that do not reveal company-system answers through the user.

A useful initial calibration target would be neither 0% nor 100%: approximately
40-70% pass^1 for GPT-4.1 on a small development set, followed by broader testing
with newer frontier and smaller models. Difficulty should come from legitimate
reasoning, coordination, and exhaustive execution—not irreversible drafts, opaque
IDs, or simulator violations.

## Conclusion

The tau2-bench result was reproduced successfully. Our 60% airline, 80% retail, and
30% telecom samples are consistent with the paper's 56%, 74%, and 34%. Task 1's
100% score is real for that task, but it means the task is saturated. It does not
indicate a scoring bug and does not generalize to a workplace benchmark.

## Current text-v1 retail check with GPT-6 Astra

On 2026-11-11, GPT-6 Astra at `xhigh` reasoning was evaluated on the complete
released English `text-v1` retail subset: 50 stratified tasks selected from the
114-task canonical frame, one trial per task. The user simulator was
`gpt-4.1-2025-04-14` at temperature 0, with seed 300, a 200-step limit, and
ten-way simulation concurrency.

| Metric | Result | 95% Wilson interval |
| --- | ---: | ---: |
| Full benchmark pass@1 | 40/50 (80%) | 67.0-88.8% |
| Exact DB match | 41/50 (82%) | 69.2-90.2% |
| Normal termination | 50/50 (100%) | — |

The benchmark is therefore not saturated for this model. Nine trajectories ended
in an incorrect database state, and one additional trajectory matched the database
but failed its natural-language assertion. The exact-state failures were
substantive and clustered into recognizable interaction errors:

- four premature handoffs after the first infeasible request, without continuing
  to the user's fallback or remaining requests (tasks 18, 32, 36, and 107);
- three incomplete multi-intent workflows (tasks 59, 66, and 104);
- one cancellation with the wrong confirmed reason (task 38); and
- one wrong variant selection followed by an extra modification to another order
  (task 79).

Task 105 was the sole DB-correct/full-score failure. The requested two-kettle
exchange required a $21.10 payment difference, but the only stored gift card had a
$17 balance. The agent correctly left the database unchanged and offered a human
handoff for adding a debit card, while the benchmark's natural-language assertion
still expected the exchange to be completed. It should be treated separately when
auditing benchmark difficulty.

This run is not directly comparable to the paper's 1.x retail score because
`text-v1` uses a newer frozen 50-task frame and reviewed English inputs. It is still
the appropriate current answer to whether generic retail is saturated: even after
excluding the questionable task-105 language assertion, exact workflow success is
82%, leaving a meaningful error tail dominated by fallback handling and exhaustive
multi-request completion.

Raw results:
`data/simulations/tau2_retail50_gpt6astra_xhigh_1trial/en-retail/results.json`.
