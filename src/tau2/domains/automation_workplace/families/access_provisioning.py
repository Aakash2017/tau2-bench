"""Typed runtime for the canonical interactive access-provisioning family."""

from __future__ import annotations

import base64
import json
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field

from tau2.utils.pydantic_utils import BaseModelNoExtra


class Worker(BaseModelNoExtra):
    worker_id: str
    legal_name: str
    worker_type: Literal["employee", "contractor", "intern"]
    status: Literal["active", "inactive"]
    manager_id: str
    primary_email: str
    department: str
    job_title: str
    contract_end_date: Optional[str] = None


class GroupHistoryEntry(BaseModelNoExtra):
    group_id: str
    added_on: str
    removed_on: Optional[str] = None


class Identity(BaseModelNoExtra):
    user_id: str
    email: str
    worker_id: Optional[str] = None
    status: Literal["active", "suspended"]
    groups: list[str] = Field(default_factory=list)
    group_expirations: dict[str, str] = Field(default_factory=dict)
    group_history: list[GroupHistoryEntry] = Field(default_factory=list)


class TrainingRecord(BaseModelNoExtra):
    worker_id: str
    course_id: str
    status: Literal["not_started", "assigned", "complete", "expired"]
    completed_at: Optional[str] = None
    assigned_at: Optional[str] = None


class AccessRequest(BaseModelNoExtra):
    request_id: str
    worker_id: str
    requested_groups: list[str]
    granted_groups: list[str] = Field(default_factory=list)
    status: str
    blocked_reason: Optional[str] = None
    access_expiration: Optional[str] = None
    approver_id: str
    description: str = ""


class SlackMessage(BaseModelNoExtra):
    message_id: str
    channel: str
    text: str
    author: str = ""
    sent_at: str = ""
    thread_id: str = ""


class SlackChannel(BaseModelNoExtra):
    name: str
    topic: str = ""
    purpose: str = ""
    num_members: int = 0


class CompanyDirectory(BaseModelNoExtra):
    company_name: str
    total_people: int
    departments: list[str]


class InjectedFault(BaseModelNoExtra):
    """A canned upstream failure for the next matching call(s), applied first."""

    tool_name: str
    match: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any]
    remaining: int = 1


class AccessProvisioningWorld(BaseModelNoExtra):
    task_id: str = ""
    current_time: str = ""
    company_directory: CompanyDirectory
    workers: dict[str, Worker] = Field(default_factory=dict)
    identities: dict[str, Identity] = Field(default_factory=dict)
    training_records: dict[str, TrainingRecord] = Field(default_factory=dict)
    access_requests: dict[str, AccessRequest] = Field(default_factory=dict)
    slack_messages: dict[str, SlackMessage] = Field(default_factory=dict)
    slack_channels: dict[str, SlackChannel] = Field(default_factory=dict)
    injected_faults: list[InjectedFault] = Field(default_factory=list)


class SearchWorkersArguments(BaseModelNoExtra):
    query: str


class SearchUsersArguments(BaseModelNoExtra):
    query: str


class GetTrainingArguments(BaseModelNoExtra):
    worker_id: str


class AddUserToGroupArguments(BaseModelNoExtra):
    user_id: str
    group_id: str
    expires_on: str


class RemoveUserFromGroupArguments(BaseModelNoExtra):
    user_id: str
    group_id: str


class AssignTrainingArguments(BaseModelNoExtra):
    worker_id: str
    course_id: str


class SearchAccessRequestsArguments(BaseModelNoExtra):
    worker_id: Optional[str] = None
    approver_id: Optional[str] = None


AccessRequestStatus = Literal[
    "New",
    "In review",
    "Provisionally granted",
    "Blocked - training",
    "Blocked - approval",
    "Blocked - conflict",
    "Completed",
    "Declined",
    "Closed - duplicate",
]
BlockedReason = Literal[
    "",
    "PRODUCTION_TRAINING_INCOMPLETE",
    "DATA_HANDLING_TRAINING_INCOMPLETE",
    "ROLE_OWNER_APPROVAL_PENDING",
    "CTO_APPROVAL_PENDING",
    "SOD_CONFLICT",
    "NOT_ELIGIBLE",
]


class UpdateAccessRequestArguments(BaseModelNoExtra):
    request_id: str
    # Jira workflow values; invalid ones are rejected with the allowed list.
    status: AccessRequestStatus
    granted_groups: list[str]
    blocked_reason: BlockedReason
    access_expiration: Optional[str] = None
    description: str


class SlackPostArguments(BaseModelNoExtra):
    channel: str
    text: str
    thread_id: Optional[str] = None


class SlackUpdateArguments(BaseModelNoExtra):
    channel: str
    message_id: str
    text: str


class SlackSearchArguments(BaseModelNoExtra):
    query: str = ""
    channel: Optional[str] = None
    count: int = 10
    page: int = 1


class SlackListChannelsArguments(BaseModelNoExtra):
    limit: int = 20
    cursor: Optional[str] = None


class SlackHistoryArguments(BaseModelNoExtra):
    channel: str
    limit: int = 10
    cursor: Optional[str] = None
    oldest: Optional[str] = None
    latest: Optional[str] = None


class SlackRepliesArguments(BaseModelNoExtra):
    channel: str
    thread_id: str


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
        "additionalProperties": False,
    }


def _entry(
    description: str, model: type[BaseModel], *, mutates: bool
) -> dict[str, Any]:
    return {
        "description": description,
        "parameters": _schema(model),
        "mutates_state": mutates,
    }


DISCOVERABLE_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "rippling_search_people_v1": _entry(
        "Search the authoritative Rippling people directory and org structure.",
        SearchWorkersArguments,
        mutates=False,
    ),
    "okta_search_users_v1": _entry(
        "Search Okta identities and current groups.",
        SearchUsersArguments,
        mutates=False,
    ),
    "lms_get_training_status_v1": _entry(
        "List a worker's LMS training records.", GetTrainingArguments, mutates=False
    ),
    "okta_add_user_to_group_v1": _entry(
        "Add an Okta identity to a group with a required expiration date.",
        AddUserToGroupArguments,
        mutates=True,
    ),
    "okta_remove_user_from_group_v1": _entry(
        "Remove one group from an Okta identity and clear its expiration.",
        RemoveUserFromGroupArguments,
        mutates=True,
    ),
    "lms_assign_training_v1": _entry(
        "Assign one LMS course to a worker.", AssignTrainingArguments, mutates=True
    ),
    "jira_search_access_requests_v1": _entry(
        "Search access requests by worker, approver, or both.",
        SearchAccessRequestsArguments,
        mutates=False,
    ),
    "jira_update_access_request_v1": _entry(
        "Update an existing access request with structured disposition fields.",
        UpdateAccessRequestArguments,
        mutates=True,
    ),
    "slack_search_messages_v1": _entry(
        "Search Slack messages. Supports in:#channel, from:name, after:YYYY-MM-DD "
        "and before:YYYY-MM-DD; results are newest first and paged.",
        SlackSearchArguments,
        mutates=False,
    ),
    "slack_list_channels_v1": _entry(
        "List Slack channels with topic, purpose and member count.",
        SlackListChannelsArguments,
        mutates=False,
    ),
    "slack_get_channel_history_v1": _entry(
        "Read a channel's top-level messages, newest first, one page at a time.",
        SlackHistoryArguments,
        mutates=False,
    ),
    "slack_get_thread_replies_v1": _entry(
        "Read a thread: the parent message and its replies, oldest first.",
        SlackRepliesArguments,
        mutates=False,
    ),
    "slack_chat_post_message": _entry(
        "Post one Slack message.", SlackPostArguments, mutates=True
    ),
    "slack_chat_update_message_v1": _entry(
        "Update one existing Slack message in place.",
        SlackUpdateArguments,
        mutates=True,
    ),
}

