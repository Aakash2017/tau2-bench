# Task 1 User Simulator Audit

Date: 2026-11-08

## Decision

The simulated user should retain an explicit approval tool. Natural-language
acknowledgement is useful conversational evidence, but it is not a reliable state
transition: phrases such as “looks good,” “okay,” or “go ahead when ready” are
ambiguous. `approve_meeting_proposal` records authorization deterministically, and
the user then tells the agent in natural language that it may schedule the exact
reviewed proposal.

The benchmark therefore uses both layers:

1. `get_pending_meeting_proposals` lets the user inspect the actual environment
   record and obtain its ID without guessing.
2. `approve_meeting_proposal` records authorization in user-controlled state.
3. The simulator explicitly tells the agent that the exact proposal is approved.
4. `schedule_approved_meeting` rejects scheduling unless that state transition has
   occurred.

## Prompt layers

### Domain scaffold

The default tau2 user prompt describes a customer contacting a customer-service
representative. That framing is wrong for an AI-employee benchmark, so Task 1 now
uses a domain-specific scaffold that says the simulator is an employee collaborating
with an AI employee in an internal workplace chat.

The scaffold requires the simulator to:

- treat unstated information and unreturned tool data as unknown;
- disclose private preferences progressively;
- expect the agent to retrieve company-system facts;
- never invent identifiers, availability, tool results, or completed work;
- use user tools only after scenario preconditions are met;
- relay a tool rejection rather than claiming success or guessing arguments; and
- stop only after all scenario completion conditions are confirmed.

### Task persona and private information

Maya knows only information a real requester would plausibly own:

- preferred window: earliest available Wednesday morning Pacific next week;
- duration: 45 minutes;
- approval preference: inspect exact time, duration, and attendees first; and
- no external pilot participant before Legal clearance.

She does not know the current brief, employee records, team availability, Legal
representative, or preparation requirements. Those remain agent/environment work.

### User tools

The tool descriptions and task instructions form a deterministic approval protocol.
The approval tool enforces only private user constraints:

- the proposal falls within the Wednesday-morning window;
- it lasts exactly 45 minutes; and
- it contains no forbidden external participant.

It intentionally does not enforce the correct internal attendee set, earliest shared
availability, current brief, Legal task, or channel post. Letting the user tool check
those facts would turn the simulator into an evaluator oracle and could hide agent
errors. Exact final-state grading checks them instead.

## Failure and recovery semantics

The benchmark does not fail an agent merely for guessing. A wrong unapproved draft
can be revised in place, and a rejected tool call leaves no consequential final
state. If the agent subsequently obtains approval and produces the exact final state,
the run passes.

It does fail when the final state is wrong or incomplete. Examples include:

- the only remaining proposal or scheduled event has the wrong date, duration, or
  attendees;
- the external participant is invited;
- the meeting is never approved or scheduled;
- the Legal preparation task or project update is absent or incorrect;
- an extra stale proposal, event, task, or update remains; or
- required completion facts are not communicated.

This matches tau's end-state philosophy while retaining environment-enforced
authorization.

## Evidence from revised trials

In two GPT-4.1-mini trials, the agent proposed the wrong calendar date. The approval
tool rejected it, the simulator accurately relayed the correction, and the agent
revised the same pending proposal. Both final states passed exactly. The simulator
never invented a proposal ID, approved an invalid proposal, or ended before all
downstream work was confirmed in any of the eight evaluated revised trials.

## Remaining limitations

- The domain-specific scaffold is currently English-only. A future multilingual
  release should add language-pack integration without reintroducing customer-service
  role text.
- Four trials per model are enough for debugging but not for estimating simulator
  violation rates.
- The approval rejection necessarily reveals the requester's exact private window.
  This is realistic user correction, but future tasks should ensure user errors do
  not reveal company-system answers that the agent is supposed to discover.
- The single task does not test conflicting user instructions, approval revocation,
  multiple pending proposals, or delegation to another approver.

## Generated-collection follow-up

The 50-task audit confirmed two additional simulator-contract requirements:

- A rejected proposal revision is not approved by a later prose acknowledgement.
  The domain scaffold now tells the simulator to inspect the revised proposal and
  call the approval tool again before authorizing execution.
- User-owned judgment must be present in the scenario and disclosed only after the
  agent establishes the relevant environment fact. Renewal tasks now instruct the
  simulator to choose `revenue-ops@atlas.example` only after the agent identifies
  the named account as unowned and asks for an assignment decision.

The user approval tool still does not validate system-derived account eligibility,
hierarchy, Legal records, recipients, or billing status. Those remain agent work and
are graded in the environment. This preserves the separation between user-owned
authority and company-system facts while making the interactive contract executable.
