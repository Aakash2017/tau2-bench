import json

import pytest

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import access_provisioning

TASK_ID = "automation_workplace__interactive__access_provisioning_007"


def _results(writes) -> list[bool]:
    task = next(t for t in get_tasks("interactive_canonical") if t.id == TASK_ID)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    for tool_name, arguments in writes:
        environment.use_tool(
            "unlock_discoverable_tool", discoverable_tool_name=tool_name
        )
        environment.use_tool(
            "call_discoverable_tool",
            discoverable_tool_name=tool_name,
            arguments=json.dumps(arguments),
        )
    return [
        environment.run_env_assertion(a, raise_assertion_error=False)
        for a in task.evaluation_criteria.env_assertions
    ]


def _golden():
    return access_provisioning.golden_call_sequence("access_provisioning_007")


def _swap(writes, old, new):
    return [tuple(json.loads(json.dumps(s).replace(old, new))) for s in writes]


def test_golden_path_passes_every_assertion():
    assert all(_results(_golden()))


def test_old_fourteen_day_default_fails():
    assert not all(_results(_swap(_golden(), "2027-01-13", "2026-12-28")))


def test_skipping_training_assignment_fails():
    writes = [s for s in _golden() if s[0] != "lms_assign_training_v1"]
    assert not all(_results(writes))


def test_announcing_a_held_request_fails():
    extra = (
        "slack_chat_post_message",
        {"channel": "eng-access-requests", "text": "Hana Kim is waiting on training."},
    )
    assert not all(_results([*_golden(), extra]))


def test_one_combined_announcement_fails():
    posts = [s for s in _golden() if s[0] == "slack_chat_post_message"]
    rest = [s for s in _golden() if s[0] != "slack_chat_post_message"]
    combined = (
        "slack_chat_post_message",
        {
            "channel": "eng-access-requests",
            "text": " ".join(step[1]["text"] for step in posts),
        },
    )

    assert not all(_results([*rest, combined]))


def test_dropping_one_announcement_fails():
    posts = [i for i, s in enumerate(_golden()) if s[0] == "slack_chat_post_message"]
    writes = [s for i, s in enumerate(_golden()) if i != posts[0]]

    assert not all(_results(writes))


def _slack(tool, **arguments):
    task = next(t for t in get_tasks("interactive_canonical") if t.id == TASK_ID)
    world = task.initial_state.initialization_data.agent_data["family_world"]
    _, response = access_provisioning.call_tool(world, tool, json.dumps(arguments))
    return json.loads(response)


def test_channels_have_topics_and_a_busy_platform_channel():
    channels = {c["name"]: c for c in _slack("slack_list_channels_v1")["channels"]}
    assert channels["eng-platform"]["topic"]
    history = _slack("slack_get_channel_history_v1", channel="eng-platform", limit=50)
    assert len(history["messages"]) == 15 and history["has_more"]


def test_history_is_paged_newest_first_and_threads_hide_replies():
    first = _slack("slack_get_channel_history_v1", channel="eng-platform")
    assert len(first["messages"]) == 10 and first["has_more"]
    stamps = [m["sent_at"] for m in first["messages"]]
    assert stamps == sorted(stamps, reverse=True)
    assert all("thread_id" not in m for m in first["messages"])


def test_thread_replies_return_the_conversation():
    hits = _slack("slack_search_messages_v1", query="parking ACCESS-384")["messages"]
    parent = hits[0]["thread_id"]
    thread = _slack(
        "slack_get_thread_replies_v1", channel="eng-platform", thread_id=parent
    )
    assert len(thread["messages"]) == 4


def test_search_needs_a_query_and_supports_operators():
    with pytest.raises(ValueError, match="query is required"):
        _slack("slack_search_messages_v1", query="")

    hits = _slack(
        "slack_search_messages_v1", query="in:#eng-platform from:Priya after:2026-10-30"
    )
    assert hits["total"] == 2
    assert {m["channel"] for m in hits["messages"]} == {"eng-platform"}
    assert len(_slack("slack_search_messages_v1", query="CI")["messages"]) <= 10
