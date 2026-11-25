import json
import threading
from types import SimpleNamespace

from experiments.automation_workplace_ui import server
from experiments.automation_workplace_ui.server import (
    KnowledgeDocumentUpdate,
    ManualSession,
)
from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage
from tau2.domains.automation_workplace.data_model import KnowledgeDocument


def test_transcript_attributes_discoverable_result_to_inner_app_operation():
    session = ManualSession.__new__(ManualSession)
    session.orchestrator = SimpleNamespace(
        trajectory=[
            AssistantMessage(
                role="assistant",
                tool_calls=[
                    ToolCall(
                        id="manual_call_1",
                        name="call_discoverable_tool",
                        arguments={
                            "discoverable_tool_name": "rippling_search_people_v1",
                            "arguments": '{"query":"Priya"}',
                        },
                    )
                ],
            ),
            ToolMessage(
                id="manual_call_1",
                role="tool",
                content='{"count":2}',
            ),
        ]
    )

    events = session._transcript()

    assert [event["name"] for event in events] == [
        "rippling_search_people_v1",
        "rippling_search_people_v1",
    ]


def test_persist_knowledge_document_rewrites_only_selected_item(tmp_path, monkeypatch):
    source_path = tmp_path / "knowledge.json"
    untouched = """  {
    \"document_id\": \"other\",
    \"title\": \"Leave me alone\",
    \"status\": \"current\",
    \"updated_at\": \"2026-01-01\",
    \"content\": \"Original formatting stays.\",
    \"tags\": [\"one\", \"two\"]
  }"""
    source_path.write_text(
        "[\n"
        '  {"document_id": "target", "title": "Old", '
        '"status": "current", "updated_at": "2025-01-01", '
        '"content": "Old text", "tags": []},\n'
        f"{untouched}\n"
        "]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        server,
        "_knowledge_source_path",
        lambda task_id, document_id: source_path,
    )
    document = KnowledgeDocument(
        document_id="target",
        title="Clear policy",
        status="current",
        updated_at="2026-11-19",
        content="Use the concrete work requirement.",
        tags=["access", "policy"],
    )

    server._persist_knowledge_document("task", document)

    result = source_path.read_text(encoding="utf-8")
    assert untouched in result
    assert "Clear policy" in result
    assert "Old text" not in result


def test_session_kb_edit_updates_live_state_and_future_task_template(monkeypatch):
    current = KnowledgeDocument(
        document_id="policy",
        title="Old title",
        status="current",
        updated_at="2026-01-01",
        content="Old content",
        tags=["policy"],
    )
    live_db = SimpleNamespace(knowledge_documents={"policy": current})
    template_documents = {"policy": current.model_dump(mode="json")}
    template = SimpleNamespace(
        initial_state=SimpleNamespace(
            initialization_data=SimpleNamespace(
                agent_data={"knowledge_documents": template_documents}
            )
        )
    )
    session = ManualSession.__new__(ManualSession)
    session._send_lock = threading.Lock()
    session.environment = SimpleNamespace(tools=SimpleNamespace(db=live_db))
    session.task = SimpleNamespace(id="task")
    session._record_event = lambda *args: None
    session._write_artifact = lambda: None
    session.snapshot = lambda: {"title": live_db.knowledge_documents["policy"].title}
    monkeypatch.setattr(server, "TASKS", {"task": template})
    monkeypatch.setattr(
        server,
        "_persist_knowledge_document",
        lambda task_id, document: server.ROOT / "data" / "knowledge.json",
    )

    result = session.update_knowledge_document(
        "policy",
        KnowledgeDocumentUpdate(
            title="Better title",
            status="current",
            updated_at="2026-11-19",
            content="Clearer content",
            tags=["policy", "access"],
        ),
    )

    assert result == {"title": "Better title"}
    assert live_db.knowledge_documents["policy"].content == "Clearer content"
    assert template_documents["policy"]["title"] == "Better title"


def test_create_and_delete_knowledge_document_preserve_other_items(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "knowledge.json"
    source_path.write_text(
        '[\n  {"document_id":"existing","title":"Existing","status":"current",'
        '"updated_at":"2026-01-01","content":"Keep me","tags":[]}\n]\n',
        encoding="utf-8",
    )
    reference_updates = []
    monkeypatch.setattr(
        server, "_task_knowledge_source_path", lambda task_id: source_path
    )
    monkeypatch.setattr(
        server,
        "_knowledge_source_path",
        lambda task_id, document_id: source_path,
    )
    monkeypatch.setattr(
        server,
        "_persist_task_document_reference",
        lambda path, document_id, *, add: (
            reference_updates.append((document_id, add)) or ["task_a", "task_b"]
        ),
    )
    created = KnowledgeDocument(
        document_id="kb_new_policy",
        title="New policy",
        status="current",
        updated_at="2026-11-19",
        content="New content",
        tags=["policy"],
    )

    _, create_tasks = server._create_knowledge_document("task_a", created)
    after_create = json.loads(source_path.read_text(encoding="utf-8"))
    _, delete_tasks = server._delete_knowledge_document("task_a", "kb_new_policy")
    after_delete = json.loads(source_path.read_text(encoding="utf-8"))

    assert [item["document_id"] for item in after_create] == [
        "existing",
        "kb_new_policy",
    ]
    assert after_delete == [
        {
            "document_id": "existing",
            "title": "Existing",
            "status": "current",
            "updated_at": "2026-01-01",
            "content": "Keep me",
            "tags": [],
        }
    ]
    assert create_tasks == delete_tasks == ["task_a", "task_b"]
    assert reference_updates == [("kb_new_policy", True), ("kb_new_policy", False)]
