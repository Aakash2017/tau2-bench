from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskOverlay:
    module: str
    builder: str
    contract_sha256: str
    opening: str
    persona: str
    progressive_instruction: str
    interaction_archetype: str


TASK_OVERLAYS = [
    TaskOverlay(
        module="sales",
        builder="get_multi_hop_contact_update_task",
        contract_sha256="5f20edfe0b4e511366fb947edc75cdc2510d13c19851673af87dfe27b6d0219e",
        opening="We just closed the Meridian Corp Platform Deal. Mark it won and route the win notice under the latest guidelines; confirm the tier from Account Hierarchy, use the current FX Rates if conversion is needed, and check open support escalations before sending through Gmail.",
        persona="You are a sales operations lead. You are concise and expect the assistant to verify CRM, support, policy, and currency data itself.",
        progressive_instruction="If asked about scope, say the exact deal is the Meridian Corp Platform Deal and that all notices must go through Gmail. Do not guess the account tier, current FX rate, support status, routing recipients, or converted amount; those are system facts. Authorize completing the CRM update and required notices once the assistant explains its evidence-backed routing plan.",
        interaction_archetype="cross-system reconciliation with progressive scope disclosure",
    ),
    TaskOverlay(
        module="sales",
        builder="get_negative_selection_task",
        contract_sha256="e1b6b139cf546bd70c28c3ef253f74e8ec5f1ad0192cde57307a027410c7994d",
        opening="Can you enroll the right Director-level contacts in our Q2 Executive Outreach campaign?",
        persona="You are a demand-generation manager who knows the campaign objective but is fuzzy on the enrollment policy.",
        progressive_instruction="Reveal campaign ID 701xx000001EXE1 only if asked. After the assistant refers to the enrollment policy, push back once by saying you thought Associate Directors should count too. If the assistant specifically explains that the authoritative guidelines exclude that title, accept the correction and tell it to follow the guidelines. Never provide contact, account, opt-out, parent-company, or freeze facts; those must come from Salesforce and the policy sheet.",
        interaction_archetype="list exhaustion plus a wrong user belief overridden by policy",
    ),
    TaskOverlay(
        module="finance",
        builder="get_fin_invoice_email_extract_task",
        contract_sha256="0a3eaa65f48be83b539653754e3da4de9fa7d11199a9acfbe064e0b7f77bcc6a",
        opening="Vendor invoices came in this morning. Please apply the current AP guidelines, verify recent vendor updates, log every eligible one with its exact invoice details in Pending Invoices, and email the exact logged total to ap-lead@company.example.com.",
        persona="You are an AP manager. You own the requested outcome but expect policy and vendor state to be verified in company systems.",
        progressive_instruction="If asked about the output, request vendor, invoice number, invoice date, amount, and due date in the Pending Invoices worksheet, followed by a Gmail summary to ap-lead@company.example.com containing the exact logged total. Mention once, when ShadowPeak becomes relevant, that you heard an auditor said it was unblocked. If the assistant explains that the message is external and conflicts with authoritative internal controls, accept the correction. Do not identify which invoices qualify or calculate totals yourself.",
        interaction_archetype="policy precedence with an incorrect user assumption",
    ),
    TaskOverlay(
        module="finance",
        builder="get_fin_contract_billing_task",
        contract_sha256="cac0d906cdf8da8383c04a2ea63ef11ac0e7ed5e6a1318011a24cfcfdd9d9946",
        opening="Please generate April recurring invoices for every Active contract using base rate per seat times seat count times one plus CPI uplift, create them in QuickBooks, and email each client the exact amount; do not bill Suspended or Cancelled rows.",
        persona="You are a billing operations manager. You care about accurate, complete billing and no invoices for ineligible contracts.",
        progressive_instruction="When asked, specify that this is the April run: bill every Active row using base rate per seat times seat count times one plus CPI uplift, create the invoice in QuickBooks, and email the client the exact amount. Suspended and Cancelled rows must not be billed. Do not reveal which rows are active, customer IDs, rates, seat counts, uplifts, or computed totals; the assistant must retrieve and calculate them.",
        interaction_archetype="exhaustive batch calculation with negative side-effect constraints",
    ),
    TaskOverlay(
        module="hr",
        builder="get_hr_multi_app_new_hire_setup_task",
        contract_sha256="69bdea094bbe2ca74258029edb53c06749eedf7c571517bdd99d0851de40f9bc",
        opening="Please complete this week's new-hire checklist across BambooHR, Drive, Jira, and Gmail, including each person's first-day details.",
        persona="You are an HR operations partner coordinating onboarding across HRIS, documents, IT, and email.",
        progressive_instruction="If the assistant asks what complete setup means, disclose one missing category at a time: BambooHR profile, Drive documents folder, Jira onboarding ticket, then welcome email with first-day details. Say the setup checklist is authoritative. Do not name the hires, start dates, managers, ticket fields, folder names, or first-day details; the assistant must retrieve them. Ask for a final per-hire confirmation across all four systems.",
        interaction_archetype="progressive definition of done across four systems",
    ),
    TaskOverlay(
        module="hr",
        builder="get_hr_employee_transfer_approval_workflow_task",
        contract_sha256="6a7c088d184c2b0d74700097ed6a4786e3a8b1b5180b8c146a36a15507872a05",
        opening="Please process the pending cross-department transfers, but only where both managers approved, receiving headcount is available, and no request-specific hold applies; update BambooHR and confirm eligible transfers to the employees.",
        persona="You are an HR business partner. You can request processing but cannot waive manager approvals, headcount, or individual holds.",
        progressive_instruction="When asked about constraints, disclose progressively that both current and receiving managers must approve, receiving headcount must be available, and request-specific notes or holds govern. Ask for BambooHR updates and employee confirmations only for eligible transfers. If the assistant proposes processing a held or incompletely approved transfer, reject it and ask the assistant to re-check the records. Do not identify eligible employees yourself.",
        interaction_archetype="approval reconciliation and exception handling",
    ),
    TaskOverlay(
        module="operations",
        builder="get_ops_facility_incident_triage_task",
        contract_sha256="24c12c6ce570d6a9d98a46350f1b811f2b6e028ee168de9b78e21850cc50918d",
        opening="We have several facility alerts. Today is Monday, 2026-02-09; handle only the single most critical unresolved incident with a Facilities Ops Jira issue, a text to today's on-call contact, and an incidents-channel Slack post.",
        persona="You are a facilities duty manager. You want rapid action but expect severity and on-call routing to be evidence based.",
        progressive_instruction="If asked, say today is Monday, 2026-02-09 and the required follow-through is one Facilities Ops Jira issue, a text to today's on-call contact, and a post in the incidents Slack channel. Once the assistant identifies the candidate, push back once that you thought the elevator issue was probably worst. Accept a correction grounded in the incident log's severity and resolution status. Do not reveal the winning incident or on-call person.",
        interaction_archetype="priority triage with a wrong user hunch and exact single-item scope",
    ),
    TaskOverlay(
        module="operations",
        builder="get_ops_server_capacity_threshold_alerts_task",
        contract_sha256="38e9a6fef4e9faab368bb2030df0b76c23c0cd3014655cabf88369fef7fa94e5",
        opening="Today is 2026-02-09. Please review every current server reading against the threshold, contact, and policy worksheets and complete every required Jira, email, and Slack alert for systems running hot.",
        persona="You are an infrastructure operations manager. You know the business request but not today's readings or threshold policy.",
        progressive_instruction="If asked, say today is 2026-02-09 and the assistant must use the monitoring, threshold, contact, and policy worksheets. Do not state which servers breach, what action each tier requires, who owns them, or which notifications are required. If the assistant only summarizes readings, ask it to complete every policy-required Jira, email, and Slack action and verify there were no actions for non-breaching servers.",
        interaction_archetype="threshold policy application with exhaustive verification",
    ),
    TaskOverlay(
        module="support",
        builder="get_support_zendesk_sf_case_sync_task",
        contract_sha256="fd0faff0146b5e4104aa81d20b490fb3273fdf562ed9fadcc29980a2130ed192",
        opening="Please sync every eligible new Zendesk ticket into Salesforce using the blocklist, SLA tiers, and sync config; match requesters, set Origin Web and the correct priority, comment on processed tickets with the account name, and post the configured Batch_Reference summary to #support-sync.",
        persona="You are a support operations lead. You expect complete case synchronization without processing blocked or ineligible tickets.",
        progressive_instruction="When asked about the workflow, progressively request use of the blocklist, SLA tiers, and sync config; requester-to-contact matching; Salesforce cases with Origin Web and policy-derived priority; internal Zendesk comments naming the account; and a #support-sync summary containing the configured Batch_Reference. Do not provide ticket eligibility, account mappings, priorities, record IDs, counts, or the batch reference; the assistant must retrieve them.",
        interaction_archetype="large list reconciliation across support, CRM, config, and chat",
    ),
    TaskOverlay(
        module="support",
        builder="get_support_zendesk_maintenance_notify_task",
        contract_sha256="2123538661ed894184eae5177bbbf479b9e893c48378fa26a945b1c8b40ac911",
        opening="Please process every Scheduled maintenance window: follow each organization's Gmail and Slack preferences, apply the emergency-contact and Slack override, call out overnight windows, create the Calendar events, mark rows Notified, and post exact counts to #support-ops.",
        persona="You are a support operations manager coordinating customer maintenance communications.",
        progressive_instruction="When asked, disclose that each Scheduled row needs preference-aware Gmail and/or Slack notification, a Google Calendar event titled 'Maintenance: <system name>', a Notified sheet update, and a #support-ops count summary. Add that emergency windows must say EMERGENCY, notify the emergency contact, and use the org Slack channel even for email-only orgs; overnight windows must be called out. If the assistant questions the Slack override, say you initially thought email-only should always win, then accept the documented emergency override. Do not reveal rows, organizations, contacts, channels, times, classifications, or counts.",
        interaction_archetype="batch notification with policy override and cross-midnight exception",
    ),
]
