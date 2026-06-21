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
    label: "Nhận request & load bảng",
    stages: ["start", "load_table"],
    idle: "Chờ gửi câu hỏi tới backend.",
  },
  {
    label: "Kiểm tra GPU/Ollama",
    stages: ["gpu", "models", "warmup"],
    idle: "Kiểm tra runtime và model local.",
  },
  {
    label: "Planner tạo SQL ứng viên",
    stages: ["planner"],
    idle: "Tách intent, cột trả lời, cột lọc/sắp xếp.",
  },
  {
    label: "Schema linking",
    stages: ["schema_linking", "ollama_embed"],
    idle: "Rank cột liên quan bằng embedding.",
  },
  {
    label: "Text-to-SQL validate",
    stages: ["text_to_sql"],
    idle: "Model kiểm tra/sửa SQL ứng viên.",
  },
  {
    label: "Execute SQL",
    stages: ["execute_sql"],
    idle: "Chạy SQL trên SQLite để lấy evidence rows.",
  },
  {
    label: "Answer synthesis",
    stages: ["answer"],
    idle: "Sinh câu trả lời chỉ dựa trên evidence.",
  },
  {
    label: "Verifier & confidence",
    stages: ["verifier", "confidence", "done"],
    idle: "Kiểm chứng evidence và tính confidence.",
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
      '<option value="">Tất cả domain</option>' +
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
  $("#expected").textContent = item.expected_answer ? `Đáp án gốc: ${item.expected_answer}` : "";
  $("#answer").textContent = "Sẵn sàng chạy trên bảng thật.";
  $("#run-status").textContent = "Trạng thái: chờ chạy.";
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
  $("#run").innerHTML = '<i data-lucide="loader-circle"></i> Đang chạy...';
  $("#answer").textContent = "Đang chạy SQL planner, execute và verifier...";
  $("#run-status").textContent = "Trạng thái: gửi request tới backend...";
  $("#run-status").className = "run-status running";
  renderPipelineInspector();
  if (window.lucide) {
    window.lucide.createIcons();
  }
  startProgressPolling(requestId);
  try {
    const payload = {
      question: $("#question").value,
      table_id: state.selected?.table_id || state.table.table_id,
      qa_id: state.selected?.qa_id || null,
      expected_answer: state.selected?.expected_answer || null,
      request_id: requestId,
    };
    const result = await fetchJson("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    applyResult(result);
    await pollProgress(requestId);
    $("#run-status").className = "run-status";
    renderTrace();
    renderTable();
  } catch (error) {
    const recovered = await recoverResult(requestId);
    if (recovered) {
      $("#run-status").textContent = "Đã khôi phục kết quả sau lỗi kết nối tạm thời.";
      $("#run-status").className = "run-status";
      renderTrace();
      renderTable();
    } else {
      const message = describeError(error);
      $("#answer").textContent = message;
      $("#run-status").textContent = `Lỗi: ${message}`;
      $("#run-status").className = "run-status error";
    }
  } finally {
    stopProgressPolling();
    $("#run").disabled = false;
    $("#run").innerHTML = '<i data-lucide="play"></i> Chạy pipeline';
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }
}

function applyResult(result) {
  state.result = result;
  $("#answer").textContent = result.answer || "(Không có câu trả lời)";
  $("#expected").textContent = result.expected_answer ? `Đáp án gốc: ${result.expected_answer}` : "";
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

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function describeError(error) {
  const text = String(error?.message || error || "").trim();
  return text || "Kết nối bị ngắt hoặc backend chưa trả response. Xem tab Progress/terminal để biết bước cuối.";
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
    $("#trace-body").innerHTML = '<div class="empty">Trace sẽ xuất hiện sau khi chạy pipeline.</div>';
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
      "Giải thích": plan.explanation || "-",
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
    $("#run-status").textContent = `Không đọc được progress: ${error.message}`;
  }
}

function renderProgressTrace() {
  const events = state.progress?.events || [];
  if (!events.length) {
    $("#trace-body").innerHTML = '<div class="empty">Đang chờ progress từ backend...</div>';
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
    pill.textContent = "Pipeline lỗi";
  } else if (isDone) {
    pill.textContent = "Hoàn tất";
  } else if (latest && latestIndex >= 0) {
    pill.textContent = `Đang chạy: ${PIPELINE_STEPS[latestIndex].label}`;
  } else {
    pill.textContent = "Chưa chạy";
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
  if (status === "done") return "Đã xong";
  if (status === "running") return "Đang chạy";
  if (status === "error") return "Lỗi";
  return "Chờ";
}

function getLiveSqlInfo() {
  if (state.result?.sql_trace?.sql) {
    const trace = state.result.sql_trace;
    const params = JSON.stringify(trace.params || []);
    const repair = trace.repaired ? "Có repair/sửa SQL" : "Không cần repair";
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
    { label: "SQL đang execute", pattern: /Executing SQL:\s*(.*)$/i },
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
    source: "Chưa có SQL",
    sql: "SQL sẽ xuất hiện sau bước Planner/Text-to-SQL.",
    meta: "Bấm “Chạy pipeline” để xem SQL ứng viên và SQL final.",
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
  const repairNotes = (trace.repair_notes || []).length ? trace.repair_notes.join("\n") : "Không có repair notes.";
  $("#trace-body").innerHTML = `
    <div class="sql-detail">
      <div class="sql-card">
        <span>Final SQL dùng để query SQLite</span>
        <pre class="sql-live">${escapeHtml(trace.sql)}</pre>
      </div>
      <div class="sql-card compact">
        <span>Params</span>
        <pre>${escapeHtml(params)}</pre>
      </div>
      <div class="sql-card compact">
        <span>Repair / fallback</span>
        <pre>${escapeHtml(trace.repaired ? repairNotes : "Không cần sửa SQL.")}</pre>
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
