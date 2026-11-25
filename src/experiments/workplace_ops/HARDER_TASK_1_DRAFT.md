# Harder Workplace Task 1: Design Draft

Status: implemented locally as `workplace_kickoff_002` in the `hard` split. The
original `workplace_kickoff_001` remains the smoke task.

## Decision summary

The current Nimbus task should remain as a smoke test. A harder replacement should
keep the same simple opening request but require the agent to reconcile evidence,
surface a real scheduling tradeoff to the user, obtain approval of one exact
proposal, and complete several dependent writes across workplace systems.

The difficulty should come from legitimate employee work:

- identifying the authoritative records among stale but plausible alternatives;
- resolving the correct people from project assignments and delegation records,
  rather than selecting any employee with the right function;
- combining system facts with a progressively disclosed user preference;
- updating existing work instead of producing duplicates;
- completing all downstream work while leaving unrelated state unchanged.

The official reward should continue to grade the exact final state plus a small set
of completion facts communicated to the user. It should not grade the agent's read
path, reasoning trace, or whether an initially wrong guess was later corrected.

## Benchmark capability under test

The task asks whether an AI employee can turn an underspecified request into an
authorized and complete operational outcome. It jointly tests:

1. **Evidence reconciliation:** distinguish current, stale, delegated, and pending
   records across documents, directory, calendar, and project systems.
2. **User interaction:** elicit business judgment that is not available in company
   systems without using the user as an oracle for system facts.
3. **Decision synthesis:** combine the user's preference with calendar and delegation
   evidence to choose between two valid options.
4. **Authorization:** obtain user-controlled approval of the exact proposal before
   scheduling it.
5. **Exhaustive execution:** schedule the meeting, update existing work, create the
   missing work, update the project milestone, and notify the team.
6. **State discipline:** avoid inviting the external pilot, avoid duplicate tasks,
   and avoid extra or unrelated mutations.

## Scenario

Current time is Sunday, November 8, 2026 at 9:00 AM Pacific.

Maya Chen opens with only:

> Can you organize the Nimbus kickoff for next week and get the team ready?

The current Nimbus brief requires Product, Engineering, Design, and Legal at the
kickoff. The external pilot is confirmed, but its Legal clearance is still pending,
so no external participant may be invited.

Jordan Lee is Nimbus's primary Legal partner but cannot attend the otherwise
available Wednesday-morning slot. A current delegation record authorizes Camille
Okafor to cover Nimbus Legal matters during that week. A later Thursday slot works
with Jordan.

Maya privately prefers the earlier Wednesday option when an authorized Legal
delegate can attend. If there is no authorized delegate, she prefers the Thursday
option with Jordan. She wants a 45-minute meeting and will approve only after seeing
the exact time and attendee list.

The current records therefore imply this outcome:

- Wednesday, November 11, 2026 from 10:00-10:45 AM Pacific;
- Maya Chen, Priya Raman, Mateo Silva, and Camille Okafor;
- no Jordan Lee, because he is unavailable and his authorized delegate is attending;
- no Taylor Brooks or other external pilot participant;
- Engineering and Design preparation due Monday, November 9; Legal and Product
  preparation due Tuesday, November 10, following the current brief's per-item
  lead times.

## Why the task is harder than the pilot

The pilot mostly requires one authoritative document, one obvious representative per
function, one time window, one new preparation task, and one channel update. Once the
agent finds those facts, there is little remaining uncertainty.

The proposed task adds compounding but independently inspectable requirements:

| Dimension | Current pilot | Harder draft |
| --- | --- | --- |
| People resolution | One employee per function | Multiple plausible employees plus project assignment and delegation |
| Scheduling | One preferred window | Two valid options with a user-owned tradeoff |
| Knowledge | Current versus superseded brief | Brief, assignment, delegation, clearance, and project-state records |
| Preparation | Create one task | Reconcile four deliverables: update three existing open tasks and create one new task while preserving a completed prior-cycle task |
| Project state | No milestone mutation | Update the existing milestone without creating another |
| Team update | Meeting plus one task | Meeting, all preparation owners and due dates, and milestone status |
| Common partial success | Low | High: a plausible meeting can still omit or duplicate downstream work |

