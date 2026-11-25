"""Pydantic-backed runtime for the meeting-coordination task family."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field

from tau2.utils.pydantic_utils import BaseModelNoExtra

FAMILY_NAME = "meeting_coordination"
FAMILY_ID = FAMILY_NAME


class SalesforceContact(BaseModelNoExtra):
    contact_id: str
    account_id: str
    name: str
    email: str
    role: str
    relationship_status: Literal["active", "pilot_ended"]
    meeting_eligibility: Literal["verified", "excluded"]
    calendar_id: str


class SalesforceOpportunity(BaseModelNoExtra):
    opportunity_id: str
    account_id: str
    name: str
    stage: str
    next_customer_meeting_at: Optional[str] = None
    coordination_note: str = ""


class SalesforceState(BaseModelNoExtra):
    contacts: dict[str, SalesforceContact] = Field(default_factory=dict)
    opportunities: dict[str, SalesforceOpportunity] = Field(default_factory=dict)


class CalendarBusyBlock(BaseModelNoExtra):
    start: str
    end: str
    summary: str


class CalendarIdentity(BaseModelNoExtra):
    calendar_id: str
    name: str
    email: str
    timezone: str
    busy: list[CalendarBusyBlock] = Field(default_factory=list)


class CalendarEvent(BaseModelNoExtra):
    event_id: str
    calendar_id: str
    summary: str
    start: str
    end: str
    timezone: str
    attendee_emails: list[str]
    description: str = ""


class GoogleCalendarState(BaseModelNoExtra):
    identities: dict[str, CalendarIdentity] = Field(default_factory=dict)
    events: dict[str, CalendarEvent] = Field(default_factory=dict)


class SlackMessage(BaseModelNoExtra):
    message_id: str
    channel: str
    text: str


class SlackState(BaseModelNoExtra):
    messages: dict[str, SlackMessage] = Field(default_factory=dict)


class MeetingCoordinationWorld(BaseModelNoExtra):
    """Typed state owned by one meeting-coordination episode."""

    task_id: str
    current_time: str
    salesforce: SalesforceState = Field(default_factory=SalesforceState)
    google_calendar: GoogleCalendarState = Field(default_factory=GoogleCalendarState)
    slack: SlackState = Field(default_factory=SlackState)


WORLD_MODEL = MeetingCoordinationWorld


class SalesforceQueryContactsArguments(BaseModelNoExtra):
    account_id: str
    page_size: int = 3
    cursor: Optional[str] = None


class CalendarFreeBusyArguments(BaseModelNoExtra):
    calendar_ids: list[str]
    time_min: str
    time_max: str


class CalendarCreateEventArguments(BaseModelNoExtra):
    calendar_id: str
    summary: str
    start: str
    end: str
    timezone: str
    attendee_emails: list[str]
    description: str = ""


class SalesforceUpdateOpportunityArguments(BaseModelNoExtra):
    opportunity_id: str
    next_customer_meeting_at: str
    coordination_note: str


class SlackPostArguments(BaseModelNoExtra):
    channel: str
    text: str


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
        "additionalProperties": False,
    }


DISCOVERABLE_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "salesforce_query_meeting_contacts_v61": {
        "description": (
            "List account meeting contacts and internal team members with verified "
            "eligibility. Results are paginated."
        ),
        "parameters": _schema(SalesforceQueryContactsArguments),
        "mutates_state": False,
    },
    "google_calendar_freebusy_query_v3": {
        "description": "Query busy intervals for one or more calendars.",
        "parameters": _schema(CalendarFreeBusyArguments),
        "mutates_state": False,
    },
    "google_calendar_events_insert_v3": {
        "description": "Create one Google Calendar event with explicit attendees.",
        "parameters": _schema(CalendarCreateEventArguments),
        "mutates_state": True,
    },
    "salesforce_update_opportunity_v61": {
        "description": "Record the scheduled customer meeting on an opportunity.",
        "parameters": _schema(SalesforceUpdateOpportunityArguments),
        "mutates_state": True,
    },
    "slack_chat_post_message": {
        "description": "Post one message to a Slack channel.",
        "parameters": _schema(SlackPostArguments),
        "mutates_state": True,
    },
}
TOOL_SCHEMAS = DISCOVERABLE_TOOL_SCHEMAS


def tool_schema(tool_name: str) -> dict[str, Any]:
    """Return one discoverable operation's public schema."""
    if tool_name not in DISCOVERABLE_TOOL_SCHEMAS:
        raise ValueError(f"Unknown meeting-coordination tool: {tool_name}")
    return {"name": tool_name, **DISCOVERABLE_TOOL_SCHEMAS[tool_name]}


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Time values must be ISO 8601 with a UTC offset") from exc
    if parsed.utcoffset() is None:
        raise ValueError("Time values must include a UTC offset")
    return parsed


