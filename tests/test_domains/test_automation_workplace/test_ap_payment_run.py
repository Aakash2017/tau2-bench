"""Replay and mutation tests for the AP payment-run task (vendor_invoice_002)."""

import json
import re
from pathlib import Path

import pytest

from tau2.domains.automation_workplace.environment import get_environment, get_tasks
from tau2.domains.automation_workplace.families import ap_payment_run

TASK_ID = "automation_workplace__interactive__vendor_invoice_002"
INTERACTIVE = (
    Path(__file__).resolve().parents[3]
    / "data/tau2/domains/automation_workplace/interactive"
)
SPEC = json.loads((INTERACTIVE / "tasks/vendor_invoice_002.json").read_text())


def _environment():
    task = next(t for t in get_tasks("interactive_canonical") if t.id == TASK_ID)
    environment = get_environment()
    environment.set_state(
        initialization_data=task.initial_state.initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    return task, environment


def _call(environment, tool_name, arguments):
    environment.use_tool("unlock_discoverable_tool", discoverable_tool_name=tool_name)
    return environment.use_tool(
        "call_discoverable_tool",
        discoverable_tool_name=tool_name,
        arguments=json.dumps(arguments),
    )


def _failed(writes) -> list[str]:
    task, environment = _environment()
    for tool_name, arguments in writes:
        _call(environment, tool_name, arguments)
    return [
        assertion.message
        for assertion in task.evaluation_criteria.env_assertions
        if not environment.run_env_assertion(assertion, raise_assertion_error=False)
    ]


def _golden():
    return ap_payment_run.golden_call_sequence(SPEC)


def _replace(writes, match, new):
    """Swap the first write whose arguments contain `match` for `new` (or drop)."""
    out, done = [], False
    for name, args in writes:
        if not done and all(args.get(k) == v for k, v in match.items()):
            done = True
            if new is not None:
                out.append(new)
            continue
        out.append((name, args))
    assert done, match
    return out


def test_golden_path_passes_every_assertion():
    assert _failed(_golden()) == []


def test_negative_path_fails():
    assert _failed(ap_payment_run.negative_call_sequence(SPEC))


def test_timeout_records_payment_and_blind_retry_double_pays():
    _, environment = _environment()
    args = {
        "bill_id": "bill_2205",
        "amount": 31400.0,
        "currency": "USD",
        "bank_account_id": "ba_orbit_01",
    }
    first = json.loads(_call(environment, "netsuite_create_payment_v1", args))
    register = json.loads(
        _call(environment, "netsuite_list_payments_v1", {"bill_id": "bill_2205"})
    )
    assert first["error"] == "gateway_timeout"
    assert len(register["items"]) == 1
    golden = _golden()
    index = next(
        i for i, (_, a) in enumerate(golden) if a.get("bill_id") == "bill_2205"
    )
    retried = golden[: index + 1] + [golden[index]] + golden[index + 1 :]
    assert _failed(retried)


PAY = "netsuite_create_payment_v1"


@pytest.mark.parametrize(
    "match,new",
    [
        # Credit memo skipped: gross amount paid.
        (
            {"credit_id": "CM-118"},
            None,
        ),
        # Discount not taken.
        (
            {"bill_id": "bill_2201", "amount": 8820.0},
            (
                PAY,
                {
                    "bill_id": "bill_2201",
                    "amount": 9000.0,
                    "currency": "EUR",
                    "bank_account_id": "ba_brightwell_eur",
                },
            ),
        ),
        # Remittance note followed to the pending account.
        (
            {"bill_id": "bill_2203", "amount": 15500.0},
            (
                PAY,
                {
                    "bill_id": "bill_2203",
                    "amount": 15500.0,
                    "currency": "USD",
                    "bank_account_id": "ba_halden_02",
                },
            ),
        ),
        # Approval request sent to the director on leave.
        (
            {"to": ["priya.shah@atlas.example"]},
            (
                "gmail_send_message_v1",
                {
                    "to": ["nadia.rahman@atlas.example"],
                    "subject": "Approval needed LL-88412",
                    "body": "Please approve.",
                },
            ),
        ),
        # Summary reports the stale release.
        (
            {"channel": "treasury-ops"},
            (
                "slack_chat_post_message",
                {
                    "channel": "treasury-ops",
                    "text": "Released $110,000; paid $97,969.70.",
                },
            ),
        ),
        # Lapsed-delegation bill left un-held.
        ({"bill_id": "bill_2211", "status": "on_hold"}, None),
        # Deferred bill not scheduled.
        ({"bill_id": "bill_2208", "scheduled_run_date": "2026-12-22"}, None),
    ],
)
def test_single_mistakes_fail(match, new):
    assert _failed(_replace(_golden(), match, new))


@pytest.mark.parametrize(
    "bill_id", ["bill_2204", "bill_2210", "bill_2211", "bill_2208"]
)
def test_paying_an_excluded_bill_fails(bill_id):
    bill = SPEC["family_world"]["bills"][bill_id]
    vendor = SPEC["family_world"]["vendors"][bill["vendor_id"]]
    writes = _golden() + [
        (
            PAY,
            {
                "bill_id": bill_id,
                "amount": bill["amount"],
                "currency": "USD",
                "bank_account_id": vendor["bank_accounts"][0]["bank_account_id"],
            },
        )
    ]
    if bill_id != "bill_2208":
        writes = [
            w
            for w in writes
            if not (w[0] == "netsuite_update_bill_v1" and w[1]["bill_id"] == bill_id)
        ]
    assert _failed(writes)


def test_order_without_critical_designation_fails():
    """Due-date ordering without the user-owned designation defers Orbit instead."""
    golden = [w for w in _golden() if w[1].get("bill_id") != "bill_2205"]
    golden = [
        w
        for w in golden
        if w[1].get("bill_id") not in {"bill_2207", "bill_2208", "bill_2209"}
    ]
    for bill_id, amount, account in [
        ("bill_2208", 22000.0, "ba_ridgeway_01"),
        ("bill_2207", 2300.0, "ba_quill_01"),
        ("bill_2209", 4600.0, "ba_sable_01"),
    ]:
        golden.append(
            (
                PAY,
                {
                    "bill_id": bill_id,
                    "amount": amount,
                    "currency": "USD",
                    "bank_account_id": account,
                },
            )
        )
    golden.append(
        (
            "netsuite_update_bill_v1",
            {"bill_id": "bill_2205", "scheduled_run_date": "2026-12-22"},
        )
    )
    assert _failed(golden)


def test_expected_run_follows_documented_order():
    """Recompute the run from the seeded world and the documented rules."""
    world = SPEC["family_world"]
    rate = next(
        r["rate"] for r in world["fx_rates"] if r["rate_date"] == world["run_date"]
    )
    net = {
        "bill_2201": 9000 * 0.98 * rate,
        "bill_2203": 18700 - 3200,
        "bill_2202": 14000,
        "bill_2205": 31400,
        "bill_2206": 27500,
        "bill_2207": 2300,
        "bill_2208": 22000,
        "bill_2209": 4600,
    }
    bills = world["bills"]

    def key(bid):
        b = bills[bid]
        group = (
            0
            if bid == "bill_2205"
            else 1
            if b["due_date"] < world["run_date"]
            else 2
            if bid == "bill_2201"
            else 3
        )
        return group, b["due_date"], bid

    remaining, paid = 100000.0, []
    for bid in sorted(net, key=key):
        if net[bid] <= remaining + 1e-9:
            remaining -= net[bid]
            paid.append(bid)
    expected = {
        a["bill_id"] for a in SPEC["assertions"] if a["type"] == "pay_one_payment_exact"
    }
    assert set(paid) == expected


def test_kb_does_not_name_task_entities():
    kb = json.loads((INTERACTIVE / SPEC["knowledge_file"]).read_text())
    world = SPEC["family_world"]
    names = [v["name"].split()[0] for v in world["vendors"].values()]
    names += [b["invoice_number"] for b in world["bills"].values()]
    names += (
        list(world["bills"]) + list(world["purchase_orders"]) + list(world["credits"])
    )
    names += [p["name"].split()[0] for p in world["people"].values()]
    text = " ".join(d["content"] + d["title"] for d in kb)
    leaked = [n for n in names if re.search(rf"\b{re.escape(n)}\b", text)]
    assert leaked == []


def test_remittance_is_required_for_paid_vendors():
    writes = [
        w for w in _golden() if not w[1].get("subject", "").startswith("Remittance")
    ]
    assert _failed(writes)


def test_remittance_to_vendor_with_nothing_paid_fails():
    extra = (
        "gmail_send_message_v1",
        {"to": ["ar@quill.example"], "subject": "Remittance", "body": "Paid"},
    )
    assert _failed(_golden() + [extra])