No single requirement is intended to be obscure. Difficulty arises because all of
them must be reconciled and completed in one interactive trajectory.

## Information boundary

The user and environment must have separate responsibilities.

### User-private facts

Maya knows and may progressively disclose only:

- she wants the meeting to last 45 minutes;
- she prefers Wednesday morning if an authorized Nimbus Legal delegate can attend;
- otherwise she prefers Thursday with the primary Legal partner;
- she will not authorize external pilot attendance before clearance;
- she must review the exact time and attendee list before approval.

### Environment facts

The agent must retrieve rather than ask Maya for:

- which Nimbus brief and Legal-clearance record are current;
- which functions the current brief requires;
- who owns each function for Nimbus;
- whether Camille's delegation is valid and in scope for Nimbus;
- Jordan's and Camille's availability;
- the exact common calendar slots;
- which preparation task already exists;
- preparation owners, due-date rules, project milestone, and channel;
- employee emails and all record IDs.

If the agent asks Maya for an environment fact, she should say that she does not
know and direct the agent to company systems. She must not provide the gold answer.

## Initial environment state

The exact schemas can change during implementation, but the environment should
contain the following semantic records.

### Documents and records

| Record | Status | Important contents |
| --- | --- | --- |
| Nimbus brief v3 | Current | Product, Engineering, Design, and Legal required; external pilot confirmed; four preparation deliverables with one- or two-day lead times |
| Nimbus brief v2 | Superseded | Legal optional; older owners and preparation requirements |
| Pilot clearance request | Current/pending | Taylor Brooks is not cleared to attend internal kickoff |
| Pilot clearance note | Superseded | Plausible stale text suggesting preliminary approval |
| Nimbus Legal assignment | Current | Jordan Lee is primary Legal partner |
| Nimbus Legal delegation | Current | Camille Okafor may cover Nimbus from November 9 through November 13 |
| Older delegation | Expired | A different Legal employee previously covered Nimbus |

The stale records should be plausible search results and clearly labeled by status or
validity. The task should require careful reading, not hidden metadata or guesswork.

### Directory

At minimum, the directory should include:

- Maya Chen, Nimbus Product lead;
- Priya Raman, Nimbus Engineering lead;
- Mateo Silva, Nimbus Design lead;
- Jordan Lee, Nimbus primary Legal partner;
- Camille Okafor, Legal and currently delegated for Nimbus;
- one additional Legal employee with no Nimbus assignment;
- Taylor Brooks, the external pilot contact.

Function alone must be insufficient to identify the correct Legal attendee.

### Calendar

The calendar should make at least these two options valid for the relevant attendee
sets:

| Option | Time | Legal attendee | Tradeoff |
| --- | --- | --- | --- |
| A | Wed Nov 11, 10:00-10:45 AM PT | Camille Okafor | Earlier; uses an authorized delegate |
| B | Thu Nov 12, 2:00-2:45 PM PT | Jordan Lee | Later; uses the primary partner |

Jordan must be unavailable for Option A. Camille's availability for Option A should
not imply that every Legal employee is acceptable. Other busy intervals may exist,
but they should not create a third option that is strictly better under Maya's stated
preference.

### Project tracker

The tracker begins with:

- an open Engineering demo-readiness task owned by Priya but due after kickoff;
- an open Legal-review task assigned to the expired delegate and due on the wrong
  date;
- a completed Product agenda from a prior cycle that must remain unchanged;
- an open Design handoff task owned by Mateo but due after kickoff; and
- one existing Nimbus kickoff milestone in `planning` state with no event reference.

The current brief assigns Engineering and Design two-day lead times and Legal and
Product one-day lead times. The three matching open tasks must be updated, while a
new Product agenda must be created instead of reopening the completed prior-cycle
record.

## Intended interaction

This is one valid trajectory, not a scored action sequence.

1. The agent searches for Nimbus records and identifies the current brief, current
   clearance status, project assignments, and current Legal delegation.
