from typing import Any, Literal, Optional

from pydantic import Field

from tau2.environment.db import DB
from tau2.utils.pydantic_utils import BaseModelNoExtra


class KnowledgeDocument(BaseModelNoExtra):
    """One versioned document in the authored workplace knowledge corpus."""

    document_id: str
    title: str
    status: Literal["current", "superseded"]
    updated_at: str
    content: str
    tags: list[str] = Field(default_factory=list)


class DatadogSignal(BaseModelNoExtra):
    """A deterministic Datadog metric-series result."""

    signal_id: str
    title: str
    query: str
    scope: str
    channel: str
    region: str
    health: Literal["healthy", "degraded"]
    freshness: Literal["current", "stale"]
    updated_at: str
    metric_name: str
    value: float
    unit: str


class DatadogState(BaseModelNoExtra):
    signals: dict[str, DatadogSignal] = Field(default_factory=dict)


class PagerDutyOnCall(BaseModelNoExtra):
    oncall_id: str
    schedule_id: str
    user_id: str
    user_name: str
    user_email: str
    start: str
    end: str
    escalation_level: int = 1


class PagerDutyIncident(BaseModelNoExtra):
    incident_id: str
    title: str
    urgency: Literal["high", "low"]
    assignee_id: str
    assignee_email: str
    incident_key: str
    status: Literal["triggered", "acknowledged", "resolved"] = "triggered"


class PagerDutyState(BaseModelNoExtra):
    oncalls: dict[str, PagerDutyOnCall] = Field(default_factory=dict)
    incidents: dict[str, PagerDutyIncident] = Field(default_factory=dict)


class LinearIssue(BaseModelNoExtra):
    issue_id: str
    identifier: str
    team_id: str
    issue_type: Literal["incident", "rca"]
    title: str
    state: str
    assignee_id: Optional[str] = None
    assignee_email: Optional[str] = None
    severity: Optional[str] = None
    scope: Optional[str] = None
    source_signal_ids: list[str] = Field(default_factory=list)
    due_date: Optional[str] = None
    related_issue_id: Optional[str] = None
    labels: list[str] = Field(default_factory=list)
    description: str = ""


class LinearState(BaseModelNoExtra):
    issues: dict[str, LinearIssue] = Field(default_factory=dict)


class StatuspageIncident(BaseModelNoExtra):
    incident_id: str
    page_id: str
    name: str
    status: Literal["investigating", "identified", "monitoring", "resolved"]
    impact: Literal["none", "minor", "major", "critical"]
    body: str
    component_ids: list[str] = Field(default_factory=list)


class StatuspageState(BaseModelNoExtra):
    incidents: dict[str, StatuspageIncident] = Field(default_factory=dict)


class SlackMessage(BaseModelNoExtra):
    message_id: str
    channel: str
    text: str


class SlackState(BaseModelNoExtra):
    messages: dict[str, SlackMessage] = Field(default_factory=dict)


class InteractiveWorkplaceWorld(BaseModelNoExtra):
    """Typed app state for locally authored interactive workplace tasks."""

    task_id: str = ""
    current_time: str = ""
    datadog: DatadogState = Field(default_factory=DatadogState)
    pagerduty: PagerDutyState = Field(default_factory=PagerDutyState)
    linear: LinearState = Field(default_factory=LinearState)
    statuspage: StatuspageState = Field(default_factory=StatuspageState)
    slack: SlackState = Field(default_factory=SlackState)


class AutomationWorkplaceDB(DB):
    """τ-owned envelope around an AutomationBench Pydantic world.

    The nested dictionary is validated as AutomationBench's ``WorldState`` before
    every API call and assertion. Keeping the envelope dependency-free lets τ load
    normally when the optional AutomationBench checkout is not installed.
    """

    source_task: str = ""
    world: dict[str, Any] = Field(default_factory=dict)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    interactive_task: str = ""
    interactive_family: str = "access_provisioning"
    knowledge_documents: dict[str, KnowledgeDocument] = Field(default_factory=dict)
    interactive_world: InteractiveWorkplaceWorld = Field(
        default_factory=InteractiveWorkplaceWorld
    )
    unlocked_tools: list[str] = Field(default_factory=list)
    interactive_assertions: list[dict[str, Any]] = Field(default_factory=list)
    family_world: dict[str, Any] = Field(default_factory=dict)
