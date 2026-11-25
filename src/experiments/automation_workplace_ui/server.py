"""Local web UI for playing the AI employee in an automation workplace task.

The runtime intentionally uses the same τ user simulator, environment, tools,
trajectory, and exact-state evaluator as a benchmark run. Only the agent is
replaced by a human-controlled participant.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tau2.agent.base_agent import HalfDuplexAgent, ValidAgentInputMessage
from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT
from tau2.data_model.message import (
    APICompatibleMessage,
    AssistantMessage,
    Message,
    MultiToolMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.data_model.simulation import SimulationRun
from tau2.domains.automation_workplace.data_model import (
    AutomationWorkplaceDB,
    KnowledgeDocument,
)
from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.family_registry import (
    check_assertion,
    tool_schemas,
)
from tau2.domains.automation_workplace.family_registry import (
    tool_schema as discoverable_tool_schema,
)
from tau2.domains.automation_workplace.prompts import USER_SIMULATION_GUIDELINES
from tau2.domains.automation_workplace.utils import (
    AUTOMATION_WORKPLACE_INTERACTIVE_DIR,
    AUTOMATION_WORKPLACE_KNOWLEDGE_PATH,
)
from tau2.environment.tool import Tool
from tau2.evaluator.evaluator import EvaluationType
from tau2.orchestrator.orchestrator import Orchestrator
from tau2.runner.simulation import run_simulation
from tau2.user.user_simulator import UserSimulator
from tau2.utils.utils import DATA_DIR

ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"
HUMAN_RUNS_DIR = ROOT / "data" / "simulations" / "automation_workplace_human"
# The Codex desktop process can carry placeholder provider variables. The local
# benchmark's checked-out .env is the explicit credential source for this runner.
load_dotenv(ROOT / ".env", override=True)


STOP = "###STOP###"


class WebAgentState(BaseModel):
    """Conversation history held by the human-controlled agent."""

    messages: list[APICompatibleMessage]


class WebAgent(HalfDuplexAgent):
    """A blocking τ agent whose next action is supplied by the browser."""

    def __init__(self, domain_policy: str, tools: list[Tool]):
        super().__init__(domain_policy=domain_policy, tools=tools)
        self._observation: list[Message] = []
        self._next_action: Optional[AssistantMessage] = None
        self._turn_finished = threading.Event()
        self._turn_finished.set()
        self._lock = threading.Lock()

    @property
    def is_waiting_for_human(self) -> bool:
        return not self._turn_finished.is_set()

    @property
    def observation(self) -> list[Message]:
        with self._lock:
            return deepcopy(self._observation)

    def set_action(self, action: AssistantMessage) -> None:
        with self._lock:
            if self._turn_finished.is_set():
                raise RuntimeError("The user is still responding; it is not your turn.")
            self._next_action = action
            self._turn_finished.set()

    def generate_next_message(
        self,
        message: ValidAgentInputMessage,
        state: WebAgentState,
    ) -> tuple[AssistantMessage, WebAgentState]:
        with self._lock:
            self._turn_finished.clear()
            if isinstance(message, MultiToolMessage):
                state.messages.extend(message.tool_messages)
            elif message is not None:
                state.messages.append(message)
            self._observation = deepcopy(state.messages)

        self._turn_finished.wait()

        with self._lock:
            response = self._next_action
            self._next_action = None
        if response is None:
            raise RuntimeError("Human agent turn released without an action")
        state.messages.append(response)
        return response, state

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> WebAgentState:
        return WebAgentState(messages=list(message_history or []))

    def stop(
        self,
        message: Optional[AssistantMessage] = None,
        state: Optional[WebAgentState] = None,
    ) -> None:
        super().stop(message, state)
        history = deepcopy(state.messages) if state else []
        with self._lock:
            self._observation = history + ([message] if message else [])
            self._turn_finished.set()

    @classmethod
    def is_stop(cls, message: AssistantMessage) -> bool:
        if message.is_tool_call() or message.content is None:
            return False
        return STOP in message.content


class CreateSessionRequest(BaseModel):
    task_id: str
    user_model: str = "gpt-4.1-2025-04-14"
    user_reasoning_effort: Optional[str] = None


class AgentActionRequest(BaseModel):
    kind: Literal["message", "tool_call"]
    content: Optional[str] = Field(default=None, max_length=20_000)
    tool_name: Optional[str] = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    ui_context: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocumentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    status: Literal["current", "superseded"]
    updated_at: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=100_000)
    tags: list[str] = Field(default_factory=list, max_length=100)


class KnowledgeDocumentCreate(KnowledgeDocumentUpdate):
    document_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]{2,99}$")


class UIEventRequest(BaseModel):
    kind: Literal[
        "app_opened",
        "folder_opened",
        "document_opened",
        "action_form_opened",
        "action_form_closed",
        "knowledge_edit_started",
        "knowledge_edit_cancelled",
        "knowledge_create_started",
        "knowledge_create_cancelled",
        "knowledge_delete_started",
        "knowledge_delete_cancelled",
    ]
    details: dict[str, Any] = Field(default_factory=dict)


def _scenario_dict(task: Any) -> dict[str, Any]:
    scenario = task.user_scenario.model_dump(mode="json")
    instructions = scenario.get("instructions", {})
    reason = instructions.get("reason_for_call", "")
    match = re.search(r"Open by saying only:\s*['\"](.+?)['\"]\.?$", reason)
    return {
        **scenario,
        "opening_message": match.group(1) if match else reason,
    }


def _task_payload(task: Any) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.id.rsplit("__", 1)[-1].replace("_", " ").title(),
        "ticket": task.ticket,
        "description": task.description.model_dump(mode="json"),
        "scenario": _scenario_dict(task),
        "assertion_count": len(task.evaluation_criteria.env_assertions or []),
    }


TASKS = {task.id: task for task in get_tasks("interactive_canonical")}


def _reload_tasks() -> None:
    """Re-read task and knowledge files so data edits show up without a restart."""
    fresh = {task.id: task for task in get_tasks("interactive_canonical")}
    TASKS.clear()
    TASKS.update(fresh)


KNOWLEDGE_SOURCE_LOCK = threading.Lock()


def _task_spec(task_id: str) -> tuple[Path, dict[str, Any]]:
    for task_path in sorted(
        (AUTOMATION_WORKPLACE_INTERACTIVE_DIR / "tasks").glob("*.json")
    ):
        spec = json.loads(task_path.read_text(encoding="utf-8"))
        if spec.get("id") == task_id:
            return task_path, spec
    raise ValueError(f"No authored task source found for {task_id!r}")


def _task_knowledge_source_path(task_id: str) -> Path:
    _, spec = _task_spec(task_id)
    if knowledge_file := spec.get("knowledge_file"):
        return AUTOMATION_WORKPLACE_INTERACTIVE_DIR / knowledge_file
    return AUTOMATION_WORKPLACE_KNOWLEDGE_PATH


def _knowledge_source_path(task_id: str, document_id: str) -> Path:
    """Resolve a document only through the selected task's authored data files."""
    _, spec = _task_spec(task_id)
    candidates = []
    if knowledge_file := spec.get("knowledge_file"):
        candidates.append(AUTOMATION_WORKPLACE_INTERACTIVE_DIR / knowledge_file)
    candidates.append(AUTOMATION_WORKPLACE_KNOWLEDGE_PATH)
    for candidate in candidates:
        documents = json.loads(candidate.read_text(encoding="utf-8"))
        if any(item.get("document_id") == document_id for item in documents):
            return candidate
    raise ValueError(
        f"No authored knowledge source found for {document_id!r} in task {task_id!r}"
    )


