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
    Task,
    UserScenario,
)
from tau2.domains.automation_workplace.data_model import AutomationWorkplaceDB
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
    """τ environment for interactive, exact-state workplace workflows."""

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
        spec.get("interactive_family", "access_provisioning"),
    )
    agent_data = {
        "interactive_task": spec["id"],
        "interactive_family": family_id,
        "knowledge_documents": selected_documents,
        "interactive_assertions": assertions,
    }
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
            nl_assertions=None,
            reward_basis=[RewardType.ENV_ASSERTION],
        ),
        user_tools=[],
    )


def _interactive_tasks() -> list[Task]:
    return [
        _build_interactive_task(load_file(path))
        for path in sorted(AUTOMATION_WORKPLACE_INTERACTIVE_TASKS_DIR.glob("*.json"))
    ]


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    tasks = _interactive_tasks()
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
