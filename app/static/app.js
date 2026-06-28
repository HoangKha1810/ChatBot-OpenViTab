const state = {
  split: "dev",
  examples: [],
  selected: null,
  table: null,
  result: null,
  progress: null,
  progressTimer: null,
  requestId: null,
  tab: "plan",
};

const PIPELINE_STEPS = [
  {
    label: "Receive request & load table",
    stages: ["start", "load_table"],
    idle: "Waiting for a question to be sent to the backend.",
  },
  {
    label: "Check GPU/Ollama",
    stages: ["gpu", "models", "warmup"],
    idle: "Checking the local runtime and models.",
  },
  {
    label: "Planner builds SQL candidate",
    stages: ["planner"],
    idle: "Detecting intent, answer column, filters, and sorting.",
  },
  {
    label: "Schema linking",
    stages: ["schema_linking", "ollama_embed"],
    idle: "Ranking relevant columns with embeddings.",
  },
  {
    label: "Text-to-SQL validate",
    stages: ["text_to_sql"],
    idle: "Model validates or repairs the SQL candidate.",
  },
  {
    label: "Execute SQL",
    stages: ["execute_sql"],
    idle: "Running SQL on SQLite to retrieve evidence rows.",
  },
  {
    label: "Answer synthesis",
    stages: ["answer"],
    idle: "Generating the answer from evidence only.",
  },
  {
    label: "Verifier & confidence",
    stages: ["verifier", "confidence", "done"],
    idle: "Verifying evidence support and computing confidence.",
  },
];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const payload = JSON.parse(text);
      message = payload.detail || payload.error || text;
    } catch (_) {
      // Keep the plain response body.
    }
    throw new Error(message || response.statusText || `HTTP ${response.status}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function init() {
  bindEvents();
  await loadHealth();
  await loadExamples();
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function bindEvents() {
  $$("#split button").forEach((button) => {
    button.addEventListener("click", async () => {
      $$("#split button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.split = button.dataset.split;
      await loadExamples();
    });
  });

  $("#domain").addEventListener("change", loadExamples);
  $("#search").addEventListener("input", renderExamples);
  $("#run").addEventListener("click", runPipeline);
  $("#reload-table").addEventListener("click", () => {
    if (state.selected) {
      loadTable(state.selected.table_id);
    }
  });

  $$(".tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveTab(button.dataset.tab);
    });
  });
}

async function loadHealth() {
  try {
    const health = await fetchJson("/api/health");
    if (!health.ok) {
      $("#dataset-status").textContent = "Missing data";
      $("#dataset-status").style.color = "#c2410c";
      $("#table-title").textContent = health.error;
      return;
    }
    $("#dataset-status").textContent = `${health.dataset.tables} tables`;
    if (health.models) {
      const missing = health.models.missing || [];
      $("#dataset-status").textContent = missing.length ? `Models missing: ${missing.length}` : `${health.dataset.tables} tables · models ok`;
      $("#dataset-status").style.color = missing.length ? "#c2410c" : "#667085";
    }
    const domains = health.dataset.domains || [];
    $("#domain").innerHTML =
      '<option value="">All domains</option>' +
      domains.map((domain) => `<option value="${escapeHtml(domain)}">${escapeHtml(domain)}</option>`).join("");
  } catch (error) {
    $("#dataset-status").textContent = "Error";
    $("#table-title").textContent = error.message;
  }
}

async function loadExamples() {
  const domain = $("#domain").value;
  const params = new URLSearchParams({ split: state.split, limit: "120" });
  if (domain) {
    params.set("domain", domain);
  }
  const payload = await fetchJson(`/api/examples?${params.toString()}`);
  state.examples = payload.items || [];
  renderExamples();
  if (state.examples.length) {
    selectExample(state.examples[0]);
  }
}

function renderExamples() {
  const query = $("#search").value.trim().toLowerCase();
  const filtered = state.examples.filter((item) => {
    const haystack = `${item.question} ${item.expected_answer} ${item.table_title} ${item.table_domain}`.toLowerCase();
    return !query || haystack.includes(query);
  });
  $("#examples").innerHTML = filtered
    .slice(0, 80)
    .map(
      (item) => `
      <button class="example ${state.selected?.qa_id === item.qa_id ? "active" : ""}" data-qa="${escapeHtml(item.qa_id)}">
        <strong>${escapeHtml(item.question)}</strong>
        <span>${escapeHtml(item.table_title)} · ${escapeHtml(item.table_domain)}</span>
      </button>
    `,
    )
    .join("");

  $$(".example").forEach((button) => {
    button.addEventListener("click", () => {
      const item = state.examples.find((example) => example.qa_id === button.dataset.qa);
      if (item) {
        selectExample(item);
      }
    });
  });
}

async function selectExample(item) {
  state.selected = item;
  state.result = null;
  state.progress = null;
  state.requestId = null;
  $("#question").value = item.question;
  $("#qa-id").textContent = item.qa_id;
  $("#table-id").textContent = item.table_id;
  $("#domain-label").textContent = item.table_domain || "No domain";
  $("#expected").textContent = item.expected_answer ? `Original answer: ${item.expected_answer}` : "";
  $("#answer").textContent = "Ready to run on the real table.";
  $("#run-status").textContent = "Status: idle.";
  $("#run-status").className = "run-status";
  $("#confidence-label").textContent = "-";
  $("#confidence-meter").value = 0;
  $("#latency").textContent = "0 ms";
  renderPipelineInspector();
  renderExamples();
  await loadTable(item.table_id);
  renderTrace();
}

async function loadTable(tableId) {
  const table = await fetchJson(`/api/table/${encodeURIComponent(tableId)}`);
  state.table = table;
  $("#table-title").textContent = table.title || table.table_id;
  $("#domain-label").textContent = table.domain || "No domain";
  $("#row-count").textContent = `${table.row_count} rows`;
  renderTable();
}

function renderTable() {
  if (!state.table) {
    $("#data-table").innerHTML = "";
    return;
  }
  const headers = state.table.headers || [];
  const evidenceRows = new Set((state.result?.evidence || []).map((row) => row.row_index));
  const head = `<thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>`;
  const body = `<tbody>${(state.table.rows || [])
    .map((row, index) => {
      const rowIndex = index + 1;
      const cells = headers.map((_, cellIndex) => `<td>${escapeHtml(row[cellIndex] || "")}</td>`).join("");
      return `<tr class="${evidenceRows.has(rowIndex) ? "highlight" : ""}">${cells}</tr>`;
    })
    .join("")}</tbody>`;
  $("#data-table").innerHTML = head + body;
}

async function runPipeline() {
  if (!state.selected && !state.table) {
    return;
  }
  const requestId = `ui-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  state.requestId = requestId;
  state.progress = { status: "running", events: [] };
  stopProgressPolling();
  setActiveTab("progress");
  $("#run").disabled = true;
  $("#run").innerHTML = '<i data-lucide="loader-circle"></i> Running...';
  $("#answer").textContent = "Running SQL planner, executor, and verifier...";
  $("#run-status").textContent = "Status: sending request to backend...";
  $("#run-status").className = "run-status running";
  renderPipelineInspector();
  if (window.lucide) {
    window.lucide.createIcons();
  }
  try {
    const payload = {
      question: $("#question").value,
      table_id: state.selected?.table_id || state.table.table_id,
      qa_id: state.selected?.qa_id || null,
      expected_answer: state.selected?.expected_answer || null,
      request_id: requestId,
    };
    await fetchJson("/api/ask/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    startProgressPolling(requestId);
    const result = await waitForResult(requestId);
    applyResult(result);
    $("#run-status").className = "run-status";
    renderTrace();
    renderTable();
  } catch (error) {
    const recovered = await recoverResult(requestId);
    if (recovered) {
      $("#run-status").textContent = "Recovered result after a temporary connection error.";
      $("#run-status").className = "run-status";
      renderTrace();
      renderTable();
    } else {
      const message = describeError(error);
      $("#answer").textContent = message;
      $("#run-status").textContent = `Error: ${message}`;
      $("#run-status").className = "run-status error";
    }
  } finally {
    stopProgressPolling();
    $("#run").disabled = false;
    $("#run").innerHTML = '<i data-lucide="play"></i> Run pipeline';
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }
}

function applyResult(result) {
  state.result = result;
  $("#answer").textContent = result.answer || "(No answer)";
  $("#expected").textContent = result.expected_answer ? `Original answer: ${result.expected_answer}` : "";
  $("#confidence-label").textContent = `${result.confidence.label} · ${result.confidence.score}`;
  $("#confidence-meter").value = result.confidence.score;
  $("#latency").textContent = `${result.latency_ms} ms`;
  renderPipelineInspector();
}

async function recoverResult(requestId) {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    await sleep(700);
    try {
      const progress = await fetchJson(`/api/progress/${encodeURIComponent(requestId)}`);
      state.progress = progress;
      if (progress.has_result || progress.status === "done") {
        const result = await fetchJson(`/api/result/${encodeURIComponent(requestId)}`);
        applyResult(result);
        return true;
      }
      if (progress.status === "error") {
        return false;
      }
    } catch (_) {
      // Keep retrying briefly; remote GUI/tunnels sometimes drop a single request.
    }
  }
  return false;
}