def _knowledge_item_spans(source: str) -> list[tuple[dict[str, Any], int, int]]:
    decoder = json.JSONDecoder()
    cursor = source.find("[") + 1
    items = []
    while cursor > 0:
        while cursor < len(source) and source[cursor] in " \t\r\n,":
            cursor += 1
        if cursor >= len(source) or source[cursor] == "]":
            break
        item, end = decoder.raw_decode(source, cursor)
        items.append((item, cursor, end))
        cursor = end
    return items


def _write_json_source(source_path: Path, source: str) -> None:
    json.loads(source)
    temporary_path = source_path.with_suffix(source_path.suffix + ".tmp")
    temporary_path.write_text(source, encoding="utf-8")
    temporary_path.replace(source_path)


def _task_specs_for_knowledge_source(
    source_path: Path,
) -> list[tuple[Path, dict[str, Any]]]:
    matches = []
    for task_path in sorted(
        (AUTOMATION_WORKPLACE_INTERACTIVE_DIR / "tasks").glob("*.json")
    ):
        spec = json.loads(task_path.read_text(encoding="utf-8"))
        knowledge_file = spec.get("knowledge_file")
        candidate = (
            AUTOMATION_WORKPLACE_INTERACTIVE_DIR / knowledge_file
            if knowledge_file
            else AUTOMATION_WORKPLACE_KNOWLEDGE_PATH
        )
        if candidate.resolve() == source_path.resolve():
            matches.append((task_path, spec))
    return matches


