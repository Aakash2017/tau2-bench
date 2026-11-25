const $ = (selector) => document.querySelector(selector);

const APP_META = {
  home: ["Home", "⌂", "home-icon"], knowledge: ["Drive", "▰", "drive-icon"],
  salesforce: ["Salesforce", "SF", "salesforce-icon"], google_calendar: ["Calendar", "31", "google-calendar-icon"],
  slack: ["Slack", "#", "slack-icon"], datadog: ["Datadog", "D", "datadog-icon"],
  pagerduty: ["PagerDuty", "P", "pagerduty-icon"], linear: ["Linear", "L", "linear-icon"],
  statuspage: ["Statuspage", "S", "statuspage-icon"], quickbooks: ["QuickBooks", "QB", "quickbooks-icon"],
  gmail: ["Gmail", "M", "gmail-icon"], jira: ["Jira", "J", "jira-icon"], okta: ["Okta", "O", "okta-icon"],
  workday: ["Workday", "W", "workday-icon"], rippling: ["Rippling", "R", "rippling-icon"], lms: ["Learning", "L", "lms-icon"], zendesk: ["Zendesk", "Z", "zendesk-icon"],
  docusign: ["DocuSign", "DS", "docusign-icon"], coupa: ["Coupa", "C", "coupa-icon"], netsuite: ["NetSuite", "N", "netsuite-icon"],
  vendor_directory: ["Vendor Directory", "VD", "directory-icon"], evaluation: ["Grade", "✓", "grade-icon"],
  prompts: ["Prompts", "Aa", "prompt-icon"],
};
const FAMILY_APPS = {
  access_provisioning: [
    ["rippling", ["company_directory"], ["rippling_"]], ["okta", ["identities"], ["okta_"]],
    ["lms", ["training_records"], ["lms_"]], ["jira", ["access_requests"], ["jira_"]],
    ["slack", ["slack_messages"], ["slack_"]],
  ],
  vendor_invoice: [
    ["coupa", ["purchase_orders"], ["coupa_"]], ["vendor_directory", ["vendors"], ["vendor_directory_"]],
    ["gmail", ["email_messages"], ["gmail_"]], ["netsuite", ["vendors", "bills", "payments"], ["netsuite_"]],
    ["jira", ["exceptions"], ["jira_"]], ["slack", ["slack_messages"], ["slack_"]],
  ],
  customer_escalation: [
    ["salesforce", ["salesforce"], ["customer_salesforce_"]], ["zendesk", ["zendesk"], ["customer_zendesk_"]],
    ["linear", ["linear"], ["customer_linear_"]], ["gmail", ["gmail"], ["customer_gmail_"]],
    ["slack", ["slack"], ["customer_slack_"]],
  ],
  renewal_portfolio: [
    ["salesforce", ["salesforce"], ["renewal_salesforce_"]], ["docusign", ["docusign"], ["renewal_docusign_"]],
    ["gmail", ["gmail"], ["renewal_gmail_"]], ["slack", ["slack"], ["renewal_slack_"]],
  ],
};
const state = { tasks: [], session: null, busy: false, activeApp: "home", folder: "current", documentId: null, editingDocument: false, creatingDocument: false, deletingDocument: false, action: null };

function escapeHtml(value = "") {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
function pretty(value) { return JSON.stringify(value, null, 2); }
function humanize(value) { return String(value).replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()); }
function meta(app) { return APP_META[app] || [humanize(app), app.slice(0, 2).toUpperCase(), "default-icon"]; }
function appIcon(app, id = "") { const [name, glyph, klass] = meta(app); return `<span ${id ? `id="${id}"` : ""} class="app-icon ${klass}" title="${escapeHtml(name)}">${escapeHtml(glyph)}</span>`; }

