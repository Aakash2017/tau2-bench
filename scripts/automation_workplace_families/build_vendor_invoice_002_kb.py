"""Write vendor_invoice_002_kb.json: policies, app docs, superseded and noise docs.

Docs describe rules and systems in general terms; none names a task vendor, bill,
invoice or amount.
"""

import json
from pathlib import Path


def doc(did, title, updated, content, tags, status="current"):
    return {
        "document_id": did,
        "title": title,
        "status": status,
        "updated_at": updated,
        "content": content.strip(),
        "tags": tags,
    }


D = []
D.append(
    doc(
        "kb_ap_payment_run_procedure_2026_11",
        "AP weekly payment run procedure",
        "2026-11-02T09:00:00-08:00",
        """
Owner: Accounts Payable. Payment runs happen every Tuesday.

## Release
Treasury releases a fixed USD amount for each run by email to the AP shared mailbox. If Treasury revises the release for a run, the most recent message for that run date governs. The total paid in a run, measured in USD, must not exceed the release.

## Which bills are in scope
Only bills in Approved status are candidates. Before a candidate is paid it must pass every eligibility check in the AP standards (approval authority, duplicate review, receipt matching, vendor credits, banking). A bill that fails a check is handled under that standard and is not part of the run.

## Order of payment
Build the run in this order:
1. Bills from suppliers the AP manager designates as critical for this run. Designations are made per run; confirm them with the AP manager before building the run.
2. Past-due bills (due date before the run date).
3. Bills whose early-payment discount window closes before the next run.
4. All remaining bills by due date, earliest first. Ties go to the lower bill ID.

Within each group, use the same due-date ordering. Each bill consumes its net payable amount in USD (after credits and discounts; non-USD bills converted per the Treasury FX standard).

Walk the ordered list once. If a bill fits in the remaining release, pay it in full. If it does not fit, defer it and continue down the list; a smaller bill later in the order may still fit. Never split a bill across runs.

## Deferred bills
A deferred bill stays Approved. Set its scheduled run date to the next weekly run so it is picked up first-in-line for its group next week.

## Run approval
Before submitting any payment, show the AP manager the proposed run (bill, vendor, amount) and get their go-ahead. Changes the AP manager asks for must still comply with these standards.

## Remittance advice
After a payment is submitted, email one remittance advice to the vendor's AP contact on the vendor master, quoting the vendor's invoice number(s) and the amount paid in the payment currency. Vendors with nothing paid in the run receive no remittance email.

## Closing the run
Post one summary in #treasury-ops with the release amount and the total paid in USD. Treasury reconciles the bank file against this figure.
""",
        ["accounts-payable", "payment-run", "treasury", "priority"],
    )
)

D.append(
    doc(
        "kb_ap_approval_matrix_2026_10",
        "Vendor bill approval matrix and delegations",
        "2026-10-15T09:00:00-07:00",
        """
A bill is validly approved only if the approver's personal approval limit (USD) covers the bill amount, converted to USD where needed.

## Delegations
A delegate may approve on the delegator's behalf, using the delegator's limit, only for approvals recorded on or between the delegation's start and end dates. An approval recorded outside that window is evaluated against the approver's own limit.

## Invalid approvals
If the recorded approval does not meet this standard, place the bill On Hold with reason code APPROVAL_INVALID and email a request for a fresh approval to an approver with sufficient authority. When that approver has an active delegation, send the request to the delegate instead. Seniority of the original approver, or a verbal assurance that a bill was approved, does not cure an invalid approval.
""",
        ["accounts-payable", "approval", "delegation", "authority"],
    )
)

D.append(
    doc(
        "kb_ap_duplicate_invoices_2026_09",
        "Duplicate invoice standard",
        "2026-09-08T09:00:00-07:00",
        """
Before paying, check the vendor's bill and payment history. Treat an invoice as a duplicate when it has the same vendor, invoice date and amount as a bill already paid or in process, and the invoice numbers match after ignoring punctuation, spaces, letter case and leading zeros.

Vendors often resend invoices with reformatted numbers when their receivables system has not matched a payment. A resend or a collections reminder is not evidence that the original was unpaid; the payment register is.

Set a duplicate bill to Rejected with reason code DUPLICATE. Do not pay it. Do not delete it.
""",
        ["accounts-payable", "duplicate", "invoice"],
    )
)