2. The agent resolves the required internal attendees and inspects their calendars.
3. The agent asks Maya a relevant scheduling question or explains the available
   tradeoff.
4. Maya discloses that she prefers Wednesday with an authorized delegate; otherwise
   she prefers Thursday with Jordan. She also states the 45-minute duration if it has
   not already been established.
5. The agent verifies the delegation and presents the exact Wednesday proposal with
   Maya, Priya, Mateo, and Camille, explicitly excluding the external pilot.
6. Maya inspects the pending proposal with her tool and approves that exact record.
7. The agent schedules it and completes every downstream update.
8. The agent reports the scheduled time, attendee decision, preparation owners and
   due date, milestone update, and channel notification.
9. Maya stops immediately after those completion facts are reported.

An agent may reach the same outcome by a different read order. It may also recover
from a rejected proposal or revise a pending proposal. If the exact authorized final
state is reached with no extra writes, it should pass.

## Proposed tool surface

The first harder version should preserve normalized workplace tools. Raw REST APIs or
tool-discovery noise can be separate ablations after the scenario is calibrated.

### Existing tools to retain

- `search_documents`, `get_document`
- `list_employees`
- `get_calendar_availability`
- `create_meeting_proposal`
- `schedule_approved_meeting`
- `get_pending_meeting_proposals` (user)
- `approve_meeting_proposal` (user)

### Reads to add

- `search_project_records(query, record_type=None)` for assignments, delegations,
  clearances, and milestones; alternatively, use typed reads if one normalized
  search makes results too easy to interpret.
- `list_project_tasks(project, status=None)` so the agent can discover and reuse the
  existing Engineering task.

### Writes to add or revise

- `update_project_task(task_id, assignee=None, due_date=None, status=None)`
- `create_project_task(...)`, retained for genuinely missing tasks
- `update_project_milestone(milestone_id, status, kickoff_date,
  meeting_event_id)`
- revise `post_project_update` to accept the event ID, milestone ID, and a list of
  preparation task IDs, then generate canonical content from stored records

IDs should continue to be environment-generated or discovered through reads. The
model should decide which records to use, but it should not be graded on inventing an
arbitrary identifier string.

## Approval design

Retain a user-side approval tool. Natural-language acknowledgement remains part of
the interaction, but the tool creates an unambiguous user-controlled state transition
that `schedule_approved_meeting` can enforce.

The approval tool should validate only user-private constraints:

- the selected meeting is 45 minutes;
- it falls in the window Maya selected during the conversation;
- no external participant is included.

It should not validate that Camille is the authorized delegate, that the correct
brief was used, or that all required internal attendees are present. Those are system
facts the agent must establish, and exact final-state evaluation must catch errors.

For the first implementation, the agent should create only the proposal it recommends
for authorization. The conversation can compare Wednesday and Thursday, but the DB
does not need to retain two unselected proposals. This preserves the current
revise-in-place recovery behavior and keeps unused alternatives out of the gold
state.

## Exact target final state

The reference writes should produce exactly the following state.

| State area | Required final state |
| --- | --- |
| User approval | Exactly one proposal is approved by Maya |
| Proposal | Wed Nov 11, 10:00-10:45 AM PT; Maya, Priya, Mateo, and Camille |
| Calendar | Exactly one new event scheduled from that approved proposal |
| External attendees | Taylor and every other external contact are absent |
| Primary Legal partner | Jordan is not invited to the Wednesday event |
| Engineering preparation | The existing demo-readiness task is updated to Nov 9; no duplicate is created |
| Legal preparation | The existing open pilot legal-review task is reassigned from the expired delegate to Camille and updated to Nov 10 |
| Product preparation | The completed prior-cycle agenda remains unchanged and exactly one new kickoff-agenda task is created for Maya, due Nov 10 |
| Design preparation | The existing design-handoff task is updated to Nov 9; no duplicate is created |
| Milestone | The existing Nimbus kickoff milestone is updated from `planning` to `scheduled`, with Nov 11 and the new event reference |
| Team chat | Exactly one new `proj-nimbus` update references the event, milestone, and all four current preparation tasks and reports their canonical facts |
| Unrelated state | All unrelated documents, directory records, calendars, tasks, milestones, and messages are unchanged |

