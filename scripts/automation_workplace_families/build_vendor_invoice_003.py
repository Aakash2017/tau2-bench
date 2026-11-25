"""Build vendor_invoice_003: the AP payment run with decision-critical images.

Derived from vendor_invoice_002 (run its builder first). Four facts move from
text into images: the revised treasury release (spreadsheet screenshot), the
approval matrix (diagram; only the superseded 2025 matrix remains as text), the
true identity of a mis-keyed resent invoice (scan), and a new-bank-account
remittance instruction (scan). Expected final state is unchanged.

Usage: python build_vendor_invoice_003.py data/tau2/domains/automation_workplace/interactive
"""

import json
import random
import sys
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

INTERACTIVE = Path(sys.argv[1])
TASK_ID = "vendor_invoice_003"
ATT_DIR = INTERACTIVE / "attachments" / TASK_ID
ATT_REL = f"tau2/domains/automation_workplace/interactive/attachments/{TASK_ID}"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(size, bold=False, serif=False, mono=False):
    name = "DejaVu" + ("SansMono" if mono else "Serif" if serif else "Sans")
    return ImageFont.truetype(
        str(FONT_DIR / f"{name}{'-Bold' if bold else ''}.ttf"), size
    )


def scanned(img, seed, angle):
    rng = random.Random(seed)
    img = img.convert("L").rotate(
        angle, resample=Image.BICUBIC, expand=True, fillcolor=236
    )
    px = img.load()
    w, h = img.size
    for _ in range(w * h // 40):
        x, y = rng.randrange(w), rng.randrange(h)
        px[x, y] = max(0, min(255, px[x, y] + rng.randint(-60, 30)))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def invoice(
    seed, angle, vendor, address, number, date, terms, po, lines, foot, stamp=None
):
    img = Image.new("RGB", (850, 1100), "white")
    d = ImageDraw.Draw(img)
    d.text((60, 55), vendor, font=font(34, bold=True, serif=True), fill="black")
    for i, line in enumerate(address):
        d.text((60, 102 + i * 24), line, font=font(17), fill="black")
    d.text((590, 60), "INVOICE", font=font(36, bold=True), fill="black")
    meta = [
        ("Invoice no.", number),
        ("Invoice date", date),
        ("Terms", terms),
        ("PO", po),
    ]
    for i, (k, v) in enumerate(meta):
        d.text((540, 125 + i * 30), k, font=font(17), fill="black")
        d.text((675, 125 + i * 30), v, font=font(17, bold=True), fill="black")
    d.text((60, 270), "Bill to", font=font(17, bold=True), fill="black")
    for i, line in enumerate(
        ["Atlas Labs, Inc.", "Accounts Payable", "ap@atlas.example"]
    ):
        d.text((60, 296 + i * 24), line, font=font(17), fill="black")
    d.rectangle((60, 410, 790, 446), fill=(225, 225, 225))
    d.text((75, 418), "Description", font=font(17, bold=True), fill="black")
    d.text((640, 418), "Amount (USD)", font=font(17, bold=True), fill="black")
    y = 462
    for desc, amount in lines:
        d.text((75, y), desc, font=font(17), fill="black")
        d.text((660, y), f"{amount:,.2f}", font=font(17), fill="black")
        y += 34
    d.line((60, y + 10, 790, y + 10), fill="black", width=2)
    total = sum(a for _, a in lines)
    d.text((420, y + 24), "TOTAL DUE (USD)", font=font(19, bold=True), fill="black")
    d.text((660, y + 24), f"{total:,.2f}", font=font(19, bold=True), fill="black")
    for i, line in enumerate(foot):
        d.text((60, 900 + i * 26), line, font=font(16), fill="black")
    if stamp:
        layer = Image.new("RGBA", (420, 120), (0, 0, 0, 0))
        s = ImageDraw.Draw(layer)
        s.rectangle((4, 4, 415, 115), outline=(170, 20, 20, 255), width=5)
        s.text((24, 18), stamp[0], font=font(30, bold=True), fill=(170, 20, 20, 255))
        s.text((24, 64), stamp[1], font=font(22, bold=True), fill=(170, 20, 20, 255))
        layer = layer.rotate(-9, expand=True)
        img.paste(layer, (380, 620), layer)
    return scanned(img, seed, angle)


def forecast():
    img = Image.new("RGB", (1180, 560), "white")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 1180, 44), fill=(241, 243, 244))
    d.text(
        (14, 11),
        "Treasury cash forecast - wk of 14 Dec 2026  (rev. 14 Dec 16:30)",
        font=font(18, bold=True),
        fill=(32, 33, 36),
    )
    cols = [14, 54, 520, 700, 880, 1166]
    heads = ["", "Outflow line", "Prior (11 Dec)", "Revised (14 Dec)", "Status"]
    rows = [
        ["Payroll true-up (12/18)", "412,000", "438,500", "updated"],
        ["AP vendor payment run (Tue 12/15)", "110,000", "100,000", "released"],
        ["Sales & use tax remittance (12/20)", "64,200", "64,200", ""],
        ["AP vendor payment run (Tue 12/22)", "125,000", "120,000", "planned"],
        ["Intercompany sweep (12/31)", "250,000", "250,000", ""],
        ["Total outflows", "961,200", "972,700", ""],
    ]
    top, rh = 70, 52
    for r in range(len(rows) + 2):
        d.line((cols[0], top + r * rh, cols[-1], top + r * rh), fill=(200, 200, 200))
    for x in cols:
        d.line((x, top, x, top + (len(rows) + 1) * rh), fill=(200, 200, 200))
    d.rectangle(
        (cols[0] + 1, top + 1, cols[-1] - 1, top + rh - 1), fill=(232, 240, 254)
    )
    d.rectangle(
        (cols[3] + 1, top + 2 * rh + 1, cols[4] - 1, top + 3 * rh - 1),
        fill=(255, 242, 157),
    )
    for c, h in enumerate(heads):
        d.text((cols[c] + 10, top + 15), h, font=font(17, bold=True), fill=(32, 33, 36))
    for r, row in enumerate(rows, start=1):
        d.text(
            (cols[0] + 8, top + r * rh + 15),
            str(r + 1),
            font=font(15),
            fill=(95, 99, 104),
        )
        for c, v in enumerate(row, start=1):
            bold = r == len(rows) or (r == 2 and c == 3)
            d.text(
                (cols[c] + 10, top + r * rh + 15),
                v,
                font=font(17, bold=bold),
                fill=(32, 33, 36),
            )
    d.text(
        (20, top + 8 * rh - 10),
        "USD. Released figures are final for the run date; planned figures are indicative.",
        font=font(15),
        fill=(95, 99, 104),
    )
    return img