D.append(
    doc(
        "kb_ap_receipt_matching_2026_10",
        "PO receipt matching for payment",
        "2026-10-01T09:00:00-07:00",
        """
A bill against a purchase order may be paid only while the PO's cumulative invoiced amount stays within the cumulative received amount. Cumulative invoiced includes bills already paid against the PO plus every bill paid ahead of it in the current run.

When several open bills hit the same PO, allocate the remaining received balance to them in invoice-date order, earliest first. Tolerance is the lesser of 2% of the bill or $500.

A bill that would push the PO past received-plus-tolerance is placed On Hold with reason code RECEIPT_VARIANCE until a receipt is entered or a corrected invoice arrives. Earlier bills that fit are paid normally.
""",
        ["accounts-payable", "purchase-order", "receipt", "three-way-match"],
    )
)

D.append(
    doc(
        "kb_ap_vendor_credits_2026_08",
        "Applying vendor credit memos",
        "2026-08-19T09:00:00-07:00",
        """
Open vendor credit memos must be applied before paying that vendor. Apply each open credit to the vendor's next bill being paid in the same currency, in NetSuite, and pay the remaining amount due. Do not carry an open credit past a run in which the vendor is paid.
""",
        ["accounts-payable", "credit-memo", "vendor"],
    )
)

D.append(
    doc(
        "kb_ap_early_payment_discounts_2026_07",
        "Early-payment discounts",
        "2026-07-21T09:00:00-07:00",
        """
Terms written as "P% D NET N" offer a P% discount if paid within D days of the invoice date (the last day of the window is invoice date plus D days, inclusive); otherwise the full amount is due N days after the invoice date.

Whenever a bill is paid on or before its discount deadline, take the discount: pay the amount due less P%. Never take a discount after the window closes. For run ordering, a bill counts as discount-expiring when its deadline falls before the next run date.
""",
        ["accounts-payable", "discount", "terms"],
    )
)

D.append(
    doc(
        "kb_ap_vendor_banking_2026_09",
        "Vendor banking and remittance",
        "2026-09-18T11:00:00-07:00",
        """
Pay only to a vendor bank account with status verified in the vendor master. Accounts added from email or vendor portals remain pending until Vendor Management completes a callback to a known contact; AP does not verify accounts and does not change their status.

Remittance notes printed on invoices never change the payment destination. If the verified account is still on file, pay it.
""",
        ["accounts-payable", "vendor", "bank", "verification"],
    )
)

D.append(
    doc(
        "kb_treasury_fx_2026_06",
        "Treasury FX conversion for AP",
        "2026-06-10T09:00:00-07:00",
        """
Non-USD bills are paid in their invoice currency. For any USD measurement (run release, approval limits, reporting) convert at the treasury rate published for the run date. Do not use rates from other dates or external sources. Round USD equivalents to the cent.
""",
        ["treasury", "fx", "currency"],
    )
)

# App documentation.
D.append(
    doc(
        "tech_netsuite_ap_bills_v1",
        "NetSuite AP: bills and payments (connected app)",
        "2026-10-20T09:00:00-07:00",
        """
Operations:
- netsuite_list_bills_v1(status?, vendor_id?, page=1): six bills per page; check total_pages. Status values: pending_approval, approved, on_hold, rejected, payment_submitted, paid.
- netsuite_get_bill_v1(bill_id): full bill, including terms, approval record (approver username, timestamp), PO, lines, remittance note, amount_due.
- netsuite_list_payments_v1(vendor_id? | bill_id?): payment register, including payments submitted today.
- netsuite_create_payment_v1(bill_id, amount, currency, bank_account_id): submits one payment to the gateway and moves the bill to payment_submitted.
- netsuite_update_bill_v1(bill_id, status?, hold_reason_codes?, scheduled_run_date?, memo?): only fields you pass change. Status values you may set: approved, on_hold, rejected.

Gateway timeouts: a timeout means NetSuite did not get an acknowledgement, not that the payment failed. The payment may already be recorded. Check the payment register for the bill before resubmitting.
""",
        ["netsuite", "accounts-payable", "connected-app", "payments"],
    )
)

