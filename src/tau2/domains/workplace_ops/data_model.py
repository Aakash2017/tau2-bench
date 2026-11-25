from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from tau2.environment.db import DB
from tau2.utils.pydantic_utils import BaseModelNoExtra


class Document(BaseModelNoExtra):
    document_id: str
    title: str
    version: int
    status: Literal["current", "superseded"]
    updated_at: str
    external_pilot: Literal["confirmed", "pending", "none"]
    required_functions: List[str] = Field(default_factory=list)
    preparation_requirements: List["PreparationRequirement"] = Field(
        default_factory=list
    )


class PreparationRequirement(BaseModelNoExtra):
    title: str
    owner_function: str
    due_days_before_kickoff: int


class Employee(BaseModelNoExtra):
    employee_id: str
    name: str
    email: str
    function: str


class ProjectRecord(BaseModelNoExtra):
    record_id: str
    project: str
    record_type: Literal["assignment", "delegation", "clearance"]
    status: Literal["current", "superseded", "expired", "pending"]
    function: Optional[str] = None
    primary_email: Optional[str] = None
    delegate_email: Optional[str] = None
    external_email: Optional[str] = None
    clearance_status: Optional[Literal["approved", "pending", "denied"]] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    notes: str = ""


class BusyInterval(BaseModelNoExtra):
    start: str
    end: str


class MeetingProposal(BaseModelNoExtra):
    proposal_id: str
    title: str
    start: str
    end: str
    attendees: List[str]
    approved_by_user: bool = False


class MeetingApprovalRule(BaseModelNoExtra):
    title: str
    window_start: str
    window_end: str
    duration_minutes: int
    forbidden_attendees: List[str] = Field(default_factory=list)
    alternate_windows: List[BusyInterval] = Field(default_factory=list)


class CalendarEvent(BaseModelNoExtra):
    event_id: str
    title: str
    start: str
    end: str
    attendees: List[str]
    source_proposal_id: str


class ProjectTask(BaseModelNoExtra):
    task_id: str
    title: str
    assignee: str
    due_date: str
    status: Literal["open", "completed"] = "open"
    project: Optional[str] = None


class ProjectMilestone(BaseModelNoExtra):
    milestone_id: str
    project: str
    name: str
    status: Literal["planning", "scheduled", "completed"] = "planning"
    kickoff_date: Optional[str] = None
    meeting_event_id: Optional[str] = None


class ChatMessage(BaseModelNoExtra):
    message_id: str
    channel: str
    project: str
    meeting_event_id: str
    preparation_task_id: Optional[str] = None
    preparation_task_ids: List[str] = Field(default_factory=list)
    milestone_id: Optional[str] = None
    content: str


class WorkplaceRecord(BaseModelNoExtra):
    """A structured record stored in one simulated workplace application."""

    record_id: str
    system: str
    record_type: str
    title: str
    status: str
    updated_at: str
    owner: Optional[str] = None
    fields: Dict[str, Any] = Field(default_factory=dict)


class ActionProposal(BaseModelNoExtra):
    """A concrete cross-system plan awaiting the requester's approval."""

    proposal_id: str
    proposal_type: str
    title: str
    details: Dict[str, Any] = Field(default_factory=dict)
    approved_by_user: bool = False


class ActionApprovalRule(BaseModelNoExtra):
    """Private requester constraints enforced when approving a proposal."""

    title: str
    proposal_type: str
    required_details: Dict[str, Any] = Field(default_factory=dict)


class ExternalMessage(BaseModelNoExtra):
    """A structured external communication sent from an approved proposal."""

    message_id: str
    system: str
    recipient: str
    subject: str
    facts: Dict[str, Any] = Field(default_factory=dict)
    source_proposal_id: str


class InternalUpdate(BaseModelNoExtra):
    """A canonical internal update referencing completed work records."""

    update_id: str
    channel: str
    topic: str
    related_record_ids: List[str]


class OnCallPage(BaseModelNoExtra):
    """A page routed through the current on-call schedule."""

    page_id: str
    schedule_record_id: str
    incident_record_id: str
    target: str


class AccessGrant(BaseModelNoExtra):
    """A provisioned access bundle for one identity."""

    grant_id: str
    identity_record_id: str
    access_level: str
    expires_on: str
    source_proposal_id: str


class WorkplaceOpsDB(DB):
    documents: Dict[str, Document] = Field(default_factory=dict)
    employees: Dict[str, Employee] = Field(default_factory=dict)
    project_records: Dict[str, ProjectRecord] = Field(default_factory=dict)
    calendar_busy: Dict[str, List[BusyInterval]] = Field(default_factory=dict)
    meeting_approval_rules: Dict[str, MeetingApprovalRule] = Field(default_factory=dict)
    meeting_proposals: Dict[str, MeetingProposal] = Field(default_factory=dict)
    calendar_events: Dict[str, CalendarEvent] = Field(default_factory=dict)
    project_tasks: Dict[str, ProjectTask] = Field(default_factory=dict)
    project_milestones: Dict[str, ProjectMilestone] = Field(default_factory=dict)
    chat_messages: List[ChatMessage] = Field(default_factory=list)
    workplace_records: Dict[str, WorkplaceRecord] = Field(default_factory=dict)
    action_approval_rules: Dict[str, ActionApprovalRule] = Field(default_factory=dict)
    action_proposals: Dict[str, ActionProposal] = Field(default_factory=dict)
    external_messages: List[ExternalMessage] = Field(default_factory=list)
    internal_updates: List[InternalUpdate] = Field(default_factory=list)
    on_call_pages: List[OnCallPage] = Field(default_factory=list)
    access_grants: List[AccessGrant] = Field(default_factory=list)


def event_id_for_proposal(proposal_id: str) -> str:
    """Return the deterministic event ID created from a proposal."""
    return f"event_{proposal_id}"


def proposal_id_for_index(index: int) -> str:
    """Return the deterministic proposal ID for a zero-based index."""
    return f"proposal_{index + 1}"


def task_id_for_index(index: int) -> str:
    """Return the deterministic project-task ID for a zero-based index."""
    return f"task_{index + 1}"


def message_id_for_index(index: int) -> str:
    """Return the deterministic chat message ID for a zero-based index."""
    return f"message_{index + 1}"


def generated_record_id_for_index(index: int) -> str:
    """Return a deterministic ID for an agent-created workplace record."""
    return f"generated_record_{index + 1}"


def renewal_follow_up_record_id(account_record_id: str) -> str:
    """Return the stable record ID for an account's renewal follow-up."""
    return f"renewal_follow_up_{account_record_id}"


def action_proposal_id_for_index(index: int) -> str:
    """Return a deterministic action-proposal ID."""
    return f"action_proposal_{index + 1}"


def external_message_id_for_index(index: int) -> str:
    """Return a deterministic external-message ID."""
    return f"external_message_{index + 1}"


def internal_update_id_for_index(index: int) -> str:
    """Return a deterministic internal-update ID."""
    return f"internal_update_{index + 1}"


def page_id_for_index(index: int) -> str:
    """Return a deterministic on-call page ID."""
    return f"page_{index + 1}"


def access_grant_id_for_index(index: int) -> str:
    """Return a deterministic access-grant ID."""
    return f"access_grant_{index + 1}"
