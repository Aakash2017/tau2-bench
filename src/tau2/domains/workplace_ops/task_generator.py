"""Deterministic candidate-task generator for the workplace operations domain.

The generator follows the telecom-domain pattern: people author workflow families,
scenario banks, and compatibility rules; code expands them into frozen, replayable
tasks.  It deliberately makes no LLM calls.  The generated collection is a review
candidate, not a claim that every composition is benchmark-ready.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from tau2.data_model.tasks import Task
from tau2.domains.workplace_ops.data_model import renewal_follow_up_record_id
from tau2.domains.workplace_ops.utils import WORKPLACE_OPS_DATA_DIR

GENERATOR_VERSION = "0.5.0"
TASKS_PER_FAMILY = 10
HARD_EVIDENCE_RECORDS_PER_TASK = 60


def _slug(value: str) -> str:
    return "_".join(
        "".join(
            character.lower() if character.isalnum() else " " for character in value
        ).split()
    )


def _record(
    record_id: str,
    system: str,
    record_type: str,
    title: str,
    status: str,
    *,
    owner: str | None = None,
    fields: dict[str, Any] | None = None,
    updated_at: str = "2026-11-08T08:30:00-08:00",
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "record_id": record_id,
        "system": system,
        "record_type": record_type,
        "title": title,
        "status": status,
        "updated_at": updated_at,
        "fields": fields or {},
    }
    if owner is not None:
        value["owner"] = owner
    return value


def _add_hard_evidence_corpus(
    records: dict[str, dict[str, Any]],
    *,
    family: str,
    entity: str,
    systems: tuple[str, ...],
    task_index: int,
) -> None:
    """Add deterministic, query-colliding evidence without answer-key labels.

    Each artifact mirrors the system, type, title vocabulary, and some values of a
    real task record.  Its non-governing context must instead be inferred from
    ordinary workplace metadata: tenant, effective period, legal entity, approval
    state, or environment.  This is closer to the evidence-selection problem in
    Hyper-tau than filler that literally says it is non-authoritative.
    """
    base_records = list(records.values())
    contexts = (
        {
            "title_suffix": "training tenant",
            "status": "reference",
            "metadata": {
                "workspace": "atlas-enablement",
                "environment": "simulation",
                "audience": "new-hire training",
            },
        },
        {
            "title_suffix": "Q2 audit snapshot",
            "status": "archived",
            "metadata": {
                "reporting_period": "2026-Q2",
                "as_of": "2026-06-30",
                "retention_reason": "quarterly audit",
            },
        },
        {
            "title_suffix": "acquisition workspace",
            "status": "reference",
            "metadata": {
                "legal_entity": "Atlas Acquisition Sandbox LLC",
                "business_unit": "corporate-development",
                "workspace": "diligence-room-7",
            },
        },
        {
            "title_suffix": "FY27 change draft",
            "status": "draft",
            "metadata": {
                "approval_state": "circulating-for-review",
                "effective_on": "2027-01-15",
                "change_window": "FY27 planning",
            },
        },
        {
            "title_suffix": "migration rehearsal",
            "status": "test",
            "metadata": {
                "environment": "pre-production",
                "migration_wave": "rehearsal-3",
                "tenant": "atlas-shadow",
            },
        },
    )
    supplemental_systems = ("Slack", "Email", "Knowledge", "Projects", "Analytics")
    for ordinal in range(1, HARD_EVIDENCE_RECORDS_PER_TASK + 1):
        source = base_records[(ordinal + task_index - 2) % len(base_records)]
        context = contexts[(ordinal + task_index - 2) % len(contexts)]
        # Preserve visible business values while removing relationship keys that
        # could make a historical copy participate in live workflow joins.
        captured_values = {
            key: value
            for key, value in source["fields"].items()
            if not key.endswith("_id") and not key.endswith("_ids")
        }
        record_id = f"evidence_{family}_{task_index:03d}_{ordinal:03d}"
        source_system = source["system"]
        system = (
            source_system
            if ordinal % 4
            else supplemental_systems[
                (ordinal + task_index) % len(supplemental_systems)
            ]
        )
        records[record_id] = _record(
            record_id,
            system,
            source["record_type"],
            f"{source['title']} — {context['title_suffix']}",
            context["status"],
            owner=source.get("owner"),
            fields={
                "subject": source["title"],
                "entity": entity,
                "captured_values": captured_values,
                **context["metadata"],
                "artifact_ref": f"{family}-{task_index:03d}-{ordinal:03d}",
            },
            updated_at=(
                f"2026-{1 + (ordinal % 9):02d}-{1 + (ordinal % 27):02d}T10:15:00-08:00"
            ),
        )


def _action(
    prefix: str,
    index: int,
    name: str,
    arguments: dict[str, Any],
    *,
    requestor: str = "assistant",
) -> dict[str, Any]:
    return {
        "action_id": f"{prefix}_{index}",
        "requestor": requestor,
        "name": name,
        "arguments": arguments,
    }


def _assertion(
    env_type: str,
    func_name: str,
    arguments: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    return {
        "env_type": env_type,
        "func_name": func_name,
        "arguments": arguments,
        "assert_value": True,
        "message": message,
    }


def _task(
    *,
    task_id: str,
    family: str,
    primary_difficulty: str,
    purpose: str,
    relevant_policies: str,
    persona: str,
    opening: str,
    known_info: str,
    unknown_info: str,
    user_instructions: str,
    ticket: str,
    records: dict[str, dict[str, Any]],
    approval_title: str,
    proposal_type: str,
    required_details: dict[str, Any],
    actions: list[dict[str, Any]],
    assertions: list[dict[str, Any]],
    communicate_info: list[str],
) -> Task:
    raw = {
        "id": task_id,
        "description": {
            "purpose": purpose,
            "relevant_policies": relevant_policies,
            "notes": (
                f"Generated deterministically by workplace_ops generator "
                f"{GENERATOR_VERSION}; family={family}; "
                f"primary_difficulty={primary_difficulty}. Candidate for human review."
            ),
        },
        "user_scenario": {
            "persona": persona,
            "instructions": {
                "domain": "workplace_ops",
                "reason_for_call": f"Open by saying only: {opening!r}",
                "known_info": known_info,
                "unknown_info": unknown_info,
                "approval_protocol": (
                    "When the assistant asks for approval, your next turn MUST be "
                    "get_pending_action_proposals. Inspect the exact proposal, then "
                    "call approve_action_proposal if it satisfies your constraints. "
                    "Never approve or authorize in prose before that tool succeeds."
                ),
                "task_instructions": user_instructions,
            },
        },
        "ticket": ticket,
        "initial_state": {
            "initialization_data": {
                "agent_data": {
                    "workplace_records": records,
                    "action_approval_rules": {
                        approval_title: {
                            "title": approval_title,
                            "proposal_type": proposal_type,
                            "required_details": required_details,
                        }
                    },
                }
            }
        },
        "evaluation_criteria": {
            "actions": actions,
            "env_assertions": assertions,
            "communicate_info": communicate_info,
            "nl_assertions": None,
            "reward_basis": ["DB", "COMMUNICATE"],
        },
        "user_tools": [
            "get_pending_action_proposals",
            "approve_action_proposal",
        ],
    }
    return Task.model_validate(raw)


@dataclass(frozen=True)
class IncidentCase:
    service: str
    requested_severity: str
    correct_severity: str
    scope: str
    unaffected: tuple[str, str]
    responder: str
    rca_owner: str
    rca_due: str
    requester: str


INCIDENT_CASES = [
    IncidentCase(
        "Card authorization",
        "SEV-1",
        "SEV-2",
        "EU web checkout",
        ("mobile", "API"),
        "nina@atlas.example",
        "nina@atlas.example",
        "2026-11-11",
        "Elena",
    ),
    IncidentCase(
        "Invoice export",
        "SEV-1",
        "SEV-2",
        "US enterprise exports",
        ("dashboard", "API"),
        "omar@atlas.example",
        "omar@atlas.example",
        "2026-11-12",
        "Priya",
    ),
    IncidentCase(
        "Identity login",
        "SEV-2",
        "SEV-1",
        "global web and mobile login",
        ("password reset", "admin console"),
        "mei@atlas.example",
        "mei@atlas.example",
        "2026-11-13",
        "Jon",
    ),
    IncidentCase(
        "Document upload",
        "SEV-1",
        "SEV-2",
        "APAC large-file uploads",
        ("small files", "downloads"),
        "sarah@atlas.example",
        "sarah@atlas.example",
        "2026-11-11",
        "Amina",
    ),
    IncidentCase(
        "Webhook delivery",
        "SEV-2",
        "SEV-1",
        "global outbound webhooks",
        ("inbound API", "dashboard"),
        "theo@atlas.example",
        "theo@atlas.example",
        "2026-11-14",
        "Marta",
    ),
    IncidentCase(
        "Search indexing",
        "SEV-1",
        "SEV-2",
        "EU indexing delay",
        ("search reads", "US indexing"),
        "li@atlas.example",
        "li@atlas.example",
        "2026-11-12",
        "Dev",
    ),
    IncidentCase(
        "Payroll sync",
        "SEV-1",
        "SEV-2",
        "Canadian payroll imports",
        ("US payroll", "manual entry"),
        "rosa@atlas.example",
        "rosa@atlas.example",
        "2026-11-15",
        "Helen",
    ),
    IncidentCase(
        "Message delivery",
        "SEV-2",
        "SEV-1",
        "global email and SMS delivery",
        ("in-app inbox", "message history"),
        "camille@atlas.example",
        "camille@atlas.example",
        "2026-11-11",
        "Mateo",
    ),
    IncidentCase(
        "Analytics refresh",
        "SEV-1",
        "SEV-2",
        "hourly revenue dashboards",
        ("raw exports", "real-time metrics"),
        "avery@atlas.example",
        "avery@atlas.example",
        "2026-11-13",
        "Sofia",
    ),
    IncidentCase(
        "Mobile push",
        "SEV-1",
        "SEV-2",
        "Android push in Europe",
        ("iOS push", "email"),
        "jordan@atlas.example",
        "jordan@atlas.example",
        "2026-11-12",
        "Marcus",
    ),
]


def _incident_task(
    index: int, case: IncidentCase, *, hard_evidence: bool = False
) -> Task:
    slug = _slug(case.service)
    task_id = (
        f"incident_triage_hard_{index:03d}"
        if hard_evidence
        else f"incident_triage_gen_{index:03d}"
    )
    prefix = f"incident_gen_{index}"
    incident_id = f"linear_{slug}_incident"
    impact_id = f"signal_{slug}_impact"
    second_id = f"signal_{slug}_second"
    stale_id = f"signal_{slug}_stale"
    policy_id = f"incident_policy_current_{index}"
    schedule_id = f"oncall_{slug}_current"
    stale_schedule_id = f"oncall_{slug}_stale"
    broad = case.correct_severity == "SEV-1"
    records = {
        stale_id: _record(
            stale_id,
            "Datadog",
            "service_signal",
            f"{case.service} aggregate",
            "stale",
            fields={
                "scope": "global",
                "suggested_severity": case.requested_severity,
                "freshness": "stale cache",
            },
            updated_at="2026-11-08T08:05:00-08:00",
        ),
        impact_id: _record(
            impact_id,
            "Datadog",
            "service_signal",
            f"{case.service} current impact",
            "current",
            fields={
                "scope": case.scope,
                "health": "unavailable" if broad else "degraded",
                "customer_impact": "confirmed",
            },
            updated_at="2026-11-08T08:58:00-08:00",
        ),
        second_id: _record(
            second_id,
            "Datadog",
            "service_signal",
            f"{case.service} corroborating signal",
            "current",
            fields={
                "scope": case.scope if broad else case.unaffected[0],
                "health": "unavailable" if broad else "healthy",
            },
            updated_at="2026-11-08T08:59:00-08:00",
        ),
        f"signal_{slug}_healthy": _record(
            f"signal_{slug}_healthy",
            "Datadog",
            "service_signal",
            f"{case.unaffected[0] if broad else case.unaffected[1]} health",
            "current",
            fields={
                "scope": case.unaffected[0] if broad else case.unaffected[1],
                "health": "healthy",
            },
            updated_at="2026-11-08T08:59:30-08:00",
        ),
        policy_id: _record(
            policy_id,
            "Knowledge",
            "policy",
            "Incident severity policy",
            "current",
            fields={
                "sev_1": "broad or multi-channel unavailability",
                "sev_2": "regional or channel-specific degradation",
                "rca_owner": case.rca_owner,
                "rca_due_date": case.rca_due,
            },
        ),
        f"incident_policy_old_{index}": _record(
            f"incident_policy_old_{index}",
            "Knowledge",
            "policy",
            "Incident severity policy",
            "superseded",
            fields={"rule": f"default {case.requested_severity} from aggregate alarms"},
            updated_at="2026-03-01T08:00:00-08:00",
        ),
        schedule_id: _record(
            schedule_id,
            "PagerDuty",
            "on_call_schedule",
            f"{case.service} on-call",
            "current",
            fields={"current_on_call": case.responder},
        ),
        stale_schedule_id: _record(
            stale_schedule_id,
            "PagerDuty",
            "on_call_schedule",
            f"{case.service} on-call",
            "superseded",
            fields={"current_on_call": "former.responder@atlas.example"},
            updated_at="2026-11-07T08:00:00-08:00",
        ),
        incident_id: _record(
            incident_id,
            "Linear",
            "incident",
            f"{case.service} incident",
            "new",
            owner="triage@atlas.example",
            fields={"severity": case.requested_severity, "scope": "unverified"},
        ),
    }
    evidence_ids = [impact_id, second_id, f"signal_{slug}_healthy"]
    if broad:
        second_healthy_id = f"signal_{slug}_healthy_second"
        records[second_healthy_id] = _record(
            second_healthy_id,
            "Datadog",
            "service_signal",
            f"{case.unaffected[1]} health",
            "current",
            fields={"scope": case.unaffected[1], "health": "healthy"},
            updated_at="2026-11-08T08:59:40-08:00",
        )
        evidence_ids.append(second_healthy_id)
    evidence_ids.append(policy_id)
    if hard_evidence:
        _add_hard_evidence_corpus(
            records,
            family="incident",
            entity=case.service,
            systems=("Datadog", "Knowledge", "PagerDuty", "Linear"),
            task_index=index,
        )
    proposal_title = f"{case.service} incident response"
    generated_id = f"generated_record_{len(records) + 1}"
    related = [incident_id, generated_id]
    actions = [
        _action(
            prefix,
            0,
            "search_workplace_records",
            {"query": case.service, "system": "Datadog"},
        ),
        _action(
            prefix,
            1,
            "search_workplace_records",
            {"query": "Incident severity policy", "system": "Knowledge"},
        ),
        _action(
            prefix,
            2,
            "search_workplace_records",
            {"query": case.service, "system": "PagerDuty"},
        ),
        _action(
            prefix,
            3,
            "search_workplace_records",
            {"query": case.service, "system": "Linear"},
        ),
        _action(
            prefix,
            4,
            "propose_incident_response",
            {
                "severity": case.correct_severity,
                "scope": case.scope,
                "global_outage": broad,
                "evidence_record_ids": evidence_ids,
                "unaffected_channels": list(case.unaffected),
            },
        ),
        _action(prefix, 5, "get_pending_action_proposals", {}, requestor="user"),
        _action(
            prefix,
            6,
            "approve_action_proposal",
            {"proposal_id": "action_proposal_1"},
            requestor="user",
        ),
        _action(
            prefix,
            7,
            "apply_incident_plan",
            {
                "proposal_id": "action_proposal_1",
                "incident_record_id": incident_id,
            },
        ),
        _action(
            prefix,
            8,
            "page_current_on_call",
            {"schedule_record_id": schedule_id, "incident_record_id": incident_id},
        ),
        _action(
            prefix,
            9,
            "create_incident_rca",
            {
                "proposal_id": "action_proposal_1",
                "incident_record_id": incident_id,
            },
        ),
        _action(
            prefix,
            10,
            "send_approved_external_messages",
            {"proposal_id": "action_proposal_1"},
        ),
        _action(
            prefix,
            11,
            "post_approved_workflow_update",
            {"proposal_id": "action_proposal_1"},
        ),
    ]
    opening = f"{case.service} looks serious. Declare a {case.requested_severity}, page the team, update customers, and start the RCA."
    return _task(
        task_id=task_id,
        family="incident",
        primary_difficulty=(
            "hard_evidence_and_user_correction"
            if hard_evidence
            else "user_correction"
            if case.requested_severity != case.correct_severity
            else "evidence_reconciliation"
        ),
        purpose="Correct an initially wrong incident diagnosis using current evidence, then complete the response across monitoring, incident tracking, paging, status communication, and RCA work.",
        relevant_policies="Current service evidence controls severity and scope; reuse the existing incident, page the current responder, and communicate only verified impact.",
        persona=f"You are {case.requester}, an operations leader who is decisive under pressure and will change course when shown concrete current evidence.",
        opening=opening,
        known_info=(
            f"You initially believe the incident is {case.requested_severity} "
            "because you saw an aggregate dashboard and remember older incident "
            "guidance. You do not know whether either source still governs."
            if hard_evidence
            else f"You initially believe the incident is {case.requested_severity}. "
            f"If the agent establishes the current scope and policy, accept "
            f"{case.correct_severity} and authorize an accurately scoped response."
        ),
        unknown_info="You do not know which signal, policy, incident, or on-call record is current, and you do not know any record IDs.",
        user_instructions=(
            "Open with exactly the reason-for-call sentence. If the assistant "
            "contradicts your requested severity, challenge it once and ask which "
            "current signals, unaffected channels, and governing policy support "
            "the correction. Do not disclose the correct severity or scope yourself, "
            "and do not concede to a bare assertion or a discussion-only artifact. "
            "After the assistant provides a coherent evidence-backed correction, "
            "inspect the exact proposal with get_pending_action_proposals and approve "
            "the proposal you have been persuaded is correct. Explicitly authorize "
            "execution after approval. Do not stop until the current responder, "
            "existing incident, customer update, RCA owner and due date, and internal "
            "update are confirmed. Then output ###STOP###."
            if hard_evidence
            else f"Open with exactly the reason-for-call sentence. Require evidence "
            f"before accepting a severity correction. Do not provide system facts. "
            f"After the agent explains why {case.correct_severity} applies to "
            f"{case.scope}, inspect the exact proposal with "
            "get_pending_action_proposals and approve it only if severity and scope "
            "match. Explicitly authorize execution after approval. Do not stop until "
            "the current responder, existing incident, customer update, RCA owner and "
            "due date, and internal update are confirmed. Then output ###STOP###."
        ),
        ticket=f"Triage the {case.service} incident. Reconcile current and stale evidence, correct the requester's severity if needed, obtain approval for the scoped communication, update the existing incident, page the current responder, create the RCA, publish the approved update, and notify the incident channel.",
        records=records,
        approval_title=proposal_title,
        proposal_type="incident_response",
        required_details=(
            {}
            if hard_evidence
            else {
                "severity": case.correct_severity,
                "scope": case.scope,
                "global_outage": broad,
            }
        ),
        actions=actions,
        assertions=[
            _assertion(
                "user",
                "assert_action_proposal_approved",
                {"proposal_id": "action_proposal_1"},
                "The requester must approve the exact incident plan.",
            ),
            _assertion(
                "assistant",
                "assert_workplace_record",
                {
                    "record_id": incident_id,
                    "system": "Linear",
                    "status": "investigating",
                    "owner": case.responder,
                    "required_fields": {
                        "severity": case.correct_severity,
                        "scope": case.scope,
                    },
                },
                "The existing incident must carry the corrected severity and scope.",
            ),
            _assertion(
                "assistant",
                "assert_on_call_page",
                {"incident_record_id": incident_id, "target": case.responder},
                "The current on-call responder must be paged once.",
            ),
            _assertion(
                "assistant",
                "assert_external_message_recipients",
                {
                    "proposal_id": "action_proposal_1",
                    "recipients": ["public-status-page"],
                },
                "Only the approved status update is published.",
            ),
            _assertion(
                "assistant",
                "assert_internal_update",
                {
                    "channel": f"inc-{slug.replace('_', '-')}",
                    "related_record_ids": related,
                },
                "The incident channel must link the incident and RCA.",
            ),
        ],
        communicate_info=[
            f"Current evidence supports {case.correct_severity} for {case.scope}, not the initially requested {case.requested_severity}.",
            f"{case.responder} was paged, the existing incident remains investigating, the scoped customer update was published, and the RCA is due {case.rca_due}.",
        ],
    )


@dataclass(frozen=True)
class InvoiceCase:
    vendor: str
    owner: str
    po_amount: int
    overage: int
    bank_mismatch: bool
    requester: str


INVOICE_CASES = [
    InvoiceCase("Apex Cloud", "lena@atlas.example", 36000, 2400, True, "Lena"),
    InvoiceCase("Beacon Data", "omar@atlas.example", 72000, 0, True, "Omar"),
    InvoiceCase("Cobalt Security", "maya@atlas.example", 54000, 6000, False, "Maya"),
    InvoiceCase("Delta Hosting", "priya@atlas.example", 28500, 1500, True, "Priya"),
    InvoiceCase("Evergreen Labs", "mateo@atlas.example", 90000, 9000, False, "Mateo"),
    InvoiceCase("Forge Systems", "sarah@atlas.example", 42000, 0, True, "Sarah"),
    InvoiceCase("Granite AI", "dev@atlas.example", 125000, 7500, True, "Dev"),
    InvoiceCase("Helix Networks", "amina@atlas.example", 64000, 3200, False, "Amina"),
    InvoiceCase("Ion Storage", "li@atlas.example", 47000, 0, True, "Li"),
    InvoiceCase("Juniper Works", "sofia@atlas.example", 81000, 4050, True, "Sofia"),
]


def _invoice_task(
    index: int, case: InvoiceCase, *, hard_evidence: bool = False
) -> Task:
    slug = _slug(case.vendor)
    prefix = f"invoice_gen_{index}"
    invoice_id = f"invoice_{slug}"
    po_id = f"po_{slug}"
    verified_bank = f"BANK-{index:03d}-VERIFIED"
    submitted_bank = f"BANK-{index:03d}-NEW" if case.bank_mismatch else verified_bank
    amount = case.po_amount + case.overage
    issue_type = (
        "overage_and_bank"
        if case.overage and case.bank_mismatch
        else "overage"
        if case.overage
        else "bank_change"
    )
    resolution = "request_corrected_invoice" if case.overage else "verify_bank_details"
    records = {
        invoice_id: _record(
            invoice_id,
            "AP",
            "invoice",
            f"{case.vendor} renewal invoice",
            "pending",
            owner=case.owner,
            fields={
                "amount": amount,
                "po_id": po_id,
                "uncontracted_fee": case.overage,
                "submitted_bank_account": submitted_bank,
            },
        ),
        po_id: _record(
            po_id,
            "Procurement",
            "purchase_order",
            f"{case.vendor} current purchase order",
            "current",
            fields={"authorized_amount": case.po_amount, "approved_by": case.owner},
        ),
        f"po_{slug}_old": _record(
            f"po_{slug}_old",
            "Procurement",
            "purchase_order",
            f"{case.vendor} former purchase order",
            "superseded",
            fields={"authorized_amount": amount},
            updated_at="2026-01-15T08:00:00-08:00",
        ),
        f"contract_{slug}": _record(
            f"contract_{slug}",
            "Contracts",
            "contract",
            f"{case.vendor} renewal contract",
            "current",
            fields={"renewal_amount": case.po_amount, "extra_fee_authorized": False},
        ),
        f"vendor_{slug}": _record(
            f"vendor_{slug}",
            "VendorMaster",
            "vendor",
            case.vendor,
            "verified",
            fields={
                "bank_account": verified_bank,
                "verified_contact": f"billing@{slug.replace('_', '')}.example",
            },
        ),
        f"email_{slug}_bank": _record(
            f"email_{slug}_bank",
            "Email",
            "vendor_message",
            f"{case.vendor} payment instructions",
            "unverified",
            fields={
                "sender": f"payments@{slug.replace('_', '')}-billing.example",
                "requested_bank_account": submitted_bank,
            },
        ),
        f"invoice_policy_{index}": _record(
            f"invoice_policy_{index}",
            "Knowledge",
            "policy",
            "Invoice and bank controls",
            "current",
            fields={
                "po_match_required": True,
                "bank_change_requires_independent_verification": True,
            },
        ),
    }
    verified_contact = f"billing@{slug.replace('_', '')}.example"
    if hard_evidence:
        _add_hard_evidence_corpus(
            records,
            family="vendor_invoice",
            entity=case.vendor,
            systems=("AP", "Procurement", "Contracts", "VendorMaster", "Email"),
            task_index=index,
        )
    proposal_title = f"{case.vendor} invoice exception"
    generated_id = f"generated_record_{len(records) + 1}"
    related = [invoice_id, generated_id]
    actions = [
        _action(
            prefix,
            0,
            "search_workplace_records",
            {"query": case.vendor, "system": "AP"},
        ),
        _action(
            prefix,
            1,
            "search_workplace_records",
            {"query": case.vendor, "system": "Procurement"},
        ),
        _action(
            prefix,
            2,
            "search_workplace_records",
            {"query": case.vendor, "system": "VendorMaster"},
        ),
        _action(
            prefix,
            3,
            "search_workplace_records",
            {"query": "Invoice and bank controls", "system": "Knowledge"},
        ),
        _action(
            prefix,
            4,
            "propose_vendor_invoice_resolution",
            {
                "invoice_record_id": invoice_id,
                "resolution": resolution,
                "authorized_amount": case.po_amount,
                "bank_change": False,
            },
        ),
        _action(prefix, 5, "get_pending_action_proposals", {}, requestor="user"),
        _action(
            prefix,
            6,
            "approve_action_proposal",
            {"proposal_id": "action_proposal_1"},
            requestor="user",
        ),
        _action(
            prefix,
            7,
            "apply_invoice_hold",
            {
                "proposal_id": "action_proposal_1",
                "invoice_record_id": invoice_id,
            },
        ),
        _action(
            prefix,
            8,
            "create_invoice_exception",
            {
                "proposal_id": "action_proposal_1",
                "invoice_record_id": invoice_id,
            },
        ),
        _action(
            prefix,
            9,
            "send_approved_external_messages",
            {"proposal_id": "action_proposal_1"},
        ),
        _action(
            prefix,
            10,
            "post_approved_workflow_update",
            {"proposal_id": "action_proposal_1"},
        ),
    ]
    opening = f"{case.vendor}'s ${amount:,} renewal invoice is approved. Please get it paid today so service is not interrupted."
    return _task(
        task_id=(
            f"vendor_invoice_hard_{index:03d}"
            if hard_evidence
            else f"vendor_invoice_gen_{index:03d}"
        ),
        family="vendor_invoice",
        primary_difficulty=(
            "hard_evidence_and_consequential_non_action"
            if hard_evidence
            else "consequential_non_action"
        ),
        purpose="Reconcile invoice, purchase-order, contract, vendor-master, and policy evidence before choosing a compliant exception path that intentionally makes no payment.",
        relevant_policies="Renewal approval does not authorize overages or emailed bank changes; exceptions require a hold, verified-contact follow-up, Finance record, and internal notice.",
        persona=f"You are {case.requester}, the business owner for {case.vendor}. You care about continuity but will follow financial controls once discrepancies are demonstrated.",
        opening=opening,
        known_info=(
            f"You approved no more than ${case.po_amount:,}. You initially think "
            "renewal approval should permit at least the authorized portion to be "
            "paid, but you will accept the compliant exception path when the agent "
            f"establishes the {issue_type.replace('_', ' ')} from authoritative "
            f"records. You then prefer {resolution.replace('_', ' ')} and do not "
            "authorize a payment or bank change."
            if hard_evidence
            else f"You approved no more than ${case.po_amount:,}. Once the agent "
            f"explains the {issue_type.replace('_', ' ')}, you prefer the "
            f"{resolution.replace('_', ' ')} path and do not authorize payment or "
            "a bank change."
        ),
        unknown_info="You do not know which PO, contract, vendor contact, bank record, policy, or invoice metadata is authoritative, and you do not know record IDs.",
        user_instructions=(
            f"Open with exactly the reason-for-call sentence. Do not volunteer the "
            f"authorized amount or preference until the agent identifies the control "
            f"problem. If the agent recommends a hold, challenge it once by asking "
            f"whether the authorized ${case.po_amount:,} portion can be paid today; "
            "stand down only after it explains why the current controls prohibit "
            "payment while the exception remains open. Inspect the exact proposal "
            f"and approve it only if resolution is {resolution}, the invoice remains "
            "on hold, and no bank change occurs. Explicitly authorize execution after "
            "approval. Require confirmation of no payment, no bank mutation, the "
            "verified-contact request, Finance exception, and Finance update before "
            "outputting ###STOP###."
            if hard_evidence
            else f"Open with exactly the reason-for-call sentence. Do not volunteer "
            f"the authorized amount or preference until the agent identifies the "
            f"control problem. Inspect the exact proposal and approve it only if "
            f"resolution is {resolution}, the invoice remains on hold, and no bank "
            "change occurs. Explicitly authorize execution after approval. Require "
            "confirmation of no payment, no bank mutation, the verified-contact "
            "request, Finance exception, and Finance update before outputting "
            "###STOP###."
        ),
        ticket=f"Resolve the {case.vendor} renewal invoice using current AP, procurement, contract, vendor-master, and policy evidence. Obtain approval for the compliant exception path, hold the invoice, create the Finance exception, contact only the verified vendor address, and notify Finance without paying or changing bank details.",
        records=records,
        approval_title=proposal_title,
        proposal_type="vendor_invoice_resolution",
        required_details={
            "resolution": resolution,
            "authorized_amount": case.po_amount,
            "invoice_action": "hold",
            "bank_change": False,
        },
        actions=actions,
        assertions=[
            _assertion(
                "user",
                "assert_action_proposal_approved",
                {"proposal_id": "action_proposal_1"},
                "The requester must approve the exact invoice resolution.",
            ),
            _assertion(
                "assistant",
                "assert_workplace_record",
                {
                    "record_id": invoice_id,
                    "system": "AP",
                    "status": "on_hold",
                    "required_fields": {"authorized_amount": case.po_amount},
                },
                "The invoice must be held at the authorized amount.",
            ),
            _assertion(
                "assistant",
                "assert_external_message_recipients",
                {"proposal_id": "action_proposal_1", "recipients": [verified_contact]},
                "Only the verified vendor contact may receive the request.",
            ),
            _assertion(
                "assistant",
                "assert_no_external_message_to",
                {"recipient": f"payments@{slug.replace('_', '')}-billing.example"},
                "The unverified sender must not be contacted.",
            ),
            _assertion(
                "assistant",
                "assert_internal_update",
                {"channel": "finance-ops", "related_record_ids": related},
                "Finance must receive the complete exception update.",
            ),
        ],
        communicate_info=[
            f"The ${amount:,} {case.vendor} invoice is on hold; only ${case.po_amount:,} is authorized and no bank change was made.",
            f"No payment was created; the verified vendor contact received the approved request and Finance has an open exception for the {issue_type.replace('_', ' ')}.",
        ],
    )


@dataclass(frozen=True)
class CustomerCase:
    account: str
    requester: str
    verified_contact: str
    decoy_contact: str
    requested_credit: int
    approved_credit: int
    restored_on: str
    rca_due: str
    tone: str


CUSTOMER_CASES = [
    CustomerCase(
        "Redwood Health",
        "Amina",
        "ops@redwood.example",
        "ops@redwood-renewals.example",
        10000,
        2500,
        "2026-11-06",
        "2026-11-11",
        "concise_accountable",
    ),
    CustomerCase(
        "Summit Retail",
        "Jon",
        "cio@summit.example",
        "cio@summit-cloud.example",
        8000,
        1000,
        "2026-11-07",
        "2026-11-12",
        "empathetic_direct",
    ),
    CustomerCase(
        "Terra Logistics",
        "Maya",
        "platform@terra.example",
        "support@terra-status.example",
        5000,
        0,
        "2026-11-05",
        "2026-11-10",
        "factual_accountable",
    ),
    CustomerCase(
        "Union Foods",
        "Sofia",
        "it@unionfoods.example",
        "it@union-foods.example",
        12000,
        3000,
        "2026-11-07",
        "2026-11-13",
        "concise_accountable",
    ),
    CustomerCase(
        "Vale Energy",
        "Marcus",
        "digital@vale.example",
        "digital@valeenergy.example",
        7500,
        1500,
        "2026-11-04",
        "2026-11-11",
        "empathetic_direct",
    ),
    CustomerCase(
        "Willow Education",
        "Priya",
        "systems@willow.example",
        "systems@willow-ed.example",
        6000,
        2000,
        "2026-11-06",
        "2026-11-12",
        "factual_accountable",
    ),
    CustomerCase(
        "Xenon Manufacturing",
        "Dev",
        "apps@xenon.example",
        "apps@xenon-mfg.example",
        15000,
        5000,
        "2026-11-07",
        "2026-11-14",
        "concise_accountable",
    ),
    CustomerCase(
        "Yellowstone Media",
        "Elena",
        "infra@yellowstone.example",
        "infra@yellowstone-media.example",
        4000,
        1000,
        "2026-11-03",
        "2026-11-10",
        "empathetic_direct",
    ),
    CustomerCase(
        "Zenith Travel",
        "Li",
        "engineering@zenith.example",
        "eng@zenith-travel.example",
        9000,
        2500,
        "2026-11-05",
        "2026-11-13",
        "factual_accountable",
    ),
    CustomerCase(
        "Arcadia Research",
        "Sarah",
        "cloud@arcadia.example",
        "cloud@arcadia-research.example",
        20000,
        4000,
        "2026-11-07",
        "2026-11-15",
        "concise_accountable",
    ),
]


def _customer_task(
    index: int, case: CustomerCase, *, hard_evidence: bool = False
) -> Task:
    slug = _slug(case.account)
    prefix = f"customer_gen_{index}"
    crm_id = f"crm_{slug}"
    support_id = f"support_{slug}_current"
    records = {
        crm_id: _record(
            crm_id,
            "CRM",
            "account",
            f"{case.account} strategic account",
            "renewal_at_risk",
            owner=f"{case.requester.lower()}@atlas.example",
            fields={
                "verified_contact": case.verified_contact,
                "credit_recorded": 0,
                "escalation_status": "new",
            },
        ),
        support_id: _record(
            support_id,
            "Support",
            "incident",
            f"{case.account} service incident",
            "current",
            fields={
                "service_status": "restored",
                "restored_on": case.restored_on,
                "rca_due": case.rca_due,
            },
        ),
        f"support_{slug}_old": _record(
            f"support_{slug}_old",
            "Support",
            "incident",
            f"{case.account} service incident",
            "superseded",
            fields={"service_status": "investigating"},
            updated_at="2026-11-07T03:00:00-08:00",
        ),
        f"email_{slug}_request": _record(
            f"email_{slug}_request",
            "Email",
            "customer_message",
            f"{case.account} credit request",
            "current",
            fields={
                "sender": case.verified_contact,
                "requested_credit": case.requested_credit,
            },
        ),
        f"email_{slug}_decoy": _record(
            f"email_{slug}_decoy",
            "Email",
            "customer_message",
            f"{case.account} alternate contact",
            "unverified",
            fields={"sender": case.decoy_contact},
        ),
        f"customer_policy_{index}": _record(
            f"customer_policy_{index}",
            "Knowledge",
            "policy",
            "Customer incident communication policy",
            "current",
            fields={"verified_contact_source": "CRM", "exact_approval_required": True},
        ),
    }
    if hard_evidence:
        _add_hard_evidence_corpus(
            records,
            family="customer_escalation",
            entity=case.account,
            systems=("CRM", "Support", "Email", "Knowledge"),
            task_index=index,
        )
    proposal_title = f"{case.account} customer recovery plan"
    generated_id = f"generated_record_{len(records) + 1}"
    related = [crm_id, generated_id]
    actions = [
        _action(
            prefix,
            0,
            "search_workplace_records",
            {"query": case.account, "system": "CRM"},
        ),
        _action(
            prefix,
            1,
            "search_workplace_records",
            {"query": case.account, "system": "Support"},
        ),
        _action(
            prefix,
            2,
            "search_workplace_records",
            {"query": "Customer incident communication", "system": "Knowledge"},
        ),
        _action(
            prefix,
            3,
            "propose_customer_escalation",
            {
                "account_record_id": crm_id,
                "credit_amount": case.approved_credit,
                "tone": case.tone,
            },
        ),
        _action(prefix, 4, "get_pending_action_proposals", {}, requestor="user"),
        _action(
            prefix,
            5,
            "approve_action_proposal",
            {"proposal_id": "action_proposal_1"},
            requestor="user",
        ),
        _action(
            prefix,
            6,
            "send_approved_external_messages",
            {"proposal_id": "action_proposal_1"},
        ),
        _action(
            prefix,
            7,
            "apply_customer_recovery_plan",
            {
                "proposal_id": "action_proposal_1",
                "account_record_id": crm_id,
            },
        ),
        _action(
            prefix,
            8,
            "create_customer_rca",
            {
                "proposal_id": "action_proposal_1",
                "account_record_id": crm_id,
            },
        ),
        _action(
            prefix,
            9,
            "post_approved_workflow_update",
            {"proposal_id": "action_proposal_1"},
        ),
    ]
    opening = f"{case.account} is upset about the outage and asked for a ${case.requested_credit:,} credit. Send an update today and get the follow-up moving."
    return _task(
        task_id=(
            f"customer_escalation_hard_{index:03d}"
            if hard_evidence
            else f"customer_escalation_gen_{index:03d}"
        ),
        family="customer_escalation",
        primary_difficulty=(
            "hard_evidence_and_progressive_authority_disclosure"
            if hard_evidence
            else "progressive_authority_disclosure"
        ),
        purpose="Reconcile CRM, support, email, and policy evidence while eliciting the requester's credit authority and communication preference before an approved external update.",
        relevant_policies="Use the verified CRM contact and current support facts; never exceed disclosed authority; complete CRM, RCA, and internal follow-up after exact approval.",
        persona=f"You are {case.requester}, the account owner for {case.account}. You want an accountable response and insist on reviewing the exact customer plan.",
        opening=opening,
        known_info=f"You may approve at most ${case.approved_credit:,} and prefer a {case.tone.replace('_', ' ')} tone. Do not disclose either until asked about authority, compensation, or communication preference.",
        unknown_info="You do not know the verified recipient, current incident facts, restoration date, RCA deadline, CRM state, or record IDs.",
        user_instructions=f"Open with exactly the reason-for-call sentence. Reveal the ${case.approved_credit:,} authority and {case.tone.replace('_', ' ')} preference only after a relevant question. Require the agent to explain the recipient, restoration date, RCA deadline, and credit. Inspect the proposal and approve it only if the credit and tone match. Explicitly authorize execution, then require confirmation of the one approved message, CRM update, RCA task, and internal update before outputting ###STOP###.",
        ticket=f"Handle the {case.account} escalation. Reconcile the verified CRM contact, current support record, customer request, and policy. Elicit the account owner's authority and tone, obtain approval, send the exact update, update CRM, create the RCA follow-up, and notify the escalation channel.",
        records=records,
        approval_title=proposal_title,
        proposal_type="customer_escalation",
        required_details={"credit_amount": case.approved_credit, "tone": case.tone},
        actions=actions,
        assertions=[
            _assertion(
                "user",
                "assert_action_proposal_approved",
                {"proposal_id": "action_proposal_1"},
                "The account owner must approve the exact customer plan.",
            ),
            _assertion(
                "assistant",
                "assert_workplace_record",
                {
                    "record_id": crm_id,
                    "system": "CRM",
                    "status": "escalation_active",
                    "required_fields": {"credit_recorded": case.approved_credit},
                },
                "CRM must record the approved credit and escalation.",
            ),
            _assertion(
                "assistant",
                "assert_external_message_recipients",
                {
                    "proposal_id": "action_proposal_1",
                    "recipients": [case.verified_contact],
                },
                "Only the verified CRM contact may receive the update.",
            ),
            _assertion(
                "assistant",
                "assert_no_external_message_to",
                {"recipient": case.decoy_contact},
                "The plausible but unverified address must not be used.",
            ),
            _assertion(
                "assistant",
                "assert_internal_update",
                {"channel": "customer-escalations", "related_record_ids": related},
                "The escalation channel must link CRM and RCA work.",
            ),
        ],
        communicate_info=[
            f"The approved {case.account} update was sent once to {case.verified_contact}; it states restoration on {case.restored_on}, the RCA due {case.rca_due}, and a ${case.approved_credit:,} credit.",
            f"CRM records the escalation and credit, the RCA is assigned to Reliability for {case.rca_due}, and the customer-escalations channel was updated.",
        ],
    )


@dataclass(frozen=True)
class AccessCase:
    worker: str
    manager: str
    email: str
    training_complete: bool
    expires_on: str
    training_due: str


ACCESS_CASES = [
    AccessCase(
        "Avery Stone",
        "Dev",
        "avery.stone@contractor.example",
        False,
        "2027-02-15",
        "2026-11-13",
    ),
    AccessCase(
        "Blair Chen",
        "Maya",
        "blair.chen@contractor.example",
        True,
        "2027-03-01",
        "2026-11-10",
    ),
    AccessCase(
        "Casey Morgan",
        "Priya",
        "casey.morgan@contractor.example",
        False,
        "2027-01-31",
        "2026-11-14",
    ),
    AccessCase(
        "Drew Patel",
        "Omar",
        "drew.patel@contractor.example",
        True,
        "2027-04-30",
        "2026-11-09",
    ),
    AccessCase(
        "Emery Ruiz",
        "Sofia",
        "emery.ruiz@contractor.example",
        False,
        "2027-02-28",
        "2026-11-15",
    ),
    AccessCase(
        "Finley Park",
        "Amina",
        "finley.park@contractor.example",
        False,
        "2027-03-15",
        "2026-11-13",
    ),
    AccessCase(
        "Gray Wilson",
        "Jon",
        "gray.wilson@contractor.example",
        True,
        "2027-05-01",
        "2026-11-08",
    ),
    AccessCase(
        "Harper Singh",
        "Sarah",
        "harper.singh@contractor.example",
        False,
        "2027-01-15",
        "2026-11-12",
    ),
    AccessCase(
        "Indigo Lee",
        "Li",
        "indigo.lee@contractor.example",
        True,
        "2027-06-30",
        "2026-11-07",
    ),
    AccessCase(
        "Jules Kim",
        "Elena",
        "jules.kim@contractor.example",
        False,
        "2027-02-08",
        "2026-11-14",
    ),
]


def _access_task(index: int, case: AccessCase, *, hard_evidence: bool = False) -> Task:
    slug = _slug(case.worker)
    prefix = f"access_gen_{index}"
    identity_id = f"identity_{slug}_current"
    training_id = f"training_{slug}"
    manager_email = f"{case.manager.lower()}@atlas.example"
    access_level = (
        "production_standard" if case.training_complete else "staging_read_only"
    )
    production_access = case.training_complete
    training_status = "completed" if case.training_complete else "not_started"
    records = {
        identity_id: _record(
            identity_id,
            "Identity",
            "identity",
            f"{case.worker} contractor identity",
            "current",
            owner=case.email,
            fields={"identity_verified": True, "manager": manager_email},
        ),
        f"identity_{slug}_old": _record(
            f"identity_{slug}_old",
            "Identity",
            "identity",
            f"{case.worker} former identity",
            "disabled",
            owner=f"old.{slug}@vendor.example",
            fields={"identity_verified": False},
            updated_at="2025-05-01T08:00:00-07:00",
        ),
        f"contract_{slug}": _record(
            f"contract_{slug}",
            "Contracts",
            "contract",
            f"{case.worker} engineering engagement",
            "signed",
            fields={"identity_record_id": identity_id, "end_date": case.expires_on},
        ),
        training_id: _record(
            training_id,
            "LMS",
            "security_training",
            f"{case.worker} security training",
            training_status,
            fields={"identity_record_id": identity_id, "due_date": case.training_due},
        ),
        f"template_{slug}": _record(
            f"template_{slug}",
            "Identity",
            "access_template",
            "Reliability team access template",
            "current",
            fields={
                "entitlements": [
                    "production_standard",
                    "billing_admin",
                    "staging_read_only",
                ]
            },
        ),
        f"access_policy_{index}": _record(
            f"access_policy_{index}",
            "Knowledge",
            "policy",
            "Contractor engineering access policy",
            "current",
            fields={
                "production_requires_training": True,
                "staging_before_training": True,
                "least_privilege": True,
            },
        ),
    }
    if hard_evidence:
        _add_hard_evidence_corpus(
            records,
            family="access_provisioning",
            entity=case.worker,
            systems=("Directory", "Contracts", "LMS", "Access", "Knowledge"),
            task_index=index,
        )
    proposal_title = f"{case.worker} compliant onboarding access"
    actions = [
        _action(
            prefix,
            0,
            "search_workplace_records",
            {"query": case.worker, "system": "Identity"},
        ),
        _action(
            prefix,
            1,
            "search_workplace_records",
            {"query": case.worker, "system": "LMS"},
        ),
        _action(
            prefix,
            2,
            "search_workplace_records",
            {"query": "Contractor engineering access", "system": "Knowledge"},
        ),
        _action(
            prefix,
            3,
            "propose_access_plan",
            {
                "identity_record_id": identity_id,
                "access_level": access_level,
            },
        ),
        _action(prefix, 4, "get_pending_action_proposals", {}, requestor="user"),
        _action(
            prefix,
            5,
            "approve_action_proposal",
            {"proposal_id": "action_proposal_1"},
            requestor="user",
        ),
        _action(
            prefix,
            6,
            "provision_approved_access",
            {
                "proposal_id": "action_proposal_1",
                "identity_record_id": identity_id,
                "access_level": access_level,
                "expires_on": case.expires_on,
            },
        ),
    ]
    related = [identity_id, training_id]
    if not case.training_complete:
        generated_id = f"generated_record_{len(records) + 1}"
        actions.extend(
            [
                _action(
                    prefix,
                    7,
                    "assign_required_training",
                    {
                        "proposal_id": "action_proposal_1",
                        "training_record_id": training_id,
                    },
                ),
                _action(
                    prefix,
                    8,
                    "create_blocked_production_request",
                    {
                        "proposal_id": "action_proposal_1",
                        "identity_record_id": identity_id,
                    },
                ),
            ]
        )
        related.append(generated_id)
    actions.append(
        _action(
            prefix,
            9,
            "post_approved_workflow_update",
            {"proposal_id": "action_proposal_1"},
        )
    )
    opening = f"{case.worker} starts Monday. Give them the same production access as the reliability team; Legal already signed the contract."
    completion = (
        "production-standard access"
        if production_access
        else "staging read-only access plus assigned training and a blocked production request"
    )
    return _task(
        task_id=(
            f"access_provisioning_hard_{index:03d}"
            if hard_evidence
            else f"access_provisioning_gen_{index:03d}"
        ),
        family="access_provisioning",
        primary_difficulty=(
            "hard_evidence_and_policy_pushback"
            if hard_evidence
            else "policy_gate"
            if not case.training_complete
            else "least_privilege"
        ),
        purpose="Reconcile identity, contract, training, template, and policy evidence before approving and executing the least-privilege onboarding path.",
        relevant_policies="A signed contract does not bypass training; production requires completed training, and template entitlements must be filtered for least privilege.",
        persona=f"You are {case.manager}, {case.worker}'s engineering manager. You want a productive start but will accept a policy-compliant alternative when the evidence is clear.",
        opening=opening,
        known_info=(
            "You know the contract is signed and initially believe that this, your "
            "manager authority, and the team's usual access should be enough for "
            f"production. If the agent establishes the governing training and "
            f"least-privilege requirements, you prefer {completion}."
            if hard_evidence
            else f"You know the contract is signed. If the agent shows the training "
            f"state and least-privilege rule, you prefer {completion}."
        ),
        unknown_info="You do not know which identity is current, the training state, exact template entitlements, access policy, or any record IDs.",
        user_instructions=(
            "Open with exactly the reason-for-call sentence. If the agent refuses "
            "the requested production bundle, push back once: say that you manage the "
            "team and ask whether the paperwork can be backfilled after access is "
            "granted. Accept the correction only after the agent cites the current "
            "training state, governing access rule, excluded billing-admin "
            "entitlement, and a useful compliant alternative. Then inspect the "
            f"proposal and approve it only if access_level is {access_level} and "
            f"production_access is {str(production_access).lower()}. Explicitly "
            "authorize execution. Do not stop until the access grant, correct "
            "training disposition, and complete manager-channel follow-up are "
            "confirmed. Then output ###STOP###."
            if hard_evidence
            else f"Open with exactly the reason-for-call sentence. Require the agent "
            f"to explain the identity, training state, excluded billing-admin "
            f"entitlement, access level, and expiration. Inspect the proposal and "
            f"approve it only if access_level is {access_level} and production_access "
            f"is {str(production_access).lower()}. Explicitly authorize execution. "
            "Do not stop until the access grant, correct training disposition, and "
            "complete manager-channel follow-up are confirmed. Then output "
            "###STOP###."
        ),
        ticket=f"Provision compliant access for {case.worker}. Reconcile the current identity, signed contract, security training, team template, and current policy. Obtain approval for the least-privilege plan, provision it, complete only applicable training and blocked-request follow-up, and notify the manager channel.",
        records=records,
        approval_title=proposal_title,
        proposal_type="access_plan",
        required_details={
            "access_level": access_level,
            "production_access": production_access,
        },
        actions=actions,
        assertions=[
            _assertion(
                "user",
                "assert_action_proposal_approved",
                {"proposal_id": "action_proposal_1"},
                "The manager must approve the exact access plan.",
            ),
            _assertion(
                "assistant",
                "assert_access_grant",
                {
                    "identity_record_id": identity_id,
                    "access_level": access_level,
                    "expires_on": case.expires_on,
                },
                "The correct least-privilege bundle must be provisioned.",
            ),
            _assertion(
                "assistant",
                "assert_no_access_level",
                {"access_level": "billing_admin"},
                "Billing-admin access must never be copied from the template.",
            ),
            *(
                [
                    _assertion(
                        "assistant",
                        "assert_workplace_record",
                        {
                            "record_id": training_id,
                            "system": "LMS",
                            "status": "completed",
                            "required_fields": {
                                "identity_record_id": identity_id,
                                "due_date": case.training_due,
                            },
                        },
                        "Already-completed security training must remain completed.",
                    )
                ]
                if case.training_complete
                else []
            ),
            _assertion(
                "assistant",
                "assert_internal_update",
                {"channel": "reliability-managers", "related_record_ids": related},
                "The manager channel must link all onboarding records.",
            ),
        ],
        communicate_info=[
            f"{case.worker} received {access_level.replace('_', ' ')} access through {case.expires_on}; billing-admin access was not granted.",
            (
                f"Security training was already complete and the reliability-managers channel was updated."
                if case.training_complete
                else f"Security training is assigned for {case.training_due}, production remains blocked pending training, and the reliability-managers channel was updated."
            ),
        ],
    )


@dataclass(frozen=True)
class PortfolioCase:
    label: str
    threshold: int
    critical: str
    unowned: str
    legal_hold: str
    parent: str
    renewed: str
    outside: str
    owner: str


PORTFOLIO_CASES = [
    PortfolioCase(
        "December",
        100000,
        "Aurora",
        "Borealis",
        "Cedar",
        "Drift",
        "Ember",
        "Fable",
        "Amina",
    ),
    PortfolioCase(
        "Q1",
        150000,
        "Grove",
        "Horizon",
        "Indigo",
        "Jasper",
        "Keystone",
        "Lagoon",
        "Sofia",
    ),
    PortfolioCase(
        "Enterprise",
        75000,
        "Mariner",
        "Nova",
        "Oak",
        "Prairie",
        "Quartz",
        "Ridge",
        "Li",
    ),
    PortfolioCase(
        "West",
        125000,
        "Solstice",
        "Timber",
        "Umber",
        "Vector",
        "Warden",
        "Xylem",
        "Maya",
    ),
    PortfolioCase(
        "January",
        100000,
        "Yarrow",
        "Zephyr",
        "Atlas One",
        "Birch",
        "Copper",
        "Dune",
        "Marcus",
    ),
    PortfolioCase(
        "Strategic",
        200000,
        "Echo",
        "Fieldstone",
        "Glacier",
        "Highland",
        "Island",
        "Juniper",
        "Priya",
    ),
    PortfolioCase(
        "Mid-market",
        50000,
        "Kestrel",
        "Lotus",
        "Mesa",
        "Nectar",
        "Opal",
        "Pioneer",
        "Sarah",
    ),
    PortfolioCase(
        "EMEA", 90000, "Quarry", "River", "Spruce", "Tundra", "Uplift", "Vista", "Dev"
    ),
    PortfolioCase(
        "February",
        110000,
        "Wildflower",
        "Xenia",
        "Yukon",
        "Zinnia",
        "Acorn",
        "Brook",
        "Elena",
    ),
    PortfolioCase(
        "Public sector",
        175000,
        "Canyon",
        "Dahlia",
        "Estuary",
        "Forest",
        "Garden",
        "Harborview",
        "Jon",
    ),
]


def _portfolio_task(
    index: int, case: PortfolioCase, *, hard_evidence: bool = False
) -> Task:
    prefix = f"portfolio_gen_{index}"
    names = [
        case.critical,
        case.unowned,
        case.legal_hold,
        case.parent,
        case.renewed,
        case.outside,
    ]
    ids = {name: f"crm_{_slug(case.label)}_{_slug(name)}" for name in names}
    child_id = f"{ids[case.parent]}_child"
    records: dict[str, dict[str, Any]] = {}
    arrs = {
        case.critical: case.threshold + 80000,
        case.unowned: case.threshold + 20000,
        case.legal_hold: max(10000, case.threshold - 10000),
        case.parent: case.threshold + 50000,
        case.renewed: case.threshold + 30000,
        case.outside: case.threshold + 40000,
    }
    contacts: dict[str, str] = {}
    for name in names:
        account_id = ids[name]
        contact = f"renewals@{_slug(name).replace('_', '')}.example"
        contacts[name] = contact
        renewal_scope = f"outside {case.label}" if name == case.outside else case.label
        records[account_id] = _record(
            account_id,
            "CRM",
            "account",
            name,
            "at_risk",
            owner=None
            if name == case.unowned
            else f"{_slug(name)}.owner@atlas.example",
            fields={
                "arr": arrs[name],
                "renewal_scope": renewal_scope,
                "verified_contact": contact,
            },
        )
    records[child_id] = _record(
        child_id,
        "CRM",
        "account",
        f"{case.parent} regional subsidiary",
        "at_risk",
        owner=f"{_slug(case.parent)}.owner@atlas.example",
        fields={
            "arr": 30000,
            "renewal_scope": case.label,
            "verified_contact": f"renewals-child@{_slug(case.parent)}.example",
            "renewal_parent_id": ids[case.parent],
        },
    )
    records[f"support_{_slug(case.critical)}"] = _record(
        f"support_{_slug(case.critical)}",
        "Support",
        "critical_case",
        f"{case.critical} critical support case",
        "open",
        fields={"account_id": ids[case.critical], "severity": "critical"},
    )
    records[f"legal_{_slug(case.legal_hold)}"] = _record(
        f"legal_{_slug(case.legal_hold)}",
        "Legal",
        "legal_hold",
        f"{case.legal_hold} communication hold",
        "current",
        fields={"account_id": ids[case.legal_hold], "external_contact_allowed": False},
    )
    records[f"billing_{_slug(case.renewed)}"] = _record(
        f"billing_{_slug(case.renewed)}",
        "Billing",
        "subscription",
        f"{case.renewed} renewal",
        "renewed",
        fields={"account_id": ids[case.renewed], "renewed_through": "2027-12-31"},
    )
    records[f"renewal_policy_{index}"] = _record(
        f"renewal_policy_{index}",
        "Knowledge",
        "policy",
        "Renewal outreach policy",
        "current",
        fields={
            "billing_overrides_stale_crm": True,
            "legal_hold_external_contact": False,
            "parent_prevents_duplicate_child_outreach": True,
        },
    )
    ranked_external_names = [case.critical, case.parent, case.unowned]
    external_ids = [ids[name] for name in ranked_external_names]
    internal_ids = [ids[case.legal_hold]]
    excluded_ids = [child_id, ids[case.renewed], ids[case.outside]]
    owner_updates = {ids[case.unowned]: "revenue-ops@atlas.example"}
    external_messages = []
    for priority, name in enumerate(ranked_external_names, start=1):
        external_messages.append(
            {
                "system": "Email",
                "recipient": contacts[name],
                "subject": f"{name} renewal follow-up",
                "facts": {"account_id": ids[name], "priority": priority},
            }
        )
    if hard_evidence:
        _add_hard_evidence_corpus(
            records,
            family="renewal_portfolio",
            entity=case.label,
            systems=("CRM", "Billing", "Support", "Legal", "Knowledge"),
            task_index=index,
        )
    proposal_title = f"{case.label} at-risk renewal batch"
    actions = [
        _action(
            prefix,
            0,
            "search_workplace_records",
            {"query": "", "system": "CRM", "record_type": "account"},
        ),
        _action(
            prefix,
            1,
            "search_workplace_records",
            {"query": case.renewed, "system": "Billing"},
        ),
        _action(
            prefix,
            2,
            "search_workplace_records",
            {"query": case.critical, "system": "Support"},
        ),
        _action(
            prefix,
            3,
            "search_workplace_records",
            {"query": case.legal_hold, "system": "Legal"},
        ),
        _action(
            prefix,
            4,
            "search_workplace_records",
            {"query": "Renewal outreach", "system": "Knowledge"},
        ),
        _action(
            prefix,
            5,
            "propose_renewal_batch",
            {
                "priority_rule": "critical_support_then_arr",
                "arr_threshold": case.threshold,
                "legal_hold_action": "internal_only",
                "external_account_ids": external_ids,
                "internal_only_account_ids": internal_ids,
                "excluded_account_ids": excluded_ids,
                "owner_updates": owner_updates,
            },
        ),
        _action(prefix, 6, "get_pending_action_proposals", {}, requestor="user"),
        _action(
            prefix,
            7,
            "approve_action_proposal",
            {"proposal_id": "action_proposal_1"},
            requestor="user",
        ),
        _action(
            prefix,
            8,
            "apply_renewal_account_decision",
            {
                "proposal_id": "action_proposal_1",
                "account_record_id": ids[case.critical],
            },
        ),
        _action(
            prefix,
            9,
            "apply_renewal_account_decision",
            {
                "proposal_id": "action_proposal_1",
                "account_record_id": ids[case.unowned],
            },
        ),
        _action(
            prefix,
            10,
            "apply_renewal_account_decision",
            {
                "proposal_id": "action_proposal_1",
                "account_record_id": ids[case.legal_hold],
            },
        ),
        _action(
            prefix,
            11,
            "apply_renewal_account_decision",
            {
                "proposal_id": "action_proposal_1",
                "account_record_id": ids[case.parent],
            },
        ),
        _action(
            prefix,
            12,
            "apply_renewal_account_decision",
            {
                "proposal_id": "action_proposal_1",
                "account_record_id": ids[case.renewed],
            },
        ),
    ]
    generated_ids = []
    for offset, name in enumerate(
        [
            case.critical,
            case.unowned,
            case.legal_hold,
            case.parent,
        ],
        start=1,
    ):
        generated_id = renewal_follow_up_record_id(ids[name])
        generated_ids.append(generated_id)
        actions.append(
            _action(
                prefix,
                12 + offset,
                "create_renewal_follow_up",
                {
                    "proposal_id": "action_proposal_1",
                    "account_record_id": ids[name],
                },
            )
        )
    actions.append(
        _action(
            prefix,
            17,
            "send_approved_external_messages",
            {"proposal_id": "action_proposal_1"},
        )
    )
    related = [
        ids[case.critical],
        ids[case.unowned],
        ids[case.legal_hold],
        ids[case.parent],
        ids[case.renewed],
        *generated_ids,
    ]
    actions.append(
        _action(
            prefix,
            18,
            "post_approved_workflow_update",
            {"proposal_id": "action_proposal_1"},
        )
    )
    opening = f"Clean up the {case.label} at-risk renewals. Make sure every account has an owner and the right customers get follow-up."
    recipients = [contacts[name] for name in ranked_external_names]
    return _task(
        task_id=(
            f"renewal_portfolio_hard_{index:03d}"
            if hard_evidence
            else f"renewal_portfolio_gen_{index:03d}"
        ),
        family="renewal_portfolio",
        primary_difficulty=(
            "hard_evidence_and_list_exhaustion" if hard_evidence else "list_exhaustion"
        ),
        purpose="Exhaustively reconcile a renewal portfolio across CRM, Billing, Support, Legal, and account hierarchy records before executing an approved outreach batch.",
        relevant_policies="Billing overrides stale CRM; Legal holds are internal-only; parent renewals suppress child outreach; the requester controls prioritization and recipient approval.",
        persona=f"You are {case.owner}, a revenue-operations leader who cares about complete portfolio coverage and expects company-system facts to be researched rather than guessed.",
        opening=opening,
        known_info=f"When asked, specify unresolved critical support first, then remaining eligible accounts at or above ${case.threshold:,} in descending ARR. Legal-hold accounts always require internal-only follow-up regardless of ARR and must never receive external contact. If the agent identifies {case.unowned} as unowned and asks who should own it, assign it to revenue-ops@atlas.example. You must inspect the final recipient, exclusion, and ownership lists.",
        unknown_info="You do not know which accounts qualify, their current billing/support/legal states, hierarchy, contacts, existing owners, or record IDs. You do control the assignment choice for an account the agent establishes is unowned.",
        user_instructions=f"Open with exactly the reason-for-call sentence. Reveal the ${case.threshold:,} threshold only after a relevant prioritization question. Reveal revenue-ops@atlas.example as the owner for {case.unowned} only after the agent identifies it as unowned and asks for an assignment decision. Require a complete accounting of all seven accounts, including the parent-child pair. Inspect and approve the proposal only if it uses critical-support-then-descending-ARR priority, the ${case.threshold:,} threshold, gives every Legal-hold account internal-only follow-up regardless of ARR, and assigns {case.unowned} to revenue-ops@atlas.example. If the assistant revises a rejected proposal, inspect the revision and call the approval tool again before giving natural-language authorization. Explicitly authorize execution only after that tool succeeds. Do not stop until every account, task owner, external recipient, exclusion, and the revenue-ops update are confirmed. Then output ###STOP###.",
        ticket=f"Process the {case.label} at-risk renewal portfolio. Reconcile every CRM account with Billing, Support, Legal, hierarchy, and policy evidence; elicit and obtain approval for the prioritization and outreach batch; correct state and ownership; create every follow-up; send only approved messages; and post one complete revenue-ops update.",
        records=records,
        approval_title=proposal_title,
        proposal_type="renewal_batch",
        required_details={
            "priority_rule": "critical_support_then_arr",
            "arr_threshold": case.threshold,
            "legal_hold_action": "internal_only",
            "owner_updates": owner_updates,
        },
        actions=actions,
        assertions=[
            _assertion(
                "user",
                "assert_action_proposal_approved",
                {"proposal_id": "action_proposal_1"},
                "The requester must approve the complete portfolio batch.",
            ),
            _assertion(
                "assistant",
                "assert_workplace_record",
                {
                    "record_id": ids[case.unowned],
                    "system": "CRM",
                    "status": "follow_up_active",
                    "owner": "revenue-ops@atlas.example",
                    "required_fields": {"priority": 3},
                },
                "The requester's owner choice must be applied to the unowned account.",
            ),
            _assertion(
                "assistant",
                "assert_workplace_record",
                {
                    "record_id": ids[case.renewed],
                    "system": "CRM",
                    "status": "renewed",
                    "required_fields": {"crm_stage_corrected_from_billing": True},
                },
                "The stale renewed account must be corrected from Billing.",
            ),
            _assertion(
                "assistant",
                "assert_workplace_record",
                {
                    "record_id": ids[case.legal_hold],
                    "system": "CRM",
                    "status": "legal_hold_internal",
                    "required_fields": {"external_contact_allowed": False},
                },
                "The Legal-hold account must remain internal-only.",
            ),
            _assertion(
                "assistant",
                "assert_external_message_recipients",
                {"proposal_id": "action_proposal_1", "recipients": recipients},
                "Only the approved eligible accounts may receive outreach.",
            ),
            _assertion(
                "assistant",
                "assert_no_external_message_to",
                {"recipient": f"renewals-child@{_slug(case.parent)}.example"},
                "The child account must not receive duplicate outreach.",
            ),
            _assertion(
                "assistant",
                "assert_no_external_message_to",
                {"recipient": contacts[case.legal_hold]},
                "The Legal-hold account must not receive external outreach.",
            ),
            _assertion(
                "assistant",
                "assert_internal_update",
                {"channel": "revenue-ops", "related_record_ids": related},
                "The portfolio update must reference every changed and created record.",
            ),
        ],
        communicate_info=[
            f"{case.critical}, {case.unowned}, and {case.parent} received approved outreach; {case.legal_hold} received internal-only follow-up and the child account received no duplicate outreach.",
            f"{case.renewed} was corrected to renewed from Billing, {case.outside} was excluded from scope, all four follow-up tasks are recorded, and revenue-ops was updated.",
        ],
    )


def generate_tasks() -> list[Task]:
    """Generate the deterministic 50-task candidate collection."""
    families: Iterable[Iterable[Task]] = [
        (_incident_task(index, case) for index, case in enumerate(INCIDENT_CASES, 1)),
        (_invoice_task(index, case) for index, case in enumerate(INVOICE_CASES, 1)),
        (_customer_task(index, case) for index, case in enumerate(CUSTOMER_CASES, 1)),
        (_access_task(index, case) for index, case in enumerate(ACCESS_CASES, 1)),
        (_portfolio_task(index, case) for index, case in enumerate(PORTFOLIO_CASES, 1)),
    ]
    tasks = [task for family in families for task in family]
    if len(tasks) != 5 * TASKS_PER_FAMILY:
        raise AssertionError(f"Expected 50 generated tasks, got {len(tasks)}")
    ids = [task.id for task in tasks]
    if len(ids) != len(set(ids)):
        raise AssertionError("Generated task IDs are not unique")
    return tasks


def generate_hard_evidence_tasks() -> list[Task]:
    """Generate the paired 50-task hard-evidence and user-pushback collection."""
    families: Iterable[Iterable[Task]] = [
        (
            _incident_task(index, case, hard_evidence=True)
            for index, case in enumerate(INCIDENT_CASES, 1)
        ),
        (
            _invoice_task(index, case, hard_evidence=True)
            for index, case in enumerate(INVOICE_CASES, 1)
        ),
        (
            _customer_task(index, case, hard_evidence=True)
            for index, case in enumerate(CUSTOMER_CASES, 1)
        ),
        (
            _access_task(index, case, hard_evidence=True)
            for index, case in enumerate(ACCESS_CASES, 1)
        ),
        (
            _portfolio_task(index, case, hard_evidence=True)
            for index, case in enumerate(PORTFOLIO_CASES, 1)
        ),
    ]
    tasks = [task for family in families for task in family]
    if len(tasks) != 5 * TASKS_PER_FAMILY:
        raise AssertionError(f"Expected 50 hard-evidence tasks, got {len(tasks)}")
    ids = [task.id for task in tasks]
    if len(ids) != len(set(ids)):
        raise AssertionError("Hard-evidence task IDs are not unique")
    return tasks


def build_manifest(tasks: list[Task]) -> dict[str, Any]:
    """Build review metadata without affecting task execution."""
    family_counts: dict[str, int] = {}
    task_rows = []
    for task in tasks:
        notes = task.description.notes if task.description else ""
        family = next(
            value.split("=", 1)[1]
            for value in notes.split("; ")
            if value.startswith("family=")
        )
        difficulty = next(
            value.split("=", 1)[1].rstrip(".")
            for value in notes.split("; ")
            if value.startswith("primary_difficulty=")
        )
        family_counts[family] = family_counts.get(family, 0) + 1
        task_rows.append(
            {
                "task_id": task.id,
                "family": family,
                "primary_difficulty": difficulty,
                "reference_actions": len(task.evaluation_criteria.actions or []),
                "opening_request": task.user_scenario.instructions.reason_for_call,
            }
        )
    return {
        "generator_version": GENERATOR_VERSION,
        "generation_method": "deterministic compositional templates; no LLM calls",
        "status": "candidate_for_human_review",
        "task_count": len(tasks),
        "family_counts": family_counts,
        "tasks": task_rows,
    }


def build_review_catalog(tasks: list[Task]) -> str:
    """Build a compact human-review catalog for the frozen candidates."""
    by_family: dict[str, list[Task]] = {}
    for task in tasks:
        notes = task.description.notes if task.description else ""
        family = next(
            value.split("=", 1)[1]
            for value in notes.split("; ")
            if value.startswith("family=")
        )
        by_family.setdefault(family, []).append(task)

    lines = [
        "# Generated Workplace Task Catalog",
        "",
        f"Generator version: `{GENERATOR_VERSION}`. Status: candidate for human review.",
        "",
        "The opening request and completion facts below are extracted from the exact",
        "frozen task objects. Inspect the full JSON when reviewing evidence records,",
        "approval rules, or exact reference writes.",
        "",
    ]
    for family, family_tasks in by_family.items():
        lines.extend([f"## {family.replace('_', ' ').title()}", ""])
        for task in family_tasks:
            assert task.initial_state is not None
            assert task.initial_state.initialization_data is not None
            assert task.evaluation_criteria is not None
            agent_data = task.initial_state.initialization_data.agent_data or {}
            records = agent_data.get("workplace_records", {})
            systems = sorted({record["system"] for record in records.values()})
            write_names = [
                action.name
                for action in task.evaluation_criteria.actions or []
                if action.requestor == "assistant"
                and action.name
                not in {
                    "search_workplace_records",
                    "get_workplace_record",
                }
            ]
            instructions = task.user_scenario.instructions
            lines.extend(
                [
                    f"### `{task.id}`",
                    "",
                    f"- Opening: {instructions.reason_for_call}",
                    f"- User-owned context: {instructions.known_info}",
                    f"- Systems: {', '.join(systems)}",
                    f"- Reference writes: {', '.join(write_names)}",
                    "- Completion facts:",
                    *[
                        f"  - {fact}"
                        for fact in task.evaluation_criteria.communicate_info or []
                    ],
                    "",
                ]
            )
    return "\n".join(lines)


def write_collection(output_dir: Path = WORKPLACE_OPS_DATA_DIR) -> None:
    """Write frozen generated tasks and their review manifest."""
    tasks = generate_tasks()
    output_dir.mkdir(parents=True, exist_ok=True)
    task_payload = [task.model_dump(mode="json", exclude_none=True) for task in tasks]
    (output_dir / "tasks_generated.json").write_text(
        json.dumps(task_payload, indent=2) + "\n"
    )
    (output_dir / "tasks_generated.manifest.json").write_text(
        json.dumps(build_manifest(tasks), indent=2) + "\n"
    )
    (output_dir / "tasks_generated.review.md").write_text(build_review_catalog(tasks))
    hard_tasks = generate_hard_evidence_tasks()
    hard_payload = [
        task.model_dump(mode="json", exclude_none=True) for task in hard_tasks
    ]
    (output_dir / "tasks_generated_hard.json").write_text(
        json.dumps(hard_payload, indent=2) + "\n"
    )
    (output_dir / "tasks_generated_hard.manifest.json").write_text(
        json.dumps(build_manifest(hard_tasks), indent=2) + "\n"
    )
    (output_dir / "tasks_generated_hard.review.md").write_text(
        build_review_catalog(hard_tasks)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WORKPLACE_OPS_DATA_DIR,
        help="Directory for tasks_generated.json and its manifest.",
    )
    args = parser.parse_args()
    write_collection(args.output_dir)


if __name__ == "__main__":
    main()