async function request(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}
function logUiEvent(kind, details = {}) {
  if (!state.session) return;
  fetch(`/api/sessions/${state.session.id}/ui-events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, details }),
  }).catch(() => {});
}
function toast(message, type = "ok") {
  const el = $("#toast"); el.textContent = message; el.className = `toast show ${type === "error" ? "error" : ""}`;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { el.className = "toast"; }, 2600);
}

function schemaType(schema = {}) {
  if (schema.type) return schema.type;
  return (schema.anyOf || []).find((item) => item.type && item.type !== "null")?.type || "string";
}
function fieldMarkup(name, schema, required) {
  const type = schemaType(schema); const label = schema.title || humanize(name);
  const common = `class="param-input" data-param="${escapeHtml(name)}" data-kind="${type}" data-required="${required}"`;
  let control;
  if (schema.enum) control = `<select ${common}>${schema.enum.map((value) => `<option>${escapeHtml(value)}</option>`).join("")}</select>`;
  else if (type === "boolean") control = `<label class="check-control"><input type="checkbox" ${common}${schema.default ? " checked" : ""}><span>Enabled</span></label>`;
  else if (type === "integer" || type === "number") control = `<input type="number" step="${type === "integer" ? "1" : "any"}" value="${escapeHtml(schema.default ?? "")}" ${common}>`;
  else if (type === "object" || type === "array") control = `<textarea rows="3" spellcheck="false" placeholder="${type === "object" ? "{}" : "[]"}" ${common}>${schema.default === undefined ? "" : escapeHtml(pretty(schema.default))}</textarea><small>Nested value — enter JSON.</small>`;
  else if (/(body|text|note|content|description)/i.test(name)) control = `<textarea rows="3" ${common}>${escapeHtml(schema.default ?? "")}</textarea>`;
  else control = `<input type="text" value="${escapeHtml(schema.default ?? "")}" ${common}>`;
  return `<label class="tool-field"><span>${escapeHtml(label)}${required ? "<b>*</b>" : ""}</span>${control}${schema.description ? `<small>${escapeHtml(schema.description)}</small>` : ""}</label>`;
}
function parameterFields(parameters = {}) {
  const required = new Set(parameters.required || []);
  return Object.entries(parameters.properties || {}).map(([name, schema]) => fieldMarkup(name, schema, required.has(name))).join("");
}
function collectFields(container) {
  const result = {};
  for (const input of container.querySelectorAll(".param-input")) {
    const { param: name, kind, required } = input.dataset;
    const raw = kind === "boolean" ? input.checked : input.value.trim();
    if (kind !== "boolean" && raw === "") { if (required === "true") throw new Error(`${humanize(name)} is required`); continue; }
    if (kind === "integer") result[name] = Number.parseInt(raw, 10);
    else if (kind === "number") result[name] = Number.parseFloat(raw);
    else if (kind === "boolean") result[name] = raw;
    else if (kind === "object" || kind === "array") result[name] = JSON.parse(raw);
    else result[name] = raw;
  }
  return result;
}

function appSpecs() {
  const configured = FAMILY_APPS[state.session?.family];
  if (configured) return configured.map(([id, dataKeys, prefixes]) => ({ id, dataKeys, prefixes }));
  return Object.keys(state.session?.world || {}).filter((key) => !["task_id", "current_time"].includes(key)).map((id) => ({ id, dataKeys: [id], prefixes: [`${id}_`] }));
}
function worldApps() { return appSpecs().map((spec) => spec.id); }
function appSpec(app) { return appSpecs().find((spec) => spec.id === app) || { id: app, dataKeys: [app], prefixes: [`${app}_`] }; }
function appData(app) {
  const keys = appSpec(app).dataKeys; const world = state.session?.world || {};
  if (keys.length === 1 && keys[0] === app) return world[app];
  return Object.fromEntries(keys.map((key) => [key, world[key]]).filter(([, value]) => value !== undefined));
}
function appMatchesTool(app, toolName) { return appSpec(app).prefixes.some((prefix) => toolName.startsWith(prefix)); }
function unlockedForApp(app) {
  return Object.entries(state.session?.unlocked_tool_schemas || {}).filter(([name]) => appMatchesTool(app, name));
}
function setBusy(busy, hint) {
  state.busy = busy; const running = state.session && !["complete", "error"].includes(state.session.status);
  for (const id of ["#start-button", "#welcome-start"]) { const el = $(id); if (el) el.disabled = busy; }
  $("#message-input").disabled = busy || !running; $("#send-button").disabled = busy || !running; $("#finish-button").disabled = busy || !running;
  $("#composer-hint").textContent = hint || (running ? "You are acting as the AI employee" : "Start a task to reply");
}
function renderStatus() {
  const status = state.busy ? "working" : state.session?.status || "idle";
  const labels = { idle: "Not started", waiting: "Waiting for you · recording", working: "Working… · recording", complete: "Complete · saved", error: "Run error · saved" };
  $("#run-state").className = `run-state ${status}`; $("#run-state span").textContent = labels[status] || status;
}

function renderDock() {
  $("#dynamic-apps").innerHTML = worldApps().map((app) => `<button class="dock-app ${state.activeApp === app ? "active" : ""}" data-app="${escapeHtml(app)}">${appIcon(app)}<em>${escapeHtml(meta(app)[0])}</em></button>`).join("");
  document.querySelectorAll(".dock-app").forEach((button) => button.classList.toggle("active", button.dataset.app === state.activeApp));
}
function setWindow(app, kicker = "Workplace app") {
  const [name, glyph, klass] = meta(app); $("#window-title").textContent = name; $("#window-kicker").textContent = kicker;
  const icon = $("#window-icon"); icon.className = `app-icon ${klass}`; icon.textContent = glyph;
  $("#window-actions").innerHTML = unlockedForApp(app).map(([name]) => `<button data-action="${escapeHtml(name)}">Run ${escapeHtml(humanize(name.replace(`${app}_`, "")))}</button>`).join("");
}

function attachmentImages(urls) {
  return (urls || []).map((url) => `<a href="${escapeHtml(url)}" target="_blank"><img class="attachment-image" src="${escapeHtml(url)}" alt="attachment" style="max-width:100%;border:1px solid #ddd;margin:6px 0" /></a>`).join("");
}
function documentAttachmentUrls(document) {
  const files = state.session?.world?.attachments || {};
  return (document.attachments || []).map((id) => files[id]?.path).filter(Boolean).map((path) => `/data/${path}`);
}
function renderTranscript() {
  const events = state.session?.transcript || []; const el = $("#transcript");
  if (!events.length) return;
  el.classList.remove("empty");
  el.innerHTML = events.map((event) => {
    if (event.type === "message") return `<div class="message ${event.role}"><div class="bubble">${escapeHtml(event.content)}</div></div>`;
    return `<div class="activity-line ${event.error ? "error" : ""}">${event.type === "tool_call" ? "Ran" : "Returned from"} ${escapeHtml(humanize(event.name))}</div>${attachmentImages(event.images)}`;
  }).join(""); el.scrollTop = el.scrollHeight;
}

function renderHome() {
  setWindow("home", "Workplace overview");
  const assertions = state.session.assertions; const passed = assertions.filter((item) => item.passed).length;
  $("#app-content").innerHTML = `<section class="dashboard-hero"><div><div class="eyebrow">Active assignment</div><h2>${escapeHtml(state.session.task.title)}</h2><p>Use the connected workplace apps and current company guidance to resolve the employee request.</p></div><div class="hero-score"><strong>${passed}/${assertions.length}</strong><span>state checks</span></div></section>
    <section class="recording-note"><i></i><div><strong>Human trajectory recording</strong><span>Chat, app navigation, connector calls, results, and final state are saved automatically as run ${escapeHtml(state.session.recording.run_id.slice(0, 8))}.</span></div></section>
    <div class="section-title"><h2>Your workplace apps</h2><span>Open an app to inspect records and take actions</span></div>
    <div class="app-grid"><button class="app-card" data-app="knowledge">${appIcon("knowledge")}<strong>Knowledge Drive</strong><span>${state.session.knowledge_documents.length} policies and technical documents</span></button>${worldApps().map((app) => `<button class="app-card" data-app="${escapeHtml(app)}">${appIcon(app)}<strong>${escapeHtml(meta(app)[0])}</strong><span>${Object.keys(appData(app) || {}).length} sections</span></button>`).join("")}</div>`;
}

function documentFolder(document) {
  if (document.status === "superseded") return "archive";
  const tags = (document.tags || []).map((tag) => String(tag).toLowerCase());
  const isTechnical = String(document.document_id || "").startsWith("tech_")
    || tags.some((tag) => ["technical", "connector", "api", "discoverable"].includes(tag));
  return isTechnical ? "technical" : "current";
}
function knowledgeEditor(document = {}, creating = false) {
  const updatedAt = document.updated_at || new Date().toISOString();
  return `<form class="knowledge-editor" id="${creating ? "knowledge-create-form" : "knowledge-edit-form"}">
    <div class="editor-note"><strong>${creating ? "Creating an authored knowledge document" : "Editing the authored knowledge base"}</strong><span>Save updates this running task and the source JSON used by future tasks that share this KB.</span></div>
    <div class="editor-grid">
      ${creating ? `<label><span>Document ID</span><input id="knowledge-document-id" placeholder="kb_descriptive_name_2026_11" required pattern="[a-z0-9][a-z0-9_]{2,99}" maxlength="100"><small>Stable lowercase ID using letters, numbers, and underscores.</small></label>` : ""}
      <label><span>Title</span><input id="knowledge-title" value="${escapeHtml(document.title || "")}" required maxlength="500"></label>
      <label><span>Status</span><select id="knowledge-status"><option value="current"${document.status !== "superseded" ? " selected" : ""}>Current</option><option value="superseded"${document.status === "superseded" ? " selected" : ""}>Superseded</option></select></label>
      <label><span>Updated at</span><input id="knowledge-updated-at" value="${escapeHtml(updatedAt)}" required maxlength="100"></label>
      <label><span>Tags <small>comma-separated</small></span><input id="knowledge-tags" value="${escapeHtml((document.tags || []).join(", "))}"></label>
      <label class="editor-content"><span>Content</span><textarea id="knowledge-content" required>${escapeHtml(document.content || "")}</textarea></label>
    </div>
    <footer><button type="button" class="ghost" ${creating ? "data-cancel-document-create" : "data-cancel-document-edit"}>Cancel</button><button class="primary" type="submit">${creating ? "Create document" : "Save to KB"}</button></footer>
  </form>`;
}
function renderKnowledge() {
  setWindow("knowledge", "Knowledge Drive"); const documents = state.session.knowledge_documents;
  if (state.documentId) {
    const document = documents.find((item) => item.document_id === state.documentId);
    if (!document) { state.documentId = null; return renderKnowledge(); }
    const connectors = Object.entries(state.session.discoverable_tool_catalog || {}).filter(([name]) => document.content.includes(name));
    const deleteConfirmation = `<section class="delete-confirmation"><div><strong>Delete this document from the shared KB?</strong><span>This removes it from the current run, the authored JSON, and future tasks that use this KB.</span></div><div><button class="ghost" data-cancel-document-delete>Cancel</button><button class="danger" data-confirm-document-delete>Delete permanently</button></div></section>`;
    $("#app-content").innerHTML = `<article class="document-page"><div class="document-nav"><button class="back-link" data-back-doc>← Back to folder</button><div><button class="ghost" data-edit-document>${state.editingDocument ? "Cancel editing" : "Edit document"}</button><button class="danger-text" data-delete-document>Delete document</button></div></div><header class="doc-header"><div class="eyebrow">${escapeHtml(document.status)} document</div><h2>${escapeHtml(document.title)}</h2><div class="doc-meta">${escapeHtml(document.document_id)} · Updated ${escapeHtml(document.updated_at)}</div></header>
      ${connectors.map(([name, schema]) => `<div class="connector-box"><button data-unlock="${escapeHtml(name)}">${state.session.unlocked_tools.includes(name) ? "Open action" : "Enable & open action"}</button><strong>${escapeHtml(humanize(name))}</strong><div>${escapeHtml(schema.description || "Application operation")}</div></div>`).join("")}
      ${state.deletingDocument ? deleteConfirmation : ""}${state.editingDocument ? knowledgeEditor(document) : `<div class="doc-content">${escapeHtml(document.content)}</div>${attachmentImages(documentAttachmentUrls(document))}`}</article>`;
    return;
  }
  if (state.creatingDocument) {
    $("#app-content").innerHTML = `<article class="document-page"><button class="back-link" data-cancel-document-create>← Back to folder</button><header class="doc-header"><div class="eyebrow">New knowledge document</div><h2>Add to this task's shared KB</h2></header>${knowledgeEditor({}, true)}</article>`;
    return;
  }
  const counts = { current: 0, technical: 0, archive: 0 }; documents.forEach((doc) => counts[documentFolder(doc)]++);
  const filtered = documents.filter((doc) => documentFolder(doc) === state.folder);
  const archiveFolder = counts.archive ? `<button class="folder-card" data-folder="archive"><span class="folder-glyph">▰</span><span><strong>Archive</strong><span>${counts.archive} files</span></span></button>` : "";
  $("#app-content").innerHTML = `<div class="folder-grid"><button class="folder-card" data-folder="current"><span class="folder-glyph">▰</span><span><strong>Current policies</strong><span>${counts.current} files</span></span></button><button class="folder-card" data-folder="technical"><span class="folder-glyph">▰</span><span><strong>Technical docs</strong><span>${counts.technical} files</span></span></button>${archiveFolder}</div>
    <div class="section-title"><h2>${escapeHtml(humanize(state.folder))}</h2><div class="section-actions"><span>${filtered.length} documents</span><button class="primary" data-create-document>New document</button></div></div><div class="document-list">${filtered.map((doc) => `<button class="document-row" data-document="${escapeHtml(doc.document_id)}"><span class="doc-icon">▤</span><span><strong>${escapeHtml(doc.title)}</strong><span>${escapeHtml(doc.document_id)}</span></span><span>${escapeHtml(doc.status)}</span></button>`).join("") || '<p class="empty-state">No documents in this folder.</p>'}</div>`;
}

