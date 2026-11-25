"""Keep the access KB fair: every graded outcome is justified, and nothing leaks.

The evidence ledger maps each assertion of each access-provisioning task to the KB
passages and seeded records that make the expected end state derivable. Editing
the KB so a justification disappears, or adding an assertion without evidence,
fails here instead of surfacing later as an unexplained model failure.
"""

import json
import re
from pathlib import Path

import pytest

INTERACTIVE = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive"
)


def _kb(file: str) -> dict:
    return {
        item["document_id"]: item
        for item in json.loads((INTERACTIVE / file).read_text())
    }


LEDGER = {
    **json.loads((INTERACTIVE / "evidence/access_provisioning.json").read_text()),
    **json.loads((INTERACTIVE / "evidence/access_precedent_extra.json").read_text()),
}
TASKS = {
    spec["id"]: spec
    for spec in (
        json.loads(path.read_text())
        for path in sorted((INTERACTIVE / "tasks").glob("access_provisioning_*.json"))
    )
}


def _squash(text: str) -> str:
    return " ".join(text.split())


def _resolve(spec: dict, path: str):
    node = spec
    for part in path.split("."):
        if isinstance(node, list):
            matches = [
                item
                for item in node
                if isinstance(item, dict)
                and part in (item.get("id"), item.get("title"))
            ]
            if len(matches) != 1:
                raise KeyError(path)
            node = matches[0]
        else:
            node = node[part]
    return node


def test_every_access_task_has_a_ledger():
    assert set(LEDGER) == set(TASKS)


@pytest.mark.parametrize("task_id", sorted(TASKS))
def test_every_assertion_is_justified(task_id):
    spec = TASKS[task_id]
    entries = LEDGER[task_id]

    kb = _kb(spec["knowledge_file"])
    assert len(entries) == len(spec["assertions"])
    for index, entry in enumerate(entries):
        # Tasks without a written workflow justify outcomes from seeded records.
        assert entry["kb"] or entry["records"], f"assertion {index} has no evidence"
        for document_id, quote in entry["kb"]:
            assert document_id in spec["knowledge_document_ids"], (index, document_id)
            assert _squash(quote) in _squash(kb[document_id]["content"]), (
                index,
                document_id,
                quote,
            )
        for path in entry["records"]:
            _resolve(spec, path)


def _task_entities() -> set[str]:
    entities: set[str] = set()
    for spec in TASKS.values():
        world = spec["family_world"]
        for worker in world["workers"].values():
            entities.add(worker["legal_name"])
            entities.update(
                part for part in worker["legal_name"].split() if len(part) >= 4
            )
            entities.add(worker["primary_email"])
        entities.update(world["identities"])
        entities.update(world["access_requests"])
        texts = [message["text"] for message in world["slack_messages"].values()]
        texts += [
            message["body_plain"]
            for message in spec.get("generic_world", {})
            .get("gmail", {})
            .get("messages", [])
        ]
        for text in texts:
            entities.update(re.findall(r"\bINC-\d+\b", text))
    return entities


def test_kb_names_no_task_people_requests_or_incidents():
    corpus = "\n".join(
        item["content"] + " " + item["title"]
        for file in {spec["knowledge_file"] for spec in TASKS.values()}
        for item in _kb(file).values()
    )
    leaks = sorted(
        entity
        for entity in _task_entities()
        if re.search(rf"(?<![\w-]){re.escape(entity)}(?![\w-])", corpus, re.IGNORECASE)
    )

    assert leaks == []
