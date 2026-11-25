"""A small, self-contained Gmail and Google Drive surface for authored tasks.

Authored tasks whose generic world declares ``meta.engine == "standalone"`` do not
need the AutomationBench checkout. The access-provisioning tasks keep their real
work in their own Okta, Jira, TalentLMS and Slack operations; the generic
``api_search`` / ``api_fetch`` surface only needs a mailbox and a drive that agents can
read, and that the grader can check was left alone (no mail sent, nothing created).

Endpoints keep the public Gmail v1 and Drive v3 shapes. Any other service answers 401,
as the domain policy documents ("a 401 means that app is not connected").
"""

from __future__ import annotations

import base64
import json
import re
from copy import deepcopy
from email import message_from_string
from typing import Any
from urllib.parse import unquote, urlparse

ENGINE = "standalone"
DESK_ADDRESS = "access-desk@atlas.example"


def is_standalone(world: dict[str, Any]) -> bool:
    return world.get("meta", {}).get("engine") == ENGINE


def new_world(current_time: str) -> dict[str, Any]:
    """An empty mailbox and drive for a standalone task."""
    return {
        "meta": {
            "schema_version": "0.1.0",
            "current_time": current_time,
            "engine": ENGINE,
        },
        "gmail": {
            "messages": [],
            "labels": [],
            "drafts": [],
            "attachments": [],
            "threads": [],
        },
        "google_drive": {"actions": {}, "folders": [], "files": []},
    }


def generic_state(world: dict[str, Any]) -> dict[str, Any]:
    """The comparable part of a standalone world (clock metadata ignored)."""
    state = deepcopy(world)
    state.pop("meta", None)
    return state


_GMAIL = "https://gmail.googleapis.com/gmail/v1/users/{userId}"
_CATALOG: list[dict[str, Any]] = [
    {
        "id": "gmail.users.getProfile",
        "method": "GET",
        "description": "Get the authenticated user's Gmail profile: email address and mailbox totals.",
        "parameters": {
            "userId": {
                "type": "string",
                "required": True,
                "location": "path",
                "default": "me",
            }
        },
        "response": "Profile: {emailAddress, messagesTotal, threadsTotal, historyId}",
        "url": _GMAIL + "/profile",
    },
    {
        "id": "gmail.users.messages.list",
        "method": "GET",
        "description": "List messages in the mailbox. Supports a search query and a result limit.",
        "parameters": {
            "userId": {
                "type": "string",
                "required": True,
                "location": "path",
                "default": "me",
            },
            "q": {
                "type": "string",
                "required": False,
                "location": "query",
                "description": "Gmail search terms.",
            },
            "maxResults": {"type": "integer", "required": False, "location": "query"},
        },
        "response": "ListMessagesResponse: {messages: [{id, threadId}], resultSizeEstimate}",
        "url": _GMAIL + "/messages",
    },
    {
        "id": "gmail.users.messages.get",
        "method": "GET",
        "description": "Fetch one message by ID, including headers and body.",
        "parameters": {
            "userId": {
                "type": "string",
                "required": True,
                "location": "path",
                "default": "me",
            },
            "id": {"type": "string", "required": True, "location": "path"},
        },
        "response": "Message: {id, threadId, labelIds, snippet, payload}",
        "url": _GMAIL + "/messages/{id}",
    },
    {
        "id": "gmail.users.messages.send",
        "method": "POST",
        "description": "Compose and deliver an email to one or more recipients.",
        "parameters": {
            "userId": {
                "type": "string",
                "required": True,
                "location": "path",
                "default": "me",
            }
        },
        "request": "{raw: base64url-encoded RFC 2822 message}",
        "response": "Message: {id, threadId, labelIds}",
        "url": _GMAIL + "/messages/send",
    },
    {
        "id": "gmail.users.labels.list",
        "method": "GET",
        "description": "List all labels in the user's mailbox.",
        "parameters": {
            "userId": {
                "type": "string",
                "required": True,
                "location": "path",
                "default": "me",
            }
        },
        "response": "ListLabelsResponse: {labels: [Label]}",
        "url": _GMAIL + "/labels",
    },
    {
        "id": "google_drive.files.list",
        "method": "GET",
        "description": "List files and folders in Google Drive, optionally filtered with a query.",
        "parameters": {
            "q": {"type": "string", "required": False, "location": "query"},
            "pageSize": {"type": "integer", "required": False, "location": "query"},
            "fields": {"type": "string", "required": False, "location": "query"},
        },
        "response": "{kind: 'drive#fileList', files: [File], incompleteSearch}",
        "url": "https://www.googleapis.com/drive/v3/files",
    },
    {
        "id": "google_drive.files.get",
        "method": "GET",
        "description": "Fetch metadata for a specific file or folder using its ID.",
        "parameters": {
            "fileId": {"type": "string", "required": True, "location": "path"}
        },
        "response": "{kind: 'drive#file', id, name, mimeType}",
        "url": "https://www.googleapis.com/drive/v3/files/{fileId}",
    },
]


def api_search(query: str, top_k: int) -> str:
    """Rank the small endpoint catalog by word overlap with the query."""
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for entry in _CATALOG:
        text = " ".join([entry["id"], entry["description"], entry["url"]]).lower()
        haystack = set(re.findall(r"[a-z0-9]+", text))
        scored.append((len(words & haystack), entry["id"], entry))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return json.dumps({"results": [entry for _, _, entry in scored[:top_k]]})


def base64_encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _error(code: int, message: str) -> str:
    return json.dumps({"error": {"code": code, "message": message}})