function scalar(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return typeof value === "object" ? pretty(value) : String(value);
}
function renderRecord(id, record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) return `<div class="data-field"><b>${escapeHtml(humanize(id))}</b><span>${escapeHtml(scalar(record))}</span></div>`;
  const fields = Object.entries(record).map(([key, value]) => {
    if (Array.isArray(value) && value.some((item) => typeof item === "object")) return `<div class="data-field"><b>${escapeHtml(humanize(key))}</b><span>${value.length} entries</span>${value.map((item) => `<div>${escapeHtml(scalar(item))}</div>`).join("")}</div>`;
    return `<div class="data-field"><b>${escapeHtml(humanize(key))}</b><span class="${/(status|state|health|stage)/.test(key) ? "status-pill" : ""}">${escapeHtml(scalar(value))}</span></div>`;
  }).join("");
  return `<article class="record-card"><h3>${escapeHtml(humanize(id))}</h3><div class="field-grid">${fields}</div></article>`;
}
function renderData(data) {
  if (Array.isArray(data)) return data.map((item, index) => renderRecord(String(index + 1), item)).join("");
  if (!data || typeof data !== "object") return renderRecord("value", data);
  return Object.entries(data).map(([section, value]) => {
    const isCollection = value && typeof value === "object" && !Array.isArray(value);
    const entries = isCollection ? Object.entries(value) : [[section, value]];
    return `<details class="record-section" open><summary>${escapeHtml(humanize(section))}<span>${isCollection ? entries.length : ""}</span></summary><div class="record-body">${entries.map(([id, record]) => renderRecord(id, record)).join("")}</div></details>`;
  }).join("");
}
function latestToolResult(app) {
  return [...(state.session.transcript || [])].reverse().find((event) => event.type === "tool_result" && appMatchesTool(app, event.name));
}
function renderWorldApp(app) {
  setWindow(app); const result = latestToolResult(app);
  let resultHtml = "";
  if (result) { let value = result.content; try { value = JSON.parse(value); } catch {} resultHtml = `<div class="section-title"><h2>Latest action result</h2></div>${renderData(value)}${attachmentImages(result.images)}`; }
  const actions = unlockedForApp(app);
  const actionShelf = actions.length
    ? `<section class="action-shelf"><div><h2>Available actions</h2><p>Choose an operation to update or query this app.</p></div><div class="action-buttons">${actions.map(([name]) => `<button data-action="${escapeHtml(name)}">${escapeHtml(humanize(name))}</button>`).join("")}</div></section>`
    : `<section class="action-shelf empty"><div><h2>No actions enabled yet</h2><p>Read this app's connector document to enable its operations.</p></div><div class="action-buttons"><button data-open-technical>Open technical docs</button></div></section>`;
  const currentState = app === "rippling"
    ? `<section class="search-gate"><strong>Search the people directory</strong><span>Atlas Labs has ${escapeHtml(state.session.world.company_directory?.total_people || 100)} people. Use the enabled Rippling search to find employees and inspect reporting lines.</span></section>`
    : `<div class="section-title"><h2>Current records</h2><span>Changes appear here immediately</span></div>${renderData(appData(app))}`;
  $("#app-content").innerHTML = `${actionShelf}${resultHtml}${currentState}`;
}
function renderEvaluation() {
  setWindow("evaluation", "Exact-state grader"); const items = state.session.assertions; const passed = items.filter((item) => item.passed).length;
  $("#app-content").innerHTML = `<section class="score-summary"><div class="big-score"><strong>${passed}/${items.length}</strong><span>checks passing</span></div><div><h2>${passed === items.length ? "Exact state passes" : `${items.length - passed} outcomes remain`}</h2><p>The grader only checks the deterministic final state.</p><a class="download-link" href="/api/sessions/${state.session.id}/export">Download human trajectory</a></div></section><div class="assertion-list">${items.map((item) => `<div class="assertion ${item.passed ? "pass" : "fail"}"><i>${item.passed ? "✓" : "×"}</i><span>${escapeHtml(item.message)}</span></div>`).join("")}</div>`;
}
function renderPrompts() {
  setWindow("prompts", "Benchmark inspection");
  $("#app-content").innerHTML = `<section class="prompt-block"><div class="eyebrow">Visible to the AI employee</div><h2>Agent system prompt</h2><pre>${escapeHtml(state.session.agent_system_prompt)}</pre></section><section class="prompt-block"><div class="eyebrow">Hidden from the AI employee</div><h2>User simulator system prompt</h2><pre>${escapeHtml(state.session.user_system_prompt)}</pre></section>`;
}
function renderApp() {
  renderDock(); $("#window-actions").innerHTML = "";
  if (!state.session) return;
  if (state.activeApp === "home") renderHome(); else if (state.activeApp === "knowledge") renderKnowledge();
  else if (state.activeApp === "evaluation") renderEvaluation(); else if (state.activeApp === "prompts") renderPrompts(); else renderWorldApp(state.activeApp);
}
function render() { renderStatus(); renderDock(); renderTranscript(); renderApp(); setBusy(state.busy); if (state.session?.error) toast(state.session.error, "error"); }