FAMILY_ID = "access_provisioning"
TOOL_SCHEMAS = DISCOVERABLE_TOOL_SCHEMAS


def tool_schema(tool_name: str) -> dict[str, Any]:
    if tool_name not in DISCOVERABLE_TOOL_SCHEMAS:
        raise ValueError(f"Unknown access-provisioning tool: {tool_name}")
    return {"name": tool_name, **DISCOVERABLE_TOOL_SCHEMAS[tool_name]}


def _terms(value: str) -> set[str]:
    return set(value.lower().replace("@", " ").replace(".", " ").split())


_DIRECTORY_FIRST_NAMES = (
    "Aarav",
    "Aisha",
    "Alejandro",
    "Amelia",
    "Ben",
    "Camila",
    "Daniel",
    "Elena",
    "Fatima",
    "Grace",
    "Hiro",
    "Imani",
    "Jonah",
    "Kavya",
    "Luca",
    "Maya",
    "Noah",
    "Omar",
    "Sofia",
    "Tariq",
    "Uma",
    "Victor",
    "Wen",
    "Zoe",
)
_DIRECTORY_LAST_NAMES = (
    "Brooks",
    "Chen",
    "Davis",
    "Martinez",
    "Okafor",
    "Patel",
    "Nguyen",
    "Kim",
    "Garcia",
    "Johnson",
)


def _all_directory_workers(world: AccessProvisioningWorld) -> dict[str, Worker]:
    workers = dict(world.workers)
    needed = world.company_directory.total_people - len(workers)
    names = [
        (first_name, last_name)
        for first_name in _DIRECTORY_FIRST_NAMES
        for last_name in _DIRECTORY_LAST_NAMES
    ]
    if needed < 0 or needed > len(names):
        raise ValueError("Company directory size cannot be generated from its seed")
    departments = world.company_directory.departments
    for index, (first_name, last_name) in enumerate(names[:needed], start=1):
        if index <= len(departments):
            department = departments[index - 1]
            manager_id = "worker_ava_cole"
            job_title = f"Head of {department}"
        else:
            department_index = (index - len(departments) - 1) % len(departments)
            department = departments[department_index]
            manager_id = f"worker_directory_{department_index + 1:03d}"
            job_title = "Specialist"
        worker_id = f"worker_directory_{index:03d}"
        workers[worker_id] = Worker(
            worker_id=worker_id,
            legal_name=f"{first_name} {last_name}",
            worker_type="employee",
            status="active",
            manager_id=manager_id,
            primary_email=(
                f"{first_name}.{last_name}.{index:03d}@atlas.example".lower()
            ),
            department=department,
            job_title=job_title,
        )
    return workers


