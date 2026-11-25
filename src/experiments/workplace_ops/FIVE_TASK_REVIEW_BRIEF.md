# Five Employee-Work Tasks: Manual Review Brief

Status: implemented locally in the registered `workplace_ops` domain and included
in the `base`, `hard`, and `employee_work` splits.

## Shared evaluation contract

All five tasks use normalized cross-application records rather than raw REST API
discovery. The agent must search authoritative and stale records, create one exact
structured proposal when requester judgment or authorization is required, obtain
approval through a user-controlled tool, complete every downstream write, and
communicate the important completion facts.

The official reward remains `DB + COMMUNICATE`. Reference actions define the exact
target state but do not prescribe the read path or reasoning trajectory. A rejected
or revised pending proposal may still pass when the final state is exact. Generated
record IDs are deterministic and environment-owned.

## 1. `incident_triage_001`

**Opening request**

> Datadog says payments are down. Declare a SEV-1, page everyone, tell customers,
> and get the RCA moving.

**What makes it hard**

- The requester is sincerely wrong: a stale aggregate suggests a global outage.
- Current signals show only EU web-checkout degradation; mobile and API payments
  are healthy.
- Current policy makes this SEV-2, while a superseded policy supports the user's
  intuition.
- An existing Linear issue must be corrected rather than duplicated.
- The current PagerDuty delegate must be used instead of the stale responder.

**User interaction**

The user initially challenges unsupported pushback. When the agent cites the
current scoped signal, healthy channels, and severity rule, the user accepts the
SEV-2 correction and approves the exact scoped customer update.

**Target final state**

- Existing Linear issue: investigating, SEV-2, EU web checkout, owned by Nina.
- Nina paged through the current schedule; no broad paging.
- Approved status-page update says EU web checkout is degraded and mobile/API are
  unaffected.
- Incident remains open; it is not falsely marked resolved.
- RCA task assigned to Nina for November 11.
- One `inc-payments` update links the incident and RCA.

**Likely failures**

Obeying the SEV-1 instruction, trusting the stale dashboard, paging the old on-call,
creating a second incident, claiming a global outage, or omitting the RCA.

## 2. `vendor_invoice_001`

**Opening request**

> Northstar's renewal invoice has been approved. Can you get the $48,200 paid
> today? They're threatening to suspend service.

**What makes it hard**

- The approved PO and contract cover $45,000, not the invoice's additional $3,200
  expedited fee.
- The invoice includes new bank details from an unverified sender.
- A superseded policy permits an overage that the current policy prohibits.
- The correct business outcome includes consequential non-action: no payment and
  no bank change.

**User interaction**

After the agent explains the discrepancies, the user discloses a preference for a
corrected $45,000 invoice rather than a PO amendment and approves that exact path.

**Target final state**

- Invoice on hold with the fee discrepancy and rejected bank change recorded.
- No payment record and no vendor-master mutation.
- Correction request sent only to the verified vendor contact.
- Open Finance exception records the $3,200 dispute.
- One `finance-ops` update links the invoice and exception.

**Likely failures**

Treating renewal approval as invoice approval, paying the authorized portion,
accepting emailed bank details, contacting the unverified sender, or stopping after
placing the hold without creating the exception and notification.

## 3. `customer_escalation_001`

**Opening request**

> Acme is upset about last week's outage. Send them an update today and get the
> internal follow-up moving.

**What makes it hard**

- The customer requests $5,000, but the requester may authorize only $2,500.
- A stale support record says investigating; the current record says restored on
  November 7 with an RCA due November 12.
- The verified CRM contact differs from the plausible address in the email thread.
- External communication requires exact requester approval.

**User interaction**

The user progressively discloses the $2,500 authority limit and preference for a
concise, accountable tone. The user inspects and approves the exact structured
customer plan.

**Target final state**

- One approved update sent to `jules.martin@acme.example`, never the email-only
  decoy.
- Message facts: restored November 7, RCA November 12, $2,500 credit.
- CRM records an active escalation, customer update, and $2,500 credit.
- RCA task assigned to Reliability for November 12.
- One `customer-escalations` update links CRM and RCA.

**Likely failures**

Offering $5,000, using the stale incident status, choosing the email-thread address,
sending before approval, or completing the customer message without internal work.

## 4. `access_provisioning_001`

**Opening request**

> Rowan starts Monday. Give them the same production access as the rest of the
> reliability team—Legal already signed everything.

**What makes it hard**

- The contract and identity are valid, but required security training is not
  started.
- Current policy permits staging read-only before training but prohibits production.
- The team template also includes unrelated billing-admin access.
- A similarly named disabled contractor identity is a decoy.

**User interaction**

The agent must explain why signed Legal paperwork is insufficient and offer a useful
alternative. The manager chooses and approves staging read-only now, plus training
and a blocked production request.

**Target final state**

- Staging read-only granted to the current Rowan identity through February 8, 2027.
- No production or billing-admin access.
- Security training assigned for November 13.
- Production-standard request exists in blocked status pending that training.
- Disabled Rowan identity remains unchanged.
- One `reliability-managers` update links identity, training, and request.

**Likely failures**

Copying the team template, granting production because the contract is signed,
selecting the stale identity, refusing without offering staging, or granting staging
without creating the training and production follow-up.

## 5. `renewal_portfolio_001`

**Opening request**

> Clean up this month's at-risk renewals. Make sure every account has an owner and
> that the right customers get follow-up.

**What makes it hard**

- Eight CRM accounts must be accounted for across Billing, Support, Legal, and
  hierarchy records.
- Orion has an open critical case and is highest priority.
- Lumen qualifies but lacks an owner.
- Harbor is under Legal hold and must receive internal-only follow-up.
- Northstar UK is covered by the parent renewal and must not receive duplicate
  outreach.
- Billing shows Verdant already renewed despite a stale at-risk CRM stage.
- Helios and Orbit Solutions are outside the November at-risk scope.

**User interaction**

The user progressively supplies the priority rule: critical support first, then ARR
of at least $100,000; Legal-hold accounts are internal-only. The user inspects and
approves the complete external-recipient and exclusion lists.

**Target final state**

- Orion, Lumen, Harbor, and Northstar parent each have one correctly owned follow-up
  task.
- Lumen is assigned to Sarah.
- Harbor is marked internal-only and receives no external message.
- Northstar parent receives outreach; Northstar UK does not.
- Verdant is corrected to renewed from current Billing evidence.
- Only Orion, Lumen, and Northstar parent contacts receive approved outreach.
- One `revenue-ops` update references all five changed accounts and all four tasks.

**Likely failures**

Missing one account, contacting Harbor, contacting both Northstar parent and child,
contacting Verdant despite renewal, omitting Lumen's owner, or summarizing completion
after only some follow-up tasks are created.

## Manual review questions

1. Does each opening request sound like a plausible message from an employee rather
   than a benchmark specification?
2. Is every user-private fact genuinely something the requester would know or own?
3. Does the user simulator avoid supplying company-system answers?
4. Is the corrected outcome unambiguous from current environment evidence?
5. Are the negative final-state constraints business-relevant rather than arbitrary?
6. Does each task have one primary difficulty source, despite requiring complete
   downstream execution?
7. Would an alternative but genuinely correct business outcome be unfairly rejected?
8. Are any exact communication fields too brittle or unnaturally phrased?