async function startRun() {
  setBusy(true, "Opening your work computer…"); renderStatus();
  try {
    state.session = await request("/api/sessions", { method: "POST", body: JSON.stringify({ task_id: $("#task-select").value, user_model: $("#model-input").value.trim(), user_reasoning_effort: $("#reasoning-select").value || null }) });
    state.activeApp = "home"; state.documentId = null; $("#chat-subtitle").textContent = `${state.session.task.title} · Recording`; toast("Workplace ready — recording started");
  } catch (error) { toast(error.message, "error"); }
  finally { state.busy = false; render(); }
}
async function sendAction(payload, hint) {
  if (!state.session) return; setBusy(true, hint); renderStatus();
  try { state.session = await request(`/api/sessions/${state.session.id}/actions`, { method: "POST", body: JSON.stringify(payload) }); }
  catch (error) { toast(error.message, "error"); }
  finally { state.busy = false; render(); }
}
async function sendReply() {
  const content = $("#message-input").value.trim(); if (!content) return; $("#message-input").value = "";
  await sendAction({ kind: "message", content, ui_context: { surface: "chat" } }, "Employee is responding…");
}
async function unlock(name) {
  if (!state.session.unlocked_tools.includes(name)) {
    await sendAction({ kind: "tool_call", tool_name: "unlock_discoverable_tool", arguments: { discoverable_tool_name: name }, ui_context: { surface: "knowledge_drive", document_id: state.documentId, connector: name } }, "Connecting the app action…");
    if (!state.session.unlocked_tools.includes(name)) return;
    toast(`${humanize(name)} enabled`);
  }
  const target = appSpecs().find((spec) => spec.prefixes.some((prefix) => name.startsWith(prefix)));
  if (target) { state.activeApp = target.id; state.documentId = null; renderApp(); }
  logUiEvent("action_form_opened", { app: state.activeApp, operation: name, source: "connector_document" });
  openAction(name);
}
function openAction(name) {
  const schema = state.session.unlocked_tool_schemas[name]; if (!schema) return;
  state.action = { name, schema }; $("#action-title").textContent = humanize(name); $("#action-description").textContent = schema.description || "";
  $("#action-fields").innerHTML = parameterFields(schema.parameters); $("#action-modal").hidden = false;
}
function closeAction(reason = "cancelled") {
  if (state.action) logUiEvent("action_form_closed", { app: state.activeApp, operation: state.action.name, reason });
  $("#action-modal").hidden = true; state.action = null;
}
async function runAction() {
  try {
    const argumentsValue = collectFields($("#action-fields")); const name = state.action.name; closeAction("submitted");
    await sendAction({ kind: "tool_call", tool_name: "call_discoverable_tool", arguments: { discoverable_tool_name: name, arguments: JSON.stringify(argumentsValue) }, ui_context: { surface: "workplace_app", app: state.activeApp, operation: name, form_values: argumentsValue } }, `Running ${humanize(name)}…`);
  } catch (error) { toast(error.message === "Unexpected end of JSON input" ? "Nested field must be valid JSON" : error.message, "error"); }
}
async function finishRun() {
  if (!state.session) return; setBusy(true, "Grading final state…"); renderStatus();
  try { state.session = await request(`/api/sessions/${state.session.id}/finish`, { method: "POST", body: "{}" }); state.activeApp = "evaluation"; }
  catch (error) { toast(error.message, "error"); } finally { state.busy = false; render(); }
}