def _epoch_ms(world: dict[str, Any]) -> int:
    from datetime import datetime

    stamp = world["meta"]["current_time"].replace("Z", "+00:00")
    return int(datetime.fromisoformat(stamp).timestamp() * 1000)


def _json(value: Any) -> str:
    return json.dumps(value)


def api_fetch(
    world: dict[str, Any],
    method: str,
    url: str,
    params: str | None,
    body: str | None,
) -> str:
    """Execute one call against the standalone Gmail and Drive state (mutates ``world``)."""
    parsed = urlparse(url)
    query = json.loads(params) if params else {}
    payload = json.loads(body) if body else {}
    method = method.upper()
    path = unquote(parsed.path).rstrip("/")
    if parsed.netloc == "gmail.googleapis.com":
        match = re.fullmatch(r"/gmail/v1/users/([^/]+)(/.*)", path)
        if not match:
            return _error(404, f"No handler for {method} {path}")
        return _gmail(world, method, match.group(2), query, payload)
    if parsed.netloc == "www.googleapis.com" and path.startswith("/drive/v3/files"):
        return _drive(world, method, path[len("/drive/v3/files") :], query)
    return _error(401, f"{parsed.netloc} is not connected for this task")


def _gmail(world, method, path, query, payload) -> str:
    messages = world["gmail"]["messages"]
    if method == "GET" and path == "/profile":
        return _json(
            {
                "emailAddress": DESK_ADDRESS,
                "messagesTotal": len(messages),
                "threadsTotal": len({m["thread_id"] for m in messages}),
                "historyId": str(1000 + len(messages)),
            }
        )
    if method == "GET" and path == "/labels":
        names = ["INBOX", "SENT", "DRAFT", "TRASH", "SPAM"]
        return _json(
            {"labels": [{"id": n, "name": n, "type": "system"} for n in names]}
        )
    if method == "GET" and path == "/messages":
        terms = str(query.get("q", "")).lower().replace("subject:", " ").split()
        limit = int(query.get("maxResults", 100))
        found = [
            m
            for m in messages
            if all(
                t
                in " ".join(
                    [m["subject"], m["body_plain"], " ".join(m["to"]), m["from_"]]
                ).lower()
                for t in terms
            )
        ][:limit]
        listing: dict[str, Any] = {"resultSizeEstimate": len(found)}
        if found:
            listing["messages"] = [
                {"id": m["id"], "threadId": m["thread_id"]} for m in found
            ]
        else:
            listing["messages"] = []
        return _json(listing)
    if method == "POST" and path == "/messages/send":
        return _send(world, payload)
    match = re.fullmatch(r"/messages/([^/]+)", path)
    if method == "GET" and match:
        message = next((m for m in messages if m["id"] == match.group(1)), None)
        if message is None:
            return _error(404, f"Message {match.group(1)} not found")
        return _json(_message_resource(message))
    return _error(404, f"No handler for {method} gmail/v1/users/me{path}")


def _send(world, payload) -> str:
    raw = payload.get("raw")
    if not raw:
        return _error(400, "Missing raw message")
    try:
        text = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
    except Exception:  # noqa: BLE001 - any decode failure is a client error
        return _error(400, "raw must be a base64url-encoded RFC 2822 message")
    parsed = message_from_string(text)

    def addresses(header):
        return [a.strip() for a in (parsed.get(header) or "").split(",") if a.strip()]

    messages = world["gmail"]["messages"]
    number = len(messages) + 1
    when = _epoch_ms(world)
    body = parsed.get_payload()
    message = {
        "id": f"{number:016x}",
        "thread_id": f"{number + 4096:016x}",
        "from_": DESK_ADDRESS,
        "from_name": None,
        "to": addresses("To"),
        "cc": addresses("Cc"),
        "bcc": addresses("Bcc"),
        "reply_to": None,
        "in_reply_to": None,
        "subject": parsed.get("Subject", ""),
        "body_plain": body if isinstance(body, str) else "",
        "body_html": None,
        "snippet": (body if isinstance(body, str) else "")[:100],
        "label_ids": ["SENT"],
        "attachment_ids": [],
        "is_read": True,
        "is_starred": False,
        "has_attachments": False,
        "date": when,
        "internal_date": when,
        "size_estimate": len(text),
    }
    messages.append(message)
    return _json(
        {"id": message["id"], "threadId": message["thread_id"], "labelIds": ["SENT"]}
    )


def _message_resource(message) -> dict[str, Any]:
    headers = [
        {"name": "From", "value": message["from_"]},
        {"name": "To", "value": ", ".join(message["to"])},
        {"name": "Subject", "value": message["subject"]},
    ]
    return {
        "id": message["id"],
        "threadId": message["thread_id"],
        "labelIds": message["label_ids"],
        "snippet": message["snippet"],
        "internalDate": str(message["internal_date"]),
        "sizeEstimate": message["size_estimate"],
        "payload": {
            "mimeType": "text/plain",
            "headers": headers,
            "body": {"data": base64_encode(message["body_plain"])},
        },
    }


def _drive(world, method, rest, query) -> str:
    files = world["google_drive"]["files"]
    if method == "GET" and rest == "":
        return _json(
            {
                "kind": "drive#fileList",
                "files": files[: int(query.get("pageSize", 100))],
                "incompleteSearch": False,
            }
        )
    match = re.fullmatch(r"/([^/]+)", rest)
    if method == "GET" and match:
        found = next((f for f in files if f.get("id") == match.group(1)), None)
        if found is None:
            return _error(404, f"File not found: {match.group(1)}")
        return _json(found)
    return _error(404, f"No handler for {method} drive/v3/files{rest}")