async function waitForResult(requestId) {
  const maxAttempts = 240;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await sleep(900);
    const progress = await fetchJson(`/api/progress/${encodeURIComponent(requestId)}`);
    state.progress = progress;
    renderPipelineInspector();
    if (state.tab === "progress") {
      renderProgressTrace();
    }
    const last = progress.events?.at(-1);
    if (last) {
      $("#run-status").textContent = `[${last.stage}] ${last.message} (${Math.round(last.elapsed_ms)} ms)`;
    }
    if (progress.has_result || progress.status === "done") {
      return fetchJson(`/api/result/${encodeURIComponent(requestId)}`);
    }
    if (progress.status === "error") {
      const message = last?.message || "Pipeline failed. Check the terminal for details.";
      throw new Error(message);
    }
  }
  throw new Error("Pipeline took too long through the tunnel. Backend may still be running; check the VPS terminal.");
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function describeError(error) {
  const text = String(error?.message || error || "").trim();
  if (/HTTP 502|Bad Gateway|Load failed|Failed to fetch/i.test(text)) {
    return "Serveo tunnel disconnected or timed out temporarily. Backend may still be running; retry or check the Progress tab.";
  }
  return text || "Connection dropped or the backend has not returned a response. Check Progress/terminal for the latest step.";
}

