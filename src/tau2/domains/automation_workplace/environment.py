from copy import deepcopy
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import (
    Description,
    EnvAssertion,
    EvaluationCriteria,
    InitializationData,
    InitialState,
    RewardType,
    StructuredUserInstructions,
    Task,
    UserScenario,
)
from tau2.domains.automation_workplace.automationbench_source import (
    compute_allowed_services,
    load_source_task,
    task_contract_sha256,
    world_state_from_dict,
)
from tau2.domains.automation_workplace.data_model import AutomationWorkplaceDB
from tau2.domains.automation_workplace.task_catalog import TASK_OVERLAYS, TaskOverlay
from tau2.domains.automation_workplace.tools import AutomationWorkplaceTools
from tau2.domains.automation_workplace.utils import (
    AUTOMATION_WORKPLACE_INTERACTIVE_DIR,
    AUTOMATION_WORKPLACE_INTERACTIVE_TASKS_DIR,
    AUTOMATION_WORKPLACE_KNOWLEDGE_PATH,
    AUTOMATION_WORKPLACE_POLICY_PATH,
    AUTOMATION_WORKPLACE_SPLIT_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


class AutomationWorkplaceEnvironment(Environment):
    """Environment whose replay is governed by source final-state assertions.

    AutomationBench intentionally generates realistic timestamps and opaque IDs at
    runtime. Replaying the same API call can therefore return cosmetically different
    JSON even when it produces an assertion-equivalent final state. τ's standard
    strict response comparison is inappropriate here; every call is still replayed,
    while the original positive and negative assertions remain the reward authority.
    """

    def set_state(
        self,
        initialization_data,
        initialization_actions,
        message_history,
        strict: bool = True,
    ):
        del strict
        return super().set_state(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=message_history,
            strict=False,
        )


def get_environment(
    db: Optional[AutomationWorkplaceDB] = None,
    solo_mode: bool = False,
) -> Environment:
    """Build the conversational AutomationBench adapter environment."""
    if solo_mode:
        raise ValueError("Solo mode not supported for automation_workplace")
    if db is None:
        db = AutomationWorkplaceDB()
    else:
        db = deepcopy(db)
    return AutomationWorkplaceEnvironment(
        domain_name="automation_workplace",
        policy=load_file(AUTOMATION_WORKPLACE_POLICY_PATH),
        tools=AutomationWorkplaceTools(db),
    )


def _task_id(source_name: str) -> str:
    return "automation_workplace__" + source_name.replace(".", "__")


def _build_user_scenario(source_task: dict, overlay: TaskOverlay) -> UserScenario:
    original_request = source_task["prompt"][1]["content"]
    return UserScenario(
        persona=overlay.persona,
        instructions=StructuredUserInstructions(
            domain="automation_workplace",
            reason_for_call=f"Open by saying only: '{overlay.opening}'",
            known_info=(
                "You ultimately want the outcome described by this source request, but "
                "you must not recite it up front:\n\n"
                f"{original_request}"
            ),
            unknown_info=(
                "You do not know values held in the connected workplace apps, including "
                "record IDs, current statuses, authoritative policy contents, calculated "
                "amounts, eligible records, recipients, or whether writes succeeded."
            ),
            task_instructions=(
                f"Open with exactly the reason-for-call sentence. {overlay.progressive_instruction} "
                "Do not quote the hidden source request or volunteer its full checklist. "
                "At any completion claim, compare the report against every requirement "
                "in the hidden source request. If any required check, write, exclusion, "
                "calculation, or notification is missing or wrong, identify that specific "
                "gap and require the assistant to repair it. Only after the complete "
                "requested final state is confirmed may you output ###STOP### exactly."
            ),
        ),
    )


def _build_task(overlay: TaskOverlay) -> Task:
    source = load_source_task(overlay.module, overlay.builder)
    actual_contract = task_contract_sha256(source)
    if actual_contract != overlay.contract_sha256:
        raise RuntimeError(
            f"AutomationBench task contract drifted for {source['task']}: "
            f"expected {overlay.contract_sha256}, got {actual_contract}. Review the "
            "upstream prompt, seed, tools, and assertions before updating the pin."
        )
    initial_world = deepcopy(source["info"]["initial_state"])
    meta = initial_world.setdefault("meta", {})
    meta["allowed_services"] = compute_allowed_services(source)
    assertions = deepcopy(source["info"]["assertions"])
    env_assertions = [
        EnvAssertion(
            env_type="assistant",
            func_name="assert_source_assertion",
            arguments={"assertion_index": index},
            assert_value=True,
            message=(
                f"AutomationBench assertion {index + 1}/{len(assertions)} failed: "
                f"{assertion['type']}"
            ),
        )
        for index, assertion in enumerate(assertions)
    ]
    source_name = source["task"]
    return Task(
        id=_task_id(source_name),
        description=Description(
            purpose=(
                "Apply a τ-style simulated user interaction layer to an unchanged public "
                f"AutomationBench task ({source_name})."
            ),
            relevant_policies=(
                "The user owns preferences, scope, and authorization; connected apps own "
                "recorded facts and authoritative policies. Final reward is the conjunction "
                "of every original positive and negative AutomationBench assertion."
            ),
            notes=(
                f"Interaction archetype: {overlay.interaction_archetype}. Source example "
                f"ID: {source['example_id']}. No communication gate or action-sequence gate."
            ),
        ),
        user_scenario=_build_user_scenario(source, overlay),
        ticket=source["prompt"][1]["content"],
        initial_state=InitialState(
            initialization_data=InitializationData(
                agent_data={
                    "source_task": source_name,
                    "world": initial_world,
                    "assertions": assertions,
                }
            )
        ),
        evaluation_criteria=EvaluationCriteria(
            actions=None,
            env_assertions=env_assertions,
            communicate_info=None,
            nl_assertions=None,
            reward_basis=[RewardType.ENV_ASSERTION],
        ),
        user_tools=[],
    )


def _build_interactive_task(spec: dict) -> Task:
    """Build one locally authored hybrid task from reviewable data files."""
    documents: dict[str, dict] = {
        document["document_id"]: document
        for document in load_file(AUTOMATION_WORKPLACE_KNOWLEDGE_PATH)
    }
    if knowledge_file := spec.get("knowledge_file"):
        family_documents = load_file(
            AUTOMATION_WORKPLACE_INTERACTIVE_DIR / knowledge_file
        )
        for document in family_documents:
            document_id = document["document_id"]
            if document_id in documents:
                raise ValueError(
                    f"Duplicate knowledge document ID {document_id!r} in "
                    f"{knowledge_file!r}"
                )
            documents[document_id] = document
    selected_documents = {
        document_id: deepcopy(documents[document_id])
        for document_id in spec["knowledge_document_ids"]
    }
    assertions = deepcopy(spec["assertions"])
    nl_assertions = list(spec.get("nl_assertions", []))
    env_assertions = [
        EnvAssertion(
            env_type="assistant",
            func_name="assert_interactive_assertion",
            arguments={"assertion_index": index},
            assert_value=True,
            message=assertion["message"],
        )
        for index, assertion in enumerate(assertions)
    ]
    family_id = spec.get(
        "family",
        spec.get("interactive_family", "incident_triage"),
    )
    agent_data = {
        "interactive_task": spec["id"],
        "interactive_family": family_id,
        "knowledge_documents": selected_documents,
        "interactive_assertions": assertions,
    }
    if generic_world := spec.get("generic_world"):
        # Normalize once so read-only api_fetch calls leave the dump unchanged.
        seeded = world_state_from_dict(deepcopy(generic_world)).model_dump(mode="json")
        agent_data["world"] = seeded
        agent_data["initial_world"] = deepcopy(seeded)
    if family_id == "incident_triage":
        agent_data["interactive_world"] = deepcopy(spec["interactive_world"])
    else:
        family_world = spec.get("family_world", spec.get("interactive_world"))
        if family_world is None:
            raise ValueError(f"Task {spec['id']!r} has no family world")
        agent_data["family_world"] = deepcopy(family_world)

    return Task(
        id=spec["id"],
        description=Description.model_validate(spec["description"]),
        user_scenario=UserScenario.model_validate(spec["user_scenario"]),
        ticket=spec["ticket"],
        initial_state=InitialState(
            initialization_data=InitializationData(agent_data=agent_data)
        ),
        evaluation_criteria=EvaluationCriteria(
            actions=None,
            env_assertions=env_assertions,
            communicate_info=None,
            # Small LLM-judged checks on what the agent tells the user; app state
            # stays graded by the deterministic env assertions above.
            nl_assertions=nl_assertions or None,
            reward_basis=[RewardType.ENV_ASSERTION]
            + ([RewardType.NL_ASSERTION] if nl_assertions else []),
        ),
        user_tools=[],
    )


def _interactive_tasks() -> list[Task]:
    return [
        _build_interactive_task(load_file(path))
        for path in sorted(AUTOMATION_WORKPLACE_INTERACTIVE_TASKS_DIR.glob("*.json"))
    ]


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    tasks = [_build_task(overlay) for overlay in TASK_OVERLAYS] + _interactive_tasks()
    if task_split_name is None:
        return tasks
    splits = get_tasks_split()
    if task_split_name not in splits:
        raise ValueError(
            f"Invalid task split name: {task_split_name}. Valid splits: {splits.keys()}"
        )
    selected = set(splits[task_split_name])
    return [task for task in tasks if task.id in selected]


def get_tasks_split() -> dict[str, list[str]]:
    return load_file(Path(AUTOMATION_WORKPLACE_SPLIT_PATH))