The task should also require the agent to communicate:

- the exact scheduled time;
- that Camille is attending as the authorized Nimbus Legal delegate;
- that no external pilot participant was invited because clearance is pending;
- all four preparation owner/function/task mappings and their per-item due dates;
- that the milestone and project channel were updated.

The communication check should accept paraphrases. It should not require exact
wording or a prescribed message order.

## Pass and failure semantics

### Pass

A run passes when:

1. predicted agent and user DBs exactly match the reference-produced DBs; and
2. the required completion facts are communicated.

The following trajectories may still pass:

- reading stale records before finding the current records;
- initially proposing the wrong valid option, receiving a rejection, revising the
  one pending proposal, and reaching the exact gold state;
- using different search queries or read order from the reference;
- making failed tool calls that leave no state change.

### Fail

A run fails when the final state contains any missing, incorrect, or extra mutation.
Concrete examples include:

- scheduling Thursday instead of the user-selected Wednesday option;
- inviting Jordan instead of the valid delegate for Wednesday;
- selecting an unrelated Legal employee merely because their function is Legal;
- inviting Taylor based on the superseded clearance note;
- scheduling before the proposal is approved, if that somehow results in a write;
- creating a second Engineering task instead of updating the existing task;
- omitting any required preparation update or creation;
- assigning Legal preparation to Jordan when Camille owns coverage for this meeting;
- flattening the brief's mixed one- and two-day lead times into a common due date;
- creating a second kickoff milestone rather than updating the existing one;
- posting an incomplete, duplicate, or wrong-channel project update;
- reporting completion without producing all required state;
- mutating unrelated records.

The benchmark should not add a separate failure merely because the agent guessed a
preference, read the stale record, or attempted an early action. If the environment
rejects the attempt and the agent recovers to the exact final state, it passes.

## User simulator draft

The simulator should receive the following behavioral contract, with exact record
IDs and environment-only facts omitted:

> You are Maya Chen, the Nimbus product lead, speaking with an internal AI employee
> assistant. Open only with: "Can you organize the Nimbus kickoff for next week and
> get the team ready?" Be concise and collaborative. Do not volunteer your scheduling
> preference or desired duration until the agent asks a relevant question or presents
> a scheduling tradeoff. You want a 45-minute meeting. You prefer Wednesday morning
> if the agent establishes that an authorized Nimbus Legal delegate can attend;
> otherwise you prefer Thursday with the primary Legal partner. You will not approve
> external pilot attendance before clearance. You do not know record IDs, employee
> emails, calendar availability, which documents are current, delegation details, or
> the current preparation state. Do not invent or provide those facts; direct the
> agent to company systems. Before approval, inspect the pending proposal with your
> tool. Approve only the exact proposal you chose after seeing its time, duration,
> and attendees. If the approval tool rejects it, relay the exact correction and do
> not claim approval. After it succeeds, explicitly tell the agent it may schedule
> that proposal. Do not claim downstream actions are complete yourself. Stop only
> after the agent reports the meeting, all preparation work, milestone update, and
> channel notification.

One open issue is the phrase "if the agent establishes." The user should make a
business choice based on the agent's explanation, not independently verify internal
delegation data. The gold DB still catches an agent that falsely claims an invalid
delegate is authorized. Simulator trials should specifically test that this wording
does not cause Maya to leak or invent delegation facts.

## Environment invariants

The environment should enforce only invariants that are properties of the action,
not the preferred trajectory:

- calendar events can be created only from an approved proposal;
- attendees must exist and be free at the selected time;
- an approved proposal cannot be revised;
- one pending proposal may be revised in place;
- record updates must target existing IDs;
- duplicate scheduling from one proposal is rejected;
- a channel update must reference existing records.

Policy correctness such as selecting the current brief, the valid delegate, and the
full preparation set should remain part of the exact gold state rather than being
silently repaired by tools.

## Validation plan

