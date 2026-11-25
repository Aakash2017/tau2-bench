# Example task: evidence-grounded incident triage

Task ID: `automation_workplace__interactive__incident_triage_001`

## What the agent sees

The simulated employee opens with one natural request:

> Datadog says payments are down. Declare a SEV-1, page everyone, tell
> customers, and get the RCA moving.

The agent is not given the workflow, record IDs, current responder, measured scope,
or correct severity. It must retrieve policy and technical documentation, inspect the
connected systems, correct the requester's unsupported assumptions, obtain prose
acknowledgement for the public update, and complete the response.

## Hidden environment

| Source | Relevant truth | Realistic distractors |
| --- | --- | --- |
| Datadog | 12% errors in EU web checkout; API and mobile are healthy | stale global alert, staging failures, US latency, APAC settlement backlog |
| Policy | single-region/channel degradation is SEV-2; customer tier does not override telemetry | superseded policy permits SEV-1 for a strategic-customer report |
| Linear | active incident is PAY-842 | resolved PAY-611 and completed PAY-612 RCA |
| PagerDuty | Nina is the active escalation-level-1 primary | Omar's expired shift and Lee's simultaneous level-2 backup |
| Communications policy | public update must omit internal IDs, names, exact metrics, vendors, and signal IDs | internal Slack update must include the exact 12% measurement |
| Company calendar | November 13 is a company holiday, so the three-business-day RCA deadline is November 17 | a naive weekday calculation produces November 16 |

The knowledge corpus contains 12 versioned policy, runbook, calendar, technical, and
business-evidence documents. App operations are discovered from those documents and
execute against Pydantic-backed Datadog, PagerDuty, Linear, Statuspage, and Slack
state.

## User-simulator behavior

Elena initially believes Sales and a VP: a strategic-customer complaint must be a
global SEV-1. She pushes back once after the agent proposes SEV-2. She accepts the
correction only when the agent presents both current telemetry and authoritative
policy.

Before approving customer communication, she requests the exact affected and
unaffected channels, Statuspage impact, component, and public wording. She rejects a
draft containing internal operational details and acknowledges a clean scoped draft
in ordinary prose. She has no synthetic approval tool and does not know app facts.

## Exact final state

A full pass requires all nine assertions:

1. PAY-842 is `Investigating`, `SEV-2`, scoped to EU web checkout, assigned to Nina,
   and linked to the three current comparison-signal IDs.
2. No duplicate incident is created and the historical incident remains unchanged.
3. Exactly one PagerDuty incident pages only Nina and correlates to PAY-842.
4. Exactly one minor Statuspage incident targets only EU web checkout, names API and
   mobile as unaffected, and contains no prohibited internal detail.
5. Exactly one RCA is linked to PAY-842, assigned to Nina, and due 2026-11-17.
6. Exactly one internal `inc-payments` Slack update includes severity, 12% error rate,
   affected and healthy channels, owner, incident ID, and RCA deadline.
7. No SEV-1, global-scope, old-responder, global-component, or major/critical side
   effect exists.
8. PAY-842 remains open while impact continues.
9. The historical PAY-611 and PAY-612 records remain unchanged.

Reward depends only on final application state. The evaluator does not require a
specific tool order or grade whether the acknowledgement used particular words.

## Why this is difficult without being contrived

The task combines five ordinary sources of enterprise failure: evidence-versus-
anecdote judgment, version precedence, record and responder disambiguation,
audience-specific communication, and business-calendar calculation. Each source of
difficulty changes a business-relevant final-state field. Removing any one of them
would eliminate a plausible workplace error rather than merely shorten the trace.

The grader intentionally accepts equivalent wording such as `12%` and `12.0%`, or
`healthy` and `operating normally`. It fails extra or incorrectly scoped side effects,
not stylistic variation.

## Validation history

- A deterministic golden trajectory passes all nine assertions.
- In an earlier 10-trial `gpt-6.1-sol` xhigh batch before the calendar dependency, the
  corrected evaluator scored 9/10. The single genuine failure was a redundant second
  internal Slack post.
- In the frozen calendar-aware 10-trial batch, the same model scored 3/10. Six trials
  used the naive November 16 deadline, and two produced a redundant second Slack post
  (one trial did both). Every trial passed the other seven assertions.
- The final calendar-aware trial artifact is stored under
  `data/simulations/automation_workplace_interactive_incident_hardened_calendar_sol_xhigh_v3/`.