def box(d, xy, text, fill, size=17):
    d.rounded_rectangle(xy, radius=14, fill=fill, outline=(60, 60, 60), width=2)
    x0, y0, x1, _ = xy
    for i, line in enumerate(text.split("\n")):
        w = d.textlength(line, font=font(size))
        d.text(
            (x0 + (x1 - x0 - w) / 2, y0 + 12 + i * (size + 6)),
            line,
            font=font(size),
            fill="black",
        )


def arrow(d, p, q, label=""):
    d.line((p, q), fill=(60, 60, 60), width=3)
    (x0, y0), (x1, y1) = p, q
    if x0 == x1:
        s = 1 if y1 > y0 else -1
        d.polygon(
            [(x1, y1), (x1 - 8, y1 - 14 * s), (x1 + 8, y1 - 14 * s)], fill=(60, 60, 60)
        )
    else:
        s = 1 if x1 > x0 else -1
        d.polygon(
            [(x1, y1), (x1 - 14 * s, y1 - 8), (x1 - 14 * s, y1 + 8)], fill=(60, 60, 60)
        )
    if label:
        d.text(
            ((x0 + x1) / 2 + 8, (y0 + y1) / 2 - 22),
            label,
            font=font(16, bold=True),
            fill=(20, 90, 20) if label == "Yes" else (170, 20, 20),
        )