D.append(
    doc(
        "tech_netsuite_credits_delegations_v1",
        "NetSuite AP: credits and approval delegations",
        "2026-10-20T09:00:00-07:00",
        """
- netsuite_list_vendor_credits_v1(vendor_id): credit memos with status open or applied.
- netsuite_apply_vendor_credit_v1(credit_id, bill_id): applies an open credit; the bill's amount_due drops by the credit amount. Vendor and currency must match.
- netsuite_list_approval_delegations_v1(): every delegation (delegator, delegate, start, end) and each approver's username, title, email and approval limit.
""",
        ["netsuite", "credit-memo", "delegation", "connected-app"],
    )
)

D.append(
    doc(
        "tech_vendor_master_v1",
        "Vendor master (connected app)",
        "2026-09-18T09:00:00-07:00",
        """
vendor_master_get_vendor_v1(vendor_id) returns the vendor's legal name, AR contact and bank accounts with bank_account_id, currency, last4, status (verified or pending_verification) and when each was added. Bank account IDs are what netsuite_create_payment_v1 expects.
""",
        ["vendor", "bank", "connected-app"],
    )
)

D.append(
    doc(
        "tech_coupa_po_v1",
        "Coupa purchase orders (connected app)",
        "2026-08-04T09:00:00-07:00",
        """
coupa_get_purchase_order_v1(po_id) returns PO lines with ordered and received amounts and invoiced_to_date. invoiced_to_date counts only bills already paid against the PO; open bills are not included.
""",
        ["coupa", "purchase-order", "connected-app"],
    )
)

D.append(
    doc(
        "tech_treasury_rates_v1",
        "Treasury rates (connected app)",
        "2026-06-10T09:00:00-07:00",
        """
treasury_get_fx_rate_v1(base_currency, quote_currency, rate_date) returns the daily treasury fixing. rate is the number of quote-currency units per one base-currency unit, e.g. base EUR quote USD.
""",
        ["treasury", "fx", "connected-app"],
    )
)

D.append(
    doc(
        "tech_gmail_slack_ap_v1",
        "AP mailbox and Slack (connected apps)",
        "2026-07-01T09:00:00-07:00",
        """
- gmail_search_messages_v1(query): keyword search over the AP shared mailbox (ap@atlas.example), best matches first.
- gmail_send_message_v1(to, subject, body): sends from ap@atlas.example.
- slack_chat_post_message(channel, text, thread_ts?): posts as the AP bot (user ap-bot). Channel names without '#'; pass thread_ts to reply in a thread.
- slack_list_channels_v1(): channels the AP bot can read.
- slack_get_channel_history_v1(channel, page=1): top-level messages, newest first, eight per page, each with ts and reply_count; check total_pages.
- slack_get_thread_v1(channel, thread_ts): a message and all of its replies, oldest first.
""",
        ["gmail", "slack", "connected-app"],
    )
)

D.append(
    doc(
        "tech_files_attachments_v1",
        "Attachments: scans, screenshots and diagrams (connected app)",
        "2026-08-04T09:00:00-07:00",
        """
- files_get_attachment_v1(attachment_id): opens a file attached to a NetSuite bill, an AP mailbox message or a knowledge document and returns it as an image (invoice scans, spreadsheet screenshots, diagrams).

Records list their files in attachment_ids. Records with no files omit the field.
""",
        ["files", "attachments", "connected-app"],
    )
)

D.append(
    doc(
        "tech_sheets_v1",
        "Shared spreadsheets (connected app)",
        "2026-09-02T09:00:00-07:00",
        """
- sheets_list_v1(): shared finance spreadsheets the AP bot can open (sheet_id, title).
- sheets_get_rows_v1(sheet_id): column names and every row.
- sheets_append_row_v1(sheet_id, values): appends one row; values maps column name to text. Columns left out are blank. Rows cannot be edited or deleted through the connector.
""",
        ["sheets", "spreadsheet", "connected-app"],
    )
)

