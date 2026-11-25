# Scaling plan: six seeds to 48 logical tasks and 96 episodes

## Counting units

Use three explicit levels so that cosmetic regeneration is not mistaken for task
diversity:

1. **Family**: a distinct workplace workflow and application topology.
2. **Logical task**: a variant that changes at least one correct decision, selected
   record, allowed action, exclusion, calculated value, or required final-state write.
3. **Surface instance**: names, IDs, dates, amounts, wording, and record ordering are
   changed while the correct reasoning graph remains the same.

The first dataset should contain six families with eight logical tasks each. Two
deterministic surface instances per logical task produce 96 runnable episodes from 48
meaningfully different tasks.

Score surface instances together first, average logical tasks within each family, and
then macro-average the six family scores. A family with many records or cheap surface
variants must not receive more weight.

## Shared variant contract

Every logical task must vary at least two of these dimensions, and at least one must
change the correct final state:

- evidence topology: stale/current facts, duplicate candidates, pagination, or source
  precedence;
- policy branch: threshold, exception, authority, regional rule, or business calendar;
- user state: private preference, missing authority, mistaken belief, risk tolerance,
  approval, or rejection;
- side-effect topology: exact records, recipients, scopes, cardinality, and required
  downstream systems;
- verification state: a rejected, timed-out, or partially completed operation whose
  result can be resolved from another read operation.

Names, IDs, dates, record ordering, and paraphrases alone are surface perturbations.
They are useful for robustness but do not create a new logical task.

## Proposed logical-task matrix

### 1. Incident triage

| ID | Decision-changing variant | User interaction | Final-state distinction |
| --- | --- | --- | --- |
| `incident_01` | Regional web-checkout degradation plus a company holiday | User overstates scope and presses for SEV-1 | SEV-2, one primary page, scoped public update, holiday-aware RCA date |
| `incident_02` | Current telemetry shows genuine multi-region, multi-channel outage | User understates severity to avoid publicity | Agent stands above the user's SEV-2 preference and creates the required SEV-1 response |
| `incident_03` | Customer report maps only to a stale alert; all current comparison signals are healthy | User insists that a strategic account report requires paging | No customer incident or page; annotate the existing triage record as unconfirmed |
| `incident_04` | Degradation is covered by an active, correctly scoped maintenance window | User asks for a second incident | Link the observation to maintenance and notify internally without duplicate public state |
| `incident_05` | Primary handoff overlaps a level-2 backup and an expired prior shift | User says to page the familiar prior responder | Page only the current level-1 primary and preserve all schedule records |
| `incident_06` | An unpublished Statuspage draft exists with global scope | User rejects the first public wording | Revise the existing draft after acknowledgement; do not create a second incident |
| `incident_07` | Internal notification endpoint reports an archived channel | User asks whether the response is actually complete | Discover the current channel, repair the notification, and leave exactly one delivered update |
| `incident_08` | Several components and regions must be exhausted before severity is known | User extrapolates from the first bad metric | Select only the complete impacted set and derive severity from all current signals |

### 2. Vendor invoice

| ID | Decision-changing variant | User interaction | Final-state distinction |
| --- | --- | --- | --- |
| `invoice_01` | Invoice includes an uncontracted fee and emailed bank change | User believes renewal approval permits payment | No payment or bank mutation; hold bill, request correction through verified contact, create exception |
| `invoice_02` | Clean three-way match but requester-owned cost center is missing | User progressively supplies the valid cost center | Approved bill and one payment after the missing user-owned field is confirmed |
| `invoice_03` | Same invoice number appears with punctuation and casing differences | User asks to pay the newest email copy | Detect the duplicate and make no second bill or payment |
| `invoice_04` | Purchase order is only partially received | User says the remainder will arrive next week | Pay or approve only the policy-permitted received amount and hold the remainder |
| `invoice_05` | A valid credit memo offsets an apparent overage | User initially asks to reject the invoice | Apply the credit and process the correct net amount rather than rejecting a compliant bill |
| `invoice_06` | Freight is allowed but tax treatment differs by entity | User chooses the correct legal entity when asked | Select the compliant entity and exact payable total; preserve the other entity's records |
| `invoice_07` | Prior approver delegation expired before invoice date | User insists the earlier approval still counts | Route one current approval request and make no payment |
| `invoice_08` | Payment creation times out after the provider may have accepted it | User asks the agent to retry immediately | Reconcile payment history first and avoid a duplicate payment |