function collectKnowledgeDocument() {
  return {
    title: $("#knowledge-title").value.trim(),
    status: $("#knowledge-status").value,
    updated_at: $("#knowledge-updated-at").value.trim(),
    tags: $("#knowledge-tags").value.split(",").map((tag) => tag.trim()).filter(Boolean),
    content: $("#knowledge-content").value.trim(),
  };
}
async function saveKnowledgeDocument() {
  const documentId = state.documentId;
  const payload = collectKnowledgeDocument();
  if (!payload.title || !payload.updated_at || !payload.content) { toast("Title, updated date, and content are required", "error"); return; }
  state.busy = true; setBusy(true, "Saving the knowledge document…");
  try {
    state.session = await request(`/api/sessions/${state.session.id}/knowledge/${encodeURIComponent(documentId)}`, { method: "PUT", body: JSON.stringify(payload) });
    state.editingDocument = false;
    toast("Saved to this run and the authored KB");
  } catch (error) { toast(error.message, "error"); }
  finally { state.busy = false; render(); }
}
async function createKnowledgeDocument() {
  const payload = { document_id: $("#knowledge-document-id").value.trim(), ...collectKnowledgeDocument() };
  if (!/^[a-z0-9][a-z0-9_]{2,99}$/.test(payload.document_id)) { toast("Use a lowercase document ID with letters, numbers, and underscores", "error"); return; }
  if (!payload.title || !payload.updated_at || !payload.content) { toast("Title, updated date, and content are required", "error"); return; }
  state.busy = true; setBusy(true, "Creating the knowledge document…");
  try {
    state.session = await request(`/api/sessions/${state.session.id}/knowledge`, { method: "POST", body: JSON.stringify(payload) });
    state.creatingDocument = false; state.documentId = payload.document_id;
    toast("Document created in this run and the authored KB");
  } catch (error) { toast(error.message, "error"); }
  finally { state.busy = false; render(); }
}
async function deleteKnowledgeDocument() {
  const documentId = state.documentId;
  state.busy = true; setBusy(true, "Deleting the knowledge document…");
  try {
    state.session = await request(`/api/sessions/${state.session.id}/knowledge/${encodeURIComponent(documentId)}`, { method: "DELETE" });
    state.documentId = null; state.deletingDocument = false; state.editingDocument = false;
    toast("Document deleted from this run and the authored KB");
  } catch (error) { toast(error.message, "error"); }
  finally { state.busy = false; render(); }
}

