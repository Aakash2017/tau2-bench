"""Lazy access to the pinned AutomationBench source checkout.

The prototype intentionally executes AutomationBench's own API simulators and
assertions. This avoids semantic drift while we evaluate whether the conversational
overlay is useful. AutomationBench is MIT licensed; see the adjacent checkout's
LICENSE file for the full notice and third-party API-schema scope note.
"""

from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path
from typing import Any

SOURCE_ENV_VAR = "AUTOMATIONBENCH_ROOT"


def _candidate_roots() -> list[Path]:
    configured = os.environ.get(SOURCE_ENV_VAR)
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())
    # .../mino/tau2-bench/src/tau2/domains/automation_workplace -> .../mino
    candidates.append(Path(__file__).resolve().parents[5] / "AutomationBench")
    candidates.append(Path.cwd() / "AutomationBench")
    return candidates


def ensure_source_checkout() -> Path:
    """Locate AutomationBench and make its Python package importable."""
    for root in _candidate_roots():
        if (root / "automationbench" / "schema" / "world.py").is_file():
            root_text = str(root)
            if root_text not in sys.path:
                sys.path.insert(0, root_text)
            return root
    searched = ", ".join(str(path) for path in _candidate_roots())
    raise RuntimeError(
        "AutomationBench source checkout not found. Clone zapier/AutomationBench "
        f"next to tau2-bench or set {SOURCE_ENV_VAR}. Searched: {searched}"
    )


def _install_datasets_stub() -> None:
    """Provide only the import surface task-builder modules require.

    Loading a task builder does not construct a Hugging Face Dataset. Avoiding that
    optional dependency keeps this bridge compatible with τ's Python environment.
    """
    if "datasets" in sys.modules:
        return
    try:
        importlib.import_module("datasets")
        return
    except ModuleNotFoundError:
        pass

    datasets = types.ModuleType("datasets")

    class Dataset:  # pragma: no cover - dataset construction is deliberately unused
        @classmethod
        def from_list(cls, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return values

    datasets.Dataset = Dataset
    datasets.concatenate_datasets = lambda values: sum(values, [])
    sys.modules["datasets"] = datasets


def load_source_task(module_name: str, builder_name: str) -> dict[str, Any]:
    """Load one public AutomationBench task without materializing its dataset."""
    ensure_source_checkout()
    _install_datasets_stub()
    module = importlib.import_module(f"automationbench.domains.{module_name}.tasks")
    task = getattr(module, builder_name)()
    if not isinstance(task, dict):
        raise TypeError(f"{module_name}.{builder_name} did not return a task object")
    return task


def task_contract_sha256(task: dict[str, Any]) -> str:
    """Fingerprint the exact upstream prompt, seed, tools, and assertions."""
    ensure_source_checkout()
    from automationbench.task_contract import task_contract_sha256 as source_hash

    return source_hash(
        example_id=task["example_id"],
        prompt=task["prompt"],
        info=task["info"],
    )


def world_state_from_dict(value: dict[str, Any]):
    """Validate serialized state using AutomationBench's Pydantic WorldState."""
    ensure_source_checkout()
    from automationbench.schema.world import WorldState

    return WorldState.model_validate(value)


def api_search(query: str, top_k: int) -> str:
    """Call AutomationBench's BM25 API-schema search unchanged."""
    ensure_source_checkout()
    from automationbench.tools.api.search import api_search as source_api_search

    return source_api_search(query=query, top_k=top_k)


def api_fetch(
    world,
    method: str,
    url: str,
    params: str | None,
    body: str | None,
) -> str:
    """Call AutomationBench's real-URL router unchanged."""
    ensure_source_checkout()
    from automationbench.tools.api.fetch import api_fetch as source_api_fetch

    return source_api_fetch(
        world=world,
        method=method,
        url=url,
        params=params,
        body=body,
    )


def base64_encode(text: str) -> str:
    """Use AutomationBench's Gmail-compatible base64url helper."""
    ensure_source_checkout()
    from automationbench.tools.api.encode import base64_encode as source_encode

    return source_encode(text)


def check_assertion(world, assertion: dict[str, Any]) -> bool:
    """Evaluate one original AutomationBench exact-state assertion."""
    ensure_source_checkout()
    import automationbench.rubric.assertions  # noqa: F401
    from automationbench.rubric.registry import AssertionRegistry

    return AssertionRegistry.check(world, assertion)


def compute_allowed_services(task: dict[str, Any]) -> list[str]:
    """Mirror AutomationBench's connected-account gating for API mode."""
    world = world_state_from_dict(task["info"]["initial_state"])
    model_fields = type(world).model_fields
    service_fields = sorted(
        (str(field) for field in model_fields if field != "meta"),
        key=len,
        reverse=True,
    )

    def service_for_name(name: str) -> str | None:
        for field in service_fields:
            if name == field or name.startswith(field + "_"):
                return field
        return None

    allowed = {
        key
        for key in task["info"]["initial_state"]
        if key != "meta" and key in model_fields
    }
    for assertion in task["info"].get("assertions", []):
        service = service_for_name(str(assertion.get("type", "")))
        if service:
            allowed.add(service)
    for tool_name in task["info"].get("zapier_tools", []):
        service = service_for_name(tool_name)
        if service:
            allowed.add(service)
    return sorted(allowed)
