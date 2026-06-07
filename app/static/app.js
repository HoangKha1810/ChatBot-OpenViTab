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
      $$(".tabs button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.tab = button.dataset.tab;
      renderTrace();
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
  $("#run").disabled = true;
  $("#run").innerHTML = '<i data-lucide="loader-circle"></i> Đang chạy...';
  $("#answer").textContent = "Đang chạy SQL planner, execute và verifier...";
  $("#run-status").textContent = "Trạng thái: gửi request tới backend...";
  $("#run-status").className = "run-status running";
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
    $("#trace-body").innerHTML = `<pre>${escapeHtml(JSON.stringify(state.result.sql_trace, null, 2))}</pre>`;
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

function kv(items) {
  return `<div class="kv">${Object.entries(items)
    .map(([key, value]) => `<div class="kv-row"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("")}</div>`;
}

init();