function renderTrace() {
  if (!state.result) {
    if (state.tab === "progress" && state.progress) {
      renderProgressTrace();
      return;
    }
    if (state.tab === "sql") {
      renderLiveSqlTrace();
      return;
    }
    $("#trace-body").innerHTML = '<div class="empty">Trace will appear after running the pipeline.</div>';
    return;
  }
  if (state.tab === "plan") {
    const plan = state.result.plan;
    $("#trace-body").innerHTML = kv({
      Intent: plan.intent,
      Operation: plan.operation,
      "Answer column": plan.answer_column || "-",
      "Filter column": plan.filter_column || "-",
      "Filter value": plan.filter_value || "-",
      "Sort column": plan.sort_column || "-",
      Explanation: plan.explanation || "-",
    });
  } else if (state.tab === "sql") {
    renderSqlTrace();
  } else if (state.tab === "models") {
    $("#trace-body").innerHTML = `<pre>${escapeHtml(JSON.stringify(state.result.model_trace || [], null, 2))}</pre>`;
  } else if (state.tab === "progress") {
    renderProgressTrace();
  } else if (state.tab === "evidence") {
    $("#trace-body").innerHTML = `<pre>${escapeHtml(JSON.stringify(state.result.evidence, null, 2))}</pre>`;
  } else if (state.tab === "verifier") {
    $("#trace-body").innerHTML = `<pre>${escapeHtml(
      JSON.stringify(
        {
          verifier: state.result.verifier,
          confidence: state.result.confidence,
        },
        null,
        2,
      ),
    )}</pre>`;
  }
}

