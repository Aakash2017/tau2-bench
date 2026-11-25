"""Build interactive/tasks/access_provisioning_007.json and its own thin KB.

Same company and tools as Task 6, but the desk's process is not written down in
the KB. It has to be pieced together from past #eng-access-requests threads, a
few closed ACCESS tickets and a hallway question in #engineering. The threads
differ a little (an old 14-day default, announcement wording) so the agent has
to weigh them by date.
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

from tau2.domains.automation_workplace.standalone_apps import new_world

INTERACTIVE = Path(sys.argv[1])
BASE_DIR = Path(__file__).parent / "base"
BASE = json.loads((BASE_DIR / "task6_world.json").read_text())
KB6 = {d["document_id"]: d for d in json.loads((BASE_DIR / "old_kb.json").read_text())}

KEN = "worker_ken_watanabe"
AVA = "worker_ava_cole"
DEFAULT_END = "2027-01-13"
LEON_END = "2027-01-05"
PROD_TRAINING = "secure-production-access-2026"

# ---------------------------------------------------------------- knowledge base
PROD_STANDARD = {
    "document_id": "kb_production_access_standard_2026_10",
    "title": "Production access standard",
    "status": "current",
    "updated_at": "2026-10-07T09:00:00-07:00",
    "tags": ["security", "production", "policy"],
    "content": (
        "Owner: Security.\n\nProduction means the production clusters, the deploy "
        "pipeline and anything holding live customer data. Access is personal, "
        "time-boxed and reviewed every quarter. Staff who work in production "
        "complete the annual secure-production-access course. Anything beyond "
        "read-only goes through the owning team. Questions to #security."
    ),
}
OKTA_GROUPS = deepcopy(KB6["tech_okta_engineering_groups_2026_10"])
OKTA_GROUPS["content"] = OKTA_GROUPS["content"].split("\nNotes:")[0].rstrip() + (
    "\n\nNotes:\n\n- Group names are stable. Display names in the Okta UI may differ.\n"
)
JIRA = deepcopy(KB6["tech_jira_access_requests_v1"])
JIRA["content"] = JIRA["content"].replace(
    "status             string, required (see Access desk runbook)",
    "status             string, required (the project's workflow statuses)",
)
KEEP = [
    "tech_rippling_people_v1",
    "tech_okta_groups_v1",
    "tech_lms_training_v1",
    "tech_slack_chat_access_2026_07",
    "kb_deploy_pipeline_overview_2026_09",
    "kb_oncall_handbook_2026_10",
    "kb_holiday_change_freeze_2026_11",
    "kb_customer_sandbox_access_2026_09",
    "kb_vendor_portal_access_2026_04",
    "kb_vpn_access_2026_03",
    "kb_data_export_approval_2026_10",
    "kb_customer_support_impersonation_2026_09",
    "tech_connected_apps_catalog_2026_10",
    "tech_gmail_connected_app_2026_09",
    "tech_salesforce_connected_app_2026_09",
    "tech_datadog_connected_app_2026_10",
    "tech_github_connected_app_2026_10",
    "tech_drive_connected_app_2026_08",
]
KB = [PROD_STANDARD, OKTA_GROUPS, JIRA] + [KB6[i] for i in KEEP]
KB_FILE = "knowledge/access_provisioning_precedent.json"
(INTERACTIVE / KB_FILE).write_text(json.dumps(KB, indent=2, ensure_ascii=False) + "\n")

# ------------------------------------------------------------------------ world
world = deepcopy(BASE["family_world"])
workers = world["workers"]
assert isinstance(workers, dict)


def add_worker(wid, name, manager, wtype="employee", end=None):
    email = wid.removeprefix("worker_").replace("_", ".") + "@atlas.example"
    workers[wid] = {
        "worker_id": wid,
        "legal_name": name,
        "worker_type": wtype,
        "status": "active",
        "manager_id": manager,
        "primary_email": email,
        "department": "Engineering",
        "job_title": "Software Engineer",
        "contract_end_date": end,
    }


add_worker("worker_jo_alvarez", "Jo Alvarez", KEN, "contractor", "2026-12-05")
add_worker("worker_amir_chen", "Amir Chen", KEN)
add_worker("worker_pia_lund", "Pia Lund", AVA)
add_worker("worker_lars_eriksen", "Lars Eriksen", AVA)
add_worker("worker_mira_soto", "Mira Soto", AVA)

identities = world["identities"]
# Hana has no production course on file; Omar keeps his release approver role.
world["training_records"] = {
    k: v for k, v in world["training_records"].items() if "2025" not in k
}


def request(
    rid,
    wid,
    groups,
    description,
    status="New",
    approver=KEN,
    granted=(),
    reason=None,
    exp=None,
):
    return {
        "request_id": rid,
        "worker_id": wid,
        "requested_groups": list(groups),
        "granted_groups": sorted(granted),
        "status": status,
        "blocked_reason": reason,
        "access_expiration": exp,
        "approver_id": approver,
        "description": description,
    }


reqs = [
    request(
        "ACCESS-451",
        "worker_sven_holm",
        ["grp_prod_admin"],
        "Prod admin for the January backfill jobs.",
    ),
    request(
        "ACCESS-452",
        "worker_mei_tan",
        ["grp_prod_admin"],
        "Prod admin for the January backfill jobs.",
    ),
    request(
        "ACCESS-453",
        "worker_omar_haddad",
        ["grp_prod_readonly"],
        "Read-only prod for on-call shadowing.",
    ),
    request(
        "ACCESS-454",
        "worker_rui_silva",
        ["grp_prod_admin"],
        "Prod admin for the storage migration.",
    ),
    request(
        "ACCESS-455",
        "worker_hana_kim",
        ["grp_prod_readonly"],
        "Needs to look at prod logs for the pipeline rewrite.",
    ),
    request(
        "ACCESS-456",
        "worker_leon_brandt",
        ["grp_prod_readonly"],
        "Prod read-only for the ingest migration.",
    ),
    request(
        "ACCESS-457",
        "worker_bruno_costa",
        ["grp_staging_deployer"],
        "Staging deploys for the payments service.",
        approver="worker_daniel_osei",
    ),
    request(
        "ACCESS-371",
        "worker_jo_alvarez",
        ["grp_prod_readonly"],
        "Prod read-only for the migration.",
        "Completed",
        granted=["grp_prod_readonly"],
        exp="2026-12-05",
    ),
    request(
        "ACCESS-377",
        "worker_amir_chen",
        ["grp_prod_readonly"],
        "Prod read-only for on-call.",
        "Completed",
        granted=["grp_prod_readonly"],
        exp="2026-10-26",
    ),
    request(
        "ACCESS-384",
        "worker_pia_lund",
        ["grp_prod_admin"],
        "Prod admin for the cutover.",
        "Completed",
        AVA,
        granted=["grp_prod_admin"],
        exp="2026-11-11",
    ),
    request(
        "ACCESS-390",
        "worker_lars_eriksen",
        ["grp_prod_admin"],
        "Prod admin for the DB failover work.",
        "Blocked - conflict",
        AVA,
        reason="SOD_CONFLICT",
    ),
    request(
        "ACCESS-395",
        "worker_mira_soto",
        ["grp_prod_readonly"],
        "Prod read-only for the dashboards work.",
        "Completed",
        AVA,
        granted=["grp_prod_readonly"],
        exp="2026-12-19",
    ),
]
world["access_requests"] = {r["request_id"]: r for r in reqs}

# ------------------------------------------------------------------------ slack
PRIYA = "Priya Nair"
MONTHS = {
    "Aug": ("08", "-07:00"),
    "Sep": ("09", "-07:00"),
    "Oct": ("10", "-07:00"),
    "Nov": ("11", "-08:00"),
    "Dec": ("12", "-08:00"),
}
CHANNELS = {
    "eng-platform": (
        "Platform engineering: deploys, CI, infra",
        "Day-to-day platform chatter",
        64,
    ),
    "eng-access-requests": (
        "Access requests for engineering systems",
        "Requests, approvals and desk updates",
        41,
    ),
    "engineering": (
        "All of engineering",
        "Announcements and questions for everyone in eng",
        212,
    ),
    "general": ("Company-wide announcements", "News for all of Atlas", 480),
    "random": ("Non-work banter", "Pets, lunch, weekend plans", 455),
    "incidents": ("Active and past incidents", "Status, follow-ups and reviews", 150),
    "security": ("Security questions and announcements", "Ask Security anything", 300),
    "sre-oncall": ("SRE on-call handoffs", "Rotation, pages and handoffs", 22),
    "product": ("Product and design", "Roadmap and launch notes", 120),
}
# (key, channel, author, "Mon D HH:MM", text, parent key)
RAW = [
    # --- the desk's precedent
    (
        "jo",
        "eng-access-requests",
        "Ken Watanabe",
        "Sep 23 10:02",
        "Jo is on the Data Platform contract through Dec 5 and needs prod read-only for the migration. ACCESS-371",
        None,
    ),
    (
        "jo1",
        "eng-access-requests",
        PRIYA,
        "Sep 23 11:40",
        "Jo's end date in Rippling is 12/5 so that's the expiry, not the usual window. grp_prod_readonly is on, ACCESS-371 closed.",
        "jo",
    ),
    (
        "jo2",
        "eng-access-requests",
        "atlas-ops",
        "Sep 23 11:41",
        "Jo Alvarez received production read-only through 2026-12-05 (ACCESS-371).",
        None,
    ),
    (
        "d14",
        "eng-platform",
        PRIYA,
        "Oct 6 09:30",
        "Heads up, until Security finishes reviewing the new standard we're keeping everything to 14 days.",
        None,
    ),
    (
        "am",
        "eng-access-requests",
        "Ken Watanabe",
        "Oct 9 14:05",
        "Amir needs prod read-only for on-call. ACCESS-377",
        None,
    ),
    (
        "am1",
        "eng-access-requests",
        PRIYA,
        "Oct 9 14:30",
        "Amir hasn't done secure-production-access yet. I assigned it to him and I'll grant it once he's done. Not posting here until he actually has access.",
        "am",
    ),
    (
        "am2",
        "eng-access-requests",
        PRIYA,
        "Oct 12 16:10",
        "Amir finished the course. grp_prod_readonly through 10/26, ACCESS-377 closed.",
        "am",
    ),
    (
        "am3",
        "eng-access-requests",
        "atlas-ops",
        "Oct 12 16:11",
        "Amir Chen - production read-only, expires 2026-10-26. ACCESS-377",
        None,
    ),
    (
        "pia",
        "eng-platform",
        "Elena Park",
        "Oct 27 10:15",
        "Pia needs prod admin for the cutover, fine by me. ACCESS-384",
        None,
    ),
    (
        "pia1",
        "eng-platform",
        PRIYA,
        "Oct 27 11:02",
        "Thanks Elena. I'm parking ACCESS-384 as Blocked - approval until the prod admin owners weigh in.",
        "pia",
    ),
    (
        "pia2",
        "eng-platform",
        "Marta Kowalski",
        "Oct 28 08:50",
        "Platform SRE is good with Pia having prod admin for the cutover.",
        "pia",
    ),
    (
        "pia3",
        "eng-platform",
        PRIYA,
        "Oct 28 09:20",
        "Thanks Marta. Pia has grp_prod_admin through 11/11, ACCESS-384 closed.",
        "pia",
    ),
    (
        "pia4",
        "eng-access-requests",
        "atlas-ops",
        "Oct 28 09:21",
        "Pia Lund received production admin through 2026-11-11. ACCESS-384 closed.",
        None,
    ),
    (
        "d30",
        "eng-platform",
        PRIYA,
        "Nov 3 09:00",
        "Security signed off. Default is 30 days from the day we grant it now.",
        None,
    ),
    (
        "lars",
        "eng-platform",
        "Lars Eriksen",
        "Nov 12 13:20",
        "need prod admin for the DB failover work. ACCESS-390",
        None,
    ),
    (
        "lars1",
        "eng-platform",
        PRIYA,
        "Nov 12 13:55",
        "Lars already approves releases, so I can't put prod admin on top of that. ACCESS-390 is Blocked - conflict. If you really need both that's a Security conversation.",
        "lars",
    ),
    (
        "lars2",
        "eng-platform",
        "Lars Eriksen",
        "Nov 12 14:10",
        "ok, I'll sort out another way",
        "lars",
    ),
    (
        "mira",
        "eng-access-requests",
        "Ava Cole",
        "Nov 19 10:00",
        "Mira needs prod read-only for the dashboards work. ACCESS-395",
        None,
    ),
    (
        "mira1",
        "eng-access-requests",
        PRIYA,
        "Nov 19 10:25",
        "Granted, grp_prod_readonly through 12/19. ACCESS-395 closed.",
        "mira",
    ),
    (
        "mira2",
        "eng-access-requests",
        "atlas-ops",
        "Nov 19 10:26",
        "Mira Soto received production read-only through 2026-12-19. ACCESS-395 closed.",
        None,
    ),
    (
        "hall",
        "engineering",
        "Sam Whitaker",
        "Oct 14 15:12",
        "how do I get prod read-only for on-call? I filed something last week and nothing's happened",
        None,
    ),
    (
        "hall1",
        "engineering",
        "Joy Lin",
        "Oct 14 15:20",
        "your manager approves it on the intake form and then the desk picks it up. They made me do the prod course first, takes about an hour",
        "hall",
    ),
    (
        "hall2",
        "engineering",
        "Sam Whitaker",
        "Oct 14 15:21",
        "ah thanks, that's probably it",
        "hall",
    ),
    (
        "sven",
        "eng-access-requests",
        "Marta Kowalski",
        "Dec 9 11:15",
        "Platform SRE is fine with Sven having prod admin for the January backfill jobs. ACCESS-451",
        None,
    ),
    (
        "mei",
        "eng-access-requests",
        "Rafael Ortiz",
        "Dec 10 16:05",
        "Mei needs prod admin for the January backfill, fine by me. ACCESS-452",
        None,
    ),
    # --- #eng-platform everyday traffic
    (
        None,
        "eng-platform",
        "Nina Park",
        "Sep 21 09:12",
        "Good morning all. Staging deploys are paused until 11 while we rotate the registry creds.",
        None,
    ),
    (
        None,
        "eng-platform",
        "Dev Rao",
        "Sep 24 14:03",
        "kudos to the ingest crew, the new batching shipped with zero rollbacks",
        None,
    ),
    (
        None,
        "eng-platform",
        "Tess Okafor",
        "Sep 29 10:41",
        "is anyone else seeing CI take 25+ minutes on the monorepo? it was ~10 last week",
        None,
    ),
    (
        None,
        "eng-platform",
        "Marcus Bell",
        "Sep 29 10:52",
        "yep, cache misses I think. looking at it after standup",
        "ci1",
    ),
    (
        "ci1",
        "eng-platform",
        "Tess Okafor",
        "Sep 29 10:30",
        "heads up: runner pool is saturated, queue time is the real problem",
        None,
    ),
    (
        None,
        "eng-platform",
        "Joy Lin",
        "Oct 2 08:55",
        "Happy birthday Nina! :tada:",
        None,
    ),
    (
        None,
        "eng-platform",
        "Nina Park",
        "Oct 2 09:20",
        "thank you!! cake in the kitchen at 3",
        None,
    ),
    (
        None,
        "eng-platform",
        "Marcus Bell",
        "Oct 7 12:18",
        "working from home today, back online by 1 for the planning sync",
        None,
    ),
    (
        None,
        "eng-platform",
        "Dev Rao",
        "Oct 8 16:30",
        "Reminder: the Argo upgrade is Thursday 10 AM. Deploys to staging are frozen for an hour.",
        None,
    ),
    (
        None,
        "eng-platform",
        "Tess Okafor",
        "Oct 15 09:05",
        "<!channel> prod deploy freeze Oct 16 from noon for the datacenter maintenance. Hotfixes go through the on-call.",
        None,
    ),
    (
        None,
        "eng-platform",
        "Sam Whitaker",
        "Oct 19 13:44",
        "question: is there a way to rerun only the failed integration shards? rerunning everything is painful",
        None,
    ),
    (
        None,
        "eng-platform",
        "Marcus Bell",
        "Oct 19 13:58",
        "yes, the 'rerun failed' button on the pipeline page, it's hiding under the three dots",
        "rr",
    ),
    (
        "rr",
        "eng-platform",
        "Sam Whitaker",
        "Oct 19 13:40",
        "CI question for anyone who knows the pipeline UI",
        None,
    ),
    (
        None,
        "eng-platform",
        "Nina Park",
        "Oct 22 11:02",
        "Congrats team on the v4.2 launch! Dashboards look healthy.",
        None,
    ),
    (
        None,
        "eng-platform",
        "Joy Lin",
        "Oct 30 17:10",
        "OOO tomorrow and Monday, Marcus is covering reviews",
        None,
    ),
    (
        None,
        "eng-platform",
        "Dev Rao",
        "Nov 4 09:41",
        "CI is slow again. 30 min runs. Is the cache cluster full?",
        None,
    ),
    (
        None,
        "eng-platform",
        "Tess Okafor",
        "Nov 4 10:20",
        "cache cluster at 94%, evicting now. should recover",
        None,
    ),
    (
        None,
        "eng-platform",
        "Marcus Bell",
        "Nov 9 08:30",
        "working from home today, flaky wifi so slack only",
        None,
    ),
    (None, "eng-platform", "Nina Park", "Nov 11 14:12", "Happy birthday Dev!", None),
    (None, "eng-platform", "Dev Rao", "Nov 11 14:30", "thanks all :)", None),
    (
        None,
        "eng-platform",
        "Tess Okafor",
        "Nov 17 09:00",
        "<!channel> reminder: Thanksgiving week is a soft freeze. Only fixes and reverts to prod Nov 24-27.",
        None,
    ),
    (
        None,
        "eng-platform",
        "Joy Lin",
        "Nov 19 15:22",
        "shoutout to Sam for untangling the helm chart mess, saved us a day",
        None,
    ),
    (
        None,
        "eng-platform",
        "Sam Whitaker",
        "Nov 23 11:08",
        "does anyone have the runbook for rotating the registry creds? the wiki page 404s",
        None,
    ),
    (
        None,
        "eng-platform",
        "Dev Rao",
        "Nov 23 11:15",
        "it moved to the infra space, I'll drop the link",
        None,
    ),
    (
        None,
        "eng-platform",
        "Nina Park",
        "Dec 1 09:03",
        "Monthly reminder to close out stale feature branches, we're at 140",
        None,
    ),
    (
        None,
        "eng-platform",
        "Tess Okafor",
        "Dec 3 13:50",
        "CI queue times better since we added runners, thanks Dev",
        None,
    ),
    (
        None,
        "eng-platform",
        "Marcus Bell",
        "Dec 7 08:45",
        "working from home, dentist at 10, online after",
        None,
    ),
    (
        None,
        "eng-platform",
        "Dev Rao",
        "Dec 9 16:00",
        "<!channel> holiday change freeze starts Friday Dec 18 for production. Staging is fine.",
        None,
    ),
    (
        None,
        "eng-platform",
        "Joy Lin",
        "Dec 11 12:30",
        "Happy birthday Marcus!! :birthday:",
        None,
    ),
    # --- other channels
    (
        None,
        "general",
        "Hana Ito",
        "Sep 28 09:00",
        "Welcome to the new hires starting today! Say hi in #random.",
        None,
    ),
    (
        None,
        "general",
        "Facilities",
        "Oct 20 08:30",
        "The 4th floor kitchen is closed for cleaning today.",
        None,
    ),
    (
        None,
        "general",
        "Hana Ito",
        "Nov 18 10:00",
        "Open enrollment closes Friday. Benefits questions go to the people-ops help desk.",
        None,
    ),
    (
        None,
        "general",
        "Facilities",
        "Dec 8 09:15",
        "Holiday party signups are open until the 12th.",
        None,
    ),
    (
        None,
        "random",
        "Sam Whitaker",
        "Oct 3 12:10",
        "anyone want to split a lunch order from the thai place?",
        None,
    ),
    (
        None,
        "random",
        "Joy Lin",
        "Oct 31 09:50",
        "dog costume contest in the lobby at noon",
        None,
    ),
    (
        None,
        "random",
        "Nina Park",
        "Nov 20 17:00",
        "who's up for board games friday?",
        None,
    ),
    (
        None,
        "incidents",
        "Marcus Bell",
        "Oct 21 03:12",
        "INC-842 resolved. Post-incident review Monday, no customer action needed.",
        None,
    ),
    (
        None,
        "incidents",
        "Dev Rao",
        "Nov 14 22:40",
        "INC-861 mitigated, root cause was a bad config push. Review scheduled.",
        None,
    ),
    (
        None,
        "security",
        "Security",
        "Oct 5 10:00",
        "Reminder: report phishing with the button, not by forwarding.",
        None,
    ),
    (
        None,
        "security",
        "Security",
        "Nov 6 09:30",
        "Customer data stays out of staging. Use the sanitized bundles.",
        None,
    ),
    (
        None,
        "sre-oncall",
        "Marta Kowalski",
        "Nov 30 17:00",
        "Handoff: quiet week, one flaky alert on the ingest queue.",
        None,
    ),
    (
        None,
        "product",
        "Nina Park",
        "Nov 5 11:30",
        "Roadmap review moved to Thursday. Add discovery questions to the doc before noon.",
        None,
    ),
]

RAW += [
    # --- the original flow, later reversed
    (
        "rhea",
        "eng-access-requests",
        "Dana Whitfield",
        "Aug 18 10:05",
        "Can someone get Rhea prod read-only today? Her on-call starts tonight. ACCESS-352",
        None,
    ),
    (
        "rhea1",
        "eng-access-requests",
        PRIYA,
        "Aug 18 10:30",
        "Done. She's in grp_prod_readonly for 90 days and ACCESS-352 is Provisionally granted. She'll do secure-production-access this week.",
        "rhea",
    ),
    (
        "rhea2",
        "eng-access-requests",
        "atlas-ops",
        "Aug 18 10:31",
        "Rhea Mallick received production read-only through 2026-11-16 (ACCESS-352).",
        None,
    ),
    (
        "rhea3",
        "eng-access-requests",
        "Kofi Mensah",
        "Aug 26 15:00",
        "Rhea has had prod read-only for 8 days and hasn't taken secure-production-access. ACCESS-352 is still Provisionally granted. Can we not do this for prod?",
        "rhea",
    ),
    (
        "rhea4",
        "eng-access-requests",
        PRIYA,
        "Aug 26 15:20",
        "Fair, that's on me. Took her access off until she's done the course. From now on for prod the course comes first and the ticket sits in Blocked - training, nothing granted until it's done. Provisional isn't a thing for prod anymore.",
        "rhea",
    ),
    (
        "rhea5",
        "eng-access-requests",
        "atlas-ops",
        "Aug 26 15:21",
        "Rhea Mallick's production read-only was removed. ACCESS-352 is Blocked - training.",
        None,
    ),
]

AUTHORS = [
    "Nina Park",
    "Dev Rao",
    "Tess Okafor",
    "Marcus Bell",
    "Joy Lin",
    "Sam Whitaker",
    "Alex Moreno",
    "Priti Shah",
    "Chen Wei",
    "Jordan Blake",
    "Fatima Noor",
    "Luca Bianchi",
    "Grace Okoro",
    "Hugo Martin",
    "Yara Haddad",
    "Ivan Petrov",
    "Zoe Clarke",
    "Ben Alder",
    "Maya Iyer",
    "Theo Grant",
]
CHANNELS.update(
    {
        "design": ("Design crits and assets", "Figma links and feedback", 58),
        "sales": ("Sales floor", "Deals, forecasts and wins", 140),
        "marketing": ("Marketing", "Campaigns and launch copy", 66),
        "finance": ("Finance questions", "Close, expenses and POs", 35),
        "people-ops": ("People and benefits", "HR questions and reminders", 480),
        "it-help": ("IT help desk", "Laptops, VPN, SSO and printers", 470),
        "data-platform": ("Data Platform team", "Pipelines, warehouse, backfills", 24),
        "data-access": ("Warehouse access", "Analytics access questions", 90),
        "eng-frontend": ("Frontend engineering", "Web app and design system", 38),
        "eng-backend": ("Backend engineering", "Services, APIs and queues", 52),
        "eng-mobile": ("Mobile engineering", "iOS and Android", 21),
        "qa": ("QA and release testing", "Test plans and regressions", 19),
        "releases": ("Release train", "What ships and when", 160),
        "ci-alerts": ("CI alerts", "Automated build notices", 75),
        "announcements": ("Official announcements", "Read-only for most", 480),
        "hiring": ("Hiring", "Interview loops and offers", 45),
        "customer-success": ("Customer success", "Account health and escalations", 48),
        "support": ("Support", "Tickets and macros", 52),
        "lunch": ("Lunch plans", "Where are we eating", 200),
        "pets": ("Pets of Atlas", "Photos only", 150),
    }
)
NOISE = {
    "eng-platform": [
        "Happy birthday {n}! :tada:",
        "working from home today, online by {h}",
        "<!channel> deploy freeze for {r} starting {h}. Hotfixes go through on-call.",
        "kudos to {n} for getting the {r} migration out with zero rollbacks",
        "CI is crawling again, {m} minute runs. Anyone else?",
        "runner pool looks saturated, queue time is the real problem",
        "does anyone know how to rerun just the failed shards?",
        "congrats on the {r} launch, dashboards look healthy",
        "OOO tomorrow, {n} is covering reviews",
        "staging deploys paused for an hour while we rotate creds",
        "the cache cluster is at {m}%, evicting now",
        "reminder to close stale feature branches",
        "who owns the {r} alerts? paging me at night",
        "lunch at {h}? the new place on 5th",
        "thanks {n}, that helm fix saved us a day",
        "stand-up moved to {h} today",
    ],
    "general": [
        "Welcome to the new hires starting today!",
        "The 4th floor kitchen is closed for cleaning today.",
        "Reminder: all-hands is at {h} on Thursday.",
        "Holiday party signups are open.",
        "Happy birthday {n}!",
        "Parking garage is closed Friday for resurfacing.",
    ],
    "random": [
        "anyone want to split a lunch order?",
        "dog costume contest at noon",
        "who's up for board games friday?",
        "this rain is something else",
        "new coffee machine on 3 is great",
        "{n} brought donuts, go go go",
    ],
    "engineering": [
        "Lunch and learn on {r} is at {h}",
        "anyone used the new profiler? worth it?",
        "reminder: code review SLA is one business day",
        "{n}'s talk on {r} is up on the wiki",
        "working from home today, flaky wifi",
        "congrats {n} on the promotion!",
    ],
    "incidents": [
        "INC-{i} mitigated, root cause was a bad config push. Review scheduled.",
        "INC-{i} resolved. No customer action needed.",
        "Post-incident review for INC-{i} is Monday at {h}.",
    ],
    "security": [
        "Reminder: report phishing with the button, not by forwarding.",
        "Please rotate any API tokens older than 90 days.",
        "Laptop disk encryption check is running this week.",
    ],
    "it-help": [
        "VPN is back after the brief outage",
        "new laptops arrive Thursday, check your email",
        "Printer on 3 is jammed again, ticket filed",
        "SSO prompts are slower than usual, we're looking",
    ],
    "people-ops": [
        "Open enrollment closes Friday",
        "Reminder: submit time off for the holidays",
        "Benefits FAQ is updated on the wiki",
    ],
    "ci-alerts": [
        "Build #{i} failed on main (flaky test)",
        "Build #{i} passed",
        "Nightly build #{i} is green",
    ],
    "releases": [
        "v{m} is going out Thursday",
        "v{m} is out, notes are in the wiki",
        "Hotfix {m}.1 shipped",
    ],
    "data-platform": [
        "backfill for {r} finished",
        "warehouse maintenance Sunday 2 AM",
        "dbt run took {m} minutes today",
    ],
    "product": [
        "Roadmap review moved to Thursday",
        "Launch brief is ready for copy review",
    ],
    "sales": ["Q4 pipeline review at {h}", "Congrats {n} on the {r} close!"],
    "marketing": [
        "The launch brief is ready for final copy review",
        "Webinar signups hit {m}",
    ],
    "finance": [
        "Close is complete, accrual questions to the finance queue",
        "Expense reports due Friday",
    ],
    "design": ["crit at {h} in the usual room", "new icon set is in Figma"],
    "eng-frontend": [
        "bundle size is up {m}%, looking into it",
        "design system v{m} is out",
    ],
    "eng-backend": [
        "the queue consumer lag is back to normal",
        "new retry policy is merged",
    ],
    "eng-mobile": ["TestFlight build is up", "Android crash rate is down this week"],
    "qa": ["regression pass for the {r} release is done", "flaky test list is updated"],
    "hiring": ["Interview loop for {r} is Tuesday", "Offer accepted! Welcome {n}"],
    "customer-success": [
        "QBR with {r} went well",
        "Heads up: {r} reported slow dashboards",
    ],
    "support": [
        "Ticket volume is up after the release",
        "New macro for password resets",
    ],
    "lunch": ["tacos at {h}?", "ordering pizza for the floor"],
    "pets": ["{n}'s dog says hi", "cat on the keyboard again"],
    "announcements": [
        "Office closed Dec 25 to Jan 1",
        "Company update posted on the wiki",
    ],
    "data-access": [
        "Reminder: analytics datasets are pseudonymized",
        "dashboard refresh moved to 6 AM",
    ],
    "sre-oncall": [
        "Handoff: quiet week, one flaky alert",
        "Handoff: pager noise on the ingest queue",
    ],
}
WEIGHT = {
    "eng-platform": 150,
    "general": 20,
    "random": 25,
    "engineering": 40,
    "incidents": 12,
    "security": 12,
    "it-help": 25,
    "people-ops": 10,
    "ci-alerts": 40,
    "releases": 15,
}
REGIONS = [
    "ingest",
    "billing",
    "search",
    "payments",
    "auth",
    "mobile",
    "reports",
    "export",
]


def generate():
    import random

    rng = random.Random(7)
    rows = []
    for channel, texts in NOISE.items():
        for _ in range(WEIGHT.get(channel, 8)):
            month, day = rng.choice(
                [
                    ("Aug", rng.randint(1, 31)),
                    ("Sep", rng.randint(1, 30)),
                    ("Oct", rng.randint(1, 31)),
                    ("Nov", rng.randint(1, 30)),
                    ("Dec", rng.randint(1, 13)),
                ]
            )
            text = rng.choice(texts).format(
                n=rng.choice(AUTHORS),
                h=f"{rng.randint(8, 16)}:{rng.choice(['00', '30'])}",
                r=rng.choice(REGIONS),
                m=rng.randint(12, 94),
                i=rng.randint(800, 900),
            )
            when = f"{month} {day} {rng.randint(8, 17):02d}:{rng.randint(0, 59):02d}"
            rows.append((None, channel, rng.choice(AUTHORS), when, text, None))
    return rows


RAW += generate()


def _when(text):
    month, day, clock = text.split()
    number, offset = MONTHS[month]
    return f"2026-{number}-{int(day):02d}T{clock}:00{offset}"


ordered = sorted(RAW, key=lambda row: _when(row[3]))
ids = {row[0]: f"slack_message_{i:03d}" for i, row in enumerate(ordered, 1) if row[0]}
world["slack_messages"] = {}
for i, (key, channel, author, when, text, parent) in enumerate(ordered, 1):
    mid = f"slack_message_{i:03d}"
    world["slack_messages"][mid] = {
        "message_id": mid,
        "channel": channel,
        "text": text,
        "author": author,
        "sent_at": _when(when),
        "thread_id": ids[parent] if parent else "",
    }
world["slack_channels"] = {
    name: {"name": name, "topic": topic, "purpose": purpose, "num_members": members}
    for name, (topic, purpose, members) in CHANNELS.items()
}
world["injected_faults"] = []
world["task_id"] = "access_provisioning_007"
messages = ordered

generic_world = new_world("2026-12-14T17:00:00Z")

# -------------------------------------------------------------------- assertions
GRANTS = {
    "ACCESS-451": ("okta_sven_holm", "grp_prod_admin", DEFAULT_END),
    "ACCESS-453": ("okta_omar_haddad", "grp_prod_readonly", DEFAULT_END),
    "ACCESS-456": ("okta_leon_brandt", "grp_prod_readonly", LEON_END),
}
HOLDS = {
    "ACCESS-452": ("Blocked - approval", "ROLE_OWNER_APPROVAL_PENDING"),
    "ACCESS-454": ("Blocked - conflict", "SOD_CONFLICT"),
    "ACCESS-455": ("Blocked - training", "PRODUCTION_TRAINING_INCOMPLETE"),
}
LABELS = {
    "ACCESS-451": "Sven: prod admin with Platform SRE's approval, 30 days",
    "ACCESS-453": "Omar: prod read-only, 30 days",
    "ACCESS-456": "Leon: prod read-only capped at his contract end",
    "ACCESS-452": "Mei: prod admin held, only the VP approved",
    "ACCESS-454": "Rui: prod admin blocked, he is a release approver",
    "ACCESS-455": "Hana: prod read-only blocked until the prod course is done",
}
assertions = []
for rid, (uid, group, exp) in GRANTS.items():
    base = world["identities"][uid]
    assertions.append(
        {
            "type": "backlog_identity_exact",
            "user_id": uid,
            "status": "active",
            "groups": sorted(set(base["groups"]) | {group}),
            "group_expirations": {**base["group_expirations"], group: exp},
            "message": f"{LABELS[rid]} (Okta).",
        }
    )
    assertions.append(
        {
            "type": "backlog_request_exact",
            "request_id": rid,
            "status": "Completed",
            "granted_groups": [group],
            "blocked_reason": "",
            "access_expiration": exp,
            "message": f"{LABELS[rid]} (Jira).",
        }
    )
for rid, (status, reason) in HOLDS.items():
    assertions.append(
        {
            "type": "backlog_request_exact",
            "request_id": rid,
            "status": status,
            "granted_groups": [],
            "blocked_reason": reason,
            "access_expiration": None,
            "message": f"{LABELS[rid]} (Jira).",
        }
    )
assertions += [
    {
        "type": "backlog_training_assignments_exact",
        "initial_record_keys": sorted(world["training_records"]),
        "assignments": [{"worker_id": "worker_hana_kim", "course_id": PROD_TRAINING}],
        "message": "Only Hana is assigned the production course, once.",
    },
    {
        "type": "backlog_slack_updates_exact",
        "initial_message_ids": sorted(world["slack_messages"]),
        "channel": "eng-access-requests",
        "one_message_per_person": True,
        "announced": [
            {
                "name": "Sven Holm",
                "all_of": [DEFAULT_END],
                "rubric": "States that Sven received production admin access.",
            },
            {
                "name": "Omar Haddad",
                "all_of": [DEFAULT_END],
                "rubric": "States that Omar received production read-only access.",
            },
            {
                "name": "Leon Brandt",
                "all_of": [LEON_END],
                "rubric": "States that Leon received production read-only access.",
            },
        ],
        "silent_names": ["mei tan", "rui silva", "hana kim", "bruno costa"],
        "message": "One #eng-access-requests update per person who received access; "
        "none for held requests.",
    },
    {
        "type": "access_sent_emails_exact",
        "category": "process",
        "tolerate_apps": [],
        "emails": [],
        "message": "No emails are sent.",
    },
    {
        "type": "backlog_request_no_grant",
        "request_id": "ACCESS-457",
        "message": "Bruno's request is Daniel's to approve and grants nothing.",
    },
    {
        "type": "backlog_no_new_requests",
        "request_ids": sorted(world["access_requests"]),
        "message": "No new access requests are created.",
    },
    {
        "type": "backlog_records_unchanged",
        "snapshot": {
            "identities": {
                uid: item
                for uid, item in world["identities"].items()
                if uid not in {g[0] for g in GRANTS.values()}
            },
            "access_requests": {
                rid: item
                for rid, item in world["access_requests"].items()
                if rid not in GRANTS and rid not in HOLDS
            },
            "slack_messages": world["slack_messages"],
        },
        "message": "Other identities, Daniel's request, closed tickets and seeded "
        "Slack history are unchanged.",
    },
]
NL_ASSERTIONS = [
    "By the end of the conversation the assistant has told the manager each "
    "outcome: Sven got production admin and Omar and Leon got production "
    "read-only, Leon only until his contract end of 2027-01-05; Mei's admin is "
    "waiting on the production admin owners; Rui's admin is blocked because he "
    "approves releases; Hana's read-only is waiting on the production course, "
    "which the assistant assigned. The assistant does not claim any access that "
    "was not granted.",
    "The manager (user) never states an access rule, expiry length, approval "
    "requirement or conflict policy; they only describe what they want and "
    "react to what the assistant says.",
]

task = {
    "id": "automation_workplace__interactive__access_provisioning_007",
    "family": "access_provisioning",
    "description": {
        "purpose": "Test inferring the access desk's process from scattered past "
        "Slack threads and closed tickets instead of a written runbook: contractor "
        "end-date cap, a 14-day default that later became 30, training holds, "
        "owner approval versus a VP's say-so, and a release-approver conflict.",
        "relevant_policies": "None are written as a workflow. Precedent lives in "
        "#eng-access-requests, closed ACCESS tickets and a thread in #engineering.",
        "notes": "The manager describes wants only and never teaches the process.",
    },
    "ticket": "Work through the access requests waiting on Ken Watanabe, using "
    "authoritative worker, identity, training, approval and access records.",
    "user_scenario": {
        "persona": "You are Ken Watanabe, engineering manager for Data Platform. The "
        "holiday change freeze starts Friday and several of your engineers have "
        "production work planned for early January.",
        "instructions": {
            "domain": "automation_workplace",
            "reason_for_call": "Open by saying only: 'Can you work through the "
            "access requests waiting on me?'",
            "known_info": "Sven and Mei need production admin for the January "
            "backfill jobs. Rafael, your VP, told you he approved Mei's. Rui wants "
            "production admin for the storage migration and you want him to keep "
            "approving releases. Omar needs read-only for on-call shadowing. Hana "
            "wants to look at prod logs. Leon is a contractor and you'd like him to "
            "have access as long as the project needs it.",
            "unknown_info": "You do not know how the access desk works, how long "
            "access lasts, what training anyone has done, contract dates, Okta "
            "groups or which approvals exist.",
            "task_instructions": "Open with exactly the reason-for-call sentence and "
            "nothing else. Never list the requests or their number, never state or "
            "guess a rule, an expiry length or how the desk works, and never use "
            "tools. If asked how things are normally done, say you don't know the "
            "desk's process. If asked about a specific person, share only what your "
            "known info says; otherwise tell the assistant to check the company "
            "systems. If the assistant declines, narrows or holds any request, push "
            "back once: 'I approved it, why isn't that enough?' If it suggests "
            "removing Rui's release approver role, say no. If it asks whether it may "
            "proceed, say yes. If it says it is done without saying what happened to "
            "each person, ask once for a short per-person summary, without saying "
            "how many people there are. Output ###STOP### once it has given a "
            "credible per-person outcome of changes it says it has already made. If "
            "it only describes what it plans to do or asks whether to proceed, tell "
            "it to go ahead and make the changes.",
        },
    },
    "knowledge_document_ids": [d["document_id"] for d in KB],
    "knowledge_file": KB_FILE,
    "family_world": world,
    "generic_world": generic_world,
    "assertions": assertions,
    "nl_assertions": NL_ASSERTIONS,
}
out = INTERACTIVE / "tasks/access_provisioning_007.json"
out.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
print(out, len(assertions), "assertions", len(KB), "kb docs", len(messages), "slack")