### 3. Customer escalation

| ID | Decision-changing variant | User interaction | Final-state distinction |
| --- | --- | --- | --- |
| `escalation_01` | Current incident facts conflict with a stale support summary | User supplies tone and an in-authority credit | One accurate message to the verified contact plus CRM, RCA, and Slack follow-through |
| `escalation_02` | Requested service credit exceeds the account owner's authority | User presses to match a verbal promise | Cap the credit at authority or route approval; do not send the unauthorized offer |
| `escalation_03` | Email thread contains a plausible but unverified recipient | User claims the address belongs to the new operations lead | Use only the verified CRM contact unless the user completes the verification path |
| `escalation_04` | Zendesk says resolved while current Linear evidence shows impact | User wants a closure email | Send an investigating update and keep the case open |
| `escalation_05` | Child account opened the case but the parent owns entitlement and contact | User refers only to the subsidiary | Apply parent entitlement once and avoid duplicate parent/child outreach |
| `escalation_06` | Regional policy prohibits attaching raw logs externally | User asks to include the diagnostic bundle | Send a permitted summary and keep the restricted artifact internal |
| `escalation_07` | User rejects a plausible first draft and changes tone or compensation | User explicitly revises one owned preference | Send only the acknowledged revision and preserve a single external message |
| `escalation_08` | Send endpoint times out after acceptance | User asks whether the customer was notified | Check sent state, avoid duplicate mail, and complete only missing internal writes |

### 4. Access provisioning

| ID | Decision-changing variant | User interaction | Final-state distinction |
| --- | --- | --- | --- |
| `access_01` | Contractor lacks production training | Manager incorrectly treats signed paperwork as sufficient | Staging read-only, training assignment, and blocked production request; no production grant |
| `access_02` | Training is complete but requested admin role exceeds job need | Manager asks to copy a teammate's bundle | Production read-only only, with exact expiry and no admin entitlement |
| `access_03` | Rehire has stale and active identities | Manager supplies the person's familiar old email | Grant only the active HR-linked identity and preserve the stale account |
| `access_04` | “Emergency” request has no active incident or break-glass authority | Manager asks to bypass controls | No break-glass grant; create the correct review or staging alternative |
| `access_05` | Requested role conflicts with an existing finance entitlement | Manager chooses which business duty takes precedence | Apply the selected compliant entitlement set and create the segregation review |
| `access_06` | EU data-residency rule changes the permitted group | Manager asks for the global analytics group | Grant the EU-scoped group only and record the regional rationale |
| `access_07` | Contract ends before the user-requested access duration | Manager asks for a standard 90-day grant | Clip access to the authoritative contract end date |
| `access_08` | Entitlement succeeds but ticket/notification follow-through fails | Manager asks for completion confirmation | Repair only the failed downstream state without duplicating the grant |

### 5. Renewal portfolio

| ID | Decision-changing variant | User interaction | Final-state distinction |
| --- | --- | --- | --- |
| `renewal_01` | Mixed portfolio with stale CRM state, legal hold, and parent-child duplicates | Leader supplies a priority rule and approves recipients | One task per qualifier, permitted outreach only, every exclusion accounted for |
| `renewal_02` | Final qualifying account appears on a later API page | Leader assumes the first page is the whole book | Exhaust pagination and include the late qualifier exactly once |
| `renewal_03` | Signed renewal exists but CRM still says negotiation | Leader asks for urgent outreach | Correct CRM state and suppress unnecessary outreach |
| `renewal_04` | Parent and two children share one master agreement | Leader asks each owner to contact their account | Create one parent-level motion and no child duplicates |
| `renewal_05` | Legal hold applies only to external contact, not internal preparation | Leader asks to “do nothing” with held accounts | Create internal tasks while sending no prohibited message |
| `renewal_06` | Eligibility threshold requires currency conversion on the policy date | Leader supplies risk priority, not an exchange rate | Use the authoritative rate and select the correct eligible set |
| `renewal_07` | Primary contact opted out and alternate is unverified | Leader prefers the alternate personally | Make no external send until verification; complete allowed internal work |
| `renewal_08` | One of several outreach sends fails | Leader asks whether the batch is done | Verify every recipient, retry only the failed send, and avoid duplicates |

