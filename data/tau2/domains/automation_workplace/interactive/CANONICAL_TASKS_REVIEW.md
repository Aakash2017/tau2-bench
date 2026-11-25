# Canonical interactive workplace tasks

This review covers the seven implemented canonical tasks across six families in the
`interactive_canonical` split. Every task uses a τ-style simulated employee,
task-local BM25 knowledge retrieval, discoverable API-shaped operations over
Pydantic state, and deterministic final-state-only reward.

| Family | Docs | Operations | Assertions | Primary difficulty |
| --- | ---: | ---: | ---: | --- |
| Incident triage | 12 | 8 | 9 | evidence, policy precedence, audience separation, business calendar |
| Vendor invoice | 10 | 10 | 8 | three-way match, unverified bank change, non-payment follow-through |
| Customer escalation | 10 | 7 | 6 | current incident truth, verified recipient, credit authority, approval |
| Access provisioning (2 tasks) | 9 | 10 | 9 / 8 | identity disambiguation, least privilege, training, no-op and recovery |
| Renewal portfolio | 10 | 6 | 7 | pagination, list exhaustion, legal hold, parent-child deduplication |
| Meeting coordination | 7 | 5 | 6 | stale brief, paginated contacts, quorum, time zones, private preference |

## 1. Incident triage

Opening:

> Datadog says payments are down. Declare a SEV-1, page everyone, tell
> customers, and get the RCA moving.

The requester is wrong about global scope and severity and pushes back once using a
Sales VP's superseded strategic-customer rule. Current telemetry shows only EU web
checkout degradation; comparison channels are healthy. The agent must select the
active Linear incident, current level-1 primary, safe public wording, detailed internal
update, and a holiday-aware RCA date.

Exact outcome: scoped SEV-2 state across Linear, PagerDuty, Statuspage, and Slack; one
linked RCA due November 17; no global, SEV-1, duplicate, old-responder, or historical-
record side effect.

## 2. Vendor invoice

Opening:

> Please pay Northstar invoice INV-7842 today against PO-3187. They also sent
> new bank details, so use those.

The requester incorrectly treats VP renewal approval as authority for an off-PO fee and
an emailed bank-account change. The agent must reconcile PO, receipts, invoice, vendor
master, and current AP policy; explain the exact mismatch; use the independently
verified vendor contact; and obtain acknowledgement of the non-payment plan.

Exact outcome: hold the existing bill for both structured reasons, make no payment,
leave the vendor bank master unchanged, create one AP exception, send one neutral
correction/verification request, post one internal AP update, and preserve unrelated
records.

## 3. Customer escalation

Opening:

> Northstar is furious. Tell Sam the global outage is resolved, give them the
> 20% credit Sales promised, and close the escalation.

The latest-looking support prose is stale, Sam is not the verified contact, the current
incident remains investigating and scoped to EU data exports, and the requested credit
exceeds authority. After those facts are established, the account owner progressively
supplies tone, a $400 in-authority credit, and the next-update commitment. The exact
external draft must be acknowledged in prose.

Exact outcome: one safe email to verified contact Priya, exactly $400 credit, an
accurate open Salesforce escalation, one linked RCA follow-up, one internal Slack
update, and no message to the unverified address.

## 4. Access provisioning

Opening:

> Give Priya the same production admin access as Miguel today. Her onboarding
> paperwork is complete, so compliance is covered.

The manager is authoritative about the work need but does not state Priya's worker
type. The agent must resolve it from Rippling, distinguish a current employee-only
CTO break-glass policy from an older department-manager approval handbook, and apply
the contractor training rule. Priya has active and stale identities, incomplete
production training, and a contract end date. After policy-backed pushback, the
manager discloses that immediate work only requires inspecting staging deployment
configuration and accepts staging read-only.

Exact outcome: grant only the active HR-linked identity staging read-only through the
contract end date, grant no production or break-glass entitlement, assign training,
reuse and block the existing production request with the staging alternative recorded,
post one manager update, and preserve the stale identity.

### Production-only counterfactual

The paired `access_provisioning_002` task has the same opening, identities, training
state, and policy. Before the conversation, an HR operations person has manually
provisioned staging read-only as a provisional workaround. The manager does not reveal
either that grant or the concrete assignment in the opening. After a focused scope
question—or as a corrective follow-up if the agent acts prematurely—the manager
discloses that Priya must compare live customer deployment configuration with Miguel,
that the required data exists only in production, and that staging cannot help. The
manager presses once for a temporary production exception.

Exact outcome: revoke the seeded staging entitlement and its expiration, grant no new
entitlement, assign the current course, reuse and block the existing request with no
grant or expiration, and preserve every unrelated identity. Because the requester is
already the manager and no access remains, the revised ticket is the durable
disposition; a redundant Slack announcement must not be posted.

## 5. Renewal portfolio

Opening:

> Work the renewal book. Have every account owner reach out today, starting
> with the accounts on the first page.

The final qualifier is deliberately on the last Salesforce page. The portfolio also
contains a signed-but-stale CRM record, a legal-hold account, a child duplicate, and an
out-of-window record. The revenue leader progressively supplies the ranking rule,
presses once to contact the held account, and approves the exact recipient set only
after every inclusion and exclusion is explained.

Exact outcome: three correctly ranked owner tasks, including an internal-only legal-
hold task; exactly two verified-recipient emails; correction of the signed renewal's
CRM state; no child duplicate or held-account outreach; and one summary accounting for
all six records.

## 6. Meeting coordination

Opening:

> Please schedule the Meridian rollout readiness review from the latest brief
> and close the loop in our systems.

The current brief conflicts with a plausible superseded brief. CRM contacts are spread
across three pages, with an excluded pilot-only contact on the last page. Six calendars
span PT and ET. The organizer withholds a genuine Wednesday-after-10-AM preference
until asked or shown candidates and acknowledges only the exact quorum-safe proposal.

Exact outcome: exactly one 45-minute event on Wednesday, November 18 from
10:30–11:15 AM PT / 1:30–2:15 PM ET, with the six verified attendees and Theo
excluded; matching Salesforce state; one complete project-channel Slack update; and
no stale-brief side effect.

## Validation status

- Every family has a deterministic golden call sequence that passes all assertions.
- Every family has a material negative sequence that fails the affected assertions
  while preservation assertions remain independently meaningful.
- Golden sequences for the five new families also pass through the shared τ
  environment dispatcher and real task evaluator.
- Cross-family tools remain locked: an active family cannot unlock another family's
  undocumented operation.

These are canonical authoring fixtures, not yet model-calibrated benchmark samples.
The next stage is to run repeated frontier-model trials, review failure clusters, then
freeze the canonical task before generating logical variants.
