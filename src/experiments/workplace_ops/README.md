# Workplace Operations Domain Prototype

Status: the registered `workplace_ops` domain now contains the two Nimbus kickoff
calibration tasks, five hand-authored employee-work archetypes, and 50 deterministic
generated review candidates. Its code lives in `src/tau2/domains/workplace_ops/`,
with data in `data/tau2/domains/workplace_ops/`. The generated collection is an
authoring and review milestone, not a publication-ready frozen benchmark; see
`GENERATED_COLLECTION_REVIEW.md` for coverage and known limitations.

`tasks.prototype.json` preserves the original two-task design sketch; it is not the
task set loaded by `tau2 run`. The runnable Task 1 definition is
`data/tau2/domains/workplace_ops/tasks.json`.

## Benchmark thesis

The proposed domain evaluates whether an AI employee can turn an incomplete human
request into policy-compliant, verifiable work across organizational knowledge and
multiple workplace applications.

The central decision is not only which tool to call. The agent must decide whether
to ask the user, search the environment, consult policy, propose a plan, request
approval, or act.

## Runnable task set

| Task | Primary capability | User interaction |
| --- | --- | --- |
| `workplace_kickoff_001` | Scheduling smoke test | Progressive preference and exact approval |
| `workplace_kickoff_002` | Evidence reconciliation and exhaustive preparation | Conditional preference, delegation, and exact approval |
| `incident_triage_001` | Operational triage and evidence-grounded correction | User begins with the wrong severity and scope |
| `vendor_invoice_001` | Financial controls and consequential non-action | User chooses a compliant exception path |
| `customer_escalation_001` | Authority-bound external communication | User discloses credit authority and approves the exact plan |
| `access_provisioning_001` | Dependency gating and least privilege | User selects a productive compliant alternative |
| `renewal_portfolio_001` | Exhaustive portfolio processing | User supplies prioritization and approves the outreach batch |

The five employee-work tasks are stored separately in `tasks_additional.json` for
reviewability and loaded into the same registered domain and `base` split.

The 50 generated candidates are stored in `tasks_generated.json`, reproduced by
`src/tau2/domains/workplace_ops/task_generator.py`, and exposed through the
`generated_review` and per-family splits. The `candidate_57` split combines them
with the seven hand-authored tasks. Following initial manual review, `base` now
contains the same 57 tasks for calibration runs; `anchors_7` preserves the original
hand-authored set.

## Original two-task rationale

The two prototype tasks deliberately share the same broad environment but isolate
different interactive capabilities.

| Task | Primary capability | User-private information | Consequential approval |
| --- | --- | --- | --- |
| `workplace_kickoff_001` | Scheduling and coordination from an incomplete request | Preferred meeting window | Approval of exact meeting proposal |
| `workplace_escalation_001` | Customer escalation across CRM, support, email, and policy | Credit authority and communication preference | Approval of exact customer draft |

Both tasks require the agent to distinguish information that should be searched for
from information that only the user can supply. The simulated user is not an answer
oracle: it reveals private information only in response to a relevant question and
uses an approval tool only after inspecting a concrete proposal.

## Task 1 walkthrough: Nimbus kickoff

The user initially asks:

> Can you organize the Nimbus kickoff for next week and get the team ready?

The environment contains two versions of the project brief, calendars, an employee
directory, a project tracker, and chat channels. The current brief says Nimbus has an
external pilot, which triggers a policy requiring internal Legal attendance while
prohibiting external attendees until Legal clears the pilot.

The user privately prefers Wednesday morning but does not state that preference
unless the agent asks. The intended interaction is:

1. Find the current brief and applicable scheduling policy.
2. Determine the required internal attendees and available slots.
3. Ask the user for a scheduling preference.
4. Create a concrete proposal for Wednesday, November 11, 2026 from 10:00-10:45 AM
   Pacific, including Legal but no external attendee.
5. Ask the user to approve that proposal.
6. After the user calls `approve_meeting_proposal`, schedule the meeting, create the
   Legal preparation task, and post the internal update.

The official score should not inspect whether the agent asked for the preference,
which brief it read, or which search path it followed. If the agent happens to guess
the correct preference and the user approves the resulting proposal, that is a valid
trajectory.