def _salesforce_query_contacts(
    world: MeetingCoordinationWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SalesforceQueryContactsArguments.model_validate(raw)
    if args.page_size < 1 or args.page_size > 3:
        raise ValueError("page_size must be between 1 and 3")
    try:
        start = int(args.cursor or "0")
    except ValueError as exc:
        raise ValueError("cursor must be a non-negative integer string") from exc
    if start < 0:
        raise ValueError("cursor must be a non-negative integer string")
    contacts = sorted(
        (
            contact
            for contact in world.salesforce.contacts.values()
            if contact.account_id == args.account_id
        ),
        key=lambda contact: contact.contact_id,
    )
    page = contacts[start : start + args.page_size]
    next_cursor = start + len(page)
    done = next_cursor >= len(contacts)
    return {
        "totalSize": len(contacts),
        "done": done,
        "records": [contact.model_dump(mode="json") for contact in page],
        "nextRecordsUrl": (
            None
            if done
            else f"/services/data/v61.0/query/meeting-contacts?cursor={next_cursor}"
        ),
        "next_cursor": None if done else str(next_cursor),
    }


def _calendar_freebusy(
    world: MeetingCoordinationWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = CalendarFreeBusyArguments.model_validate(raw)
    start = _parse_time(args.time_min)
    end = _parse_time(args.time_max)
    if end <= start:
        raise ValueError("time_max must be after time_min")
    calendars: dict[str, Any] = {}
    for calendar_id in args.calendar_ids:
        identity = world.google_calendar.identities.get(calendar_id)
        if identity is None:
            calendars[calendar_id] = {"errors": [{"reason": "notFound"}]}
            continue
        busy = [
            block.model_dump(mode="json", exclude={"summary"})
            for block in identity.busy
            if _parse_time(block.start) < end and _parse_time(block.end) > start
        ]
        busy.extend(
            {"start": event.start, "end": event.end}
            for event in world.google_calendar.events.values()
            if (
                event.calendar_id == calendar_id
                or identity.email in event.attendee_emails
            )
            and _parse_time(event.start) < end
            and _parse_time(event.end) > start
        )
        busy.sort(key=lambda block: (block["start"], block["end"]))
        calendars[calendar_id] = {
            "busy": busy,
            "timezone": identity.timezone,
        }
    return {
        "kind": "calendar#freeBusy",
        "timeMin": args.time_min,
        "timeMax": args.time_max,
        "calendars": calendars,
    }


def _calendar_create_event(
    world: MeetingCoordinationWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = CalendarCreateEventArguments.model_validate(raw)
    if args.calendar_id not in world.google_calendar.identities:
        raise ValueError("Organizer calendar not found")
    start = _parse_time(args.start)
    end = _parse_time(args.end)
    if end <= start:
        raise ValueError("end must be after start")
    known_emails = {
        identity.email for identity in world.google_calendar.identities.values()
    }
    unknown = sorted(set(args.attendee_emails) - known_emails)
    if unknown:
        raise ValueError(f"Unknown calendar attendee email(s): {', '.join(unknown)}")
    event_id = f"gcal_event_{len(world.google_calendar.events) + 1:03d}"
    event = CalendarEvent(
        event_id=event_id,
        calendar_id=args.calendar_id,
        summary=args.summary,
        start=args.start,
        end=args.end,
        timezone=args.timezone,
        attendee_emails=list(args.attendee_emails),
        description=args.description,
    )
    world.google_calendar.events[event_id] = event
    return {
        "kind": "calendar#event",
        "id": event_id,
        "status": "confirmed",
        "summary": event.summary,
        "start": {"dateTime": event.start, "timeZone": event.timezone},
        "end": {"dateTime": event.end, "timeZone": event.timezone},
        "attendees": [
            {"email": email, "responseStatus": "needsAction"}
            for email in event.attendee_emails
        ],
    }


def _salesforce_update_opportunity(
    world: MeetingCoordinationWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SalesforceUpdateOpportunityArguments.model_validate(raw)
    opportunity = world.salesforce.opportunities.get(args.opportunity_id)
    if opportunity is None:
        raise ValueError("Salesforce opportunity not found")
    _parse_time(args.next_customer_meeting_at)
    opportunity.next_customer_meeting_at = args.next_customer_meeting_at
    opportunity.coordination_note = args.coordination_note
    return {
        "id": opportunity.opportunity_id,
        "success": True,
        "errors": [],
    }


def _slack_post(world: MeetingCoordinationWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = SlackPostArguments.model_validate(raw)
    message_id = f"slack_message_{len(world.slack.messages) + 1:03d}"
    message = SlackMessage(
        message_id=message_id,
        channel=args.channel,
        text=args.text,
    )
    world.slack.messages[message_id] = message
    return {
        "ok": True,
        "channel": args.channel,
        "ts": f"1795026600.{len(world.slack.messages):06d}",
        "message": message.model_dump(mode="json"),
    }


_HANDLERS: dict[
    str, Callable[[MeetingCoordinationWorld, dict[str, Any]], dict[str, Any]]
] = {
    "salesforce_query_meeting_contacts_v61": _salesforce_query_contacts,
    "google_calendar_freebusy_query_v3": _calendar_freebusy,
    "google_calendar_events_insert_v3": _calendar_create_event,
    "salesforce_update_opportunity_v61": _salesforce_update_opportunity,
    "slack_chat_post_message": _slack_post,
}


def _call_tool_model(
    world: MeetingCoordinationWorld, tool_name: str, arguments: str
) -> str:
    """Execute one family operation and return an API-shaped JSON response."""
    if tool_name not in _HANDLERS:
        raise ValueError(f"Unknown meeting-coordination tool: {tool_name}")
    try:
        raw = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"arguments must be valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("arguments must encode one JSON object")
    return json.dumps(_HANDLERS[tool_name](world, raw), sort_keys=True)


def _contains_all(value: str, required: list[str]) -> bool:
    lowered = value.lower()
    return all(term.lower() in lowered for term in required)


def _coordination_events(world: MeetingCoordinationWorld) -> list[CalendarEvent]:
    return [
        event
        for event in world.google_calendar.events.values()
        if event.event_id != "gcal_event_existing_001"
    ]


def _check_assertion_model(
    world: MeetingCoordinationWorld, assertion: dict[str, Any]
) -> bool:
    """Evaluate one exact-final-state meeting assertion."""
    assertion_type = assertion["type"]
    if assertion_type == "meeting_calendar_event_exact":
        events = _coordination_events(world)
        return bool(
            len(events) == 1
            and events[0].event_id == "gcal_event_002"
            and events[0].calendar_id == "cal_morgan"
            and events[0].summary == "Meridian rollout readiness review"
            and events[0].start == "2026-11-18T10:30:00-08:00"
            and events[0].end == "2026-11-18T11:15:00-08:00"
            and events[0].timezone == "America/Los_Angeles"
            and set(events[0].attendee_emails)
            == {
                "morgan@atlas.example",
                "avery@atlas.example",
                "lena@atlas.example",
                "ravi@atlas.example",
                "elena@meridian.example",
                "marcus@meridian.example",
            }
            and len(events[0].attendee_emails) == 6
        )
    if assertion_type == "meeting_pilot_contact_excluded":
        events = _coordination_events(world)
        pilot = world.salesforce.contacts.get("con_theo_pilot")
        return bool(
            pilot
            and pilot.relationship_status == "pilot_ended"
            and pilot.meeting_eligibility == "excluded"
            and all(
                "theo@meridian.example" not in event.attendee_emails for event in events
            )
        )
    if assertion_type == "meeting_salesforce_followthrough":
        opportunity = world.salesforce.opportunities.get("opp_meridian_rollout")
        return bool(
            opportunity
            and opportunity.next_customer_meeting_at == "2026-11-18T10:30:00-08:00"
            and _contains_all(
                opportunity.coordination_note,
                [
                    "gcal_event_002",
                    "45",
                    "Morgan",
                    "Avery",
                    "Lena",
                    "Ravi",
                    "Elena",
                    "Marcus",
                    "current brief",
                    "Theo",
                    "excluded",
                ],
            )
        )
    if assertion_type == "meeting_slack_followthrough":
        new_messages = [
            message
            for message in world.slack.messages.values()
            if message.message_id != "slack_message_existing_001"
        ]
        return bool(
            len(new_messages) == 1
            and new_messages[0].channel == "proj-meridian"
            and _contains_all(
                new_messages[0].text,
                [
                    "Wednesday",
                    "November 18",
                    "10:30",
                    "11:15",
                    "PT",
                    "1:30",
                    "2:15",
                    "ET",
                    "Morgan",
                    "Avery",
                    "Lena",
                    "Ravi",
                    "Elena",
                    "Marcus",
                    "45",
                    "gcal_event_002",
                ],
            )
            and "theo" not in new_messages[0].text.lower()
        )
    if assertion_type == "meeting_unrelated_records_preserved":
        existing_event = world.google_calendar.events.get("gcal_event_existing_001")
        existing_message = world.slack.messages.get("slack_message_existing_001")
        pilot = world.salesforce.contacts.get("con_theo_pilot")
        return bool(
            existing_event
            and existing_event.summary == "FY27 planning"
            and existing_event.start == "2026-11-19T09:00:00-08:00"
            and existing_event.end == "2026-11-19T10:00:00-08:00"
            and existing_message
            and existing_message.channel == "proj-meridian"
            and existing_message.text == "Pilot wrap-up completed on October 30."
            and pilot
            and pilot.role == "Pilot evaluator"
        )
    if assertion_type == "meeting_no_stale_brief_side_effect":
        events = _coordination_events(world)
        return bool(
            len(events) == 1
            and all(
                _parse_time(event.end) - _parse_time(event.start)
                == _parse_time("2026-11-18T11:15:00-08:00")
                - _parse_time("2026-11-18T10:30:00-08:00")
                for event in events
            )
            and all(event.start != "2026-11-19T09:00:00-08:00" for event in events)
        )
    raise ValueError(f"Unknown meeting assertion type: {assertion_type}")


def validate_world(raw: dict[str, Any]) -> MeetingCoordinationWorld:
    """Validate serialized family state before every operation or assertion."""
    return MeetingCoordinationWorld.model_validate(raw)


def call_tool(
    raw_world: dict[str, Any], tool_name: str, arguments: str
) -> tuple[dict[str, Any], str]:
    """Execute an operation and return serialized new state plus JSON response."""
    world = validate_world(raw_world)
    response = _call_tool_model(world, tool_name, arguments)
    return world.model_dump(mode="json"), response


def check_assertion(raw_world: dict[str, Any], assertion: dict[str, Any]) -> bool:
    """Evaluate an exact-state assertion against serialized family state."""
    return _check_assertion_model(validate_world(raw_world), assertion)


def golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return the deterministic successful write sequence for task validation."""
    return [
        (
            "google_calendar_events_insert_v3",
            {
                "calendar_id": "cal_morgan",
                "summary": "Meridian rollout readiness review",
                "start": "2026-11-18T10:30:00-08:00",
                "end": "2026-11-18T11:15:00-08:00",
                "timezone": "America/Los_Angeles",
                "attendee_emails": [
                    "morgan@atlas.example",
                    "avery@atlas.example",
                    "lena@atlas.example",
                    "ravi@atlas.example",
                    "elena@meridian.example",
                    "marcus@meridian.example",
                ],
                "description": "Current brief; verified rollout quorum.",
            },
        ),
        (
            "salesforce_update_opportunity_v61",
            {
                "opportunity_id": "opp_meridian_rollout",
                "next_customer_meeting_at": "2026-11-18T10:30:00-08:00",
                "coordination_note": (
                    "Current brief; event gcal_event_002; 45 minutes; attendees "
                    "Morgan, Avery, Lena, Ravi, Elena, and Marcus. Theo excluded "
                    "because the pilot ended."
                ),
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "proj-meridian",
                "text": (
                    "Wednesday, November 18, 10:30-11:15 AM PT / 1:30-2:15 PM "
                    "ET. 45 minutes. Attendees: Morgan, Avery, Lena, Ravi, Elena, "
                    "and Marcus. Event gcal_event_002."
                ),
            },
        ),
    ]


def negative_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return a complete but superseded-brief scheduling path."""
    return [
        (
            "google_calendar_events_insert_v3",
            {
                "calendar_id": "cal_morgan",
                "summary": "Meridian rollout readiness review",
                "start": "2026-11-19T09:00:00-08:00",
                "end": "2026-11-19T10:00:00-08:00",
                "timezone": "America/Los_Angeles",
                "attendee_emails": [
                    "morgan@atlas.example",
                    "avery@atlas.example",
                    "lena@atlas.example",
                    "ravi@atlas.example",
                    "elena@meridian.example",
                    "marcus@meridian.example",
                    "theo@meridian.example",
                ],
                "description": "Scheduled from the October pilot brief.",
            },
        ),
        (
            "salesforce_update_opportunity_v61",
            {
                "opportunity_id": "opp_meridian_rollout",
                "next_customer_meeting_at": "2026-11-19T09:00:00-08:00",
                "coordination_note": (
                    "October pilot brief; event gcal_event_002; 60 minutes; "
                    "attendees Morgan, Avery, Lena, Ravi, Elena, Marcus, and Theo."
                ),
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "proj-meridian",
                "text": (
                    "Thursday, November 19, 9:00-10:00 AM PT / 12:00-1:00 PM "
                    "ET. 60 minutes. Attendees: Morgan, Avery, Lena, Ravi, Elena, "
                    "Marcus, and Theo. Event gcal_event_002."
                ),
            },
        ),
    ]