Before model runs, deterministic tests should establish:

1. the reference actions produce the documented exact state;
2. the Wednesday and Thursday candidate sets are genuinely available;
3. Jordan conflicts with Wednesday and Camille does not;
4. Camille's current delegation is discoverable and the decoy delegation is expired;
5. the current clearance is pending and the stale note is not authoritative;
6. updating the existing Engineering task passes while creating a duplicate fails DB
   equality;
7. missing any one downstream write fails;
8. every extra downstream write fails;
9. a rejected or revised early proposal can still reach the gold state;
10. alternative read/search paths with the same writes pass;
11. the user simulator never supplies environment-only facts across repeated trials;
12. the user stops normally after complete confirmation.

## Calibration plan

Run at least 10 trials per model during design iteration and 20 once the task is
stable. Report exact DB, communication, simulator-policy, and termination outcomes
separately before collapsing them into pass/fail.

Useful initial calibration bands, not leaderboard targets:

| Model class | Desired pass^1 band |
| --- | ---: |
| Small/mini | 20-50% |
| GPT-4.1-class | 40-70% |
| Strong frontier | 60-90% |

The task is probably still too easy if all capable models pass nearly every trial
and failures do not include at least three substantive categories. It is probably
broken rather than hard if failures are dominated by simulator violations, opaque
IDs, ambiguous wording, irreversible harmless mistakes, or step-limit termination.

Expected substantive failure categories are:

- wrong authority or attendee selection;
- wrong option after user preference disclosure;
- duplicate-versus-update error;
- partial downstream completion;
- stale-record or clearance error;
- correct state but incomplete completion communication.

### GPT-4.1 calibration observed locally

All runs used `gpt-4.1-2025-04-14` for both agent and user simulator, temperature
0, 200 maximum steps, and 20 trials of the single hard task.

| Version | Full pass | Exact DB | Interpretation |
| --- | ---: | ---: | --- |
| Corrected simulator, three common-deadline items | 20/20 | 20/20 | Saturated |
| Four mixed-state tracker records, common deadline | 17/20 | 19/20 normal runs | Lower headline mostly from reporting and one calendar loop |
| Four mixed-state records, brief-specific deadlines | 14/20 | 14/20 | Six substantive final-state failures |

In the stable mixed-deadline version, all 20 runs stopped normally. Each of the six
failures left the existing Engineering and Design tasks at their stale post-kickoff
dates instead of applying the current brief's two-day lead time. Legal reassignment,
Product task creation, scheduling, milestone update, and the canonical channel post
were otherwise completed. This is a realistic exhaustive-reconciliation failure,
not an approval oracle, identifier artifact, or simulator termination problem.

The 70% point is useful calibration for this task, not evidence that the single task
is score-equivalent to tau2-bench. The latter evaluates a heterogeneous task
population; broader domain difficulty must come from additional realistic workflow
archetypes rather than continually adding clauses to this kickoff.

## Deliberate non-goals for this iteration

- raw REST APIs or undocumented tool schemas;
- arbitrary ID generation by the agent;
- grading exact search queries or action order;
- fragile exact-string grading for chat or user communication;
- document or spreadsheet artifact quality;
- more than one external-communication approval flow;
- difficulty created primarily by a low step cap.

Those dimensions may be valuable later, but adding them now would make it harder to
tell whether failures come from knowledge-work reasoning or interface friction.

## Questions to resolve before implementation

1. Should the final team update be canonical and tool-generated, or should the agent
   author free-form content that is checked semantically?
2. Should delegation and clearance be modeled as typed project records or as normal
   searchable documents with validity metadata?
3. Do the four mixed-state preparation records plus a milestone provide enough
   downstream breadth, or should a later task—not this one—test artifact creation?
4. Should the user reveal the conditional preference when asked generally, or only
   after the agent presents both concrete options?
5. Should `COMMUNICATE` remain a gating reward component, or should deterministic DB
   state be the only official reward with communication retained as a diagnostic?
6. After calibration, should this replace `workplace_kickoff_001` or become a new
   task while the existing one remains an explicit smoke-test split?
