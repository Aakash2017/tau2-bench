import json
import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, Literal, Optional

from tau2.domains.workplace_ops.data_model import (
    AccessGrant,
    ActionProposal,
    CalendarEvent,
    ChatMessage,
    Document,
    Employee,
    ExternalMessage,
    InternalUpdate,
    MeetingProposal,
    OnCallPage,
    ProjectMilestone,
    ProjectRecord,
    ProjectTask,
    WorkplaceOpsDB,
    WorkplaceRecord,
    access_grant_id_for_index,
    action_proposal_id_for_index,
    event_id_for_proposal,
    external_message_id_for_index,
    generated_record_id_for_index,
    internal_update_id_for_index,
    message_id_for_index,
    page_id_for_index,
    proposal_id_for_index,
    renewal_follow_up_record_id,
    task_id_for_index,
)
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


class WorkplaceOpsTools(ToolKitBase):
    """Agent-facing tools for workplace coordination."""

    db: WorkplaceOpsDB

    def __init__(self, db: WorkplaceOpsDB) -> None:
        super().__init__(db)

    @staticmethod
    def _search_tokens(value: str) -> set[str]:
        """Normalize free-form search text and enum-like values."""
        tokens = re.findall(r"[a-z0-9]+", value.lower())
        return {
            token[:-1]
            if len(token) > 4
            and token.endswith("s")
            and not token.endswith(("ss", "us", "is"))
            else token
            for token in tokens
        }

    @classmethod
    def _normalized_label(cls, value: str) -> str:
        return "_".join(sorted(cls._search_tokens(value)))

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "Date-times must use ISO 8601 format with a UTC offset"
            ) from exc

    def _validate_interval(self, start: str, end: str) -> tuple[datetime, datetime]:
        start_dt = self._parse_datetime(start)
        end_dt = self._parse_datetime(end)
        if end_dt <= start_dt:
            raise ValueError("Meeting end must be after meeting start")
        return start_dt, end_dt

    def _validate_attendees(self, attendees: list[str]) -> list[str]:
        if len(attendees) != len(set(attendees)):
            raise ValueError("Attendee list contains duplicates")
        known_emails = {employee.email for employee in self.db.employees.values()}
        unknown = sorted(set(attendees) - known_emails)
        if unknown:
            raise ValueError(f"Unknown attendee(s): {unknown}")
        return sorted(attendees)

    def _check_availability(self, attendees: list[str], start: str, end: str) -> None:
        start_dt, end_dt = self._validate_interval(start, end)
        conflicts = []
        for email in attendees:
            for interval in self.db.calendar_busy.get(email, []):
                busy_start = self._parse_datetime(interval.start)
                busy_end = self._parse_datetime(interval.end)
                if start_dt < busy_end and end_dt > busy_start:
                    conflicts.append(email)
                    break
        if conflicts:
            raise ValueError(f"Meeting conflicts with attendee calendars: {conflicts}")

    @is_tool(ToolType.READ)
    def search_documents(self, query: str) -> list[Document]:
        """Search workplace documents by title and document contents.

        Args:
            query: Words describing the project or document to find.

        Returns:
            Every matching document, including status and version metadata.
        """
        terms = {term.lower() for term in query.split() if term.strip()}
        matches = []
        for document in self.db.documents.values():
            haystack = " ".join(
                [
                    document.title,
                    document.status,
                    document.external_pilot,
                    *document.required_functions,
                    *[
                        " ".join(
                            [
                                requirement.title,
                                requirement.owner_function,
                                str(requirement.due_days_before_kickoff),
                            ]
                        )
                        for requirement in document.preparation_requirements
                    ],
                ]
            ).lower()
            if all(term in haystack for term in terms):
                matches.append(document)
        return sorted(matches, key=lambda item: (item.title, item.version))

    @is_tool(ToolType.READ)
    def get_document(self, document_id: str) -> Document:
        """Retrieve a workplace document by its exact ID.

        Args:
            document_id: The document's unique ID.

        Returns:
            The requested document.
        """
        if document_id not in self.db.documents:
            raise ValueError("Document not found")
        return self.db.documents[document_id]

    @is_tool(ToolType.READ)
    def list_employees(self, function: Optional[str] = None) -> list[Employee]:
        """List employees, optionally filtering by business function.

        Args:
            function: Optional function such as Product, Engineering, Design, or Legal.

        Returns:
            Matching employee directory records.
        """
        employees = list(self.db.employees.values())
        if function is not None:
            employees = [
                employee
                for employee in employees
                if employee.function.lower() == function.lower()
            ]
        return sorted(employees, key=lambda item: item.email)

    @is_tool(ToolType.READ)
    def search_project_records(
        self, query: str, record_type: Optional[str] = None
    ) -> list[ProjectRecord]:
        """Search project assignments, delegations, and clearance records.

        Args:
            query: Words expected in the project record.
            record_type: Optional type: assignment, delegation, or clearance.

        Returns:
            Matching records, including status and validity metadata.
        """
        terms = {term.lower() for term in query.split() if term.strip()}
        matches = []
        for record in self.db.project_records.values():
            if record_type is not None and record.record_type != record_type.lower():
                continue
            haystack = " ".join(
                str(value)
                for value in record.model_dump().values()
                if value is not None
            ).lower()
            if all(term in haystack for term in terms):
                matches.append(record)
        return sorted(matches, key=lambda item: item.record_id)

    @is_tool(ToolType.READ)
    def list_project_tasks(
        self, project: str, status: Optional[str] = None
    ) -> list[ProjectTask]:
        """List existing tasks for a project before creating or updating work.

        Args:
            project: Exact project name.
            status: Optional task status, such as open or completed.

        Returns:
            Matching project tasks.
        """
        tasks = [
            task
            for task in self.db.project_tasks.values()
            if task.project is not None and task.project.lower() == project.lower()
        ]
        if status is not None:
            tasks = [task for task in tasks if task.status == status.lower()]
        return sorted(tasks, key=lambda item: item.task_id)

    @is_tool(ToolType.READ)
    def list_project_milestones(self, project: str) -> list[ProjectMilestone]:
        """List existing milestones for a project.

        Args:
            project: Exact project name.

        Returns:
            Matching project milestones.
        """
        milestones = [
            milestone
            for milestone in self.db.project_milestones.values()
            if milestone.project.lower() == project.lower()
        ]
        return sorted(milestones, key=lambda item: item.milestone_id)

    @is_tool(ToolType.READ)
    def get_calendar_availability(
        self, emails: list[str], start: str, end: str
    ) -> dict[str, list[dict[str, str]]]:
        """Return busy intervals for employees within a requested time range.

        Args:
            emails: Employee email addresses whose calendars should be checked.
            start: Beginning of the search range in ISO 8601 format with UTC offset.
            end: End of the search range in ISO 8601 format with UTC offset.

        Returns:
            Busy intervals keyed by employee email. Empty lists mean fully available.
        """
        range_start, range_end = self._validate_interval(start, end)
        known_emails = {employee.email for employee in self.db.employees.values()}
        unknown = sorted(set(emails) - known_emails)
        if unknown:
            raise ValueError(f"Unknown employee email(s): {unknown}")
        result: dict[str, list[dict[str, str]]] = {}
        for email in sorted(set(emails)):
            visible = []
            for interval in self.db.calendar_busy.get(email, []):
                busy_start = self._parse_datetime(interval.start)
                busy_end = self._parse_datetime(interval.end)
                if busy_start < range_end and busy_end > range_start:
                    visible.append(interval.model_dump())
            result[email] = visible
        return result

    @is_tool(ToolType.READ)
    def search_workplace_records(
        self,
        query: str,
        system: Optional[str] = None,
        record_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[WorkplaceRecord]:
        """Search structured records across simulated workplace applications.

        Args:
            query: Words that must appear somewhere in the record.
            system: Optional application name, such as Datadog, Linear, CRM, or AP.
            record_type: Optional category hint used to rank results; semantic
                alternatives do not suppress otherwise relevant matches.
            status: Optional exact record status.
            limit: Number of ranked records to return, from 1 through 10.
            offset: Number of ranked records to skip for pagination.

        Returns:
            One page of matching records with source, status, owner, and fields.
        """
        if limit < 1 or limit > 10:
            raise ValueError("Search limit must be between 1 and 10")
        if offset < 0:
            raise ValueError("Search offset must be non-negative")
        terms = self._search_tokens(query)
        candidates: list[tuple[int, WorkplaceRecord, list[str]]] = []
        for record in self.db.workplace_records.values():
            if system is not None and record.system.lower() != system.lower():
                continue
            type_match = int(
                record_type is not None
                and bool(
                    self._search_tokens(record_type)
                    & self._search_tokens(record.record_type)
                )
            )
            if status is not None and self._normalized_label(
                record.status
            ) != self._normalized_label(status):
                continue
            haystack = " ".join(
                [
                    record.record_id,
                    record.system,
                    record.record_type,
                    record.title,
                    record.status,
                    record.owner or "",
                    json.dumps(record.fields, sort_keys=True),
                ]
            ).lower()
            document_terms = re.findall(r"[a-z0-9]+", haystack.lower())
            normalized_document_terms = [
                token[:-1]
                if len(token) > 4
                and token.endswith("s")
                and not token.endswith(("ss", "us", "is"))
                else token
                for token in document_terms
            ]
            if not terms or terms & set(normalized_document_terms):
                candidates.append((type_match, record, normalized_document_terms))
        if not terms:
            ordered = [
                record
                for _, record, _ in sorted(
                    candidates, key=lambda item: (-item[0], item[1].record_id)
                )
            ]
            return ordered[offset : offset + limit]
        document_frequency = {
            term: sum(term in set(document) for _, _, document in candidates)
            for term in terms
        }
        average_length = sum(len(document) for _, _, document in candidates) / max(
            1, len(candidates)
        )
        ranked: list[tuple[float, WorkplaceRecord]] = []
        k1 = 1.5
        b = 0.75
        for type_match, record, document in candidates:
            counts = Counter(document)
            score = float(type_match)
            for term in terms:
                frequency = counts[term]
                if not frequency:
                    continue
                inverse_document_frequency = math.log(
                    1
                    + (len(candidates) - document_frequency[term] + 0.5)
                    / (document_frequency[term] + 0.5)
                )
                score += inverse_document_frequency * (
                    frequency
                    * (k1 + 1)
                    / (
                        frequency
                        + k1 * (1 - b + b * len(document) / max(1, average_length))
                    )
                )
            ranked.append((score, record))
        ordered = [
            record
            for _, record in sorted(
                ranked, key=lambda item: (-item[0], item[1].record_id)
            )
        ]
        return ordered[offset : offset + limit]

    @is_tool(ToolType.READ)
    def get_workplace_record(self, record_id: str) -> WorkplaceRecord:
        """Retrieve one workplace record by exact ID."""
        if record_id not in self.db.workplace_records:
            raise ValueError("Workplace record not found")
        return self.db.workplace_records[record_id]

    @is_tool(ToolType.WRITE)
    def create_action_proposal(
        self,
        proposal_type: str,
        title: str,
        details: dict[str, Any],
    ) -> ActionProposal:
        """Create or revise a structured plan for requester review.

        A pending proposal with the same type and title is revised in place so a
        corrected attempt does not leave stale approval records.
        """
        rules = [
            rule
            for rule in self.db.action_approval_rules.values()
            if rule.proposal_type == proposal_type
        ]
        if self.db.action_approval_rules and not rules:
            raise ValueError(
                "This proposal type has no approval workflow; use the relevant "
                "family-specific proposal tool"
            )
        if len(rules) == 1:
            title = rules[0].title
        details = self._canonicalize_proposal_details(proposal_type, details)
        matches = [
            proposal
            for proposal in self.db.action_proposals.values()
            if proposal.proposal_type == proposal_type and proposal.title == title
        ]
        if any(proposal.approved_by_user for proposal in matches):
            raise ValueError("An approved action proposal already exists")
        if len(matches) > 1:
            raise ValueError("Multiple pending action proposals already exist")
        if matches:
            matches[0].details = details
            return matches[0]
        proposal_id = action_proposal_id_for_index(len(self.db.action_proposals))
        proposal = ActionProposal(
            proposal_id=proposal_id,
            proposal_type=proposal_type,
            title=title,
            details=details,
        )
        self.db.action_proposals[proposal_id] = proposal
        return proposal

    def _canonicalize_proposal_details(
        self, proposal_type: str, supplied: dict[str, Any]
    ) -> dict[str, Any]:
        """Derive record representation while preserving business decisions."""
        details = dict(supplied)
        records = list(self.db.workplace_records.values())
        if proposal_type == "incident_response":
            rule = self._canonical_rule(proposal_type)
            service = rule.title.removesuffix(" incident response")
            current_signals = [
                record
                for record in records
                if record.system == "Datadog" and record.status == "current"
            ]
            current_policies = [
                record
                for record in records
                if record.system == "Knowledge"
                and record.status == "current"
                and record.title == "Incident severity policy"
            ]
            if not current_signals or len(current_policies) != 1:
                raise ValueError("Current incident evidence or policy is missing")
            unaffected: list[str] = []
            for record in current_signals:
                channel = record.fields.get("scope")
                if (
                    record.fields.get("health") == "healthy"
                    and isinstance(channel, str)
                    and channel != details.get("scope")
                    and channel not in unaffected
                ):
                    unaffected.append(channel)
            details["global_outage"] = details.get("severity") == "SEV-1"
            details["evidence_record_ids"] = [
                record.record_id for record in current_signals
            ] + [current_policies[0].record_id]
            details["external_messages"] = [
                {
                    "system": "StatusPage",
                    "recipient": "public-status-page",
                    "subject": f"{service} service incident",
                    "facts": {
                        "scope": details.get("scope"),
                        "severity": details.get("severity"),
                        "status": "investigating",
                        "unaffected_channels": unaffected,
                    },
                }
            ]
        elif proposal_type == "vendor_invoice_resolution":
            invoices = [record for record in records if record.record_type == "invoice"]
            if len(invoices) != 1:
                return details
            invoice = invoices[0]
            vendor_name = invoice.title.removesuffix(" renewal invoice")
            vendors = [
                record
                for record in records
                if record.system == "VendorMaster" and record.title == vendor_name
            ]
            if len(vendors) != 1:
                return details
            authorized = int(details.get("authorized_amount", 0))
            overage = int(invoice.fields.get("amount", 0)) - authorized
            verified_bank = vendors[0].fields.get("bank_account")
            bank_mismatch = (
                invoice.fields.get("submitted_bank_account") != verified_bank
            )
            issue_type = (
                "overage_and_bank"
                if overage > 0 and bank_mismatch
                else "overage"
                if overage > 0
                else "bank_change"
            )
            external_messages = [
                {
                    "system": "Email",
                    "recipient": vendors[0].fields.get("verified_contact"),
                    "subject": (
                        f"{vendor_name} invoice correction required"
                        if overage > 0
                        else f"{vendor_name} bank verification required"
                    ),
                    "facts": {
                        "authorized_amount": authorized,
                        "remove_fee": max(0, overage),
                        "use_verified_bank_account": verified_bank,
                        "issue_type": issue_type,
                    },
                }
            ]
            details = {
                "resolution": details.get("resolution"),
                "authorized_amount": authorized,
                "invoice_action": "hold",
                "bank_change": details.get("bank_change"),
                "external_messages": external_messages,
            }
        elif proposal_type == "customer_escalation":
            account = self.db.workplace_records.get(
                details.get("account_record_id", "")
            )
            if account is None:
                crm_accounts = [record for record in records if record.system == "CRM"]
                account = crm_accounts[0] if len(crm_accounts) == 1 else None
            if account is None:
                return details
            account_name = account.title.removesuffix(" strategic account")
            support = next(
                (
                    record
                    for record in records
                    if record.system == "Support"
                    and record.status == "current"
                    and account_name.lower() in record.title.lower()
                ),
                None,
            )
            if support is None:
                return details
            details.update(
                {
                    "credit_amount": details.get("credit_amount"),
                    "tone": details.get("tone"),
                    "recipient": account.fields.get("verified_contact"),
                    "restored_on": support.fields.get("restored_on"),
                    "rca_due": support.fields.get("rca_due"),
                    "external_messages": [
                        {
                            "system": "Email",
                            "recipient": account.fields.get("verified_contact"),
                            "subject": f"{account_name} service follow-up",
                            "facts": {
                                "service_status": "restored",
                                "restored_on": support.fields.get("restored_on"),
                                "rca_due": support.fields.get("rca_due"),
                                "service_credit": details.get("credit_amount"),
                                "tone": details.get("tone"),
                            },
                        }
                    ],
                }
            )
            details.pop("account_record_id", None)
        elif proposal_type == "access_plan":
            identity_id = details.get("identity_record_id")
            identity = self.db.workplace_records.get(identity_id or "")
            if identity is None:
                identities = [
                    record
                    for record in records
                    if record.record_type == "identity" and record.status == "current"
                ]
                identity = identities[0] if len(identities) == 1 else None
            if identity is None:
                return details
            identity_id = identity.record_id
            contract = next(
                (
                    record
                    for record in records
                    if record.record_type == "contract"
                    and record.fields.get("identity_record_id") == identity_id
                ),
                None,
            )
            training = next(
                (
                    record
                    for record in records
                    if record.record_type == "security_training"
                    and record.fields.get("identity_record_id") == identity_id
                ),
                None,
            )
            if contract is None or training is None:
                return details
            access_level = details.get("access_level")
            production = isinstance(access_level, str) and access_level.startswith(
                "production"
            )
            details = {
                "identity_record_id": identity_id,
                "access_level": access_level,
                "production_access": production,
                "expires_on": contract.fields.get("end_date"),
                "training_due": training.fields.get("due_date"),
                "training_status": training.status,
                "training_action": (
                    "none" if training.status == "completed" else "assign"
                ),
                "production_request_status": (
                    "not_required" if production else "blocked_pending_training"
                ),
            }
        elif proposal_type == "renewal_batch":
            external_messages = []
            for priority, account_id in enumerate(
                details.get("external_account_ids", []), start=1
            ):
                account = self.db.workplace_records.get(account_id)
                if account is None:
                    continue
                external_messages.append(
                    {
                        "system": "Email",
                        "recipient": account.fields.get("verified_contact"),
                        "subject": f"{account.title} renewal follow-up",
                        "facts": {"account_id": account_id, "priority": priority},
                    }
                )
            details["external_messages"] = external_messages
        return details

    def _canonical_rule(self, proposal_type: str):
        rules = [
            rule
            for rule in self.db.action_approval_rules.values()
            if rule.proposal_type == proposal_type
        ]
        if len(rules) != 1:
            raise ValueError(
                f"Expected exactly one approval rule for {proposal_type!r}; "
                f"found {len(rules)}"
            )
        return rules[0]

    def _store_canonical_proposal(
        self, proposal_type: str, details: dict[str, Any]
    ) -> ActionProposal:
        rule = self._canonical_rule(proposal_type)
        return self.create_action_proposal(
            proposal_type=proposal_type,
            title=rule.title,
            details=details,
        )

    @is_tool(ToolType.WRITE)
    def propose_incident_response(
        self,
        severity: str,
        scope: str,
        global_outage: bool,
        evidence_record_ids: list[str],
        unaffected_channels: list[str],
    ) -> ActionProposal:
        """Create the single canonical incident plan for requester approval.

        The environment owns proposal naming and the status-message record shape;
        the agent supplies the business judgment and its evidence.
        """
        rule = self._canonical_rule("incident_response")
        service = rule.title.removesuffix(" incident response")
        details = {
            "severity": severity,
            "scope": scope,
            "global_outage": global_outage,
            "evidence_record_ids": evidence_record_ids,
            "external_messages": [
                {
                    "system": "StatusPage",
                    "recipient": "public-status-page",
                    "subject": f"{service} service incident",
                    "facts": {
                        "scope": scope,
                        "severity": severity,
                        "status": "investigating",
                        "unaffected_channels": unaffected_channels,
                    },
                }
            ],
        }
        return self._store_canonical_proposal("incident_response", details)

    @is_tool(ToolType.WRITE)
    def propose_vendor_invoice_resolution(
        self,
        invoice_record_id: str,
        resolution: Literal[
            "request_corrected_invoice",
            "verify_bank_details",
        ],
        authorized_amount: int,
        bank_change: bool,
    ) -> ActionProposal:
        """Create one canonical invoice-resolution plan for requester approval.

        Select the structured resolution matching the current control issue. The
        invoice remains on hold under either resolution until the issue is cleared.
        """
        invoice = self.db.workplace_records.get(invoice_record_id)
        if invoice is None or invoice.record_type != "invoice":
            raise ValueError("Invoice record not found")
        vendor_name = invoice.title.removesuffix(" renewal invoice")
        vendors = [
            record
            for record in self.db.workplace_records.values()
            if record.system == "VendorMaster" and record.title == vendor_name
        ]
        if len(vendors) != 1:
            raise ValueError("Verified vendor-master record not found")
        vendor = vendors[0]
        verified_contact = vendor.fields.get("verified_contact")
        verified_bank = vendor.fields.get("bank_account")
        overage = int(invoice.fields.get("amount", 0)) - authorized_amount
        submitted_bank = invoice.fields.get("submitted_bank_account")
        bank_mismatch = submitted_bank != verified_bank
        issue_type = (
            "overage_and_bank"
            if overage > 0 and bank_mismatch
            else "overage"
            if overage > 0
            else "bank_change"
        )
        subject = (
            f"{vendor_name} invoice correction required"
            if overage > 0
            else f"{vendor_name} bank verification required"
        )
        details = {
            "resolution": resolution,
            "authorized_amount": authorized_amount,
            "invoice_action": "hold",
            "bank_change": bank_change,
            "external_messages": [
                {
                    "system": "Email",
                    "recipient": verified_contact,
                    "subject": subject,
                    "facts": {
                        "authorized_amount": authorized_amount,
                        "remove_fee": max(0, overage),
                        "use_verified_bank_account": verified_bank,
                        "issue_type": issue_type,
                    },
                }
            ],
        }
        return self._store_canonical_proposal("vendor_invoice_resolution", details)

    @is_tool(ToolType.WRITE)
    def propose_customer_escalation(
        self,
        account_record_id: str,
        credit_amount: int,
        tone: Literal[
            "concise_accountable",
            "empathetic_direct",
            "factual_accountable",
        ],
    ) -> ActionProposal:
        """Create one canonical customer-recovery plan for requester approval.

        The tone values are stable structured choices. The requester may describe
        one naturally (for example, "factual and accountable"); select the matching
        canonical value exposed by this tool rather than inventing prose.
        """
        account = self.db.workplace_records.get(account_record_id)
        if account is None or account.system != "CRM":
            raise ValueError("CRM account record not found")
        account_name = account.title.removesuffix(" strategic account")
        support_records = [
            record
            for record in self.db.workplace_records.values()
            if record.system == "Support"
            and record.status == "current"
            and account_name.lower() in record.title.lower()
        ]
        if len(support_records) != 1:
            raise ValueError("Current support incident not found")
        support = support_records[0]
        recipient = account.fields.get("verified_contact")
        restored_on = support.fields.get("restored_on")
        rca_due = support.fields.get("rca_due")
        details = {
            "credit_amount": credit_amount,
            "tone": tone,
            "recipient": recipient,
            "restored_on": restored_on,
            "rca_due": rca_due,
            "external_messages": [
                {
                    "system": "Email",
                    "recipient": recipient,
                    "subject": f"{account_name} service follow-up",
                    "facts": {
                        "service_status": "restored",
                        "restored_on": restored_on,
                        "rca_due": rca_due,
                        "service_credit": credit_amount,
                        "tone": tone,
                    },
                }
            ],
        }
        return self._store_canonical_proposal("customer_escalation", details)

    @is_tool(ToolType.WRITE)
    def propose_access_plan(
        self,
        identity_record_id: str,
        access_level: str,
    ) -> ActionProposal:
        """Create one canonical least-privilege access plan for approval.

        The plan makes the training disposition explicit: completed training must
        be preserved, while incomplete training must be assigned during execution.
        """
        identity = self.db.workplace_records.get(identity_record_id)
        if identity is None or identity.record_type != "identity":
            raise ValueError("Identity record not found")
        contracts = [
            record
            for record in self.db.workplace_records.values()
            if record.record_type == "contract"
            and record.fields.get("identity_record_id") == identity_record_id
        ]
        trainings = [
            record
            for record in self.db.workplace_records.values()
            if record.record_type == "security_training"
            and record.fields.get("identity_record_id") == identity_record_id
        ]
        if len(contracts) != 1 or len(trainings) != 1:
            raise ValueError("Contract or security-training record not found")
        training = trainings[0]
        production_access = access_level.startswith("production")
        details = {
            "identity_record_id": identity_record_id,
            "access_level": access_level,
            "production_access": production_access,
            "expires_on": contracts[0].fields.get("end_date"),
            "training_due": training.fields.get("due_date"),
            "training_status": training.status,
            "training_action": ("none" if training.status == "completed" else "assign"),
            "production_request_status": (
                "not_required" if production_access else "blocked_pending_training"
            ),
        }
        return self._store_canonical_proposal("access_plan", details)

    @is_tool(ToolType.WRITE)
    def propose_renewal_batch(
        self,
        priority_rule: Literal["critical_support_then_arr"],
        arr_threshold: int,
        legal_hold_action: Literal["internal_only"],
        external_account_ids: list[str],
        internal_only_account_ids: list[str],
        excluded_account_ids: list[str],
        owner_updates: dict[str, str],
    ) -> ActionProposal:
        """Create one complete, canonical renewal batch for approval.

        The structured priority and Legal-hold choices are exposed explicitly so
        natural user wording maps to stable proposal values. Legal-hold accounts
        belong in ``internal_only_account_ids`` regardless of the ARR threshold.
        """
        batch_ids = [
            *external_account_ids,
            *internal_only_account_ids,
            *excluded_account_ids,
        ]
        if len(batch_ids) != len(set(batch_ids)):
            raise ValueError("An account may appear in only one renewal-batch list")
        unknown_owner_ids = sorted(set(owner_updates) - set(batch_ids))
        if unknown_owner_ids:
            raise ValueError(
                "Owner updates must target accounts in this renewal batch: "
                f"{unknown_owner_ids}"
            )
        for account_id, owner in owner_updates.items():
            account = self.db.workplace_records.get(account_id)
            if account is None or account.system != "CRM":
                raise ValueError(f"CRM account not found: {account_id}")
            if account.owner is not None:
                raise ValueError(f"Account already has an owner: {account_id}")
            if not owner.strip():
                raise ValueError(f"Owner must be non-empty for: {account_id}")
        unowned_ids = sorted(
            account_id
            for account_id in batch_ids
            if (
                (account := self.db.workplace_records.get(account_id)) is not None
                and account.system == "CRM"
                and account.owner is None
            )
        )
        missing_owner_ids = sorted(set(unowned_ids) - set(owner_updates))
        if missing_owner_ids:
            raise ValueError(
                "The proposal needs a requester-selected owner for each unowned "
                f"account: {missing_owner_ids}"
            )
        external_messages = []
        for priority, account_id in enumerate(external_account_ids, start=1):
            account = self.db.workplace_records.get(account_id)
            if account is None or account.system != "CRM":
                raise ValueError(f"CRM account not found: {account_id}")
            external_messages.append(
                {
                    "system": "Email",
                    "recipient": account.fields.get("verified_contact"),
                    "subject": f"{account.title} renewal follow-up",
                    "facts": {"account_id": account_id, "priority": priority},
                }
            )
        details = {
            "priority_rule": priority_rule,
            "arr_threshold": arr_threshold,
            "legal_hold_action": legal_hold_action,
            "external_account_ids": external_account_ids,
            # These sets have no business ordering. Canonicalize them so an
            # equivalent proposal does not fail exact end-state comparison.
            "internal_only_account_ids": sorted(internal_only_account_ids),
            "excluded_account_ids": sorted(excluded_account_ids),
            "owner_updates": dict(sorted(owner_updates.items())),
            "external_messages": external_messages,
        }
        return self._store_canonical_proposal("renewal_batch", details)

    def _approved_proposal(
        self, proposal_id: str, proposal_type: str
    ) -> ActionProposal:
        proposal = self.db.action_proposals.get(proposal_id)
        if proposal is None or proposal.proposal_type != proposal_type:
            raise ValueError(f"Approved {proposal_type} proposal not found")
        if not proposal.approved_by_user:
            raise ValueError("Action proposal has not been approved by the user")
        return proposal

    def _create_canonical_record(
        self,
        *,
        system: str,
        record_type: str,
        title: str,
        status: str,
        owner: Optional[str],
        fields: dict[str, Any],
        record_id: Optional[str] = None,
    ) -> WorkplaceRecord:
        record_id = record_id or generated_record_id_for_index(
            len(self.db.workplace_records)
        )
        if record_id in self.db.workplace_records:
            raise ValueError(f"Workplace record already exists: {record_id}")
        record = WorkplaceRecord(
            record_id=record_id,
            system=system,
            record_type=record_type,
            title=title,
            status=status,
            updated_at="2026-11-08T09:00:00-08:00",
            owner=owner,
            fields=fields,
        )
        self.db.workplace_records[record_id] = record
        return record

    @is_tool(ToolType.WRITE)
    def apply_incident_plan(
        self, proposal_id: str, incident_record_id: str
    ) -> WorkplaceRecord:
        """Apply an approved incident plan to the existing incident record."""
        proposal = self._approved_proposal(proposal_id, "incident_response")
        incident = self.db.workplace_records.get(incident_record_id)
        if incident is None or incident.record_type != "incident":
            raise ValueError("Incident record not found")
        service = incident.title.removesuffix(" incident")
        schedules = [
            record
            for record in self.db.workplace_records.values()
            if record.record_type == "on_call_schedule"
            and record.status == "current"
            and record.title == f"{service} on-call"
        ]
        if len(schedules) != 1:
            raise ValueError("Current incident on-call schedule not found")
        evidence_ids = proposal.details.get("evidence_record_ids", [])
        source_signal_ids = [
            record_id
            for record_id in evidence_ids
            if record_id in self.db.workplace_records
            and self.db.workplace_records[record_id].system == "Datadog"
        ]
        incident.status = "investigating"
        incident.owner = schedules[0].fields.get("current_on_call")
        incident.fields.update(
            {
                "severity": proposal.details.get("severity"),
                "scope": proposal.details.get("scope"),
                "source_signal_ids": source_signal_ids,
                "response_proposal_id": proposal_id,
            }
        )
        incident.updated_at = "2026-11-08T09:00:00-08:00"
        return incident

    @is_tool(ToolType.WRITE)
    def create_incident_rca(
        self, proposal_id: str, incident_record_id: str
    ) -> WorkplaceRecord:
        """Create the canonical RCA task for an approved incident plan."""
        self._approved_proposal(proposal_id, "incident_response")
        incident = self.db.workplace_records.get(incident_record_id)
        if incident is None or incident.record_type != "incident":
            raise ValueError("Incident record not found")
        policies = [
            record
            for record in self.db.workplace_records.values()
            if record.system == "Knowledge"
            and record.status == "current"
            and record.title == "Incident severity policy"
        ]
        if len(policies) != 1:
            raise ValueError("Current incident policy not found")
        service = incident.title.removesuffix(" incident")
        return self._create_canonical_record(
            system="Linear",
            record_type="task",
            title=f"RCA: {service} incident",
            status="open",
            owner=policies[0].fields.get("rca_owner"),
            fields={
                "due_date": policies[0].fields.get("rca_due_date"),
                "incident_record_id": incident_record_id,
            },
        )

    @is_tool(ToolType.WRITE)
    def apply_invoice_hold(
        self, proposal_id: str, invoice_record_id: str
    ) -> WorkplaceRecord:
        """Apply the approved control hold to an existing invoice."""
        proposal = self._approved_proposal(proposal_id, "vendor_invoice_resolution")
        invoice = self.db.workplace_records.get(invoice_record_id)
        if invoice is None or invoice.record_type != "invoice":
            raise ValueError("Invoice record not found")
        vendor_name = invoice.title.removesuffix(" renewal invoice")
        vendor = next(
            (
                record
                for record in self.db.workplace_records.values()
                if record.system == "VendorMaster" and record.title == vendor_name
            ),
            None,
        )
        if vendor is None:
            raise ValueError("Verified vendor-master record not found")
        authorized = int(proposal.details.get("authorized_amount", 0))
        overage = int(invoice.fields.get("amount", 0)) - authorized
        bank_mismatch = invoice.fields.get(
            "submitted_bank_account"
        ) != vendor.fields.get("bank_account")
        issue_type = (
            "overage_and_bank"
            if overage > 0 and bank_mismatch
            else "overage"
            if overage > 0
            else "bank_change"
        )
        invoice.status = "on_hold"
        invoice.fields.update(
            {
                "hold_reason": issue_type,
                "authorized_amount": authorized,
                "bank_change_rejected": bank_mismatch,
                "resolution_proposal_id": proposal_id,
            }
        )
        invoice.updated_at = "2026-11-08T09:00:00-08:00"
        return invoice

    @is_tool(ToolType.WRITE)
    def create_invoice_exception(
        self, proposal_id: str, invoice_record_id: str
    ) -> WorkplaceRecord:
        """Create the canonical Finance exception from an approved invoice plan."""
        proposal = self._approved_proposal(proposal_id, "vendor_invoice_resolution")
        invoice = self.db.workplace_records.get(invoice_record_id)
        if invoice is None or invoice.record_type != "invoice":
            raise ValueError("Invoice record not found")
        vendor_name = invoice.title.removesuffix(" renewal invoice")
        authorized = int(proposal.details.get("authorized_amount", 0))
        return self._create_canonical_record(
            system="Finance",
            record_type="invoice_exception",
            title=f"{vendor_name} invoice control exception",
            status="open",
            owner="finance-ops@atlas.example",
            fields={
                "invoice_record_id": invoice_record_id,
                "disputed_amount": max(
                    0, int(invoice.fields.get("amount", 0)) - authorized
                ),
                "bank_verification_required": bool(
                    invoice.fields.get("bank_change_rejected")
                ),
                "resolution": proposal.details.get("resolution"),
            },
        )

    @is_tool(ToolType.WRITE)
    def apply_customer_recovery_plan(
        self, proposal_id: str, account_record_id: str
    ) -> WorkplaceRecord:
        """Record an approved customer-recovery plan in CRM."""
        proposal = self._approved_proposal(proposal_id, "customer_escalation")
        account = self.db.workplace_records.get(account_record_id)
        if account is None or account.system != "CRM":
            raise ValueError("CRM account record not found")
        account.status = "escalation_active"
        account.fields.update(
            {
                "credit_recorded": proposal.details.get("credit_amount"),
                "escalation_status": "customer_updated",
                "customer_plan_id": proposal_id,
            }
        )
        account.updated_at = "2026-11-08T09:00:00-08:00"
        return account

    @is_tool(ToolType.WRITE)
    def create_customer_rca(
        self, proposal_id: str, account_record_id: str
    ) -> WorkplaceRecord:
        """Create the canonical RCA follow-up for an approved customer plan."""
        proposal = self._approved_proposal(proposal_id, "customer_escalation")
        account = self.db.workplace_records.get(account_record_id)
        if account is None or account.system != "CRM":
            raise ValueError("CRM account record not found")
        account_name = account.title.removesuffix(" strategic account")
        support = next(
            (
                record
                for record in self.db.workplace_records.values()
                if record.system == "Support"
                and record.status == "current"
                and account_name.lower() in record.title.lower()
            ),
            None,
        )
        if support is None:
            raise ValueError("Current support incident not found")
        return self._create_canonical_record(
            system="Linear",
            record_type="task",
            title=f"Deliver {account_name} incident RCA",
            status="open",
            owner="reliability@atlas.example",
            fields={
                "due_date": proposal.details.get("rca_due"),
                "incident_record_id": support.record_id,
                "account_record_id": account_record_id,
            },
        )

    @is_tool(ToolType.WRITE)
    def assign_required_training(
        self, proposal_id: str, training_record_id: str
    ) -> WorkplaceRecord:
        """Assign required training recorded in an approved access plan."""
        proposal = self._approved_proposal(proposal_id, "access_plan")
        if proposal.details.get("training_action") != "assign":
            raise ValueError("The approved access plan does not require assignment")
        training = self.db.workplace_records.get(training_record_id)
        if training is None or training.record_type != "security_training":
            raise ValueError("Security training record not found")
        if training.status == "completed":
            raise ValueError("Completed security training must remain unchanged")
        training.status = "assigned"
        training.fields.update(
            {
                "due_date": proposal.details.get("training_due"),
                "assigned_by_plan": proposal_id,
            }
        )
        training.updated_at = "2026-11-08T09:00:00-08:00"
        return training

    @is_tool(ToolType.WRITE)
    def create_blocked_production_request(
        self, proposal_id: str, identity_record_id: str
    ) -> WorkplaceRecord:
        """Create the canonical blocked production request after staging access."""
        self._approved_proposal(proposal_id, "access_plan")
        identity = self.db.workplace_records.get(identity_record_id)
        if identity is None or identity.record_type != "identity":
            raise ValueError("Identity record not found")
        training = next(
            (
                record
                for record in self.db.workplace_records.values()
                if record.record_type == "security_training"
                and record.fields.get("identity_record_id") == identity_record_id
            ),
            None,
        )
        if training is None:
            raise ValueError("Security training record not found")
        worker = identity.title.removesuffix(" contractor identity")
        return self._create_canonical_record(
            system="AccessRequests",
            record_type="production_access_request",
            title=f"{worker} production access after training",
            status="blocked",
            owner=identity.fields.get("manager"),
            fields={
                "identity_record_id": identity_record_id,
                "blocked_on": training.record_id,
                "requested_level": "production_standard",
            },
        )

    @is_tool(ToolType.WRITE)
    def apply_renewal_account_decision(
        self, proposal_id: str, account_record_id: str
    ) -> WorkplaceRecord:
        """Apply the approved batch decision for one CRM renewal account."""
        proposal = self._approved_proposal(proposal_id, "renewal_batch")
        account = self.db.workplace_records.get(account_record_id)
        if account is None or account.system != "CRM":
            raise ValueError("CRM account record not found")
        details = proposal.details
        external_ids = details.get("external_account_ids", [])
        internal_ids = details.get("internal_only_account_ids", [])
        excluded_ids = details.get("excluded_account_ids", [])
        owner_updates = details.get("owner_updates", {})
        if account.owner is None:
            owner = owner_updates.get(account_record_id)
            if not owner:
                raise ValueError(
                    "Approved renewal batch has no owner for this unowned account"
                )
            account.owner = owner
        if account_record_id in external_ids:
            account.status = "follow_up_active"
            account.fields.update(
                {
                    "priority": external_ids.index(account_record_id) + 1,
                    "batch_proposal_id": proposal_id,
                }
            )
        elif account_record_id in internal_ids:
            account.status = "legal_hold_internal"
            account.fields.update(
                {
                    "external_contact_allowed": False,
                    "batch_proposal_id": proposal_id,
                }
            )
        elif account_record_id in excluded_ids:
            billing = next(
                (
                    record
                    for record in self.db.workplace_records.values()
                    if record.system == "Billing"
                    and record.fields.get("account_id") == account_record_id
                ),
                None,
            )
            if billing is None or billing.status != "renewed":
                raise ValueError("Excluded account has no completed Billing renewal")
            account.status = "renewed"
            account.fields.update(
                {
                    "renewed_through": billing.fields.get("renewed_through"),
                    "crm_stage_corrected_from_billing": True,
                }
            )
        else:
            raise ValueError("Account is absent from the approved renewal batch")
        account.updated_at = "2026-11-08T09:00:00-08:00"
        return account

    @is_tool(ToolType.WRITE)
    def create_renewal_follow_up(
        self, proposal_id: str, account_record_id: str
    ) -> WorkplaceRecord:
        """Create the canonical follow-up for an included renewal account."""
        proposal = self._approved_proposal(proposal_id, "renewal_batch")
        account = self.db.workplace_records.get(account_record_id)
        if account is None or account.system != "CRM":
            raise ValueError("CRM account record not found")
        external_ids = proposal.details.get("external_account_ids", [])
        internal_ids = proposal.details.get("internal_only_account_ids", [])
        if account_record_id not in external_ids + internal_ids:
            raise ValueError("Account does not require a renewal follow-up")
        child_ids = [
            record.record_id
            for record in self.db.workplace_records.values()
            if record.system == "CRM"
            and record.fields.get("renewal_parent_id") == account_record_id
        ]
        fields: dict[str, Any] = {
            "account_id": account_record_id,
            "external_contact": account_record_id in external_ids,
        }
        if child_ids:
            fields["covers_child_account_ids"] = child_ids
        return self._create_canonical_record(
            system="Linear",
            record_type="renewal_follow_up",
            title=f"{account.title} renewal follow-up",
            status="open",
            owner=account.owner,
            fields=fields,
            record_id=renewal_follow_up_record_id(account_record_id),
        )

    @is_tool(ToolType.WRITE)
    def update_workplace_record(
        self,
        record_id: str,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        field_updates: Optional[dict[str, Any]] = None,
    ) -> WorkplaceRecord:
        """Update a known record in its source application."""
        if record_id not in self.db.workplace_records:
            raise ValueError("Workplace record not found")
        if status is None and owner is None and not field_updates:
            raise ValueError("At least one workplace-record field must be updated")
        record = self.db.workplace_records[record_id]
        if status is not None:
            record.status = status
        if owner is not None:
            record.owner = owner
        if field_updates:
            record.fields.update(field_updates)
        record.updated_at = "2026-11-08T09:00:00-08:00"
        return record

    @is_tool(ToolType.WRITE)
    def create_workplace_record(
        self,
        system: str,
        record_type: str,
        title: str,
        status: str,
        owner: Optional[str] = None,
        fields: Optional[dict[str, Any]] = None,
    ) -> WorkplaceRecord:
        """Create a new structured record with an environment-generated ID."""
        record_id = generated_record_id_for_index(len(self.db.workplace_records))
        record = WorkplaceRecord(
            record_id=record_id,
            system=system,
            record_type=record_type,
            title=title,
            status=status,
            updated_at="2026-11-08T09:00:00-08:00",
            owner=owner,
            fields=fields or {},
        )
        self.db.workplace_records[record_id] = record
        return record

    @is_tool(ToolType.WRITE)
    def send_approved_external_messages(
        self, proposal_id: str
    ) -> list[ExternalMessage]:
        """Send structured external messages contained in an approved proposal."""
        proposal = self.db.action_proposals.get(proposal_id)
        if proposal is None:
            raise ValueError("Action proposal not found")
        if not proposal.approved_by_user:
            raise ValueError("Action proposal has not been approved by the user")
        if any(
            message.source_proposal_id == proposal_id
            for message in self.db.external_messages
        ):
            raise ValueError("External messages for this proposal were already sent")
        message_specs = proposal.details.get("external_messages")
        if not isinstance(message_specs, list) or not message_specs:
            raise ValueError("Proposal contains no external messages")
        messages = []
        for spec in message_specs:
            if not isinstance(spec, dict):
                raise ValueError("External message specification must be an object")
            required = {"system", "recipient", "subject", "facts"}
            if set(spec) != required:
                raise ValueError(
                    "External message requires system, recipient, subject, and facts"
                )
            message = ExternalMessage(
                message_id=external_message_id_for_index(
                    len(self.db.external_messages)
                ),
                system=spec["system"],
                recipient=spec["recipient"],
                subject=spec["subject"],
                facts=spec["facts"],
                source_proposal_id=proposal_id,
            )
            self.db.external_messages.append(message)
            messages.append(message)
        return messages

    @is_tool(ToolType.WRITE)
    def post_internal_update(
        self, channel: str, related_record_ids: list[str]
    ) -> InternalUpdate:
        """Post a canonical internal update linked to the completed records.

        The environment derives the topic from the referenced record titles so
        models are not graded on arbitrary wording choices.
        """
        if not related_record_ids:
            raise ValueError("At least one related record is required")
        if len(related_record_ids) != len(set(related_record_ids)):
            raise ValueError("Related record list contains duplicates")
        missing = sorted(set(related_record_ids) - set(self.db.workplace_records))
        if missing:
            raise ValueError(f"Related workplace record(s) not found: {missing}")
        sorted_record_ids = sorted(related_record_ids)
        topic = " | ".join(
            self.db.workplace_records[record_id].title
            for record_id in sorted_record_ids
        )
        update = InternalUpdate(
            update_id=internal_update_id_for_index(len(self.db.internal_updates)),
            channel=channel,
            topic=topic,
            related_record_ids=sorted_record_ids,
        )
        self.db.internal_updates.append(update)
        return update

    @is_tool(ToolType.WRITE)
    def post_approved_workflow_update(self, proposal_id: str) -> InternalUpdate:
        """Verify an approved workflow is complete and post its canonical update.

        The environment derives the internal channel and exact record links. This
        call fails when any required downstream record is still missing, so it is
        also the agent's final cross-system verification step.
        """
        proposal = self.db.action_proposals.get(proposal_id)
        if proposal is None or not proposal.approved_by_user:
            raise ValueError("An approved action proposal is required")
        records = list(self.db.workplace_records.values())
        related: list[str]
        if proposal.proposal_type == "incident_response":
            incidents = [
                record
                for record in records
                if record.record_type == "incident"
                and record.fields.get("response_proposal_id") == proposal_id
            ]
            if len(incidents) != 1:
                raise ValueError("Completed incident update not found")
            rcas = [
                record
                for record in records
                if record.record_type == "task"
                and record.fields.get("incident_record_id") == incidents[0].record_id
                and record.title.startswith("RCA:")
            ]
            if len(rcas) != 1:
                raise ValueError("Completed incident RCA not found")
            if not any(
                page.incident_record_id == incidents[0].record_id
                for page in self.db.on_call_pages
            ):
                raise ValueError("Current responder has not been paged")
            channel = "inc-" + re.sub(
                r"[^a-z0-9]+",
                "-",
                incidents[0].title.removesuffix(" incident").lower(),
            ).strip("-")
            related = [incidents[0].record_id, rcas[0].record_id]
        elif proposal.proposal_type == "vendor_invoice_resolution":
            invoices = [
                record
                for record in records
                if record.record_type == "invoice"
                and record.fields.get("resolution_proposal_id") == proposal_id
            ]
            if len(invoices) != 1:
                raise ValueError("Completed invoice hold not found")
            exceptions = [
                record
                for record in records
                if record.record_type == "invoice_exception"
                and record.fields.get("invoice_record_id") == invoices[0].record_id
            ]
            if len(exceptions) != 1:
                raise ValueError("Completed Finance exception not found")
            channel = "finance-ops"
            related = [invoices[0].record_id, exceptions[0].record_id]
        elif proposal.proposal_type == "customer_escalation":
            accounts = [
                record
                for record in records
                if record.system == "CRM"
                and record.fields.get("customer_plan_id") == proposal_id
            ]
            if len(accounts) != 1:
                raise ValueError("Completed CRM escalation update not found")
            rcas = [
                record
                for record in records
                if record.record_type == "task"
                and record.fields.get("account_record_id") == accounts[0].record_id
            ]
            if len(rcas) != 1:
                raise ValueError("Completed customer RCA not found")
            channel = "customer-escalations"
            related = [accounts[0].record_id, rcas[0].record_id]
        elif proposal.proposal_type == "access_plan":
            grants = [
                grant
                for grant in self.db.access_grants
                if grant.source_proposal_id == proposal_id
            ]
            if len(grants) != 1:
                raise ValueError("Completed access grant not found")
            identity_id = grants[0].identity_record_id
            trainings = [
                record
                for record in records
                if record.record_type == "security_training"
                and record.fields.get("identity_record_id") == identity_id
            ]
            if len(trainings) != 1:
                raise ValueError("Security training record not found")
            related = [identity_id, trainings[0].record_id]
            if proposal.details.get("production_access"):
                if (
                    proposal.details.get("training_action") != "none"
                    or trainings[0].status != "completed"
                    or "assigned_by_plan" in trainings[0].fields
                ):
                    raise ValueError(
                        "Production access requires completed training to remain unchanged"
                    )
            else:
                blocked = [
                    record
                    for record in records
                    if record.record_type == "production_access_request"
                    and record.fields.get("identity_record_id") == identity_id
                    and record.status == "blocked"
                ]
                if (
                    proposal.details.get("training_action") != "assign"
                    or trainings[0].status != "assigned"
                    or len(blocked) != 1
                ):
                    raise ValueError(
                        "Assigned training and blocked production request are required"
                    )
                related.append(blocked[0].record_id)
            channel = "reliability-managers"
        elif proposal.proposal_type == "renewal_batch":
            external_ids = proposal.details.get("external_account_ids", [])
            internal_ids = proposal.details.get("internal_only_account_ids", [])
            included_ids = [*external_ids, *internal_ids]
            renewed_ids = [
                record_id
                for record_id in proposal.details.get("excluded_account_ids", [])
                if record_id in self.db.workplace_records
                and self.db.workplace_records[record_id].status == "renewed"
            ]
            decisions_complete = all(
                self.db.workplace_records[record_id].status == "follow_up_active"
                for record_id in external_ids
            ) and all(
                self.db.workplace_records[record_id].status == "legal_hold_internal"
                for record_id in internal_ids
            )
            if not decisions_complete or len(renewed_ids) != 1:
                raise ValueError(
                    "Before finalizing, call apply_renewal_account_decision for "
                    "every approved external and internal account, plus the excluded "
                    "account whose completed renewal is confirmed in Billing"
                )
            follow_ups = [
                record
                for record in records
                if record.record_type == "renewal_follow_up"
                and record.fields.get("account_id") in included_ids
            ]
            if len(follow_ups) != len(included_ids):
                raise ValueError("A follow-up is required for every included account")
            required_accounts = included_ids + renewed_ids
            if any(
                self.db.workplace_records[record_id].updated_at
                != "2026-11-08T09:00:00-08:00"
                for record_id in required_accounts
            ):
                raise ValueError("Every included renewal account must be updated")
            channel = "revenue-ops"
            related = required_accounts + [record.record_id for record in follow_ups]
        else:
            raise ValueError("This proposal type has no canonical workflow update")
        if not any(
            message.source_proposal_id == proposal_id
            for message in self.db.external_messages
        ) and proposal.details.get("external_messages"):
            raise ValueError("Approved external messages have not been sent")
        return self.post_internal_update(channel=channel, related_record_ids=related)

    @is_tool(ToolType.WRITE)
    def page_current_on_call(
        self, schedule_record_id: str, incident_record_id: str
    ) -> OnCallPage:
        """Page the responder named by a current on-call schedule record."""
        schedule = self.db.workplace_records.get(schedule_record_id)
        incident = self.db.workplace_records.get(incident_record_id)
        if schedule is None or schedule.record_type != "on_call_schedule":
            raise ValueError("On-call schedule record not found")
        if schedule.status != "current":
            raise ValueError("Only a current on-call schedule may be used")
        if incident is None or incident.record_type != "incident":
            raise ValueError("Incident record not found")
        target = schedule.fields.get("current_on_call")
        if not isinstance(target, str) or not target:
            raise ValueError("On-call schedule has no current responder")
        page = OnCallPage(
            page_id=page_id_for_index(len(self.db.on_call_pages)),
            schedule_record_id=schedule_record_id,
            incident_record_id=incident_record_id,
            target=target,
        )
        self.db.on_call_pages.append(page)
        return page

    @is_tool(ToolType.WRITE)
    def provision_approved_access(
        self,
        proposal_id: str,
        identity_record_id: str,
        access_level: str,
        expires_on: str,
    ) -> AccessGrant:
        """Provision an approved access bundle while enforcing training gates."""
        proposal = self.db.action_proposals.get(proposal_id)
        identity = self.db.workplace_records.get(identity_record_id)
        if proposal is None or not proposal.approved_by_user:
            raise ValueError("An approved action proposal is required")
        if identity is None or identity.record_type != "identity":
            raise ValueError("Identity record not found")
        if proposal.details.get("access_level") != access_level:
            raise ValueError("Access level does not match the approved proposal")
        try:
            datetime.strptime(expires_on, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Access expiration must use YYYY-MM-DD format") from exc
        if access_level.startswith("production"):
            incomplete_training = any(
                record.record_type == "security_training"
                and record.fields.get("identity_record_id") == identity_record_id
                and record.status != "completed"
                for record in self.db.workplace_records.values()
            )
            if incomplete_training:
                raise ValueError(
                    "Production access cannot be granted before training completion"
                )
        grant = AccessGrant(
            grant_id=access_grant_id_for_index(len(self.db.access_grants)),
            identity_record_id=identity_record_id,
            access_level=access_level,
            expires_on=expires_on,
            source_proposal_id=proposal_id,
        )
        self.db.access_grants.append(grant)
        return grant

    @is_tool(ToolType.WRITE)
    def create_meeting_proposal(
        self,
        title: str,
        start: str,
        end: str,
        attendees: list[str],
    ) -> MeetingProposal:
        """Create or revise a pending meeting proposal for the user to review.

        This does not schedule a calendar event. The user must approve this exact
        proposal before it can be scheduled. If an unapproved proposal with the same
        title already exists, this call revises that draft instead of leaving a stale
        proposal behind.

        Args:
            title: Proposed meeting title.
            start: Proposed start in ISO 8601 format with UTC offset.
            end: Proposed end in ISO 8601 format with UTC offset.
            attendees: Exact employee email addresses to invite.

        Returns:
            The stored proposal.
        """
        normalized_attendees = self._validate_attendees(attendees)
        self._check_availability(normalized_attendees, start, end)
        proposals_for_title = [
            proposal
            for proposal in self.db.meeting_proposals.values()
            if proposal.title == title
        ]
        if any(proposal.approved_by_user for proposal in proposals_for_title):
            raise ValueError("An approved proposal with this title already exists")
        if len(proposals_for_title) > 1:
            raise ValueError("Multiple pending proposals with this title exist")
        if proposals_for_title:
            proposal = proposals_for_title[0]
            proposal.start = start
            proposal.end = end
            proposal.attendees = normalized_attendees
            return proposal
        proposal_id = proposal_id_for_index(len(self.db.meeting_proposals))
        proposal = MeetingProposal(
            proposal_id=proposal_id,
            title=title,
            start=start,
            end=end,
            attendees=normalized_attendees,
        )
        self.db.meeting_proposals[proposal_id] = proposal
        return proposal

    @is_tool(ToolType.WRITE)
    def schedule_approved_meeting(self, proposal_id: str) -> CalendarEvent:
        """Schedule a meeting from an already user-approved proposal.

        Args:
            proposal_id: The exact approved proposal to schedule.

        Returns:
            The newly created calendar event.
        """
        if proposal_id not in self.db.meeting_proposals:
            raise ValueError("Meeting proposal not found")
        proposal = self.db.meeting_proposals[proposal_id]
        if not proposal.approved_by_user:
            raise ValueError("Meeting proposal has not been approved by the user")
        event_id = event_id_for_proposal(proposal_id)
        if event_id in self.db.calendar_events:
            raise ValueError("Meeting proposal has already been scheduled")
        event = CalendarEvent(
            event_id=event_id,
            title=proposal.title,
            start=proposal.start,
            end=proposal.end,
            attendees=proposal.attendees,
            source_proposal_id=proposal.proposal_id,
        )
        self.db.calendar_events[event_id] = event
        return event

    @is_tool(ToolType.WRITE)
    def create_project_task(
        self,
        title: str,
        assignee: str,
        due_date: str,
        project: Optional[str] = None,
    ) -> ProjectTask:
        """Create an internal project preparation task.

        Args:
            title: Task title.
            assignee: Employee email responsible for the task.
            due_date: Due date in YYYY-MM-DD format.
            project: Optional project name used to group related work.

        Returns:
            The newly created project task.
        """
        known_emails = {employee.email for employee in self.db.employees.values()}
        if assignee not in known_emails:
            raise ValueError("Task assignee is not in the employee directory")
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Task due date must use YYYY-MM-DD format") from exc
        task_id = task_id_for_index(len(self.db.project_tasks))
        task = ProjectTask(
            task_id=task_id,
            title=title,
            assignee=assignee,
            due_date=due_date,
            project=project,
        )
        self.db.project_tasks[task_id] = task
        return task

    @is_tool(ToolType.WRITE)
    def update_project_task(
        self,
        task_id: str,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> ProjectTask:
        """Update an existing project task without creating a duplicate.

        Args:
            task_id: Existing task identifier returned by list_project_tasks.
            assignee: Optional replacement employee email.
            due_date: Optional replacement due date in YYYY-MM-DD format.
            status: Optional replacement status: open or completed.

        Returns:
            The updated project task.
        """
        if task_id not in self.db.project_tasks:
            raise ValueError("Project task not found")
        if assignee is None and due_date is None and status is None:
            raise ValueError("At least one project task field must be updated")
        task = self.db.project_tasks[task_id]
        if assignee is not None:
            known_emails = {employee.email for employee in self.db.employees.values()}
            if assignee not in known_emails:
                raise ValueError("Task assignee is not in the employee directory")
            task.assignee = assignee
        if due_date is not None:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("Task due date must use YYYY-MM-DD format") from exc
            task.due_date = due_date
        if status is not None:
            if status not in {"open", "completed"}:
                raise ValueError("Task status must be open or completed")
            task.status = status
        return task

    @is_tool(ToolType.WRITE)
    def update_project_milestone(
        self,
        milestone_id: str,
        status: str,
        kickoff_date: str,
        meeting_event_id: str,
    ) -> ProjectMilestone:
        """Update an existing project milestone after scheduling its kickoff.

        Args:
            milestone_id: Existing identifier returned by list_project_milestones.
            status: New milestone status: planning, scheduled, or completed.
            kickoff_date: Scheduled kickoff date in YYYY-MM-DD format.
            meeting_event_id: Calendar event associated with the milestone.

        Returns:
            The updated milestone.
        """
        if milestone_id not in self.db.project_milestones:
            raise ValueError("Project milestone not found")
        if status not in {"planning", "scheduled", "completed"}:
            raise ValueError("Invalid milestone status")
        try:
            datetime.strptime(kickoff_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Kickoff date must use YYYY-MM-DD format") from exc
        if meeting_event_id not in self.db.calendar_events:
            raise ValueError("Calendar event not found")
        milestone = self.db.project_milestones[milestone_id]
        milestone.status = status
        milestone.kickoff_date = kickoff_date
        milestone.meeting_event_id = meeting_event_id
        return milestone

    @is_tool(ToolType.WRITE)
    def post_project_update(
        self,
        channel: str,
        project: str,
        meeting_event_id: str,
        preparation_task_id: Optional[str] = None,
        preparation_task_ids: Optional[list[str]] = None,
        milestone_id: Optional[str] = None,
    ) -> ChatMessage:
        """Post a canonical internal update from scheduled work records.

        Args:
            channel: Internal chat channel without a leading '#'.
            project: Project name used in the update.
            meeting_event_id: Scheduled calendar event to report.
            preparation_task_id: One preparation task to report (legacy form).
            preparation_task_ids: Preparation tasks to report together.
            milestone_id: Optional project milestone to report.

        Returns:
            The posted internal chat message.
        """
        if meeting_event_id not in self.db.calendar_events:
            raise ValueError("Calendar event not found")
        if preparation_task_id is not None and preparation_task_ids is not None:
            raise ValueError("Use one preparation-task argument form, not both")
        task_ids = (
            [preparation_task_id]
            if preparation_task_id is not None
            else list(preparation_task_ids or [])
        )
        if not task_ids:
            raise ValueError("At least one preparation task is required")
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Preparation task list contains duplicates")
        missing_tasks = [
            task_id for task_id in task_ids if task_id not in self.db.project_tasks
        ]
        if missing_tasks:
            raise ValueError(f"Preparation task(s) not found: {missing_tasks}")
        if milestone_id is not None and milestone_id not in self.db.project_milestones:
            raise ValueError("Project milestone not found")
        event = self.db.calendar_events[meeting_event_id]
        tasks = [self.db.project_tasks[task_id] for task_id in task_ids]
        content_parts = [f"{project} kickoff is scheduled for {event.start}."]
        if milestone_id is not None:
            milestone = self.db.project_milestones[milestone_id]
            content_parts.append(
                f"Milestone '{milestone.name}' is {milestone.status} for "
                f"{milestone.kickoff_date}."
            )
        content_parts.extend(
            f"{task.assignee} owns '{task.title}' due {task.due_date}."
            for task in tasks
        )
        content = " ".join(content_parts)
        message = ChatMessage(
            message_id=message_id_for_index(len(self.db.chat_messages)),
            channel=channel,
            project=project,
            meeting_event_id=meeting_event_id,
            preparation_task_id=preparation_task_id,
            preparation_task_ids=([] if preparation_task_id is not None else task_ids),
            milestone_id=milestone_id,
            content=content,
        )
        self.db.chat_messages.append(message)
        return message

    def assert_calendar_event(
        self,
        title: str,
        start: str,
        end: str,
        attendees: list[str],
    ) -> bool:
        """Check that exactly one calendar event matches the expected fields."""
        expected_attendees = sorted(attendees)
        matches = [
            event
            for event in self.db.calendar_events.values()
            if event.title == title
            and event.start == start
            and event.end == end
            and event.attendees == expected_attendees
        ]
        return len(matches) == 1

    def assert_no_calendar_invite(self, email: str) -> bool:
        """Check that an email address is absent from every calendar event."""
        return all(
            email not in event.attendees for event in self.db.calendar_events.values()
        )

    def assert_project_task(self, task_id: str, assignee: str, due_date: str) -> bool:
        """Check that a project task has the expected owner and due date."""
        task = self.db.project_tasks.get(task_id)
        return (
            task is not None and task.assignee == assignee and task.due_date == due_date
        )

    def assert_project_task_details(
        self,
        title: str,
        project: str,
        assignee: str,
        due_date: str,
        status: str = "open",
    ) -> bool:
        """Check that exactly one task has all expected project-task fields."""
        matches = [
            task
            for task in self.db.project_tasks.values()
            if task.title == title
            and task.project == project
            and task.assignee == assignee
            and task.due_date == due_date
            and task.status == status
        ]
        return len(matches) == 1

    def assert_project_milestone(
        self,
        milestone_id: str,
        status: str,
        kickoff_date: str,
        meeting_event_id: str,
    ) -> bool:
        """Check the exact updated milestone fields."""
        milestone = self.db.project_milestones.get(milestone_id)
        return (
            milestone is not None
            and milestone.status == status
            and milestone.kickoff_date == kickoff_date
            and milestone.meeting_event_id == meeting_event_id
        )

    def assert_chat_message_references(
        self,
        channel: str,
        meeting_event_id: str,
        preparation_task_ids: list[str],
        milestone_id: str,
    ) -> bool:
        """Check one message references the complete kickoff work set."""
        expected_tasks = sorted(preparation_task_ids)
        matches = [
            message
            for message in self.db.chat_messages
            if message.channel == channel
            and message.meeting_event_id == meeting_event_id
            and sorted(message.preparation_task_ids) == expected_tasks
            and message.milestone_id == milestone_id
        ]
        return len(matches) == 1

    def assert_chat_message_contains(
        self, channel: str, required_text: list[str]
    ) -> bool:
        """Check that one message in a channel contains every required string."""
        return any(
            message.channel == channel
            and all(text.lower() in message.content.lower() for text in required_text)
            for message in self.db.chat_messages
        )

    def assert_workplace_record(
        self,
        record_id: str,
        system: str,
        status: str,
        owner: Optional[str] = None,
        required_fields: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Check the exact mutable fields of one workplace record."""
        record = self.db.workplace_records.get(record_id)
        if record is None or record.system != system or record.status != status:
            return False
        if owner is not None and record.owner != owner:
            return False
        return all(
            record.fields.get(key) == value
            for key, value in (required_fields or {}).items()
        )

    def assert_action_proposal_approved(
        self, proposal_id: str, proposal_type: str
    ) -> bool:
        """Check an exact structured proposal is user-approved."""
        proposal = self.db.action_proposals.get(proposal_id)
        return (
            proposal is not None
            and proposal.proposal_type == proposal_type
            and proposal.approved_by_user
        )

    def assert_external_message_recipients(
        self, proposal_id: str, recipients: list[str]
    ) -> bool:
        """Check the complete recipient set sent from one approved proposal."""
        actual = sorted(
            message.recipient
            for message in self.db.external_messages
            if message.source_proposal_id == proposal_id
        )
        return actual == sorted(recipients)

    def assert_no_external_message_to(self, recipient: str) -> bool:
        """Check that no external communication was sent to a recipient."""
        return all(
            message.recipient != recipient for message in self.db.external_messages
        )

    def assert_internal_update(
        self, channel: str, related_record_ids: list[str]
    ) -> bool:
        """Check one canonical internal update references the complete work set."""
        expected = sorted(related_record_ids)
        matches = [
            update
            for update in self.db.internal_updates
            if update.channel == channel and update.related_record_ids == expected
        ]
        return len(matches) == 1

    def assert_on_call_page(self, incident_record_id: str, target: str) -> bool:
        """Check that exactly one page reached the expected incident responder."""
        matches = [
            page
            for page in self.db.on_call_pages
            if page.incident_record_id == incident_record_id and page.target == target
        ]
        return len(matches) == 1

    def assert_access_grant(
        self, identity_record_id: str, access_level: str, expires_on: str
    ) -> bool:
        """Check that exactly one expected access bundle was provisioned."""
        matches = [
            grant
            for grant in self.db.access_grants
            if grant.identity_record_id == identity_record_id
            and grant.access_level == access_level
            and grant.expires_on == expires_on
        ]
        return len(matches) == 1

    def assert_no_access_level(self, access_level: str) -> bool:
        """Check that a prohibited access level was never provisioned."""
        return all(
            grant.access_level != access_level for grant in self.db.access_grants
        )