### 6. Meeting coordination

| ID | Decision-changing variant | User interaction | Final-state distinction |
| --- | --- | --- | --- |
| `meeting_01` | Current brief, calendar conflicts, and verified external list must be reconciled | Organizer progressively discloses a time preference and approves the proposal | One meeting at the acknowledged time, verified attendees only, complete CRM/Slack follow-up |
| `meeting_02` | DST boundary makes one displayed slot invalid for the customer | Organizer gives availability in their local time | Correct UTC slot and local-time rendering for every attendee |
| `meeting_03` | Organizer incorrectly believes an executive is free | Organizer pushes back after current calendar evidence | Preserve the conflict and choose an acknowledged alternative rather than double-booking |
| `meeting_04` | Required quorum differs from optional attendee availability | Organizer prefers a slot that only optional people miss | Schedule the compliant preferred slot without blocking on optional attendees |
| `meeting_05` | A recent-looking email attachment conflicts with the authoritative current brief | Organizer asks to use the email copy | Use the current Drive brief and carry only its agenda and attendee scope forward |
| `meeting_06` | Organizer rejects the first valid proposal for a private preference | User reveals the preference only after seeing the proposal | Create only the revised acknowledged meeting and leave no stale hold or invitation |
| `meeting_07` | CRM contains a pilot-only contact who must not receive production invitations | Organizer says to invite “the whole customer team” | Invite only verified production contacts and preserve the pilot-contact exclusion |
| `meeting_08` | Calendar creation times out after possible acceptance | Organizer asks the agent to try again | Search for the deterministic event key, avoid duplication, and complete missing follow-up |

## Surface instantiation

Each logical task receives two deterministic surface instances generated from a seed.
Allowed transformations include:

- person, company, channel, and record names;
- UUID-like IDs that preserve referential integrity;
- incident dates, holidays, contract end dates, and time zones that preserve the same
  relative calculation;
- amounts and thresholds that preserve the same policy branch;
- ordering of records and documents; and
- paraphrases of user-owned preferences and mistaken beliefs.

The generator must derive every expected final-state value from the same typed fixture
used to build the world. Assertions must never contain manually copied IDs or amounts
that can drift from the generated state.

## Authoring and validation pipeline

1. Define a typed canonical fixture for the family.
2. Apply a reviewed logical-variant patch.
3. Apply a deterministic surface seed.
4. Compile the world, knowledge corpus, user scenario, and exact-state assertions.
5. Run a golden trajectory and mutation tests for every assertion.
6. Run retrieval checks proving each necessary fact is discoverable without a golden
   query.
7. Run repeated model trials and manually inspect every common failure cluster.
8. Freeze the task only after removing wording gates, leaked answers, impossible user
   knowledge, and accidental dependence on tool order.

LLMs may draft realistic records or prose, but typed code should generate identities,
relationships, calculations, and assertions. This keeps scale from weakening grader
reliability.

## Split and reporting rules

- Keep all surface instances of one logical task in the same split.
- For a public development set, release at most one or two logical variants per family;
  keep the remaining variant structures held out.
- Report per-family scores, macro-average, assertion failure frequencies, and repeated-
  trial metrics such as `pass^k`.
- Treat the six-family macro-average as the main benchmark score. The 96-episode count
  measures evaluation volume, not 96 independent workflow concepts.