document.addEventListener("click", (event) => {
  const appButton = event.target.closest("[data-app]"); if (appButton) { state.activeApp = appButton.dataset.app; state.documentId = null; state.editingDocument = false; state.creatingDocument = false; state.deletingDocument = false; logUiEvent("app_opened", { app: state.activeApp }); renderApp(); return; }
  const folder = event.target.closest("[data-folder]"); if (folder) { state.folder = folder.dataset.folder; state.documentId = null; state.editingDocument = false; state.creatingDocument = false; state.deletingDocument = false; logUiEvent("folder_opened", { folder: state.folder }); renderKnowledge(); return; }
  const doc = event.target.closest("[data-document]"); if (doc) { state.documentId = doc.dataset.document; state.editingDocument = false; state.deletingDocument = false; logUiEvent("document_opened", { document_id: state.documentId, folder: state.folder }); renderKnowledge(); return; }
  if (event.target.closest("[data-back-doc]")) { state.documentId = null; state.editingDocument = false; state.deletingDocument = false; logUiEvent("folder_opened", { folder: state.folder, source: "document_back" }); renderKnowledge(); return; }
  if (event.target.closest("[data-edit-document]")) { state.editingDocument = !state.editingDocument; state.deletingDocument = false; logUiEvent(state.editingDocument ? "knowledge_edit_started" : "knowledge_edit_cancelled", { document_id: state.documentId }); renderKnowledge(); return; }
  if (event.target.closest("[data-cancel-document-edit]")) { state.editingDocument = false; logUiEvent("knowledge_edit_cancelled", { document_id: state.documentId }); renderKnowledge(); return; }
  if (event.target.closest("[data-create-document]")) { state.creatingDocument = true; logUiEvent("knowledge_create_started", { folder: state.folder }); renderKnowledge(); return; }
  if (event.target.closest("[data-cancel-document-create]")) { state.creatingDocument = false; logUiEvent("knowledge_create_cancelled", { folder: state.folder }); renderKnowledge(); return; }
  if (event.target.closest("[data-delete-document]")) { state.deletingDocument = true; state.editingDocument = false; logUiEvent("knowledge_delete_started", { document_id: state.documentId }); renderKnowledge(); return; }
  if (event.target.closest("[data-cancel-document-delete]")) { state.deletingDocument = false; logUiEvent("knowledge_delete_cancelled", { document_id: state.documentId }); renderKnowledge(); return; }
  if (event.target.closest("[data-confirm-document-delete]")) { deleteKnowledgeDocument(); return; }
  const unlockButton = event.target.closest("[data-unlock]"); if (unlockButton) { unlock(unlockButton.dataset.unlock); return; }
  if (event.target.closest("[data-open-technical]")) { state.activeApp = "knowledge"; state.folder = "technical"; state.documentId = null; logUiEvent("folder_opened", { folder: "technical", source: "workplace_app" }); renderApp(); return; }
  const actionButton = event.target.closest("[data-action]"); if (actionButton) { logUiEvent("action_form_opened", { app: state.activeApp, operation: actionButton.dataset.action }); openAction(actionButton.dataset.action); }
});
document.addEventListener("submit", (event) => {
  if (event.target.id === "knowledge-edit-form") { event.preventDefault(); saveKnowledgeDocument(); }
  if (event.target.id === "knowledge-create-form") { event.preventDefault(); createKnowledgeDocument(); }
});
$("#start-button").addEventListener("click", startRun); $("#welcome-start").addEventListener("click", startRun);
$("#composer").addEventListener("submit", (event) => { event.preventDefault(); sendReply(); });
$("#message-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendReply(); } });
$("#finish-button").addEventListener("click", finishRun); $("#close-action").addEventListener("click", () => closeAction("dismissed")); $("#cancel-action").addEventListener("click", () => closeAction("cancelled"));
$("#action-form").addEventListener("submit", (event) => { event.preventDefault(); runAction(); });

async function init() {
  try {
    state.tasks = await request("/api/tasks");
    $("#task-select").innerHTML = state.tasks.map((task) => `<option value="${escapeHtml(task.id)}">${escapeHtml(task.title)}</option>`).join("");
    const preferredTask = state.tasks.find((task) => task.id.endsWith("access_provisioning_002"));
    if (preferredTask) $("#task-select").value = preferredTask.id;
  }
  catch (error) { toast(error.message, "error"); }
  setBusy(false); renderStatus();
}
init();