The task passes only when the predicted agent and user databases exactly match the
state produced by replaying the reference writes, and the required completion facts
are communicated. For Task 1, the exact target state is:

| State area | Required final state |
| --- | --- |
| User approvals | `proposal_1` is the only approved meeting proposal |
| Meeting proposals | Exactly one proposal exists, for November 11 from 10:00-10:45 AM Pacific with Maya, Priya, Mateo, and Jordan |
| Calendar | Exactly one new Nimbus event exists and matches the approved proposal |
| Attendees | The attendee set is exact; the external pilot contact is absent |
| Project tracker | Exactly one new task exists: the Legal review packet, owned by Jordan and due November 10 |
| Team chat | Exactly one new Nimbus update records the meeting time, preparation owner, and due date |
| Unrelated state | Documents, directory records, and all unrelated application state are unchanged |

Any missing, additional, or incorrect write causes a DB mismatch. Examples include a
duplicate event, a wrong time or attendee, an external invitation, a missing Legal
task, an extra project task, or an unrelated record mutation.

Approval timing is enforced by the environment rather than by trajectory grading:
`schedule_approved_meeting` rejects a proposal unless its ID is already present in
user-controlled approval state. A rejected early attempt followed by a correct,
approved schedule may still pass because it leaves the exact target end state.

## Task 2 walkthrough: Acme escalation

The user initially asks:

> Acme is upset about last week's outage. Send them an update today and get the
> internal follow-up moving.

The environment contains the Acme CRM record, a customer email requesting a $5,000
credit, the resolved support incident, the current customer-communications policy,
and internal project/chat systems.

The user privately has authority to approve at most $2,500 and requires review of an
external draft before it is sent. The intended interaction is:

1. Reconcile the customer request, CRM record, incident status, and policy.
2. Ask what credit amount the user is authorized and willing to approve.
3. Draft an update stating that service was restored on November 7, that the RCA is
   due November 12, and that a $2,500 credit is offered without promising the
   requested $5,000.
4. Ask the user to review and approve the exact draft.
5. After `approve_customer_draft`, send it to the verified customer contact, update
   CRM, create the RCA task, and post the internal escalation update.

This task should fail if the agent promises $5,000, sends before approval, emails a
decoy address, describes the incident as unresolved, or omits internal follow-up.

## Tool boundary

Task 1 uses a deliberately small normalized interface. This keeps the first
experiment focused on user interaction, policy application, and cross-application
completion. Raw REST schemas and tool discovery can be introduced later as explicit
ablations instead of being confounded with the first user-control experiment.

Agent read tools:

- `search_documents`, `get_document`
- `list_employees`, `get_calendar_availability`

Agent proposal and write tools:

- `create_meeting_proposal`, `schedule_approved_meeting`
- `create_project_task`, `post_project_update`

User tools:

- `get_pending_meeting_proposals`, `approve_meeting_proposal`

The meeting-proposal record is shared by the agent and user toolkits, but only the
user tool can set its approval field. The scheduling tool rejects unapproved proposal
IDs. This makes authorization an environment property rather than something inferred
from conversational phrasing alone.

Task 2's email, CRM, support, and customer-draft tools remain conceptual and are not
registered in the runnable domain.

## Evaluation approach

Task 1 uses the standard `DB + COMMUNICATE` reward basis. Tau2 replays the reference
actions in a fresh environment, hashes both the agent and user databases, and compares
those hashes with the predicted end state. The action list is one way to produce the
target state; it is not a required trajectory.

The environment assertions remain as non-gating diagnostics so a failed run can show
which important invariant was missed. They do not replace exact DB equality and do
not penalize alternative read or reasoning paths.

## Questions after the Task 1 pilot

1. Should the next version add searchable app actions or raw REST-like schemas as an
   explicit tool-discovery ablation?
2. Should every consequential action require a user-side approval tool, or only
   actions that communicate externally, spend money, or disclose information?
3. Should the official reward use only deterministic environment assertions, or is
   a semantic communication check acceptable as a gate?
4. Is `workplace_ops` the right domain boundary, or should the first contribution be
   narrower, such as `project_operations`?
5. Should the benchmark require the agent to produce a structured document artifact
   in the first version, or defer artifact evaluation until the interaction and
   multi-application state model are stable?