def _search_workers(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SearchWorkersArguments.model_validate(raw)
    query = _terms(args.query)
    directory = _all_directory_workers(world)
    workers = []
    for item in directory.values():
        searchable = " ".join(
            [
                item.worker_id,
                item.legal_name,
                item.primary_email,
                item.status,
                item.manager_id,
                item.department,
                item.job_title,
            ]
        )
        if not query & _terms(searchable):
            continue
        result = item.model_dump(mode="json")
        manager = directory.get(item.manager_id)
        result["manager_name"] = manager.legal_name if manager else None
        workers.append(result)
    workers.sort(key=lambda item: item["worker_id"])
    return {
        "company": world.company_directory.company_name,
        "company_people_count": len(directory),
        "people": workers,
        "count": len(workers),
    }


def _search_users(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SearchUsersArguments.model_validate(raw)
    query = _terms(args.query)
    users = [
        item.model_dump(mode="json")
        for item in world.identities.values()
        if query & _terms(" ".join([item.user_id, item.email, item.status]))
    ]
    users.sort(key=lambda item: item["user_id"])
    return {"users": users, "count": len(users)}


def _get_training(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = GetTrainingArguments.model_validate(raw)
    records = [
        item.model_dump(mode="json")
        for item in world.training_records.values()
        if item.worker_id == args.worker_id
    ]
    records.sort(key=lambda item: item["course_id"])
    return {"records": records}


def _add_group(world: AccessProvisioningWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = AddUserToGroupArguments.model_validate(raw)
    identity = world.identities.get(args.user_id)
    if identity is None:
        raise ValueError("Okta user not found")
    if identity.status != "active":
        raise ValueError("Cannot grant a suspended identity")
    if args.group_id not in identity.groups:
        identity.groups.append(args.group_id)
        identity.groups.sort()
        identity.group_history.append(
            GroupHistoryEntry(group_id=args.group_id, added_on=world.current_time[:10])
        )
    identity.group_expirations[args.group_id] = args.expires_on
    return {"user": identity.model_dump(mode="json")}


def _remove_group(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = RemoveUserFromGroupArguments.model_validate(raw)
    identity = world.identities.get(args.user_id)
    if identity is None:
        raise ValueError("Okta user not found")
    if args.group_id in identity.groups:
        identity.groups.remove(args.group_id)
        for entry in identity.group_history:
            if entry.group_id == args.group_id and entry.removed_on is None:
                entry.removed_on = world.current_time[:10]
    identity.group_expirations.pop(args.group_id, None)
    return {"user": identity.model_dump(mode="json")}


def _assign_training(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = AssignTrainingArguments.model_validate(raw)
    if args.worker_id not in world.workers:
        raise ValueError("Worker not found")
    key = f"{args.worker_id}:{args.course_id}"
    existing = world.training_records.get(key)
    if existing and existing.status == "complete":
        return {"assignment": existing.model_dump(mode="json")}
    record = TrainingRecord(
        worker_id=args.worker_id,
        course_id=args.course_id,
        status="assigned",
        assigned_at=world.current_time,
    )
    world.training_records[key] = record
    return {"assignment": record.model_dump(mode="json")}


def _search_requests(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SearchAccessRequestsArguments.model_validate(raw)
    if args.worker_id is None and args.approver_id is None:
        raise ValueError("Provide worker_id, approver_id, or both")
    requests = [
        item.model_dump(mode="json")
        for item in world.access_requests.values()
        if args.worker_id in (None, item.worker_id)
        and args.approver_id in (None, item.approver_id)
    ]
    requests.sort(key=lambda item: item["request_id"])
    return {"issues": requests, "count": len(requests)}


def _update_request(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = UpdateAccessRequestArguments.model_validate(raw)
    request = world.access_requests.get(args.request_id)
    if request is None:
        raise ValueError("Access request not found")
    request.status = args.status
    request.granted_groups = sorted(set(args.granted_groups))
    request.blocked_reason = args.blocked_reason
    request.access_expiration = args.access_expiration
    request.description = args.description
    return {"issue": request.model_dump(mode="json")}


def _update_slack(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SlackUpdateArguments.model_validate(raw)
    message = world.slack_messages.get(args.message_id)
    if message is None:
        raise ValueError("Slack message not found")
    if message.channel != args.channel.removeprefix("#"):
        raise ValueError("Slack message is not in the requested channel")
    message.text = args.text
    return {"ok": True, "message": message.model_dump(mode="json")}


def _public_message(
    message: SlackMessage, replies: int | None = None
) -> dict[str, Any]:
    shown = {
        key: value
        for key, value in message.model_dump(mode="json").items()
        if value or key in {"message_id", "channel", "text"}
    }
    if replies:
        shown["reply_count"] = replies
    return shown


def _reply_counts(world: AccessProvisioningWorld) -> dict[str, int]:
    counts: dict[str, int] = {}
    for message in world.slack_messages.values():
        if message.thread_id:
            counts[message.thread_id] = counts.get(message.thread_id, 0) + 1
    return counts


def _slack_order(message: SlackMessage) -> tuple[str, str]:
    return (message.sent_at, message.message_id)


def _page(
    items: list[Any], limit: int, cursor: str | None, cap: int = 15
) -> tuple[list[Any], str]:
    try:
        start = max(int(cursor or 0), 0)
    except ValueError:
        raise ValueError("invalid_cursor") from None
    limit = min(max(limit, 1), cap)
    end = start + limit
    return items[start:end], (str(end) if end < len(items) else "")


def _slack_channel(world: AccessProvisioningWorld, name: str) -> str:
    name = name.removeprefix("#")
    known = {m.channel for m in world.slack_messages.values()} | set(
        world.slack_channels
    )
    if name not in known:
        raise ValueError(f"channel_not_found: #{name}")
    return name


def _search_slack(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SlackSearchArguments.model_validate(raw)
    channel = args.channel.removeprefix("#") if args.channel else None
    author = after = before = None
    words: list[str] = []
    for token in args.query.split():
        key, _, value = token.partition(":")
        if key == "in" and value:
            channel = value.removeprefix("#")
        elif key == "from" and value:
            author = value.removeprefix("@").lower()
        elif key == "after" and value:
            after = value
        elif key == "before" and value:
            before = value
        else:
            words.append(token.lower())
    if not words and not (channel or author or after or before):
        raise ValueError("invalid_arguments: query is required")
    matches = []
    for message in world.slack_messages.values():
        if channel and message.channel != channel:
            continue
        if author and author not in message.author.lower():
            continue
        if after and message.sent_at[:10] <= after[:10]:
            continue
        if before and message.sent_at[:10] >= before[:10]:
            continue
        haystack = _terms(f"{message.channel} {message.author} {message.text}")
        if any(not _terms(word) <= haystack for word in words):
            continue
        matches.append(message)
    matches.sort(key=_slack_order, reverse=True)
    count = min(max(args.count, 1), 15)
    page = max(args.page, 1)
    window = matches[(page - 1) * count : page * count]
    replies = _reply_counts(world)
    return {
        "messages": [_public_message(m, replies.get(m.message_id)) for m in window],
        "count": len(matches),
        "total": len(matches),
        "channels": sorted({m.channel for m in matches}),
        "page": page,
        "pages": -(-len(matches) // count),
    }


def _list_slack_channels(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SlackListChannelsArguments.model_validate(raw)
    channels = dict(world.slack_channels)
    for message in world.slack_messages.values():
        channels.setdefault(message.channel, SlackChannel(name=message.channel))
    ordered = [channels[name] for name in sorted(channels)]
    window, cursor = _page(ordered, args.limit, args.cursor, cap=50)
    return {
        "channels": [c.model_dump(mode="json") for c in window],
        "next_cursor": cursor,
    }


def _slack_history(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SlackHistoryArguments.model_validate(raw)
    channel = _slack_channel(world, args.channel)
    messages = [
        m
        for m in world.slack_messages.values()
        if m.channel == channel and not m.thread_id
    ]
    if args.oldest:
        messages = [m for m in messages if m.sent_at[:10] >= args.oldest[:10]]
    if args.latest:
        messages = [m for m in messages if m.sent_at[:10] <= args.latest[:10]]
    messages.sort(key=_slack_order, reverse=True)
    window, cursor = _page(messages, args.limit, args.cursor)
    replies = _reply_counts(world)
    return {
        "messages": [_public_message(m, replies.get(m.message_id)) for m in window],
        "has_more": bool(cursor),
        "next_cursor": cursor,
    }


def _slack_replies(
    world: AccessProvisioningWorld, raw: dict[str, Any]
) -> dict[str, Any]:
    args = SlackRepliesArguments.model_validate(raw)
    channel = _slack_channel(world, args.channel)
    parent = world.slack_messages.get(args.thread_id)
    if parent is None or parent.channel != channel or parent.thread_id:
        raise ValueError("thread_not_found")
    thread = sorted(
        (m for m in world.slack_messages.values() if m.thread_id == parent.message_id),
        key=_slack_order,
    )
    return {"messages": [_public_message(m) for m in [parent, *thread]]}


def _post_slack(world: AccessProvisioningWorld, raw: dict[str, Any]) -> dict[str, Any]:
    args = SlackPostArguments.model_validate(raw)
    channel = _slack_channel(world, args.channel)
    if args.thread_id and (
        args.thread_id not in world.slack_messages
        or world.slack_messages[args.thread_id].channel != channel
    ):
        raise ValueError("thread_not_found")
    message_id = f"slack_message_{len(world.slack_messages) + 1:03d}"
    message = SlackMessage(
        message_id=message_id,
        channel=channel,
        text=args.text,
        author="atlas-ops",
        sent_at=world.current_time,
        thread_id=args.thread_id or "",
    )
    world.slack_messages[message_id] = message
    return {"ok": True, "message": _public_message(message)}


_HANDLERS: dict[
    str, Callable[[AccessProvisioningWorld, dict[str, Any]], dict[str, Any]]
] = {
    "rippling_search_people_v1": _search_workers,
    "okta_search_users_v1": _search_users,
    "lms_get_training_status_v1": _get_training,
    "okta_add_user_to_group_v1": _add_group,
    "okta_remove_user_from_group_v1": _remove_group,
    "lms_assign_training_v1": _assign_training,
    "jira_search_access_requests_v1": _search_requests,
    "jira_update_access_request_v1": _update_request,
    "slack_search_messages_v1": _search_slack,
    "slack_list_channels_v1": _list_slack_channels,
    "slack_get_channel_history_v1": _slack_history,
    "slack_get_thread_replies_v1": _slack_replies,
    "slack_chat_post_message": _post_slack,
    "slack_chat_update_message_v1": _update_slack,
}


def validate_world(raw: dict[str, Any]) -> AccessProvisioningWorld:
    return AccessProvisioningWorld.model_validate(raw)


def _call_tool_model(
    world: AccessProvisioningWorld, tool_name: str, arguments: str
) -> str:
    if tool_name not in _HANDLERS:
        raise ValueError(f"Unknown access-provisioning tool: {tool_name}")
    try:
        raw = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"arguments must be valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("arguments must encode one JSON object")
    for fault in world.injected_faults:
        if (
            fault.remaining > 0
            and fault.tool_name == tool_name
            and all(raw.get(key) == value for key, value in fault.match.items())
        ):
            # Returned rather than raised so the spent fault persists with the world.
            fault.remaining -= 1
            return json.dumps(fault.response, sort_keys=True)
    return json.dumps(_HANDLERS[tool_name](world, raw), sort_keys=True)


def call_tool(
    raw_world: dict[str, Any], tool_name: str, arguments: str
) -> tuple[dict[str, Any], str]:
    world = validate_world(raw_world)
    response = _call_tool_model(world, tool_name, arguments)
    return world.model_dump(mode="json"), response


def _contains_all(value: str, terms: list[str]) -> bool:
    lowered = value.lower()
    return all(term.lower() in lowered for term in terms)


def _llm_content_judge(text: str, rubric: str) -> bool:
    """Ask a small model whether one workplace message meets a one-line rubric."""
    from tau2.config import DEFAULT_LLM_NL_ASSERTIONS, DEFAULT_LLM_NL_ASSERTIONS_ARGS
    from tau2.data_model.message import SystemMessage, UserMessage
    from tau2.utils.llm_utils import generate

    # An empty or malformed reply is retried rather than graded as a failure.
    for attempt in range(3):
        response = generate(
            model=DEFAULT_LLM_NL_ASSERTIONS,
            messages=[
                SystemMessage(
                    role="system",
                    content=(
                        "You check one workplace message (a chat post or an email) against "
                        "one requirement. "
                        "Judge meaning, not wording. Messages often use internal "
                        "identifiers: access groups are named grp_* (grp_breakglass is "
                        "break-glass access, grp_prod_readonly is production read-only, "
                        "grp_prod_admin is production admin, grp_staging_readonly and "
                        "grp_staging_deployer are staging access, grp_analytics_readonly "
                        "is analytics read-only), and training courses are named by "
                        "course ID such as secure-production-access-2026. An identifier "
                        "counts the same as its plain-language name. Extra detail beyond "
                        "the requirement is fine. Reply with JSON "
                        '{"reasoning": "<one sentence>", "met": true|false}.'
                    ),
                ),
                UserMessage(
                    role="user",
                    content=f"Requirement: {rubric}\n\nMessage:\n{text}",
                ),
            ],
            call_name="access_content_judge",
            **DEFAULT_LLM_NL_ASSERTIONS_ARGS,
        )
        try:
            return bool(json.loads(response.content or "").get("met"))
        except (json.JSONDecodeError, AttributeError):
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


# Grading calls go through this hook so offline tests can substitute the judge.
CONTENT_JUDGE: Callable[[str, str], bool] = _llm_content_judge
_JUDGE_CACHE: dict[tuple[str, str], bool] = {}


def _content_meets(text: str, rubric: str) -> bool:
    """Judge message content once per (text, rubric) so replays stay consistent."""
    key = (text, rubric)
    if key not in _JUDGE_CACHE:
        _JUDGE_CACHE[key] = CONTENT_JUDGE(text, rubric)
    return _JUDGE_CACHE[key]


def _mentions_training(value: str) -> bool:
    """Accept the course ID as naming the training requirement."""
    lowered = value.lower()
    return "training" in lowered or "secure-production-access" in lowered


def _check_assertion_model(
    world: AccessProvisioningWorld, assertion: dict[str, Any]
) -> bool:
    assertion_type = assertion["type"]
    active = world.identities.get("okta_priya_active")
    stale = world.identities.get("okta_priya_stale")
    request = world.access_requests.get("ACCESS-391")
    if assertion_type == "access_active_identity_staging_only":
        return bool(
            active
            and active.worker_id == "worker_priya_raman"
            and active.status == "active"
            and active.groups == ["grp_staging_readonly"]
            and active.group_expirations == {"grp_staging_readonly": "2026-12-14"}
        )
    if assertion_type == "access_active_identity_no_entitlements":
        return bool(
            active
            and active.worker_id == "worker_priya_raman"
            and active.status == "active"
            and active.groups == []
            and active.group_expirations == {}
        )
    if assertion_type == "access_no_production_entitlement":
        forbidden = {"grp_prod_admin", "grp_prod_readonly", "grp_breakglass"}
        return bool(active and forbidden.isdisjoint(active.groups))
    if assertion_type == "access_training_assigned_exact":
        records = [
            item
            for item in world.training_records.values()
            if item.worker_id == "worker_priya_raman"
            and item.course_id == "secure-production-access-2026"
        ]
        return bool(
            len(records) == 1
            and records[0].status == "assigned"
            and records[0].assigned_at == "2026-11-14T10:15:00-08:00"
        )
    if assertion_type == "access_existing_request_blocked_exact":
        return bool(
            request
            and request.worker_id == "worker_priya_raman"
            and request.requested_groups == ["grp_prod_admin"]
            and request.granted_groups == ["grp_staging_readonly"]
            and request.status == "Blocked - training"
            and request.blocked_reason == "PRODUCTION_TRAINING_INCOMPLETE"
            and request.access_expiration == "2026-12-14"
        )
    if assertion_type == "access_existing_request_blocked_no_grant_exact":
        return bool(
            request
            and request.worker_id == "worker_priya_raman"
            and request.requested_groups == ["grp_prod_admin"]
            and request.granted_groups == []
            and request.status == "Blocked - training"
            and request.blocked_reason == "PRODUCTION_TRAINING_INCOMPLETE"
            and request.access_expiration is None
        )
    if assertion_type == "access_no_unrelated_api_side_effects":
        # The family registry evaluates this cross-world assertion against the
        # AutomationWorkplaceDB envelope. Direct family replays have no generic
        # AutomationBench world and therefore satisfy it by construction.
        return True
    if assertion_type == "access_no_duplicate_request":
        priya = [
            item
            for item in world.access_requests.values()
            if item.worker_id == "worker_priya_raman"
        ]
        return len(priya) == 1 and priya[0].request_id == "ACCESS-391"
    if assertion_type == "access_no_priya_slack_update":
        return not any(
            "priya raman" in message.text.lower()
            for message in world.slack_messages.values()
        )
    if assertion_type == "access_manager_notified_once":
        messages = [
            message
            for message in world.slack_messages.values()
            if "priya raman" in message.text.lower()
        ]
        if len(messages) != 1 or messages[0].channel != "eng-access-requests":
            return False
        text = messages[0].text
        if not _contains_all(text, ["Priya Raman", "2026-12-14"]):
            return False
        if rubric := assertion.get("rubric"):
            return _content_meets(text, rubric)
        return _contains_all(
            text, ["staging read-only", "production", "blocked"]
        ) and _mentions_training(text)
    if assertion_type == "access_manager_notified_no_access_once":
        messages = [
            message
            for message in world.slack_messages.values()
            if "priya raman" in message.text.lower()
        ]
        if len(messages) != 1 or messages[0].channel != "eng-access-requests":
            return False
        text = messages[0].text.lower()
        no_grant = any(
            phrase in text
            for phrase in (
                "no access",
                "no new access",
                "no entitlement",
                "nothing was granted",
                "nothing granted",
            )
        )
        incorrectly_claims_staging = any(
            phrase in text
            for phrase in (
                "received staging",
                "granted staging",
                "staging read-only is active",
            )
        )
        return bool(
            no_grant
            and not incorrectly_claims_staging
            and _contains_all(
                messages[0].text,
                ["Priya Raman", "production", "blocked"],
            )
            and _mentions_training(messages[0].text)
        )
    if assertion_type == "access_stale_identity_preserved":
        return bool(
            stale
            and stale.email == "priya.raman.intern@atlas.example"
            and stale.status == "suspended"
            and stale.groups == []
            and stale.group_expirations == {}
        )
    if assertion_type == "access_reference_user_preserved":
        miguel = world.identities.get("okta_miguel")
        return bool(
            miguel
            and miguel.groups == ["grp_prod_admin", "grp_staging_readonly"]
            and miguel.group_expirations == {}
        )
    if assertion_type == "access_noise_records_preserved":
        expected_identities = {
            "okta_priya_shah": (
                "worker_priya_shah",
                "active",
                ["grp_salesforce_readonly"],
                {},
            ),
            "okta_miguel_santiago": (
                "worker_miguel_santiago",
                "active",
                ["grp_staging_readonly"],
                {"grp_staging_readonly": "2027-02-28"},
            ),
        }
        for identity_id, expected in expected_identities.items():
            identity = world.identities.get(identity_id)
            if identity is None:
                return False
            actual = (
                identity.worker_id,
                identity.status,
                identity.groups,
                identity.group_expirations,
            )
            if actual != expected:
                return False

        expected_requests = {
            "ACCESS-386": (
                "worker_priya_shah",
                "Completed",
                ["grp_salesforce_readonly"],
                None,
            ),
            "ACCESS-392": (
                "worker_miguel_santiago",
                "Blocked - training",
                ["grp_staging_readonly"],
                "2027-02-28",
            ),
        }
        for request_id, expected in expected_requests.items():
            noise_request = world.access_requests.get(request_id)
            if noise_request is None:
                return False
            actual = (
                noise_request.worker_id,
                noise_request.status,
                noise_request.granted_groups,
                noise_request.access_expiration,
            )
            if actual != expected:
                return False

        expected_training = {
            "worker_priya_shah:security-awareness-2026": "complete",
            "worker_miguel_santiago:secure-production-access-2026": "assigned",
        }
        if any(
            key not in world.training_records
            or world.training_records[key].status != status
            for key, status in expected_training.items()
        ):
            return False

        expected_slack = {
            "slack_message_017": (
                "it-help",
                "If an application tile is missing, submit an app visibility access request. This queue does not approve production entitlements.",
            ),
            "slack_message_019": (
                "data-access",
                "Warehouse data access requests need a data owner and retention purpose. Production application roles are handled elsewhere.",
            ),
            "slack_message_022": (
                "prod-ops",
                "The billing-service production configuration freeze begins Friday; staging validation closes Thursday.",
            ),
        }
        return all(
            message_id in world.slack_messages
            and world.slack_messages[message_id].channel == channel
            and world.slack_messages[message_id].text == text
            for message_id, (channel, text) in expected_slack.items()
        )
    if assertion_type.startswith("backlog_"):
        return _check_backlog_assertion(world, assertion)
    raise ValueError(f"Unknown access-provisioning assertion type: {assertion_type}")


def _mentions_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def _check_backlog_assertion(
    world: AccessProvisioningWorld, assertion: dict[str, Any]
) -> bool:
    """Data-driven checks for multi-request backlog tasks.

    Each assertion carries its own expected values, so one task file can grade
    several independent requests without person-specific checker code.
    """
    assertion_type = assertion["type"]
    if assertion_type == "backlog_identity_exact":
        identity = world.identities.get(assertion["user_id"])
        return bool(
            identity
            and identity.status == assertion["status"]
            and identity.groups == sorted(assertion["groups"])
            and identity.group_expirations == assertion["group_expirations"]
        )
    if assertion_type == "backlog_request_no_grant":
        request = world.access_requests.get(assertion["request_id"])
        return bool(
            request
            and request.granted_groups == []
            and request.access_expiration is None
            and request.status != "Completed"
        )
    if assertion_type == "backlog_request_exact":
        request = world.access_requests.get(assertion["request_id"])
        # Some dispositions have more than one defensible (status, reason) pair.
        accepted = assertion.get("accepted_dispositions") or [
            [assertion["status"], assertion["blocked_reason"]]
        ]
        return bool(
            request
            and [request.status, request.blocked_reason or ""] in accepted
            and request.granted_groups == sorted(assertion["granted_groups"])
            and request.access_expiration == assertion["access_expiration"]
            and _contains_all(
                request.description, assertion.get("description_contains", [])
            )
        )
    if assertion_type == "backlog_training_assignments_exact":
        new_keys = sorted(
            set(world.training_records) - set(assertion["initial_record_keys"])
        )
        expected = sorted(
            f"{item['worker_id']}:{item['course_id']}"
            for item in assertion["assignments"]
        )
        return new_keys == expected and all(
            world.training_records[key].status == "assigned" for key in new_keys
        )
    if assertion_type == "backlog_no_new_requests":
        return sorted(world.access_requests) == sorted(assertion["request_ids"])
    if assertion_type == "backlog_slack_updates_exact":
        new_messages = [
            message
            for message_id, message in world.slack_messages.items()
            if message_id not in set(assertion["initial_message_ids"])
        ]
        if any(message.channel != assertion["channel"] for message in new_messages):
            return False
        if any(
            _mentions_any(message.text, assertion["silent_names"])
            for message in new_messages
        ):
            return False
        if assertion.get("one_message_per_person"):
            names = [person["name"].lower() for person in assertion["announced"]]
            if len(new_messages) != len(names):
                return False
            if any(
                sum(name in message.text.lower() for name in names) != 1
                for message in new_messages
            ):
                return False
        for person in assertion["announced"]:
            mentions = [
                message
                for message in new_messages
                if person["name"].lower() in message.text.lower()
            ]
            if len(mentions) != 1:
                return False
            text = mentions[0].text
            if not _contains_all(text, person.get("all_of", [])):
                return False
            if rubric := person.get("rubric"):
                if not _content_meets(text, rubric):
                    return False
                continue
            if not all(
                _mentions_any(text, options) for options in person.get("any_of", [])
            ):
                return False
            if person.get("mentions_training") and not _mentions_training(text):
                return False
        return True
    if assertion_type == "backlog_records_unchanged":
        snapshot = assertion["snapshot"]
        collections = {
            "identities": world.identities,
            "access_requests": world.access_requests,
            "training_records": world.training_records,
            "slack_messages": world.slack_messages,
        }
        for name, expected_records in snapshot.items():
            actual_records = collections[name]
            for record_id, expected in expected_records.items():
                actual = actual_records.get(record_id)
                # Snapshots predate fields added with defaults; compare through the model.
                if actual is None or actual.model_dump(mode="json") != type(
                    actual
                ).model_validate(expected).model_dump(mode="json"):
                    return False
        return True
    raise ValueError(f"Unknown access backlog assertion type: {assertion_type}")


# Who ends up with which access, and what was left alone, versus how the outcome
# was recorded and announced. Reported separately so convention mismatches do not
# hide (or masquerade as) access mistakes.
PROCESS_ASSERTION_TYPES = {
    "access_existing_request_blocked_exact",
    "access_existing_request_blocked_no_grant_exact",
    "access_no_duplicate_request",
    "access_manager_notified_once",
    "access_manager_notified_no_access_once",
    "access_no_priya_slack_update",
    "backlog_request_exact",
    "backlog_slack_updates_exact",
    "backlog_no_new_requests",
}


def assertion_category(assertion: dict[str, Any]) -> str:
    """Return "decision" or "process" for one assertion."""
    if category := assertion.get("category"):
        return category
    return "process" if assertion["type"] in PROCESS_ASSERTION_TYPES else "decision"


def check_assertion(raw_world: dict[str, Any], assertion: dict[str, Any]) -> bool:
    """Evaluate exact final state; conversation or call order is never inspected."""
    return _check_assertion_model(validate_world(raw_world), assertion)


def golden_call_sequence(
    task_id: str = "access_provisioning_001",
) -> list[tuple[str, dict[str, Any]]]:
    """Return one deterministic, policy-compliant write trajectory."""
    if task_id == "access_provisioning_003":
        return _backlog_golden_call_sequence()
    if task_id == "access_provisioning_004":
        return _scoping_golden_call_sequence()
    if task_id == "access_provisioning_005":
        return _queue_golden_call_sequence()
    if task_id == "access_provisioning_006":
        return _review_golden_call_sequence()
    if task_id == "access_provisioning_007":
        return _precedent_golden_call_sequence()
    if task_id == "access_provisioning_002":
        return [
            (
                "okta_remove_user_from_group_v1",
                {
                    "user_id": "okta_priya_active",
                    "group_id": "grp_staging_readonly",
                },
            ),
            (
                "lms_assign_training_v1",
                {
                    "worker_id": "worker_priya_raman",
                    "course_id": "secure-production-access-2026",
                },
            ),
            (
                "jira_update_access_request_v1",
                {
                    "request_id": "ACCESS-391",
                    "status": "Blocked - training",
                    "granted_groups": [],
                    "blocked_reason": "PRODUCTION_TRAINING_INCOMPLETE",
                    "access_expiration": None,
                    "description": "No access granted because the assignment requires production-only data and current production training is incomplete.",
                },
            ),
        ]
    return [
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_priya_active",
                "group_id": "grp_staging_readonly",
                "expires_on": "2026-12-14",
            },
        ),
        (
            "lms_assign_training_v1",
            {
                "worker_id": "worker_priya_raman",
                "course_id": "secure-production-access-2026",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-391",
                "status": "Blocked - training",
                "granted_groups": ["grp_staging_readonly"],
                "blocked_reason": "PRODUCTION_TRAINING_INCOMPLETE",
                "access_expiration": "2026-12-14",
                "description": "Granted staging read-only through 2026-12-14; production admin remains blocked until required training is complete.",
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "eng-access-requests",
                "text": "Priya Raman received staging read-only through 2026-12-14. Production admin is blocked pending required training.",
            },
        ),
    ]


def negative_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return a plausible but over-privileged manager-following trajectory."""
    return [
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_priya_active",
                "group_id": "grp_prod_admin",
                "expires_on": "2027-02-12",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-391",
                "status": "Completed",
                "granted_groups": ["grp_prod_admin"],
                "blocked_reason": "",
                "access_expiration": "2027-02-12",
                "description": "Copied Miguel's production administrator access after manager approval.",
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "eng-access-requests",
                "text": "Priya Raman received production administrator access as requested.",
            },
        ),
    ]


def production_only_negative_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Return a useless staging workaround with incomplete follow-through."""
    return [
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_priya_active",
                "group_id": "grp_staging_readonly",
                "expires_on": "2026-12-19",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-391",
                "status": "Blocked - training",
                "granted_groups": ["grp_staging_readonly"],
                "blocked_reason": "PRODUCTION_TRAINING_INCOMPLETE",
                "access_expiration": "2026-12-19",
                "description": "Granted staging read-only even though the work requires production-only data.",
            },
        ),
    ]


def _backlog_golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Clear the six-request backlog: three grants, three holds."""
    return [
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_lena_ortiz",
                "group_id": "grp_prod_readonly",
                "expires_on": "2027-01-15",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-401",
                "status": "Completed",
                "granted_groups": ["grp_prod_readonly"],
                "blocked_reason": "",
                "access_expiration": "2027-01-15",
                "description": "Granted production read-only through the contract end date.",
            },
        ),
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_sam_whitaker",
                "group_id": "grp_breakglass",
                "expires_on": "2026-12-18",
            },
        ),
        (
            "lms_assign_training_v1",
            {
                "worker_id": "worker_sam_whitaker",
                "course_id": "secure-production-access-2026",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-402",
                "status": "Blocked - training",
                "granted_groups": ["grp_breakglass"],
                "blocked_reason": "PRODUCTION_TRAINING_INCOMPLETE",
                "access_expiration": "2026-12-18",
                "description": "Break-glass for INC-901 under written CTO approval from Elena Park, window ends 2026-12-18. Production admin blocked pending training.",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-403",
                "status": "Declined",
                "granted_groups": [],
                "blocked_reason": "NOT_ELIGIBLE",
                "access_expiration": None,
                "description": "Worker is inactive in Rippling; contract ended 2026-12-12.",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-404",
                "status": "Closed - duplicate",
                "granted_groups": [],
                "blocked_reason": "",
                "access_expiration": None,
                "description": "Duplicate of ACCESS-398, which already granted this access.",
            },
        ),
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_noor_haddad",
                "group_id": "grp_staging_deployer",
                "expires_on": "2027-01-08",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-406",
                "status": "Completed",
                "granted_groups": ["grp_staging_deployer"],
                "blocked_reason": "",
                "access_expiration": "2027-01-08",
                "description": "Granted staging deployer through the internship end date.",
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "eng-access-requests",
                "text": "Lena Ortiz received production read-only through 2027-01-15. ACCESS-401 is complete.",
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "eng-access-requests",
                "text": "Sam Whitaker received break-glass for INC-901 through 2026-12-18 under CTO approval. Production admin remains blocked pending secure-production-access training; ACCESS-402 was updated.",
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "eng-access-requests",
                "text": "Noor Haddad received staging deployer through 2027-01-08. ACCESS-406 is complete.",
            },
        ),
    ]


def _grant_and_close(
    user_id: str,
    request_id: str,
    group_id: str,
    expires_on: str,
    *,
    status: str = "Completed",
    blocked_reason: str = "",
    description: str = "Granted.",
) -> list[tuple[str, dict[str, Any]]]:
    return [
        (
            "okta_add_user_to_group_v1",
            {"user_id": user_id, "group_id": group_id, "expires_on": expires_on},
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": request_id,
                "status": status,
                "granted_groups": [group_id],
                "blocked_reason": blocked_reason,
                "access_expiration": expires_on,
                "description": description,
            },
        ),
    ]


def _scoping_golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Scope down, grant partially, and block a role conflict."""
    return [
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-411",
                "status": "Blocked - conflict",
                "granted_groups": [],
                "blocked_reason": "SOD_CONFLICT",
                "access_expiration": None,
                "description": "Blocked: grp_prod_admin cannot be combined with his "
                "existing grp_release_approver role.",
            },
        ),
        *_grant_and_close(
            "okta_hana_sato",
            "ACCESS-412",
            "grp_prod_readonly",
            "2027-01-14",
            description="Work is read-only monitoring; granted production read-only "
            "instead of admin, through the contract end.",
        ),
        *_grant_and_close(
            "okta_ravi_menon",
            "ACCESS-413",
            "grp_staging_deployer",
            "2027-01-14",
            status="Blocked - training",
            blocked_reason="PRODUCTION_TRAINING_INCOMPLETE",
            description="Granted staging deployer; production read-only blocked "
            "pending training.",
        ),
        (
            "lms_assign_training_v1",
            {
                "worker_id": "worker_ravi_menon",
                "course_id": "secure-production-access-2026",
            },
        ),
        *_grant_and_close(
            "okta_ines_duarte", "ACCESS-414", "grp_analytics_readonly", "2027-01-14"
        ),
        *_grant_and_close(
            "okta_owen_pike", "ACCESS-415", "grp_staging_readonly", "2027-01-14"
        ),
        *_grant_and_close(
            "okta_kofi_mensah", "ACCESS-416", "grp_staging_readonly", "2027-01-05"
        ),
        *[
            (
                "slack_chat_post_message",
                {"channel": "eng-access-requests", "text": text},
            )
            for text in (
                "Hana Sato received production read-only through 2027-01-14.",
                "Ravi Menon received staging deployer through 2027-01-14. Production "
                "read-only is blocked pending secure-production-access training.",
                "Ines Duarte received analytics read-only through 2027-01-14.",
                "Owen Pike received staging read-only through 2027-01-14.",
                "Kofi Mensah received staging read-only through 2027-01-05.",
            )
        ],
    ]


def _close_without_grant(
    request_id: str, status: str, blocked_reason: str, description: str
) -> tuple[str, dict[str, Any]]:
    return (
        "jira_update_access_request_v1",
        {
            "request_id": request_id,
            "status": status,
            "granted_groups": [],
            "blocked_reason": blocked_reason,
            "access_expiration": None,
            "description": description,
        },
    )


def _queue_golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Clear the twelve-request queue for Payments Platform."""
    default_end = "2027-01-16"
    grants = [
        ("okta_leo_fischer", "ACCESS-421", "grp_staging_readonly", default_end),
        ("okta_mira_novak", "ACCESS-422", "grp_staging_readonly", "2027-01-08"),
        ("okta_aditi_rao", "ACCESS-423", "grp_analytics_readonly", default_end),
        ("okta_carla_mendes", "ACCESS-424", "grp_prod_readonly", default_end),
        ("okta_sofia_lind", "ACCESS-431", "grp_staging_deployer", "2027-01-12"),
        ("okta_pavel_ivanov", "ACCESS-432", "grp_prod_readonly", default_end),
    ]
    sequence = [
        step
        for user_id, request_id, group_id, expires_on in grants
        for step in _grant_and_close(user_id, request_id, group_id, expires_on)
    ]
    sequence += _grant_and_close(
        "okta_bruno_costa",
        "ACCESS-426",
        "grp_staging_deployer",
        default_end,
        status="Blocked - training",
        blocked_reason="PRODUCTION_TRAINING_INCOMPLETE",
        description="Staging deployer granted; production read-only blocked on "
        "training.",
    )
    sequence += _grant_and_close(
        "okta_femi_adeyemi",
        "ACCESS-427",
        "grp_breakglass",
        "2026-12-19",
        status="Blocked - training",
        blocked_reason="PRODUCTION_TRAINING_INCOMPLETE",
        description="Break-glass for INC-912 under written CTO approval; production "
        "admin blocked on training.",
    )
    sequence += [
        (
            "lms_assign_training_v1",
            {"worker_id": worker_id, "course_id": "secure-production-access-2026"},
        )
        for worker_id in ("worker_bruno_costa", "worker_femi_adeyemi")
    ]
    sequence += [
        _close_without_grant(
            "ACCESS-425",
            "Blocked - conflict",
            "SOD_CONFLICT",
            "Conflicts with his existing release approver role.",
        ),
        _close_without_grant(
            "ACCESS-428",
            "Declined",
            "NOT_ELIGIBLE",
            "Worker is inactive; contract ended 2026-12-11.",
        ),
        _close_without_grant(
            "ACCESS-429", "Closed - duplicate", "", "Duplicate of ACCESS-410."
        ),
    ]
    sequence += [
        ("slack_chat_post_message", {"channel": "eng-access-requests", "text": text})
        for text in (
            f"Leo Fischer received staging read-only through {default_end}.",
            "Mira Novak received staging read-only through 2027-01-08.",
            f"Aditi Rao received analytics read-only through {default_end}.",
            f"Carla Mendes received production read-only through {default_end}.",
            f"Bruno Costa received staging deployer through {default_end}. "
            "Production read-only is blocked pending training.",
            "Femi Adeyemi received break-glass for INC-912 through 2026-12-19.",
            "Sofia Lind received staging deployer through 2027-01-12.",
            f"Pavel Ivanov received production read-only through {default_end}.",
        )
    ]
    return sequence


def _review_golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Clear the Data Platform queue and apply the outstanding Q4 removals.

    The approval request goes out through the generic Gmail API, so it appears as
    an ``api_fetch`` step that family-only replays skip.
    """
    default_end = "2027-01-13"
    sequence = _grant_and_close(
        "okta_sven_holm", "ACCESS-441", "grp_prod_admin", default_end
    )
    sequence += _grant_and_close(
        "okta_omar_haddad", "ACCESS-443", "grp_prod_admin", "2027-01-08"
    )
    sequence += _grant_and_close(
        "okta_hana_kim", "ACCESS-445", "grp_analytics_readonly", default_end
    )
    leon = _grant_and_close(
        "okta_leon_brandt", "ACCESS-446", "grp_prod_readonly", "2027-01-05"
    )
    # The first Okta call for Leon times out without applying; retry it.
    sequence += [leon[0], *leon]
    sequence += [
        _close_without_grant(
            "ACCESS-442",
            "Blocked - approval",
            "ROLE_OWNER_APPROVAL_PENDING",
            "Waiting on the production admin role owners; approval requested.",
        ),
        _close_without_grant(
            "ACCESS-444",
            "Blocked - conflict",
            "SOD_CONFLICT",
            "Conflicts with his release approver role; his exception ended 2026-11-30.",
        ),
        (
            "api_fetch",
            {
                "method": "POST",
                "url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                "body": json.dumps(
                    {
                        "raw": base64.urlsafe_b64encode(
                            b"To: prod-admin-owners@atlas.example\r\n"
                            b"Subject: Role owner approval: ACCESS-442\r\n\r\n"
                            b"Please approve grp_prod_admin for Mei Tan "
                            b"(ACCESS-442), for the January backfill jobs."
                        ).decode()
                    }
                ),
            },
        ),
    ]
    sequence += [
        ("okta_remove_user_from_group_v1", {"user_id": user_id, "group_id": group})
        for user_id, group in (
            ("okta_lena_ostrowski", "grp_prod_admin"),
            ("okta_tomas_ruiz", "grp_prod_readonly"),
        )
    ]
    sequence += [
        ("slack_chat_post_message", {"channel": "eng-access-requests", "text": text})
        for text in (
            f"Sven Holm received production admin through {default_end}.",
            "Omar Haddad received production admin through 2027-01-08.",
            f"Hana Kim received analytics read-only through {default_end}.",
            "Leon Brandt received production read-only through 2027-01-05.",
        )
    ]
    return sequence


def _precedent_golden_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Grant three, hold three, and announce only the grants."""
    default_end = "2027-01-13"
    sequence = _grant_and_close(
        "okta_sven_holm", "ACCESS-451", "grp_prod_admin", default_end
    )
    sequence += _grant_and_close(
        "okta_omar_haddad", "ACCESS-453", "grp_prod_readonly", default_end
    )
    sequence += _grant_and_close(
        "okta_leon_brandt", "ACCESS-456", "grp_prod_readonly", "2027-01-05"
    )
    sequence += [
        _close_without_grant(
            "ACCESS-452",
            "Blocked - approval",
            "ROLE_OWNER_APPROVAL_PENDING",
            "Waiting on the production admin owners.",
        ),
        _close_without_grant(
            "ACCESS-454",
            "Blocked - conflict",
            "SOD_CONFLICT",
            "Release approver cannot also hold production admin.",
        ),
        (
            "lms_assign_training_v1",
            {
                "worker_id": "worker_hana_kim",
                "course_id": "secure-production-access-2026",
            },
        ),
        _close_without_grant(
            "ACCESS-455",
            "Blocked - training",
            "PRODUCTION_TRAINING_INCOMPLETE",
            "Assigned secure-production-access-2026.",
        ),
    ]
    sequence += [
        ("slack_chat_post_message", {"channel": "eng-access-requests", "text": text})
        for text in (
            f"Sven Holm received production admin through {default_end}. ACCESS-451",
            f"Omar Haddad received production read-only through {default_end}. "
            "ACCESS-453",
            "Leon Brandt received production read-only through 2027-01-05. ACCESS-456",
        )
    ]
    return sequence


def scoping_shortcut_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Grant exactly what was asked, resolving the conflict by dropping a role."""
    return [
        (
            "okta_remove_user_from_group_v1",
            {"user_id": "okta_tomas_rivera", "group_id": "grp_release_approver"},
        ),
        *_grant_and_close(
            "okta_tomas_rivera", "ACCESS-411", "grp_prod_admin", "2027-01-14"
        ),
        *_grant_and_close(
            "okta_hana_sato", "ACCESS-412", "grp_prod_admin", "2027-06-13"
        ),
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_ravi_menon",
                "group_id": "grp_prod_readonly",
                "expires_on": "2027-01-14",
            },
        ),
        *_grant_and_close(
            "okta_kofi_mensah", "ACCESS-416", "grp_staging_readonly", "2027-01-14"
        ),
    ]


def backlog_shortcut_call_sequence() -> list[tuple[str, dict[str, Any]]]:
    """Approve everything as the manager asked, the way a careless agent would."""
    return [
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_sam_whitaker",
                "group_id": "grp_prod_admin",
                "expires_on": "2026-12-23",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-402",
                "status": "Completed",
                "granted_groups": ["grp_prod_admin"],
                "blocked_reason": "",
                "access_expiration": "2026-12-23",
                "description": "Approved by manager and VP Engineering.",
            },
        ),
        (
            "okta_add_user_to_group_v1",
            {
                "user_id": "okta_maya_chen",
                "group_id": "grp_staging_readonly",
                "expires_on": "2027-03-16",
            },
        ),
        (
            "jira_update_access_request_v1",
            {
                "request_id": "ACCESS-405",
                "status": "Completed",
                "granted_groups": ["grp_analytics_readonly"],
                "blocked_reason": "",
                "access_expiration": "2027-06-14",
                "description": "Approved by Jordan Bell.",
            },
        ),
        (
            "slack_chat_post_message",
            {
                "channel": "eng-access-requests",
                "text": "Backlog cleared: Sam Whitaker, Maya Chen, Priya Shah and Dev Raghavan are all set.",
            },
        ),
    ]


def apply_golden_path(world: AccessProvisioningWorld) -> AccessProvisioningWorld:
    """Apply the intended writes; useful for dataset and assertion validation."""
    for tool_name, arguments in golden_call_sequence(world.task_id):
        if tool_name in _HANDLERS:
            _call_tool_model(world, tool_name, json.dumps(arguments))
    return world
