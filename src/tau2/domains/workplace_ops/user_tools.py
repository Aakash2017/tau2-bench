from datetime import datetime

from tau2.domains.workplace_ops.data_model import (
    ActionProposal,
    MeetingProposal,
    WorkplaceOpsDB,
)
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


class WorkplaceOpsUserTools(ToolKitBase):
    """Private tools available to the simulated workplace requester."""

    db: WorkplaceOpsDB

    def __init__(self, db: WorkplaceOpsDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def get_pending_meeting_proposals(self) -> list[MeetingProposal]:
        """Inspect meeting proposals that are waiting for your approval.

        Returns:
            Every unapproved meeting proposal, including the ID needed to approve it.
        """
        return sorted(
            [
                proposal
                for proposal in self.db.meeting_proposals.values()
                if not proposal.approved_by_user
            ],
            key=lambda proposal: proposal.proposal_id,
        )

    @is_tool(ToolType.WRITE)
    def approve_meeting_proposal(self, proposal_id: str) -> str:
        """Record your approval of an exact meeting proposal.

        Inspect the proposal first. Use this only when you explicitly authorize the
        agent to schedule that exact proposal. After approval, clearly tell the agent
        in natural language that it may schedule the meeting.

        Args:
            proposal_id: The exact reviewed proposal to approve.

        Returns:
            Confirmation that the approval is recorded.
        """
        if proposal_id not in self.db.meeting_proposals:
            raise ValueError("Meeting proposal not found")
        proposal = self.db.meeting_proposals[proposal_id]
        if proposal.approved_by_user:
            raise ValueError("Meeting proposal is already approved")
        rule = self.db.meeting_approval_rules.get(proposal.title)
        if rule is None:
            raise ValueError("You have no approval instructions for this proposal")
        start = datetime.fromisoformat(proposal.start)
        end = datetime.fromisoformat(proposal.end)
        allowed_windows = [
            (rule.window_start, rule.window_end),
            *[(window.start, window.end) for window in rule.alternate_windows],
        ]
        violations = []
        if not any(
            start >= datetime.fromisoformat(window_start)
            and end <= datetime.fromisoformat(window_end)
            for window_start, window_end in allowed_windows
        ):
            formatted_windows = " or ".join(
                f"{window_start} to {window_end}"
                for window_start, window_end in allowed_windows
            )
            violations.append(f"the meeting must be within {formatted_windows}")
        duration_minutes = int((end - start).total_seconds() / 60)
        if duration_minutes != rule.duration_minutes:
            violations.append(f"the meeting must last {rule.duration_minutes} minutes")
        forbidden = sorted(set(proposal.attendees) & set(rule.forbidden_attendees))
        if forbidden:
            violations.append(f"these attendees must not be invited: {forbidden}")
        if violations:
            raise ValueError(
                "Proposal does not satisfy your approval constraints: "
                + "; ".join(violations)
            )
        proposal.approved_by_user = True
        return (
            f"Proposal {proposal_id} is approved. Tell the agent explicitly that "
            "it may schedule this proposal."
        )

    def assert_meeting_proposal_approved(self, proposal_id: str) -> bool:
        """Check whether the exact proposal is approved in user-controlled state."""
        proposal = self.db.meeting_proposals.get(proposal_id)
        return proposal is not None and proposal.approved_by_user

    @is_tool(ToolType.READ)
    def get_pending_action_proposals(self) -> list[ActionProposal]:
        """Inspect structured workplace plans waiting for your approval."""
        return sorted(
            [
                proposal
                for proposal in self.db.action_proposals.values()
                if not proposal.approved_by_user
            ],
            key=lambda proposal: proposal.proposal_id,
        )

    @is_tool(ToolType.WRITE)
    def approve_action_proposal(self, proposal_id: str) -> str:
        """Approve one exact workplace plan after inspecting its structured details."""
        proposal = self.db.action_proposals.get(proposal_id)
        if proposal is None:
            raise ValueError("Action proposal not found")
        if proposal.approved_by_user:
            raise ValueError("Action proposal is already approved")
        rule = self.db.action_approval_rules.get(proposal.title)
        if rule is None or rule.proposal_type != proposal.proposal_type:
            raise ValueError("You have no approval instructions for this proposal")
        violations = [
            f"{key} must be {expected!r}"
            for key, expected in rule.required_details.items()
            if proposal.details.get(key) != expected
        ]
        if violations:
            raise ValueError(
                "Proposal does not satisfy your approval constraints: "
                + "; ".join(violations)
            )
        proposal.approved_by_user = True
        return (
            f"Proposal {proposal_id} is approved. Tell the agent explicitly that "
            "it may execute this exact plan."
        )

    def assert_action_proposal_approved(self, proposal_id: str) -> bool:
        """Check an exact action proposal is approved in user-controlled state."""
        proposal = self.db.action_proposals.get(proposal_id)
        return proposal is not None and proposal.approved_by_user