def matrix():
    img = Image.new("RGB", (1200, 1060), "white")
    d = ImageDraw.Draw(img)
    d.text(
        (40, 24), "Vendor bill approval matrix", font=font(28, bold=True), fill="black"
    )
    d.text(
        (40, 62),
        "Accounts Payable  |  effective 1 Oct 2026  |  replaces the 2025 role-based matrix",
        font=font(16),
        fill=(80, 80, 80),
    )
    q, ok, bad = (255, 244, 214), (220, 242, 220), (250, 222, 222)
    box(d, (380, 110, 820, 165), "Recorded approval on a vendor bill", (235, 235, 235))
    box(
        d,
        (300, 215, 900, 315),
        "Does the approver's own personal approval\nlimit cover the bill amount in USD?\n(non-USD: treasury rate for the run date)",
        q,
    )
    box(d, (920, 230, 1170, 300), "VALID", ok, 22)
    box(
        d,
        (300, 375, 900, 475),
        "Was the approval recorded on or between the\nstart and end dates of a delegation in which\nthe approver is the delegate?",
        q,
    )
    box(
        d,
        (300, 535, 900, 615),
        "Does the delegator's limit cover the\nbill amount in USD?",
        q,
    )
    box(d, (920, 540, 1170, 610), "VALID", ok, 22)
    box(
        d,
        (60, 690, 1140, 860),
        "INVALID APPROVAL\nSet the bill On Hold with reason code APPROVAL_INVALID. Do not pay it.\n"
        "Email a request for a fresh approval to an approver whose own limit covers the bill.\n"
        "If that approver has an active delegation today, send the request to the delegate instead.",
        bad,
        18,
    )
    arrow(d, (600, 165), (600, 215))
    arrow(d, (900, 265), (920, 265), "")
    d.text((895, 232), "Yes", font=font(16, bold=True), fill=(20, 90, 20))
    arrow(d, (600, 315), (600, 375), "No")
    arrow(d, (600, 475), (600, 535), "Yes")
    arrow(d, (900, 575), (920, 575), "")
    d.text((895, 542), "Yes", font=font(16, bold=True), fill=(20, 90, 20))
    arrow(d, (600, 615), (600, 690), "No")
    d.line((300, 425, 200, 425), fill=(60, 60, 60), width=3)
    d.text((222, 398), "No", font=font(16, bold=True), fill=(170, 20, 20))
    arrow(d, (200, 425), (200, 690))
    notes = [
        "Notes",
        "1. A delegate approves with the delegator's limit only inside the delegation window. Outside it, the approver's own limit applies.",
        "2. Seniority of the original approver, or a verbal or emailed assurance of approval, does not cure an invalid approval.",
        "3. Limits are personal and listed on each approver record in NetSuite.",
    ]
    for i, n in enumerate(notes):
        d.text((60, 900 + i * 32), n, font=font(16, bold=i == 0), fill="black")
    return img


base = json.loads((INTERACTIVE / "tasks/vendor_invoice_002.json").read_text())
task = deepcopy(base)
world = task["family_world"]
world["task_id"] = TASK_ID

ATT_DIR.mkdir(parents=True, exist_ok=True)
files = {
    "att_treasury_forecast_1214": ("cash_forecast_rev_2026-12-14.png", forecast()),
    "att_approval_matrix_2026_10": ("ap_approval_matrix_2026-10.png", matrix()),
    "att_scan_kestrel_resend": (
        "kestrel_invoice_scan.png",
        invoice(
            11,
            0.7,
            "Kestrel Analytics",
            ["410 Harbor Way, Suite 300", "Portland, OR 97209", "ar@kestrel.example"],
            "INV-020931",
            "02 Oct 2026",
            "NET 30",
            "PO-5477",
            [("Churn model refresh, September", 8750.0)],
            ["Remit by ACH to the account on file.", "Questions: ar@kestrel.example"],
            stamp=("COPY - RESENT", "08 DEC 2026  2ND NOTICE"),
        ),
    ),
    "att_scan_halden_77310": (
        "halden_invoice_scan.png",
        invoice(
            12,
            -0.5,
            "Halden Facilities Group",
            [
                "88 Mercer Industrial Park",
                "Oakland, CA 94607",
                "accounts@halden-facilities.example",
            ],
            "HFG-77310",
            "18 Nov 2026",
            "NET 30",
            "PO-5402",
            [("HVAC maintenance, HQ floors 2-5", 18700.0)],
            [
                "REMITTANCE: please note our NEW remittance account,",
                "account number ending 8842, effective immediately.",
                "Payments to the previous account may be delayed.",
            ],
        ),
    ),
    "att_scan_corvid_3610": (
        "corvid_invoice_scan.png",
        invoice(
            13,
            0.4,
            "Corvid Data Services",
            ["1200 Fifth Ave, Floor 9", "Seattle, WA 98101", "billing@corvid.example"],
            "CDS-3610",
            "05 Dec 2026",
            "NET 30",
            "PO-5530",
            [("Managed pipeline service, December (partial)", 12000.0)],
            ["Thank you for your business."],
        ),
    ),
}
world["attachments"] = {}
for att_id, (name, img) in files.items():
    img.save(ATT_DIR / name, optimize=True)
    world["attachments"][att_id] = {
        "attachment_id": att_id,
        "filename": name,
        "content_type": "image/png",
        "path": f"{ATT_REL}/{name}",
    }

