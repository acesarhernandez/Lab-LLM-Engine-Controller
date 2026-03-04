from __future__ import annotations


def render_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LLM Engine Control</title>
  <style>
    :root {
      --ink: #16202a;
      --muted: #5c6975;
      --paper: #f4efe5;
      --panel: rgba(255, 250, 241, 0.84);
      --line: rgba(28, 41, 53, 0.12);
      --signal-ready: #147d64;
      --signal-waking: #d16d1a;
      --signal-alert: #b73926;
      --signal-idle: #5f6975;
      --shadow: 0 20px 40px rgba(32, 42, 53, 0.12);
      --radius-xl: 28px;
      --radius-lg: 20px;
      --radius-md: 14px;
      --mono: "SFMono-Regular", "Menlo", "Consolas", monospace;
      --sans: "Avenir Next", "Gill Sans", "Trebuchet MS", sans-serif;
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
    }

    * {
      box-sizing: border-box;
    }

    html, body {
      margin: 0;
      min-height: 100%;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(255, 196, 118, 0.35), transparent 38%),
        radial-gradient(circle at left 25%, rgba(90, 146, 190, 0.16), transparent 34%),
        linear-gradient(180deg, #f8f4eb 0%, #ebe3d4 100%);
      font-family: var(--sans);
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.18) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.14) 1px, transparent 1px);
      background-size: 28px 28px;
      opacity: 0.22;
    }

    body {
      position: relative;
    }

    .shell {
      position: relative;
      z-index: 1;
      max-width: 1200px;
      margin: 0 auto;
      padding: 28px 18px 48px;
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
      gap: 18px;
      margin-bottom: 18px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: var(--radius-xl);
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .hero-main {
      padding: 28px;
      position: relative;
      overflow: hidden;
    }

    .hero-main::after {
      content: "";
      position: absolute;
      right: -54px;
      top: -72px;
      width: 180px;
      height: 180px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(209, 109, 26, 0.18), transparent 68%);
    }

    .eyebrow {
      margin: 0 0 12px;
      font-size: 0.78rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 700;
    }

    .hero-title {
      margin: 0;
      font-family: var(--serif);
      font-size: clamp(2.2rem, 5vw, 4.4rem);
      line-height: 0.92;
      max-width: 10ch;
    }

    .hero-copy {
      margin: 14px 0 0;
      max-width: 54ch;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.65;
    }

    .hero-side {
      padding: 22px;
      display: grid;
      gap: 14px;
      align-content: start;
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    .state-pill {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(28, 41, 53, 0.08);
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-size: 0.76rem;
      color: var(--signal-idle);
    }

    .state-dot {
      width: 11px;
      height: 11px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.18);
    }

    .state-ready {
      color: var(--signal-ready);
    }

    .state-waking,
    .state-pc_online {
      color: var(--signal-waking);
    }

    .state-offline,
    .state-misconfigured {
      color: var(--signal-alert);
    }

    .state-waking .state-dot,
    .state-pc_online .state-dot {
      animation: pulse 1.7s infinite;
    }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(209, 109, 26, 0.35); }
      70% { box-shadow: 0 0 0 12px rgba(209, 109, 26, 0); }
      100% { box-shadow: 0 0 0 0 rgba(209, 109, 26, 0); }
    }

    .tiny-meta {
      font-size: 0.82rem;
      color: var(--muted);
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      gap: 18px;
    }

    .rail,
    .stage {
      display: grid;
      gap: 18px;
      align-content: start;
    }

    .card {
      padding: 22px;
    }

    .card h2,
    .card h3 {
      margin: 0;
      font-size: 1rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .card-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }

    .field {
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
    }

    .field label {
      font-size: 0.84rem;
      color: var(--muted);
      font-weight: 700;
    }

    .field input {
      width: 100%;
      padding: 12px 14px;
      border-radius: var(--radius-md);
      border: 1px solid rgba(28, 41, 53, 0.12);
      background: rgba(255, 255, 255, 0.8);
      color: var(--ink);
      font: inherit;
    }

    .toggle {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 6px;
      font-size: 0.9rem;
      color: var(--muted);
    }

    .toggle input {
      width: 18px;
      height: 18px;
      accent-color: #1e6e94;
    }

    .stack {
      display: grid;
      gap: 10px;
    }

    .btn {
      appearance: none;
      border: 0;
      border-radius: 999px;
      padding: 12px 16px;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
    }

    .btn:disabled {
      cursor: wait;
      opacity: 0.7;
    }

    .btn:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 12px 22px rgba(22, 32, 42, 0.14);
    }

    .btn-primary {
      background: linear-gradient(135deg, #183b58 0%, #2b7196 100%);
      color: #fff;
    }

    .btn-signal {
      background: linear-gradient(135deg, #cc6128 0%, #e4932a 100%);
      color: #fff;
    }

    .btn-quiet {
      background: rgba(255, 255, 255, 0.78);
      color: var(--ink);
      border: 1px solid rgba(28, 41, 53, 0.1);
    }

    .status-blade {
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(220px, 0.9fr);
      gap: 18px;
    }

    .summary {
      display: grid;
      gap: 16px;
    }

    .summary-title {
      margin: 0;
      font-size: clamp(1.5rem, 4vw, 2.8rem);
      line-height: 1;
      font-family: var(--serif);
    }

    .summary-copy {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
      font-size: 1rem;
    }

    .glance {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .glance-item {
      border-radius: var(--radius-lg);
      padding: 14px;
      border: 1px solid rgba(28, 41, 53, 0.08);
      background: rgba(255, 255, 255, 0.64);
    }

    .glance-label {
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }

    .glance-value {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 800;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .detail-item {
      padding: 14px;
      border-radius: var(--radius-lg);
      border: 1px solid rgba(28, 41, 53, 0.08);
      background: rgba(255, 255, 255, 0.68);
    }

    .detail-item dt {
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }

    .detail-item dd {
      margin: 0;
      font-size: 0.95rem;
      line-height: 1.45;
      word-break: break-word;
    }

    .callout {
      border-radius: var(--radius-lg);
      padding: 16px;
      background: linear-gradient(135deg, rgba(14, 52, 74, 0.94), rgba(31, 90, 119, 0.9));
      color: #f8fcff;
    }

    .callout h3 {
      margin-bottom: 8px;
      color: rgba(248, 252, 255, 0.84);
      font-size: 0.84rem;
    }

    .callout p {
      margin: 0;
      line-height: 1.6;
      color: rgba(248, 252, 255, 0.96);
    }

    .status-feed {
      display: grid;
      gap: 10px;
      max-height: 290px;
      overflow: auto;
      padding-right: 4px;
    }

    .feed-item {
      border-radius: var(--radius-lg);
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(28, 41, 53, 0.08);
    }

    .feed-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 6px;
      font-size: 0.8rem;
      color: var(--muted);
    }

    .feed-body {
      margin: 0;
      font-size: 0.92rem;
      line-height: 1.5;
    }

    .status-banner {
      min-height: 22px;
      font-size: 0.9rem;
      color: var(--muted);
    }

    .status-banner.error {
      color: var(--signal-alert);
      font-weight: 700;
    }

    .status-banner.good {
      color: var(--signal-ready);
      font-weight: 700;
    }

    .kbd {
      font-family: var(--mono);
      font-size: 0.82rem;
      padding: 2px 6px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid rgba(28, 41, 53, 0.1);
    }

    .hidden {
      display: none !important;
    }

    @media (max-width: 980px) {
      .hero,
      .layout,
      .status-blade {
        grid-template-columns: 1fr;
      }

      .hero-main,
      .hero-side,
      .card {
        padding: 18px;
      }
    }

    @media (max-width: 640px) {
      .shell {
        padding: 14px 12px 28px;
      }

      .glance,
      .detail-grid {
        grid-template-columns: 1fr;
      }

      .state-pill {
        width: 100%;
        justify-content: center;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="panel hero-main">
        <p class="eyebrow">V1 Control Surface</p>
        <h1 class="hero-title">LLM engine wake and ready status.</h1>
        <p class="hero-copy">
          This dashboard watches the same backend API your other apps will use. It never triggers wake
          from polling alone. You can refresh safely, fire a manual wake when the PC is asleep, or run
          an <span class="kbd">ensure-ready</span> preflight before an app needs Ollama.
        </p>
      </div>
      <aside class="panel hero-side">
        <div class="pill-row">
          <span id="heroState" class="state-pill state-offline">
            <span class="state-dot"></span>
            <span id="heroStateText">No Status Yet</span>
          </span>
        </div>
        <div class="tiny-meta">
          <strong>Polling:</strong> every 3 seconds while auto-refresh is enabled
        </div>
        <div class="tiny-meta">
          <strong>Security:</strong> the API key stays in your browser storage only if you choose to remember it
        </div>
        <div class="tiny-meta">
          <strong>Service:</strong> same-origin dashboard for this engine-control server
        </div>
      </aside>
    </section>

    <section class="layout">
      <aside class="rail">
        <section class="panel card">
          <div class="card-head">
            <h2>Access</h2>
            <span class="tiny-meta">Bearer token</span>
          </div>
          <div class="field">
            <label for="apiKeyInput">API key</label>
            <input id="apiKeyInput" type="password" autocomplete="off" placeholder="Paste ENGINE_API_KEY">
          </div>
          <label class="toggle">
            <span>Remember this key on this browser</span>
            <input id="rememberKeyToggle" type="checkbox">
          </label>
          <div class="stack" style="margin-top: 14px;">
            <button id="connectBtn" class="btn btn-primary">Connect and Load Status</button>
            <button id="clearKeyBtn" class="btn btn-quiet">Clear Saved Key</button>
          </div>
          <p id="authBanner" class="status-banner" aria-live="polite"></p>
        </section>

        <section class="panel card">
          <div class="card-head">
            <h2>Actions</h2>
            <span id="busyTag" class="tiny-meta">Idle</span>
          </div>
          <div class="stack">
            <button id="refreshBtn" class="btn btn-quiet">Refresh Status</button>
            <button id="wakeBtn" class="btn btn-signal">Wake Engine</button>
            <button id="ensureBtn" class="btn btn-primary">Ensure Ready</button>
          </div>
          <label class="toggle" style="margin-top: 14px;">
            <span>Auto-refresh</span>
            <input id="autoRefreshToggle" type="checkbox" checked>
          </label>
          <div class="field" style="margin-top: 14px;">
            <label for="timeoutInput">Ensure-ready timeout (seconds)</label>
            <input id="timeoutInput" type="number" min="1" max="600" value="90">
          </div>
          <p id="actionBanner" class="status-banner" aria-live="polite"></p>
        </section>

        <section class="panel card">
          <div class="card-head">
            <h2>Recent Events</h2>
            <span class="tiny-meta">Client-side log</span>
          </div>
          <div id="feed" class="status-feed"></div>
        </section>
      </aside>

      <section class="stage">
        <section class="panel card">
          <div class="status-blade">
            <div class="summary">
              <div>
                <p class="eyebrow" style="margin-bottom: 10px;">Live Engine Snapshot</p>
                <h2 id="engineLabel" class="summary-title">Awaiting first refresh</h2>
              </div>
              <p id="summaryCopy" class="summary-copy">
                Paste your API key, then load the live status. This panel updates from <span class="kbd">GET /v1/engine/status</span>.
              </p>
              <div class="glance">
                <div class="glance-item">
                  <p class="glance-label">PC Awake</p>
                  <p id="pcAwakeValue" class="glance-value">Unknown</p>
                </div>
                <div class="glance-item">
                  <p class="glance-label">Ollama Ready</p>
                  <p id="ollamaReadyValue" class="glance-value">Unknown</p>
                </div>
                <div class="glance-item">
                  <p class="glance-label">Wake In Progress</p>
                  <p id="wakeProgressValue" class="glance-value">Unknown</p>
                </div>
                <div class="glance-item">
                  <p class="glance-label">Cooldown</p>
                  <p id="cooldownValue" class="glance-value">0s</p>
                </div>
              </div>
            </div>

            <div class="callout">
              <h3>How To Read This</h3>
              <p id="calloutCopy">
                <strong>Offline</strong> means the PC and Ollama are both unreachable. <strong>PC online</strong> means
                Windows is awake, but Ollama is still coming up. <strong>Ready</strong> means apps can safely use the engine.
              </p>
            </div>
          </div>
        </section>

        <section class="panel card">
          <div class="card-head">
            <h2>Signals</h2>
            <span class="tiny-meta">Current raw values</span>
          </div>
          <dl class="detail-grid">
            <div class="detail-item">
              <dt>Engine state</dt>
              <dd id="stateValue">Unknown</dd>
            </div>
            <div class="detail-item">
              <dt>Masked MAC</dt>
              <dd id="macValue">Unknown</dd>
            </div>
            <div class="detail-item">
              <dt>PC host</dt>
              <dd id="hostValue">Unknown</dd>
            </div>
            <div class="detail-item">
              <dt>Probe port</dt>
              <dd id="probePortValue">Unknown</dd>
            </div>
            <div class="detail-item">
              <dt>Ollama URL</dt>
              <dd id="ollamaUrlValue">Unknown</dd>
            </div>
            <div class="detail-item">
              <dt>Wake enabled</dt>
              <dd id="wakeEnabledValue">Unknown</dd>
            </div>
            <div class="detail-item">
              <dt>Last wake sent</dt>
              <dd id="lastWakeValue">Never</dd>
            </div>
            <div class="detail-item">
              <dt>Last ready</dt>
              <dd id="lastReadyValue">Never</dd>
            </div>
            <div class="detail-item">
              <dt>Last checked</dt>
              <dd id="lastCheckedValue">Never</dd>
            </div>
            <div class="detail-item">
              <dt>Last state change</dt>
              <dd id="lastStateChangeValue">Never</dd>
            </div>
            <div class="detail-item">
              <dt>Last error</dt>
              <dd id="lastErrorValue">None</dd>
            </div>
            <div class="detail-item">
              <dt>Status summary</dt>
              <dd id="statusSummaryValue">No status loaded yet.</dd>
            </div>
          </dl>
        </section>
      </section>
    </section>
  </main>

  <script>
    const STORAGE_KEY = "llm-engine-server.api-key";
    const POLL_INTERVAL_MS = 3000;

    const refs = {
      apiKeyInput: document.getElementById("apiKeyInput"),
      rememberKeyToggle: document.getElementById("rememberKeyToggle"),
      connectBtn: document.getElementById("connectBtn"),
      clearKeyBtn: document.getElementById("clearKeyBtn"),
      refreshBtn: document.getElementById("refreshBtn"),
      wakeBtn: document.getElementById("wakeBtn"),
      ensureBtn: document.getElementById("ensureBtn"),
      timeoutInput: document.getElementById("timeoutInput"),
      autoRefreshToggle: document.getElementById("autoRefreshToggle"),
      authBanner: document.getElementById("authBanner"),
      actionBanner: document.getElementById("actionBanner"),
      heroState: document.getElementById("heroState"),
      heroStateText: document.getElementById("heroStateText"),
      busyTag: document.getElementById("busyTag"),
      engineLabel: document.getElementById("engineLabel"),
      summaryCopy: document.getElementById("summaryCopy"),
      pcAwakeValue: document.getElementById("pcAwakeValue"),
      ollamaReadyValue: document.getElementById("ollamaReadyValue"),
      wakeProgressValue: document.getElementById("wakeProgressValue"),
      cooldownValue: document.getElementById("cooldownValue"),
      stateValue: document.getElementById("stateValue"),
      macValue: document.getElementById("macValue"),
      hostValue: document.getElementById("hostValue"),
      probePortValue: document.getElementById("probePortValue"),
      ollamaUrlValue: document.getElementById("ollamaUrlValue"),
      wakeEnabledValue: document.getElementById("wakeEnabledValue"),
      lastWakeValue: document.getElementById("lastWakeValue"),
      lastReadyValue: document.getElementById("lastReadyValue"),
      lastCheckedValue: document.getElementById("lastCheckedValue"),
      lastStateChangeValue: document.getElementById("lastStateChangeValue"),
      lastErrorValue: document.getElementById("lastErrorValue"),
      statusSummaryValue: document.getElementById("statusSummaryValue"),
      feed: document.getElementById("feed"),
      calloutCopy: document.getElementById("calloutCopy")
    };

    let pollTimer = null;
    let latestStatus = null;
    let busy = false;

    function readStoredKey() {
      try {
        return window.localStorage.getItem(STORAGE_KEY) || "";
      } catch {
        return "";
      }
    }

    function storeKey(value) {
      try {
        if (refs.rememberKeyToggle.checked && value) {
          window.localStorage.setItem(STORAGE_KEY, value);
        } else {
          window.localStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        // Ignore storage failures in locked-down browsers.
      }
    }

    function getApiKey() {
      return refs.apiKeyInput.value.trim();
    }

    function setBanner(node, message, tone = "") {
      node.textContent = message || "";
      node.className = "status-banner" + (tone ? " " + tone : "");
    }

    function setBusy(nextBusy, label) {
      busy = nextBusy;
      refs.busyTag.textContent = nextBusy ? label : "Idle";
      refs.refreshBtn.disabled = nextBusy;
      refs.wakeBtn.disabled = nextBusy;
      refs.ensureBtn.disabled = nextBusy;
      refs.connectBtn.disabled = nextBusy;
    }

    function addFeed(message, tone = "note") {
      const row = document.createElement("article");
      row.className = "feed-item";
      const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      row.innerHTML = `
        <div class="feed-head">
          <span>${tone}</span>
          <span>${time}</span>
        </div>
        <p class="feed-body"></p>
      `;
      row.querySelector(".feed-body").textContent = message;
      refs.feed.prepend(row);
      while (refs.feed.children.length > 8) {
        refs.feed.removeChild(refs.feed.lastChild);
      }
    }

    function boolText(value) {
      return value ? "Yes" : "No";
    }

    function timeText(value) {
      if (!value) {
        return "Never";
      }
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) {
        return value;
      }
      return parsed.toLocaleString();
    }

    function applyStatePill(state) {
      refs.heroState.className = "state-pill state-" + state;
      refs.heroStateText.textContent = state.replace("_", " ");
    }

    function applyStatus(status) {
      latestStatus = status;
      applyStatePill(status.state);
      refs.engineLabel.textContent = status.label || "Engine";
      refs.summaryCopy.textContent = status.english_summary || "No summary available.";
      refs.pcAwakeValue.textContent = boolText(status.pc_awake);
      refs.ollamaReadyValue.textContent = boolText(status.ollama_ready);
      refs.wakeProgressValue.textContent = boolText(status.wake_in_progress);
      refs.cooldownValue.textContent = `${status.cooldown_remaining_seconds || 0}s`;
      refs.stateValue.textContent = status.state;
      refs.macValue.textContent = status.mac_masked || "Not available";
      refs.hostValue.textContent = status.pc_host || "Not set";
      refs.probePortValue.textContent = status.pc_probe_port ?? "Disabled";
      refs.ollamaUrlValue.textContent = status.ollama_base_url || "Not set";
      refs.wakeEnabledValue.textContent = boolText(status.wake_enabled);
      refs.lastWakeValue.textContent = timeText(status.last_wake_sent_at);
      refs.lastReadyValue.textContent = timeText(status.last_ready_at);
      refs.lastCheckedValue.textContent = timeText(status.last_status_checked_at);
      refs.lastStateChangeValue.textContent = timeText(status.last_state_change_at);
      refs.lastErrorValue.textContent = status.last_error || "None";
      refs.statusSummaryValue.textContent = status.english_summary || "No status loaded yet.";
      refs.calloutCopy.innerHTML = status.ready
        ? "<strong>Ready</strong> means other apps can safely use Ollama right now."
        : status.state === "pc_online"
          ? "<strong>PC online</strong> means Windows is up, but Ollama is still starting."
          : status.state === "waking"
            ? "<strong>Waking</strong> means a wake signal was sent recently and the PC is still coming up."
            : "<strong>Offline</strong> means the PC and Ollama are not reachable yet.";
    }

    async function apiRequest(path, options = {}) {
      const apiKey = getApiKey();
      if (!apiKey) {
        throw new Error("Paste the API key first.");
      }

      const headers = new Headers(options.headers || {});
      headers.set("Authorization", `Bearer ${apiKey}`);
      if (options.body && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }

      const response = await fetch(path, { ...options, headers });
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json().catch(() => ({}))
        : await response.text().catch(() => "");

      if (!response.ok) {
        const detail = payload?.detail;
        if (typeof detail === "string") {
          throw new Error(detail);
        }
        if (detail && typeof detail === "object" && detail.message) {
          throw new Error(detail.message);
        }
        if (typeof payload === "string" && payload) {
          throw new Error(payload);
        }
        throw new Error(`Request failed with status ${response.status}.`);
      }

      return payload;
    }

    async function refreshStatus(showSuccess = false) {
      try {
        const status = await apiRequest("/v1/engine/status");
        applyStatus(status);
        if (showSuccess) {
          setBanner(refs.actionBanner, "Status refreshed.", "good");
        }
        setBanner(refs.authBanner, "Connected.", "good");
        return status;
      } catch (error) {
        setBanner(refs.actionBanner, error.message, "error");
        if (String(error.message).toLowerCase().includes("api key")) {
          setBanner(refs.authBanner, error.message, "error");
        }
        throw error;
      }
    }

    async function wakeEngine() {
      setBusy(true, "Waking");
      try {
        const result = await apiRequest("/v1/engine/wake", { method: "POST" });
        setBanner(refs.actionBanner, result.english_summary || "Wake request sent.", "good");
        addFeed(result.english_summary || "Wake request sent.", result.wake_sent ? "wake" : "cooldown");
        await refreshStatus(false);
      } catch (error) {
        setBanner(refs.actionBanner, error.message, "error");
        addFeed(error.message, "error");
      } finally {
        setBusy(false, "Idle");
      }
    }

    async function ensureReady() {
      const timeoutSeconds = Number.parseInt(refs.timeoutInput.value || "90", 10);
      const payload = Number.isFinite(timeoutSeconds) ? { timeout_seconds: timeoutSeconds } : { timeout_seconds: 90 };
      setBusy(true, "Ensuring");
      try {
        const result = await apiRequest("/v1/engine/ensure-ready", {
          method: "POST",
          body: JSON.stringify(payload)
        });
        setBanner(refs.actionBanner, result.english_summary || "Engine is ready.", "good");
        addFeed(
          `${result.english_summary || "Engine is ready."} Waited ${result.waited_seconds}s.`,
          result.already_ready ? "ready" : "ensure"
        );
        await refreshStatus(false);
      } catch (error) {
        setBanner(refs.actionBanner, error.message, "error");
        addFeed(error.message, "error");
      } finally {
        setBusy(false, "Idle");
      }
    }

    function startPolling() {
      stopPolling();
      if (!refs.autoRefreshToggle.checked) {
        return;
      }
      pollTimer = window.setInterval(async () => {
        if (busy || !getApiKey()) {
          return;
        }
        try {
          await refreshStatus(false);
        } catch {
          // Keep the last visible state; the banner already explains the issue.
        }
      }, POLL_INTERVAL_MS);
    }

    function stopPolling() {
      if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    }

    async function connectAndLoad() {
      const apiKey = getApiKey();
      if (!apiKey) {
        setBanner(refs.authBanner, "Paste the API key first.", "error");
        return;
      }

      storeKey(apiKey);
      setBusy(true, "Connecting");
      try {
        await refreshStatus(false);
        setBanner(refs.authBanner, "Connected. Live status loaded.", "good");
        addFeed("Connected and loaded live status.", "connect");
        startPolling();
      } catch (error) {
        stopPolling();
        setBanner(refs.authBanner, error.message, "error");
      } finally {
        setBusy(false, "Idle");
      }
    }

    function clearSavedKey() {
      refs.apiKeyInput.value = "";
      refs.rememberKeyToggle.checked = false;
      storeKey("");
      stopPolling();
      setBanner(refs.authBanner, "Saved key cleared.", "");
      setBanner(refs.actionBanner, "", "");
      addFeed("Saved API key cleared from this browser.", "clear");
    }

    function hydrateStoredKey() {
      const stored = readStoredKey();
      if (!stored) {
        return;
      }
      refs.apiKeyInput.value = stored;
      refs.rememberKeyToggle.checked = true;
    }

    refs.connectBtn.addEventListener("click", connectAndLoad);
    refs.refreshBtn.addEventListener("click", async () => {
      setBusy(true, "Refreshing");
      try {
        await refreshStatus(true);
        addFeed("Manual status refresh completed.", "refresh");
      } catch (error) {
        addFeed(error.message, "error");
      } finally {
        setBusy(false, "Idle");
      }
    });
    refs.wakeBtn.addEventListener("click", wakeEngine);
    refs.ensureBtn.addEventListener("click", ensureReady);
    refs.clearKeyBtn.addEventListener("click", clearSavedKey);
    refs.autoRefreshToggle.addEventListener("change", () => {
      if (refs.autoRefreshToggle.checked) {
        addFeed("Auto-refresh enabled.", "poll");
        startPolling();
      } else {
        addFeed("Auto-refresh paused.", "poll");
        stopPolling();
      }
    });
    refs.rememberKeyToggle.addEventListener("change", () => storeKey(getApiKey()));
    refs.apiKeyInput.addEventListener("input", () => {
      if (refs.rememberKeyToggle.checked) {
        storeKey(getApiKey());
      }
    });

    hydrateStoredKey();
    addFeed("Dashboard loaded. Paste the API key to start.", "boot");
  </script>
</body>
</html>
"""