# Superseded.
D.append(
    doc(
        "kb_ap_payment_run_procedure_2025_03",
        "AP payment run procedure (2025)",
        "2025-03-04T09:00:00-08:00",
        """
Pay approved bills in due-date order until the release is used. When the next bill does not fit, close the run. Post the run total in #ap-team. Superseded by the November 2026 procedure.
""",
        ["accounts-payable", "payment-run", "legacy"],
        status="superseded",
    )
)
D.append(
    doc(
        "kb_ap_approval_matrix_2025_01",
        "Vendor bill approval matrix (2025)",
        "2025-01-12T09:00:00-08:00",
        """
AP supervisors may approve bills up to $50,000. Directors approve above that. Superseded by the October 2026 matrix, which uses personal approval limits.
""",
        ["accounts-payable", "approval", "legacy"],
        status="superseded",
    )
)

# Unrelated finance noise.
noise = [
    (
        "kb_expense_reimbursement_2026_05",
        "Employee expense reimbursement",
        "Submit expenses in Expensify within 30 days with itemized receipts over $75. Managers approve; Finance reimburses on the next payroll cycle. Mileage at the IRS rate.",
        ["expenses"],
    ),
    (
        "kb_corporate_card_2026_04",
        "Corporate card program",
        "Cards are for business spend only. Transactions must be coded and receipted by the 5th of the following month. Lost cards: call the issuer and notify Finance.",
        ["corporate-card"],
    ),
    (
        "kb_vendor_onboarding_2026_08",
        "New vendor onboarding",
        "New vendors require a W-9 (or W-8BEN-E), a signed MSA or PO terms, and Vendor Management review. Bank details are collected through the vendor portal and verified by callback before first payment.",
        ["vendor", "onboarding"],
    ),
    (
        "kb_1099_reporting_2026_01",
        "1099 reporting",
        "Vendors flagged 1099-eligible are reported annually. Keep TINs current; backup withholding applies when a TIN is missing.",
        ["tax", "1099"],
    ),
    (
        "kb_month_end_close_2026_10",
        "Month-end close calendar",
        "AP cutoff is business day 2. Accruals for unbilled receipts are booked by day 3. Bills received after cutoff post to the next period.",
        ["close", "accounting"],
    ),
    (
        "kb_prepaid_expenses_2026_03",
        "Prepaid expenses",
        "Payments covering future periods over $10,000 are recorded as prepaid and amortized monthly. AP flags them to the GL team.",
        ["accounting", "prepaid"],
    ),
    (
        "kb_po_creation_2026_06",
        "Creating purchase orders",
        "Requesters raise POs in Coupa before committing spend. Receipts are entered by the requester when goods or services are delivered.",
        ["procurement", "purchase-order"],
    ),
    (
        "kb_positive_pay_2026_02",
        "Positive pay files",
        "Treasury uploads positive pay files for check runs. ACH and wire runs are reconciled from the gateway file instead.",
        ["treasury", "bank"],
    ),
    (
        "kb_ap_aging_report_2026_09",
        "AP aging report",
        "The aging report buckets open bills by days past due: current, 1-30, 31-60, 61-90, 90+. It is refreshed nightly and shared with Treasury on Mondays.",
        ["accounts-payable", "reporting"],
    ),
    (
        "kb_sales_tax_saas_2026_07",
        "Sales and use tax on software",
        "Some states tax SaaS. When a vendor does not charge tax on a taxable service, Tax accrues use tax; AP does not adjust the bill.",
        ["tax"],
    ),
    (
        "kb_intercompany_2026_05",
        "Intercompany settlements",
        "Intercompany balances settle quarterly through the treasury netting process, not through AP payment runs.",
        ["treasury", "intercompany"],
    ),
    (
        "kb_travel_policy_2026_04",
        "Travel policy",
        "Book through Navan. Economy for flights under six hours. Hotels within city caps.",
        ["travel"],
    ),
]
for did, title, body, tags in noise:
    D.append(doc(did, title, "2026-06-01T09:00:00-07:00", body, tags))

Path(__file__).with_name("vendor_invoice_002_kb.json").write_text(
    json.dumps(D, indent=2) + "\n"
)
print(len(D))