mail = world["mailbox"]
mail["msg_tr_1214"]["body"] = (
    "Revising Tuesday's release after the payroll true-up came in higher than "
    "forecast. Updated forecast attached; please keep the run inside the released "
    "figure. Gwen"
)
mail["msg_tr_1214"]["attachment_ids"] = ["att_treasury_forecast_1214"]
mail["msg_kestrel_resend"].update(
    subject="Resending invoice - payment outstanding",
    body="Hello, our records show the attached invoice as unpaid. Re-attaching for "
    "processing. Kestrel Analytics AR",
    attachment_ids=["att_scan_kestrel_resend"],
)
bills = world["bills"]
# Keyed by a clerk from the resend: digit misread and the received date entered.
bills["bill_2204"].update(
    invoice_number="INV-020981",
    invoice_date="2026-12-08",
    due_date="2027-01-07",
    attachment_ids=["att_scan_kestrel_resend"],
)
bills["bill_2203"].update(remit_to_note="", attachment_ids=["att_scan_halden_77310"])
bills["bill_2210"]["attachment_ids"] = ["att_scan_corvid_3610"]

kb = json.loads((INTERACTIVE / base["knowledge_file"]).read_text())
for doc in kb:
    if doc["document_id"] == "kb_ap_approval_matrix_2026_10":
        doc["content"] = (
            "The current vendor bill approval matrix, covering approval authority, "
            "delegations and how to handle an invalid approval, is published as a "
            "one-page diagram (attached). It replaces the 2025 role-based matrix."
        )
        doc["attachments"] = ["att_approval_matrix_2026_10"]
    elif doc["document_id"] == "kb_ap_duplicate_invoices_2026_09":
        doc["content"] += (
            "\n\nWhen a bill carries a scan of the vendor's invoice, the scan is the "
            "source of truth for invoice number, date and amount. NetSuite fields are "
            "keyed by hand from the vendor's document and can contain entry errors."
        )
    elif doc["document_id"] == "kb_ap_payment_run_procedure_2026_11":
        doc["content"] = doc["content"].replace(
            "A bill that fails a check is handled under that standard and is not part "
            "of the run.",
            "A bill that fails a check is handled under that standard and is not part "
            "of the run. Open every source scan attached to an approved bill before "
            "deciding it.",
        )
        assert "Open every source scan" in doc["content"]
KB_FILE = "knowledge/vendor_invoice_payment_run_mm.json"
(INTERACTIVE / KB_FILE).write_text(json.dumps(kb, indent=2) + "\n")

task["id"] = f"automation_workplace__interactive__{TASK_ID}"
task["knowledge_file"] = KB_FILE
task["knowledge_document_ids"] = [d["document_id"] for d in kb]
task["description"] = {
    **base["description"],
    "notes": base["description"]["notes"]
    + " Multimodal variant: the revised release, the current approval matrix, a "
    "mis-keyed resent invoice and a new-bank remittance instruction are only "
    "readable from attached images.",
}
(INTERACTIVE / f"tasks/{TASK_ID}.json").write_text(json.dumps(task, indent=2) + "\n")
print(f"{len(files)} images, {len(task['assertions'])} assertions, {len(kb)} docs")