def _persist_task_document_reference(
    source_path: Path, document_id: str, *, add: bool
) -> list[str]:
    affected_task_ids = []
    for task_path, spec in _task_specs_for_knowledge_source(source_path):
        ids = list(spec.get("knowledge_document_ids", []))
        if add and document_id not in ids:
            ids.append(document_id)
        elif not add and document_id in ids:
            ids.remove(document_id)
        else:
            continue
        spec["knowledge_document_ids"] = ids
        temporary_path = task_path.with_suffix(task_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        temporary_path.replace(task_path)
        affected_task_ids.append(spec["id"])
    return affected_task_ids


def _persist_knowledge_document(task_id: str, document: KnowledgeDocument) -> Path:
    """Atomically replace one authored KB document and preserve the surrounding corpus."""
    source_path = _knowledge_source_path(task_id, document.document_id)
    with KNOWLEDGE_SOURCE_LOCK:
        source = source_path.read_text(encoding="utf-8")
        match: Optional[tuple[int, int]] = None
        matched_item: Optional[dict[str, Any]] = None
        for item, start, end in _knowledge_item_spans(source):
            if item.get("document_id") == document.document_id:
                if match is not None:
                    raise ValueError(
                        f"Duplicate {document.document_id!r} in {source_path.name}"
                    )
                match = (start, end)
                matched_item = item
        if match is None:
            raise ValueError(f"No {document.document_id!r} in {source_path.name}")
        if matched_item == document.model_dump(mode="json"):
            return source_path
        replacement = json.dumps(
            document.model_dump(mode="json"), indent=2, ensure_ascii=False
        ).replace("\n", "\n  ")
        updated_source = source[: match[0]] + replacement + source[match[1] :]
        _write_json_source(source_path, updated_source)
    return source_path


def _create_knowledge_document(
    task_id: str, document: KnowledgeDocument
) -> tuple[Path, list[str]]:
    source_path = _task_knowledge_source_path(task_id)
    with KNOWLEDGE_SOURCE_LOCK:
        source = source_path.read_text(encoding="utf-8")
        if any(
            item.get("document_id") == document.document_id
            for item, _, _ in _knowledge_item_spans(source)
        ):
            raise ValueError(f"Document {document.document_id!r} already exists")
        closing = source.rfind("]")
        if closing < 0:
            raise ValueError(f"Invalid knowledge source: {source_path.name}")
        before = source[:closing].rstrip()
        serialized = json.dumps(
            document.model_dump(mode="json"), indent=2, ensure_ascii=False
        ).replace("\n", "\n  ")
        separator = "\n" if before.endswith("[") else ",\n"
        updated_source = (
            before + separator + "  " + serialized + "\n" + source[closing:]
        )
        _write_json_source(source_path, updated_source)
        affected_task_ids = _persist_task_document_reference(
            source_path, document.document_id, add=True
        )
    return source_path, affected_task_ids


def _delete_knowledge_document(
    task_id: str, document_id: str
) -> tuple[Path, list[str]]:
    source_path = _knowledge_source_path(task_id, document_id)
    with KNOWLEDGE_SOURCE_LOCK:
        source = source_path.read_text(encoding="utf-8")
        spans = _knowledge_item_spans(source)
        target_index = next(
            (
                index
                for index, (item, _, _) in enumerate(spans)
                if item.get("document_id") == document_id
            ),
            None,
        )
        if target_index is None:
            raise ValueError(f"Unknown knowledge document: {document_id}")
        _, start, end = spans[target_index]
        if len(spans) == 1:
            opening = source.find("[")
            closing = source.rfind("]")
            updated_source = source[: opening + 1] + "\n" + source[closing:]
        elif target_index < len(spans) - 1:
            next_start = spans[target_index + 1][1]
            line_start = source.rfind("\n", 0, start) + 1
            updated_source = source[:line_start] + "  " + source[next_start:]
        else:
            previous_end = spans[target_index - 1][2]
            comma = source.find(",", previous_end, start)
            if comma < 0:
                raise ValueError(f"Cannot locate separator for {document_id!r}")
            updated_source = source[:comma] + source[end:]
        _write_json_source(source_path, updated_source)
        affected_task_ids = _persist_task_document_reference(
            source_path, document_id, add=False
        )
    return source_path, affected_task_ids


class ManualSession:
    """One human-agent conversation and its live benchmark state."""

    def __init__(self, request: CreateSessionRequest):
        _reload_tasks()
        if request.task_id not in TASKS:
            raise ValueError(f"Unknown task: {request.task_id}")
        self.id = uuid.uuid4().hex
        self.task = deepcopy(TASKS[request.task_id])
        self.user_model = request.user_model.strip()
        if not self.user_model:
            raise ValueError("User simulator model cannot be empty")
        self.user_reasoning_effort = request.user_reasoning_effort
        self.environment = get_environment()
        initialization = self.task.initial_state.model_dump(mode="json")
        self.family = initialization["initialization_data"]["agent_data"][
            "interactive_family"
        ]
        llm_args = (
            {"reasoning_effort": request.user_reasoning_effort}
            if request.user_reasoning_effort
            else {"temperature": 0.0}
        )
        self.agent = WebAgent(
            tools=self.environment.get_tools(),
            domain_policy=self.environment.get_policy(),
        )
        self.user = UserSimulator(
            instructions=str(self.task.user_scenario),
            tools=None,
            llm=self.user_model,
            llm_args=llm_args,
            global_guidelines_override=USER_SIMULATION_GUIDELINES,
        )
        self.orchestrator = Orchestrator(
            domain="automation_workplace",
            agent=self.agent,
            user=self.user,
            environment=self.environment,
            task=self.task,
            max_steps=200,
            max_errors=10,
            timeout=900,
            validate_communication=True,
        )
        self.result: Optional[SimulationRun] = None
        self.error: Optional[str] = None
        self._send_lock = threading.Lock()
        self._record_lock = threading.Lock()
        self._event_sequence = 0
        self._recorded_transcript_events = 0
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.run_directory = HUMAN_RUNS_DIR / self.id
        self.events_path = self.run_directory / "events.jsonl"
        self.artifact_path = self.run_directory / "trajectory.json"
        self.run_directory.mkdir(parents=True, exist_ok=False)
        self._done = threading.Event()
        self._record_event(
            "session_started",
            {
                "task_id": self.task.id,
                "family": self.family,
                "user_model": self.user_model,
                "user_reasoning_effort": self.user_reasoning_effort,
                "runner": "visual_workplace",
                "participant_role": "human_ai_employee",
            },
        )
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._wait_until_ready(timeout=15)
        self._record_new_transcript_events()
        self._write_artifact()

    def _run(self) -> None:
        try:
            self.result = run_simulation(
                self.orchestrator,
                evaluation_type=EvaluationType.ENV,
            )
        except Exception as exc:  # surfaced in the UI with the session intact
            self.error = f"{type(exc).__name__}: {exc}"
        finally:
            self._done.set()

    def _record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self._record_lock:
            self._event_sequence += 1
            event = {
                "schema_version": "automation-workplace-human-v1",
                "session_id": self.id,
                "sequence": self._event_sequence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "payload": payload,
            }
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def _record_new_transcript_events(self) -> None:
        transcript = self._transcript()
        for event in transcript[self._recorded_transcript_events :]:
            self._record_event("trajectory_event", event)
        self._recorded_transcript_events = len(transcript)

    def _recorded_events(self) -> list[dict[str, Any]]:
        with self._record_lock:
            if not self.events_path.exists():
                return []
            return [
                json.loads(line)
                for line in self.events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    def _write_artifact(self) -> None:
        artifact = {
            "schema_version": "automation-workplace-human-v1",
            "session_id": self.id,
            "started_at": self.started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "task_id": self.task.id,
            "family": self.family,
            "participant_role": "human_ai_employee",
            "events": self._recorded_events(),
            "snapshot": self.snapshot(),
        }
        temporary_path = self.run_directory / "trajectory.json.tmp"
        temporary_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.artifact_path)

    def record_ui_event(self, request: UIEventRequest) -> None:
        self._record_event(
            "human_ui_event",
            {"kind": request.kind, "details": request.details},
        )

    def update_knowledge_document(
        self, document_id: str, request: KnowledgeDocumentUpdate
    ) -> dict[str, Any]:
        """Update this run's KB and its authored JSON source for future runs."""
        with self._send_lock:
            db = self.environment.tools.db
            current = db.knowledge_documents.get(document_id)
            if current is None:
                raise ValueError(f"Unknown knowledge document: {document_id}")
            updated = KnowledgeDocument(
                document_id=document_id,
                **request.model_dump(mode="json"),
            )
            source_path = _persist_knowledge_document(self.task.id, updated)
            db.knowledge_documents[document_id] = updated

            # New sessions are constructed from these in-memory task templates.
            # Keep every task that shares this document synchronized with disk.
            serialized = updated.model_dump(mode="json")
            for task in TASKS.values():
                documents = task.initial_state.initialization_data.agent_data.get(
                    "knowledge_documents", {}
                )
                if document_id in documents:
                    documents[document_id] = deepcopy(serialized)

            changed_fields = [
                field
                for field in ("title", "status", "updated_at", "content", "tags")
                if getattr(current, field) != getattr(updated, field)
            ]
            self._record_event(
                "knowledge_document_edited",
                {
                    "document_id": document_id,
                    "changed_fields": changed_fields,
                    "source_file": str(source_path.relative_to(ROOT)),
                    "before": current.model_dump(mode="json"),
                    "after": serialized,
                },
            )
            self._write_artifact()
            return self.snapshot()

    def create_knowledge_document(
        self, request: KnowledgeDocumentCreate
    ) -> dict[str, Any]:
        """Create a document in this task family's authored and live KB."""
        with self._send_lock:
            db = self.environment.tools.db
            if request.document_id in db.knowledge_documents:
                raise ValueError(f"Document {request.document_id!r} already exists")
            document = KnowledgeDocument.model_validate(request.model_dump(mode="json"))
            source_path, affected_task_ids = _create_knowledge_document(
                self.task.id, document
            )
            db.knowledge_documents[document.document_id] = document
            serialized = document.model_dump(mode="json")
            for task_id in affected_task_ids:
                task = TASKS.get(task_id)
                if task is None:
                    continue
                documents = task.initial_state.initialization_data.agent_data.get(
                    "knowledge_documents", {}
                )
                documents[document.document_id] = deepcopy(serialized)
            self._record_event(
                "knowledge_document_created",
                {
                    "document_id": document.document_id,
                    "source_file": str(source_path.relative_to(ROOT)),
                    "affected_task_ids": affected_task_ids,
                    "document": serialized,
                },
            )
            self._write_artifact()
            return self.snapshot()

    def delete_knowledge_document(self, document_id: str) -> dict[str, Any]:
        """Delete a document from this task family's authored and live KB."""
        with self._send_lock:
            db = self.environment.tools.db
            current = db.knowledge_documents.get(document_id)
            if current is None:
                raise ValueError(f"Unknown knowledge document: {document_id}")
            source_path, affected_task_ids = _delete_knowledge_document(
                self.task.id, document_id
            )
            del db.knowledge_documents[document_id]
            for task_id in affected_task_ids:
                task = TASKS.get(task_id)
                if task is None:
                    continue
                documents = task.initial_state.initialization_data.agent_data.get(
                    "knowledge_documents", {}
                )
                documents.pop(document_id, None)
            self._record_event(
                "knowledge_document_deleted",
                {
                    "document_id": document_id,
                    "source_file": str(source_path.relative_to(ROOT)),
                    "affected_task_ids": affected_task_ids,
                    "document": current.model_dump(mode="json"),
                },
            )
            self._write_artifact()
            return self.snapshot()

    def _wait_until_ready(self, timeout: float = 360) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._done.is_set() or self.agent.is_waiting_for_human:
                return
            time.sleep(0.03)
        raise TimeoutError("Timed out waiting for the agent")

    def send(self, request: AgentActionRequest) -> dict[str, Any]:
        with self._send_lock:
            if self._done.is_set():
                raise RuntimeError("This run has already ended. Start a fresh run.")
            if request.kind == "message":
                content = (request.content or "").strip()
                if not content:
                    raise ValueError("Message content cannot be empty")
                action = AssistantMessage(role="assistant", content=content)
            else:
                tool_name = (request.tool_name or "").strip()
                available_tools = {tool.name for tool in self.agent.tools}
                if tool_name not in available_tools:
                    raise ValueError(f"Unknown agent tool: {tool_name}")
                action = AssistantMessage(
                    role="assistant",
                    tool_calls=[
                        ToolCall(
                            id=f"manual_{uuid.uuid4().hex}",
                            name=tool_name,
                            arguments=request.arguments,
                            requestor="assistant",
                        )
                    ],
                )
            self._record_event(
                "human_action_submitted",
                {
                    "kind": request.kind,
                    "content": request.content,
                    "tool_name": request.tool_name,
                    "arguments": request.arguments,
                    "ui_context": request.ui_context,
                },
            )
            self.agent.set_action(action)
            self._wait_until_ready()
            self._record_new_transcript_events()
            self._record_event(
                "state_checkpoint",
                {
                    "status": "complete" if self._done.is_set() else "waiting",
                    "passed_count": sum(
                        result["passed"]
                        for result in self._assertions(self._db_snapshot())
                    ),
                },
            )
            self._write_artifact()
            return self.snapshot()

    def finish(self) -> dict[str, Any]:
        with self._send_lock:
            if not self._done.is_set():
                self._record_event("human_finish_requested", {})
                self.agent.set_action(AssistantMessage(role="assistant", content=STOP))
                self._done.wait(timeout=30)
            self._record_new_transcript_events()
            snapshot = self.snapshot()
            self._record_event(
                "session_finished",
                {
                    "status": snapshot["status"],
                    "full_pass": snapshot["full_pass"],
                    "passed_count": snapshot["passed_count"],
                    "assertion_count": len(snapshot["assertions"]),
                    "reward": snapshot["reward"],
                },
            )
            self._write_artifact()
            return self.snapshot()

    def _db_snapshot(self) -> AutomationWorkplaceDB:
        return AutomationWorkplaceDB.model_validate(
            self.environment.tools.db.model_dump(mode="json")
        )

    def _assertions(self, db: AutomationWorkplaceDB) -> list[dict[str, Any]]:
        results = []
        for index, assertion in enumerate(db.interactive_assertions):
            try:
                passed = check_assertion(db, assertion)
                error = None
            except Exception as exc:
                passed = False
                error = f"{type(exc).__name__}: {exc}"
            results.append(
                {
                    "index": index + 1,
                    "passed": passed,
                    "message": assertion.get("message", f"Assertion {index + 1}"),
                    "condition": assertion,
                    "error": error,
                }
            )
        return results

    def _transcript(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        call_names: dict[str, str] = {}
        for message in list(self.orchestrator.trajectory):
            if isinstance(message, (AssistantMessage, UserMessage)):
                if message.tool_calls:
                    for call in message.tool_calls:
                        display_name = call.name
                        if call.name == "call_discoverable_tool":
                            display_name = call.arguments.get(
                                "discoverable_tool_name", call.name
                            )
                        call_names[call.id] = display_name
                        events.append(
                            {
                                "type": "tool_call",
                                "role": message.role,
                                "name": display_name,
                                "arguments": call.arguments,
                                "call_id": call.id,
                                "turn": message.turn_idx,
                            }
                        )
                elif message.content:
                    events.append(
                        {
                            "type": "message",
                            "role": message.role,
                            "content": message.content,
                            "turn": message.turn_idx,
                        }
                    )
            elif isinstance(message, ToolMessage):
                events.append(
                    {
                        "type": "tool_result",
                        "role": "tool",
                        "name": call_names.get(message.id, "tool result"),
                        "content": message.content,
                        "error": message.error,
                        "images": [f"/data/{path}" for path in message.images or []],
                        "call_id": message.id,
                        "turn": message.turn_idx,
                    }
                )
        return events

    def snapshot(self) -> dict[str, Any]:
        db = self._db_snapshot()
        assertion_results = self._assertions(db)
        world = (
            db.interactive_world.model_dump(mode="json")
            if db.interactive_family == "incident_triage"
            else db.family_world
        )
        reward = None
        reward_info = None
        if self.result is not None and self.result.reward_info is not None:
            reward = self.result.reward_info.reward
            reward_info = self.result.reward_info.model_dump(mode="json")
        return {
            "id": self.id,
            "status": (
                "error"
                if self.error
                else "complete"
                if self._done.is_set()
                else "waiting"
                if self.agent.is_waiting_for_human
                else "working"
            ),
            "error": self.error,
            "task": _task_payload(self.task),
            "user_model": self.user_model,
            "user_reasoning_effort": self.user_reasoning_effort,
            "transcript": self._transcript(),
            "assertions": assertion_results,
            "full_pass": bool(assertion_results)
            and all(item["passed"] for item in assertion_results),
            "passed_count": sum(item["passed"] for item in assertion_results),
            "world": world,
            "family": db.interactive_family,
            "knowledge_documents": [
                document.model_dump(mode="json")
                for document in db.knowledge_documents.values()
            ],
            "unlocked_tools": db.unlocked_tools,
            "unlocked_tool_schemas": {
                name: discoverable_tool_schema(db.interactive_family, name)
                for name in db.unlocked_tools
            },
            "discoverable_tool_catalog": {
                name: discoverable_tool_schema(db.interactive_family, name)
                for name in tool_schemas(db.interactive_family)
            },
            "tools": [tool.openai_schema["function"] for tool in self.agent.tools],
            "policy": self.environment.get_policy(),
            "agent_system_prompt": SYSTEM_PROMPT.format(
                domain_policy=self.environment.get_policy(),
                agent_instruction=AGENT_INSTRUCTION,
            ),
            "user_system_prompt": self.user.system_prompt,
            "reward": reward,
            "reward_info": reward_info,
            "recording": {
                "run_id": self.id,
                "event_log": str(self.events_path.relative_to(ROOT)),
                "artifact": str(self.artifact_path.relative_to(ROOT)),
            },
        }


SESSIONS: dict[str, ManualSession] = {}
SESSIONS_LOCK = threading.Lock()

app = FastAPI(title="τ Workplace Manual Test Lab")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _session(session_id: str) -> ManualSession:
    with SESSIONS_LOCK:
        session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/data/{path:path}")
def attachment(path: str) -> FileResponse:
    root = (AUTOMATION_WORKPLACE_INTERACTIVE_DIR / "attachments").resolve()
    file = (DATA_DIR / path).resolve()
    if not file.is_relative_to(root) or not file.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(file)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/tasks")
def list_tasks() -> list[dict[str, Any]]:
    _reload_tasks()
    return [_task_payload(task) for task in TASKS.values()]


@app.post("/api/sessions")
def create_session(request: CreateSessionRequest) -> dict[str, Any]:
    try:
        session = ManualSession(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with SESSIONS_LOCK:
        SESSIONS[session.id] = session
    return session.snapshot()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return _session(session_id).snapshot()


@app.post("/api/sessions/{session_id}/actions")
def send_action(session_id: str, request: AgentActionRequest) -> dict[str, Any]:
    try:
        return _session(session_id).send(request)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/ui-events")
def record_ui_event(session_id: str, request: UIEventRequest) -> dict[str, bool]:
    try:
        _session(session_id).record_ui_event(request)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True}


@app.put("/api/sessions/{session_id}/knowledge/{document_id}")
def update_knowledge_document(
    session_id: str,
    document_id: str,
    request: KnowledgeDocumentUpdate,
) -> dict[str, Any]:
    try:
        return _session(session_id).update_knowledge_document(document_id, request)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/knowledge")
def create_knowledge_document(
    session_id: str,
    request: KnowledgeDocumentCreate,
) -> dict[str, Any]:
    try:
        return _session(session_id).create_knowledge_document(request)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/api/sessions/{session_id}/knowledge/{document_id}")
def delete_knowledge_document(
    session_id: str,
    document_id: str,
) -> dict[str, Any]:
    try:
        return _session(session_id).delete_knowledge_document(document_id)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/finish")
def finish_session(session_id: str) -> dict[str, Any]:
    try:
        return _session(session_id).finish()
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/export")
def export_session(session_id: str) -> FileResponse:
    session = _session(session_id)
    session._write_artifact()
    return FileResponse(
        session.artifact_path,
        media_type="application/json",
        filename=f"{session.task.id}__{session.id}.json",
    )
