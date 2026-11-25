from copy import deepcopy
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.workplace_ops.data_model import WorkplaceOpsDB
from tau2.domains.workplace_ops.tools import WorkplaceOpsTools
from tau2.domains.workplace_ops.user_tools import WorkplaceOpsUserTools
from tau2.domains.workplace_ops.utils import (
    WORKPLACE_OPS_ADDITIONAL_TASK_SET_PATH,
    WORKPLACE_OPS_DB_PATH,
    WORKPLACE_OPS_GENERATED_HARD_TASK_SET_PATH,
    WORKPLACE_OPS_GENERATED_TASK_SET_PATH,
    WORKPLACE_OPS_POLICY_PATH,
    WORKPLACE_OPS_TASK_SET_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


def get_environment(
    db: Optional[WorkplaceOpsDB] = None,
    solo_mode: bool = False,
) -> Environment:
    """Build the workplace operations environment with shared agent/user state."""
    if solo_mode:
        raise ValueError("Solo mode not supported for workplace_ops")
    if db is None:
        db = WorkplaceOpsDB.load(WORKPLACE_OPS_DB_PATH)
    else:
        db = deepcopy(db)
    tools = WorkplaceOpsTools(db)
    user_tools = WorkplaceOpsUserTools(db)
    policy = load_file(WORKPLACE_OPS_POLICY_PATH)
    return Environment(
        domain_name="workplace_ops",
        policy=policy,
        tools=tools,
        user_tools=user_tools,
    )


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    raw_tasks = [
        *load_file(WORKPLACE_OPS_TASK_SET_PATH),
        *load_file(WORKPLACE_OPS_ADDITIONAL_TASK_SET_PATH),
        *load_file(WORKPLACE_OPS_GENERATED_TASK_SET_PATH),
        *load_file(WORKPLACE_OPS_GENERATED_HARD_TASK_SET_PATH),
    ]
    tasks = [Task.model_validate(task) for task in raw_tasks]
    if task_split_name is None:
        return tasks
    splits = get_tasks_split()
    if task_split_name not in splits:
        raise ValueError(
            f"Invalid task split name: {task_split_name}. Valid splits: {splits.keys()}"
        )
    return [task for task in tasks if task.id in splits[task_split_name]]


def get_tasks_split() -> dict[str, list[str]]:
    split_path = (
        Path(WORKPLACE_OPS_TASK_SET_PATH).parent
        / f"split_{Path(WORKPLACE_OPS_TASK_SET_PATH).stem}.json"
    )
    return load_file(split_path)
