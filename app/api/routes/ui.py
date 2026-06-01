from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["ui"])


UI_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Text To Doc Builder</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --surface: #ffffff;
      --surface-muted: #f0f3f6;
      --text: #1f2933;
      --muted: #697586;
      --line: #d8dee8;
      --accent: #176b5d;
      --accent-dark: #0f4d43;
      --danger: #b42318;
      --warning: #9a6700;
      --ready: #146c43;
      --processing: #175cd3;
      --shadow: 0 12px 36px rgba(15, 23, 42, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      letter-spacing: 0;
    }

    button,
    input,
    textarea {
      font: inherit;
      letter-spacing: 0;
    }

    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 22px;
    }

    .brand {
      display: grid;
      gap: 4px;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
      font-weight: 720;
    }

    .subtitle {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }

    .status-pill {
      min-width: 118px;
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      color: var(--muted);
      text-align: center;
      font-weight: 650;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(340px, 0.78fr);
      gap: 18px;
      align-items: start;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }

    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
    }

    .panel-title {
      margin: 0;
      font-size: 16px;
      line-height: 1.3;
      font-weight: 720;
    }

    .panel-body {
      padding: 18px;
    }

    .field {
      display: grid;
      gap: 8px;
      margin-bottom: 16px;
    }

    .field:last-child {
      margin-bottom: 0;
    }

    label {
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
    }

    textarea,
    input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      color: var(--text);
      outline: none;
      transition: border-color 140ms ease, box-shadow 140ms ease;
    }

    textarea {
      min-height: 220px;
      padding: 12px;
      resize: vertical;
      line-height: 1.5;
    }

    .json-field {
      min-height: 120px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 13px;
    }

    input {
      height: 42px;
      padding: 0 12px;
    }

    textarea:focus,
    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(23, 107, 93, 0.16);
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 18px;
    }

    .button {
      min-height: 42px;
      border: 1px solid transparent;
      border-radius: 8px;
      padding: 0 16px;
      cursor: pointer;
      font-weight: 720;
      transition: background 140ms ease, border-color 140ms ease, color 140ms ease, opacity 140ms ease;
    }

    .button.primary {
      background: var(--accent);
      color: #ffffff;
    }

    .button.primary:hover {
      background: var(--accent-dark);
    }

    .button.secondary {
      background: var(--surface-muted);
      border-color: var(--line);
      color: var(--text);
    }

    .button.secondary:hover {
      border-color: #b9c4d0;
      background: #e9edf2;
    }

    .button:disabled {
      cursor: not-allowed;
      opacity: 0.58;
    }

    .summary {
      display: grid;
      grid-template-columns: 120px minmax(0, 1fr);
      gap: 10px 12px;
      margin: 0;
    }

    .summary dt {
      color: var(--muted);
      font-weight: 700;
    }

    .summary dd {
      min-width: 0;
      margin: 0;
      overflow-wrap: anywhere;
    }

    .empty {
      margin: 0;
      color: var(--muted);
    }

    .badge {
      display: inline-flex;
      min-height: 28px;
      align-items: center;
      border-radius: 8px;
      padding: 4px 9px;
      background: var(--surface-muted);
      color: var(--muted);
      font-size: 13px;
      font-weight: 760;
      text-transform: lowercase;
    }

    .badge.ready {
      background: #dcfce7;
      color: var(--ready);
    }

    .badge.processing,
    .badge.queued {
      background: #dbeafe;
      color: var(--processing);
    }

    .badge.failed,
    .badge.canceled {
      background: #fee4e2;
      color: var(--danger);
    }

    .message {
      display: none;
      margin: 16px 0 0;
      border-radius: 8px;
      padding: 12px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }

    .message.error {
      display: block;
      border: 1px solid #fecdca;
      background: #fffbfa;
      color: var(--danger);
    }

    .message.warning {
      display: block;
      border: 1px solid #fedf89;
      background: #fffcf5;
      color: var(--warning);
    }

    pre {
      min-height: 180px;
      max-height: 420px;
      margin: 16px 0 0;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #111827;
      color: #f9fafb;
      padding: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      line-height: 1.55;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .download-row {
      display: none;
      margin-top: 16px;
    }

    .download-row.visible {
      display: flex;
    }

    @media (max-width: 860px) {
      .shell {
        width: min(100% - 20px, 720px);
        padding-top: 18px;
      }

      .topbar {
        align-items: stretch;
        flex-direction: column;
      }

      .layout {
        grid-template-columns: 1fr;
      }

      .summary {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <h1>Text To Doc Builder</h1>
        <p class="subtitle">Тестовая панель генерации документов</p>
      </div>
      <div id="topStatus" class="status-pill">idle</div>
    </header>

    <div class="layout">
      <section class="panel" aria-labelledby="requestTitle">
        <div class="panel-header">
          <h2 id="requestTitle" class="panel-title">Запрос</h2>
        </div>
        <div class="panel-body">
          <form id="documentForm">
            <div class="field">
              <label for="prompt">Prompt</label>
              <textarea id="prompt" name="prompt" required minlength="1" maxlength="50000" placeholder="Сделай краткий документ по итогам встречи"></textarea>
            </div>

            <div class="field">
              <label for="overrides">Overrides JSON</label>
              <textarea id="overrides" class="json-field" name="overrides" spellcheck="false" placeholder='{"title":"Итоги встречи"}'></textarea>
            </div>

            <div class="field">
              <label for="apiToken">API token</label>
              <input id="apiToken" name="apiToken" type="password" autocomplete="off" placeholder="X-API-Token">
            </div>

            <div class="actions">
              <button id="submitButton" class="button primary" type="submit">Создать документ</button>
              <button id="resetButton" class="button secondary" type="button">Сбросить</button>
            </div>
          </form>
        </div>
      </section>

      <section class="panel" aria-labelledby="resultTitle">
        <div class="panel-header">
          <h2 id="resultTitle" class="panel-title">Результат</h2>
          <span id="statusBadge" class="badge">empty</span>
        </div>
        <div class="panel-body">
          <p id="emptyState" class="empty">Документ еще не создавался.</p>

          <dl id="summary" class="summary" hidden>
            <dt>document_id</dt>
            <dd id="documentId">-</dd>
            <dt>request_id</dt>
            <dd id="requestId">-</dd>
            <dt>job_id</dt>
            <dd id="jobId">-</dd>
            <dt>status</dt>
            <dd id="documentStatus">-</dd>
            <dt>stage</dt>
            <dd id="currentStage">-</dd>
            <dt>format</dt>
            <dd id="outputFormat">-</dd>
            <dt>file</dt>
            <dd id="fileName">-</dd>
          </dl>

          <div id="downloadRow" class="download-row">
            <button id="downloadButton" class="button primary" type="button">Скачать файл</button>
          </div>

          <div id="errorMessage" class="message"></div>
          <div id="warningsMessage" class="message"></div>
          <pre id="rawOutput" aria-label="Raw API response">{}</pre>
        </div>
      </section>
    </div>
  </main>

  <script>
    const form = document.getElementById("documentForm");
    const promptInput = document.getElementById("prompt");
    const overridesInput = document.getElementById("overrides");
    const apiTokenInput = document.getElementById("apiToken");
    const submitButton = document.getElementById("submitButton");
    const resetButton = document.getElementById("resetButton");
    const downloadButton = document.getElementById("downloadButton");
    const downloadRow = document.getElementById("downloadRow");
    const topStatus = document.getElementById("topStatus");
    const statusBadge = document.getElementById("statusBadge");
    const emptyState = document.getElementById("emptyState");
    const summary = document.getElementById("summary");
    const rawOutput = document.getElementById("rawOutput");
    const errorMessage = document.getElementById("errorMessage");
    const warningsMessage = document.getElementById("warningsMessage");

    const fields = {
      documentId: document.getElementById("documentId"),
      requestId: document.getElementById("requestId"),
      jobId: document.getElementById("jobId"),
      documentStatus: document.getElementById("documentStatus"),
      currentStage: document.getElementById("currentStage"),
      outputFormat: document.getElementById("outputFormat"),
      fileName: document.getElementById("fileName"),
    };

    let pollTimer = null;
    let currentDownloadUrl = null;
    let currentFileName = null;

    apiTokenInput.value = localStorage.getItem("tdb_api_token") || "";
    apiTokenInput.addEventListener("input", () => {
      const value = apiTokenInput.value.trim();
      if (value) {
        localStorage.setItem("tdb_api_token", value);
      } else {
        localStorage.removeItem("tdb_api_token");
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      stopPolling();
      setBusy(true);
      clearMessages();

      try {
        const payload = buildPayload();
        const response = await fetch("/documents", {
          method: "POST",
          headers: jsonHeaders(),
          body: JSON.stringify(payload),
        });
        const data = await readJson(response);

        if (!response.ok) {
          throw new Error(formatApiError(response, data));
        }

        renderDocument(data);
        maybeStartPolling(data);
      } catch (error) {
        renderError(error instanceof Error ? error.message : String(error));
      } finally {
        setBusy(false);
      }
    });

    resetButton.addEventListener("click", () => {
      stopPolling();
      form.reset();
      apiTokenInput.value = localStorage.getItem("tdb_api_token") || "";
      currentDownloadUrl = null;
      currentFileName = null;
      clearMessages();
      rawOutput.textContent = "{}";
      emptyState.hidden = false;
      summary.hidden = true;
      downloadRow.classList.remove("visible");
      setStatus("empty");
      topStatus.textContent = "idle";
    });

    downloadButton.addEventListener("click", async () => {
      if (!currentDownloadUrl) {
        return;
      }

      clearMessages();
      downloadButton.disabled = true;

      try {
        const response = await fetch(currentDownloadUrl, {
          headers: authHeaders(),
        });
        if (!response.ok) {
          const data = await readJson(response);
          throw new Error(formatApiError(response, data));
        }

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = currentFileName || "document.docx";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
      } catch (error) {
        renderError(error instanceof Error ? error.message : String(error));
      } finally {
        downloadButton.disabled = false;
      }
    });

    function buildPayload() {
      const prompt = promptInput.value.trim();
      if (!prompt) {
        throw new Error("Prompt не должен быть пустым.");
      }

      const payload = {
        prompt,
        metadata: {
          client: "test-ui",
        },
      };

      const overrides = parseOverrides();
      if (Object.keys(overrides).length > 0) {
        payload.overrides = overrides;
      }

      return payload;
    }

    function parseOverrides() {
      const raw = overridesInput.value.trim();
      if (!raw) {
        return {};
      }

      const parsed = JSON.parse(raw);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
        throw new Error("Overrides должен быть JSON-объектом.");
      }
      return parsed;
    }

    function jsonHeaders() {
      return {
        ...authHeaders(),
        "Content-Type": "application/json",
        "Accept": "application/json",
      };
    }

    function authHeaders() {
      const token = apiTokenInput.value.trim();
      return token ? { "X-API-Token": token } : {};
    }

    async function readJson(response) {
      const text = await response.text();
      if (!text) {
        return {};
      }

      try {
        return JSON.parse(text);
      } catch {
        return { detail: text };
      }
    }

    function formatApiError(response, data) {
      const detail = data.detail || data.error_message || response.statusText;
      const message = typeof detail === "string" ? detail : JSON.stringify(detail);
      return `HTTP ${response.status}: ${message}`;
    }

    function renderDocument(data) {
      rawOutput.textContent = JSON.stringify(data, null, 2);
      emptyState.hidden = true;
      summary.hidden = false;

      fields.documentId.textContent = data.document_id || "-";
      fields.requestId.textContent = data.request_id || "-";
      fields.jobId.textContent = data.job_id || "-";
      fields.documentStatus.textContent = data.status || "-";
      fields.currentStage.textContent = data.current_stage || "-";
      fields.outputFormat.textContent = data.output_format || "-";
      fields.fileName.textContent = data.file_name || "-";

      currentDownloadUrl = data.download_url || null;
      currentFileName = data.file_name || null;
      downloadRow.classList.toggle("visible", Boolean(currentDownloadUrl));

      setStatus(data.status || "unknown");

      if (data.error_message) {
        renderError(data.error_message);
      }

      if (Array.isArray(data.warnings) && data.warnings.length > 0) {
        warningsMessage.className = "message warning";
        warningsMessage.textContent = data.warnings.join("\\n");
      } else {
        warningsMessage.className = "message";
        warningsMessage.textContent = "";
      }
    }

    function maybeStartPolling(data) {
      if (!data.document_id || !["queued", "processing"].includes(data.status)) {
        return;
      }

      pollTimer = window.setInterval(async () => {
        try {
          const response = await fetch(`/documents/${encodeURIComponent(data.document_id)}`, {
            headers: authHeaders(),
          });
          const nextData = await readJson(response);
          if (!response.ok) {
            throw new Error(formatApiError(response, nextData));
          }
          renderDocument(nextData);
          if (!["queued", "processing"].includes(nextData.status)) {
            stopPolling();
          }
        } catch (error) {
          stopPolling();
          renderError(error instanceof Error ? error.message : String(error));
        }
      }, 2000);
    }

    function stopPolling() {
      if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    }

    function clearMessages() {
      errorMessage.className = "message";
      errorMessage.textContent = "";
      warningsMessage.className = "message";
      warningsMessage.textContent = "";
    }

    function renderError(message) {
      errorMessage.className = "message error";
      errorMessage.textContent = message;
      topStatus.textContent = "error";
    }

    function setBusy(isBusy) {
      submitButton.disabled = isBusy;
      topStatus.textContent = isBusy ? "sending" : topStatus.textContent;
    }

    function setStatus(status) {
      statusBadge.className = `badge ${status}`;
      statusBadge.textContent = status;
      topStatus.textContent = status === "empty" ? "idle" : status;
    }
  </script>
</body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse)
def test_ui() -> HTMLResponse:
    return HTMLResponse(UI_HTML)