function startProgressPolling(requestId) {
  pollProgress(requestId);
  state.progressTimer = window.setInterval(() => pollProgress(requestId), 900);
}

function stopProgressPolling() {
  if (state.progressTimer) {
    window.clearInterval(state.progressTimer);
    state.progressTimer = null;
  }
}

async function pollProgress(requestId) {
  try {
    const progress = await fetchJson(`/api/progress/${encodeURIComponent(requestId)}`);
    state.progress = progress;
    renderPipelineInspector();
    const last = progress.events?.at(-1);
    if (last) {
      $("#run-status").textContent = `[${last.stage}] ${last.message} (${Math.round(last.elapsed_ms)} ms)`;
    }
    if (state.tab === "progress") {
      renderProgressTrace();
    }
  } catch (error) {
    $("#run-status").textContent = `Could not read progress: ${error.message}`;
  }
}

function renderProgressTrace() {
  const events = state.progress?.events || [];
  if (!events.length) {
    $("#trace-body").innerHTML = '<div class="empty">Waiting for backend progress...</div>';
    return;
  }
  $("#trace-body").innerHTML = `<div class="progress-list">${events
    .map(
      (event) => `
        <div class="progress-item">
          <span>${escapeHtml(Math.round(event.elapsed_ms))} ms</span>
          <strong>[${escapeHtml(event.stage)}] ${escapeHtml(event.message)}</strong>
        </div>
      `,
    )
    .join("")}</div>`;
}

function setActiveTab(tab) {
  state.tab = tab;
  $$(".tabs button").forEach((item) => {
    item.classList.toggle("active", item.dataset.tab === tab);
  });
  renderTrace();
}

function renderPipelineInspector() {
  const stepper = $("#pipeline-steps");
  if (!stepper) {
    return;
  }
  const events = state.progress?.events || [];
  const latest = events.at(-1);
  const latestIndex = latest ? eventStepIndex(latest, events.length - 1, events) : -1;
  const progressStatus = state.progress?.status || (state.result ? "done" : "idle");
  const isDone = Boolean(state.result) || progressStatus === "done";
  const isError = progressStatus === "error";

  const doneCount = isDone
    ? PIPELINE_STEPS.length
    : PIPELINE_STEPS.filter((_, index) => getStepStatus(index, latestIndex, isDone, isError) === "done").length;
  $("#step-count").textContent = `${doneCount}/${PIPELINE_STEPS.length}`;

  const pill = $("#pipeline-stage-pill");
  pill.className = `stage-pill ${isError ? "error" : isDone ? "done" : latest ? "running" : ""}`;
  if (isError) {
    pill.textContent = "Pipeline failed";
  } else if (isDone) {
    pill.textContent = "Complete";
  } else if (latest && latestIndex >= 0) {
    pill.textContent = `Running: ${PIPELINE_STEPS[latestIndex].label}`;
  } else {
    pill.textContent = "Not run";
  }

  stepper.innerHTML = PIPELINE_STEPS.map((step, index) => {
    const stepEvents = events.filter((event, eventIndex) => eventStepIndex(event, eventIndex, events) === index);
    const last = stepEvents.at(-1);
    const status = getStepStatus(index, latestIndex, isDone, isError);
    return `
      <div class="pipeline-step ${status}">
        <div class="step-index">${index + 1}</div>
        <div>
          <div class="step-label">${escapeHtml(step.label)}</div>
          <div class="step-message">${escapeHtml(last?.message || step.idle)}</div>
          <div class="step-time">${last ? `${Math.round(last.elapsed_ms)} ms` : statusText(status)}</div>
        </div>
      </div>
    `;
  }).join("");

  const sqlInfo = getLiveSqlInfo();
  $("#sql-source").textContent = sqlInfo.source;
  $("#live-sql").textContent = sqlInfo.sql;
  $("#live-sql-meta").innerHTML = sqlInfo.meta;
}

