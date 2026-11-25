# Workplace Operations Generated Collection: Review Guide

Status: **50 deterministic candidate tasks for human review**, plus the seven
existing hand-authored calibration tasks. These candidates are included in the
registered `workplace_ops` domain but are not presented as publication-ready.

## Collection summary

| Split | Tasks | Purpose |
| --- | ---: | --- |
| `base` | 57 | Seven hand-authored anchors plus 50 generated tasks |
| `anchors_7` | 7 | Original hand-authored calibration tasks |
| `candidate_57` | 57 | Alias retained for the initial combined collection |
| `generated_review` | 50 | Complete generated candidate collection |
| `generated_hard_evidence` | 50 | Paired authority-selection and user-pushback variants |
| `generated_incident` | 10 | Evidence-grounded correction and incident execution |
| `generated_vendor_invoice` | 10 | Financial controls and consequential non-action |
| `generated_customer_escalation` | 10 | Progressive authority disclosure and external approval |
| `generated_access_provisioning` | 10 | Training gates and least privilege |
| `generated_renewal_portfolio` | 10 | List exhaustion and cross-system reconciliation |

The generator is
[`task_generator.py`](../../tau2/domains/workplace_ops/task_generator.py). It uses
only deterministic Python scenario banks and templates; it makes no LLM calls. The
frozen task artifact is `data/tau2/domains/workplace_ops/tasks_generated.json`, and
`tasks_generated.manifest.json` records family, difficulty, and reference-action
counts. `tasks_generated.review.md` is the compact task-by-task review catalog with
each opening request, user-owned context, systems, reference writes, and completion
facts.

Following initial manual review, the generated tasks are included in the default
`base` split for model calibration. They are still not publication-ready: retain,
revise, or remove individual tasks based on simulator audits and model traces.

## What varies within each family

### Incident triage

- Service, impact scope, responders, and RCA dates vary.
- Some users over-escalate a scoped SEV-2 condition to SEV-1.
- Other users under-escalate broad multi-channel unavailability to SEV-2.
- Every task includes stale evidence, a current policy, stale and current on-call
  schedules, an existing incident, exact customer communication, and RCA follow-up.

### Vendor invoices

- Invoice and purchase-order amounts vary.
- Cases include overage plus bank mismatch, overage only, and bank mismatch only.
- The approved resolution is either a corrected invoice or independent bank
  verification.
- Correct completion intentionally includes no payment and no bank mutation.

### Customer escalations

- Requested and authorized credit amounts, restoration dates, RCA deadlines,
  verified contacts, decoy contacts, and requested tone vary.
- The requester owns the credit limit and communication preference; company systems
  own the incident and contact facts.
- External email, CRM state, RCA follow-up, and internal notification must all be
  completed.

### Access provisioning

- Six workers have incomplete training and require staging access plus a blocked
  production request.
- Four workers have completed training and may receive production-standard access.
- Every case includes a disabled identity decoy and a team template containing an
  inappropriate billing-admin entitlement.

### Renewal portfolios

- Portfolio scope, ARR threshold, account names, owners, and contacts vary.
- Each portfolio includes a critical-support account, an unowned eligible account,
  a Legal-hold account, a parent-child pair, a Billing-confirmed renewal, and an
  out-of-scope account.
- Every source account must be classified before the approved batch is executed.

## Automated guarantees

The generated-task test suite checks that:

1. The frozen JSON and manifest reproduce exactly from the generator.
2. The collection has exactly ten tasks in each of five families.
3. Every reference trajectory executes without tool errors and passes DB and
   diagnostic environment checks.
4. Every task fails exact-state grading if its final internal update is omitted.
5. User-controlled approval rejects an invalid proposal in every family.
6. User simulator instructions do not expose generated proposal, CRM, Linear, or
   environment-generated record IDs.
7. Natural-language retrieval uses BM25-style ranking, and semantic record-type
   hints cannot suppress otherwise relevant records.
8. Family-specific finalization rejects incomplete downstream work before posting
   the canonical internal update.
9. Every hard-evidence task adds exactly 60 query-colliding workplace artifacts
   without evaluator-like `not_authoritative` or `approved: false` labels.
10. Hard-evidence search returns at most ten ranked records per page and supports
    deterministic pagination and authority filters.

Run the focused checks with:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/test_domains/test_workplace_ops/test_generated_tasks.py -q
```

Reproduce the frozen candidates with:

```bash
PYTHONPATH=src .venv/bin/python \
  -m tau2.domains.workplace_ops.task_generator
```

## Important limitations to review

The first collection intentionally prioritizes authoring infrastructure and exact
replay validity. It still has several likely benchmark-quality issues:

1. **Within-family structural similarity.** The ten tasks in a family share a tool
   graph. This is useful for controlled variants but may overweight template
   recognition and should not be mistaken for ten independent archetypes.
2. **Normalized application interface.** BM25-style `search_workplace_records` and
   family-specific write tools flatten some real differences among Datadog, Linear,
   CRM, AP, and identity systems. This is intentional for the first collection so
   difficulty comes from evidence reconciliation rather than hidden API enums.
3. **No injected write failures yet.** Verification tasks where a downstream call
   fails or partially succeeds require additional environment behavior rather than
   data-only composition.
4. **Approval is always tool-backed.** This provides deterministic authorization,
   but the collection does not yet compare tool-backed approval with natural-language
   acknowledgement.
5. **Communication criteria need calibration.** Required completion facts are exact
   and should be inspected for unnecessary wording brittleness before model runs.
6. **Generated prose needs human review.** Names and requests are plausible but have
   not been reviewed one by one for organizational realism or accidental ambiguity.
7. **Evidence overload is not sufficient difficulty for the strongest tested
   model.** On the 50 paired hard-evidence tasks, GPT-6.1-sol xhigh retained 45/50
   exact DB completion. One additional zero was a user-simulator approval-tool
   violation; excluding it leaves the same effective exact-state rate as the clean
   collection. The hard corpus substantially increased retrieval work and token use,
   but did not create an AutomationBench-sized accuracy drop. See `RESULTS.md`.

## Suggested manual review procedure

Review two tasks from each family first: `_001` and `_003`. Together they cover the
main within-family branches, including SEV-1 versus SEV-2 correction, bank-only versus
overage controls, zero versus positive customer credit, training incomplete versus
complete, and multiple portfolio thresholds.

For each task, answer:

1. Does the opening request sound like a real employee message?
2. Is the user-private information genuinely owned by the requester?
3. Is every system fact discoverable, with a clear authoritative source?
4. Is the intended business outcome unique enough for exact-state grading?
5. Are prohibited side effects business-relevant?
6. Does the task test a decision rather than merely add record volume?
7. Would another legitimate final state be unfairly rejected?
8. Does the user simulator know too much, reveal too much, or approve too easily?

After that review, the next implementation pass should add new workflow blueprints
(people operations and compliance are the clearest gaps), failure-injection tasks,
and model-failure-derived cases rather than simply increasing the number of rows in
the five existing scenario banks.
