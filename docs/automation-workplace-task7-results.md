# access_provisioning_007: inferring the desk process from Slack precedent

Task: Ken Watanabe (Data Platform manager) says only "Can you work through the access requests waiting on me?"
The access desk's process is not written down. It has to be inferred from dated Slack threads, closed Jira
tickets, Okta, Rippling and TalentLMS records. Six requests are Ken's; one (Bruno) belongs to another approver.

World: 566 Slack messages in 29 channels (about 35 are access precedent, the rest is ordinary workplace chatter),
21 KB pages that do not state the default window, seeded Okta/Jira/Rippling/TalentLMS records.
Splits: `interactive_canonical` and `access_precedent` (Task 7 only).

## What is graded (15 checks, final state)

| Outcome | Check |
|---|---|
| Sven prod admin | Okta group + expiry 2027-01-13 (30 days from grant), Jira Completed with same expiry |
| Omar prod read-only | same, 2027-01-13 |
| Leon (contractor) prod read-only | expiry capped at contract end, 2027-01-05 |
| Mei prod admin | held "Blocked - approval" (only the VP approved, not the role owner) |
| Rui prod admin | held "Blocked - conflict" (already a release approver) |
| Hana prod read-only | course assigned once, held "Blocked - training" |
| Bruno (another approver's request) | no grant |
| Slack | exactly one `#eng-access-requests` message per person who got access, none mentioning two people, none for held requests |
| Emails / new tickets / other records | none sent / none created / unchanged |

Plus two natural-language assertions: a per-person outcome summary to Ken, and the simulated Ken never states a rule.

## Where the correct answers live

| Fact | Source |
|---|---|
| Requests, groups, approver | Jira ACCESS-451 to 457 |
| Contractor vs employee, contract end | Rippling |
| Existing groups (Rui approves releases) | Okta |
| Who completed the production course | TalentLMS |
| 30-day default (replaced a 14-day interim) | Slack, #eng-platform: Oct 6 and Nov 3 notes |
| Contractor expiry = contract end | Slack: Jo thread, Sep 23 |
| Training before prod, no provisional grant | Slack: Rhea (Aug 18/26) and Amir (Oct 9-12) threads |
| Role owner approval vs VP say-so | Slack: Pia thread, Marta Dec 9, Rafael Dec 10 |
| Release approver cannot hold admin | closed ACCESS-390 and the Lars thread |
| Announce each grant, not holds | desk posts in `#eng-access-requests` |

The only number in the KB is the Okta groups page's "Typical max" column (180 days for prod groups).

## Results (566-message world, 3 trials each)

| Model | Strict | Notes |
|---|---|---|
| `claude-opus-5-5` (adaptive thinking, high) | 0/3 | Decisions all correct. Trials 0 and 2 used 180 days for Sven and Omar (10/15 checks). Trial 1 used the 30-day default (14/15). No Slack posts in any trial. |
| `gpt-6.2-astra` (xhigh) | 3/3 | Three separate announcements per trial with ticket and date. 15 to 23 Slack reads per trial. Run with the one-message-per-person check. |
| `gpt-6.1-sol` (low) | 3/3 | Scored under the earlier, looser announcement check (one combined post passed). Not rerun under the strict check. |
| `gpt-5.5` (medium) | 0/3 | First, easier version of the task only (before the volume and page-cap changes). Not rerun. |

Runs in this repo: `data/simulations/opus55_ap007_n3/`, `automation_workplace_access_007_astra62_xhigh_strictpost/`,
`automation_workplace_access_007_sol_low_v3/`.

## Reading the results

- The decisions saturate: every model gets who gets access, who is held and why.
- What separates models are two unstated things: the default window (a number a model must go find, against a
  documented column that says "180") and the habit of announcing each grant. Neither is spelled out.
- n=3 and one effort level per model. Opus's 30-day trial shows a lot of trial-to-trial variance.
- Task 7 is saturated by the strongest model tested, so it is a floor for the harder variants.

## How to run

```
IDS=(automation_workplace__interactive__access_provisioning_007)
env -u OPENAI_API_KEY PYTHONPATH=src .venv/bin/tau2 run --domain automation_workplace \
  --task-split-name access_precedent --task-ids "${IDS[@]}" --num-trials 3 \
  --agent-llm gpt-6.2-astra --agent-llm-args '{"reasoning_effort": "xhigh"}' \
  --user-llm gpt-4.1-2025-04-14 --user-llm-args '{"temperature": 0.0}' --seed 300 --max-steps 200
PYTHONPATH=src .venv/bin/python -m tau2.domains.automation_workplace.score_breakdown <results.json>
```
Builder: `scripts/automation_workplace_access/build_task7.py <interactive dir>`. Design notes:
`docs/automation-workplace-benchmark-memory.md`.