function eventStepIndex(event, eventIndex, events) {
  if (event.stage === "ollama_chat") {
    for (let index = eventIndex - 1; index >= 0; index -= 1) {
      if (["text_to_sql", "answer", "verifier"].includes(events[index].stage)) {
        return PIPELINE_STEPS.findIndex((step) => step.stages.includes(events[index].stage));
      }
    }
    return PIPELINE_STEPS.findIndex((step) => step.stages.includes("text_to_sql"));
  }
  return PIPELINE_STEPS.findIndex((step) => step.stages.includes(event.stage));
}

function getStepStatus(index, latestIndex, isDone, isError) {
  if (isDone) {
    return "done";
  }
  if (latestIndex < 0) {
    return "pending";
  }
  if (isError && index === latestIndex) {
    return "error";
  }
  if (index < latestIndex) {
    return "done";
  }
  if (index === latestIndex) {
    return "running";
  }
  return "pending";
}

function statusText(status) {
  if (status === "done") return "Complete";
  if (status === "running") return "Running";
  if (status === "error") return "Error";
  return "Waiting";
}

function getLiveSqlInfo() {
  if (state.result?.sql_trace?.sql) {
    const trace = state.result.sql_trace;
    const params = JSON.stringify(trace.params || []);
    const repair = trace.repaired ? "SQL was repaired" : "No repair needed";
    const notes = (trace.repair_notes || []).length ? `<br>${escapeHtml(trace.repair_notes.join(" | "))}` : "";
    return {
      source: "Final SQL",
      sql: trace.sql,
      meta: `Params: <code>${escapeHtml(params)}</code> · ${escapeHtml(repair)}${notes}`,
    };
  }

  const events = state.progress?.events || [];
  const patterns = [
    { label: "Final SQL", pattern: /Final SQL:\s*(.*)$/i },
    { label: "Executing SQL", pattern: /Executing SQL:\s*(.*)$/i },
    { label: "Fallback SQL", pattern: /Fallback SQL:\s*(.*)$/i },
    { label: "Candidate SQL", pattern: /Candidate SQL:\s*(.*)$/i },
  ];
  for (const event of [...events].reverse()) {
    for (const item of patterns) {
      const match = String(event.message || "").match(item.pattern);
      if (match) {
        return {
          source: item.label,
          sql: match[1],
          meta: `Stage: <code>${escapeHtml(event.stage)}</code> · ${Math.round(event.elapsed_ms)} ms`,
        };
      }
    }
  }
  return {
    source: "No SQL yet",
    sql: "SQL will appear after Planner/Text-to-SQL.",
    meta: 'Press "Run pipeline" to inspect the candidate and final SQL.',
  };
}

function renderLiveSqlTrace() {
  const sqlInfo = getLiveSqlInfo();
  $("#trace-body").innerHTML = `
    <div class="sql-detail">
      <div class="sql-card">
        <span>${escapeHtml(sqlInfo.source)}</span>
        <pre class="sql-live">${escapeHtml(sqlInfo.sql)}</pre>
        <p>${sqlInfo.meta}</p>
      </div>
    </div>
  `;
}

function renderSqlTrace() {
  const trace = state.result.sql_trace;
  const params = JSON.stringify(trace.params || [], null, 2);
  const repairNotes = (trace.repair_notes || []).length ? trace.repair_notes.join("\n") : "No repair notes.";
  $("#trace-body").innerHTML = `
    <div class="sql-detail">
      <div class="sql-card">
        <span>Final SQL used to query SQLite</span>
        <pre class="sql-live">${escapeHtml(trace.sql)}</pre>
      </div>
      <div class="sql-card compact">
        <span>Params</span>
        <pre>${escapeHtml(params)}</pre>
      </div>
      <div class="sql-card compact">
        <span>Repair / fallback</span>
        <pre>${escapeHtml(trace.repaired ? repairNotes : "No SQL repair needed.")}</pre>
      </div>
    </div>
  `;
}

function kv(items) {
  return `<div class="kv">${Object.entries(items)
    .map(([key, value]) => `<div class="kv-row"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("")}</div>`;
}

init();
