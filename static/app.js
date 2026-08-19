// 中转站管理面板前端逻辑
const state = {
  stations: [],
  currentId: null,
  models: [],          // 当前模型名列表
  results: {},         // model -> { available, latency_ms, error }
  editingId: null,     // 编辑中的 station id；null 表示新增
  busy: false,         // 是否正在测试中
};

const $ = (sel) => document.querySelector(sel);

async function api(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      if (data.detail) detail = data.detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------- 列表 ----------
async function loadStations() {
  state.stations = await api("/api/stations");
  renderStationList();
  if (state.currentId && !state.stations.some((s) => s.id === state.currentId)) {
    state.currentId = null;
    showEmpty();
  }
  if (!state.currentId && state.stations.length > 0) {
    selectStation(state.stations[0].id);
  }
}

function renderStationList() {
  const ul = $("#station-list");
  ul.innerHTML = "";
  state.stations.forEach((s) => {
    const li = document.createElement("li");
    li.className = "station-item" + (s.id === state.currentId ? " active" : "");
    li.innerHTML = `
      <div class="station-name">${escapeHtml(s.name)}</div>
      <div class="station-url">${escapeHtml(s.base_url)}</div>
    `;
    li.addEventListener("click", () => selectStation(s.id));
    ul.appendChild(li);
  });
}

function selectStation(id) {
  state.currentId = id;
  state.models = [];
  state.results = {};
  renderStationList();
  const s = state.stations.find((x) => x.id === id);
  if (!s) return;
  $("#detail-name").textContent = s.name;
  $("#detail-meta").innerHTML = `
    <span>地址：${escapeHtml(s.base_url)}</span>
    <span>协议：${escapeHtml(s.protocol)}</span>
    <span>密钥：${escapeHtml(s.api_key_masked)}</span>
  `;
  $("#detail").classList.remove("hidden");
  $("#empty").classList.add("hidden");
  $("#summary").classList.add("hidden");
  $("#table-wrap").classList.add("hidden");
  setStatus("", "");
}

function showEmpty() {
  $("#detail").classList.add("hidden");
  $("#empty").classList.remove("hidden");
}

// ---------- 弹窗 ----------
function openModal(id) {
  state.editingId = id || null;
  const isEdit = !!id;
  $("#modal-title").textContent = isEdit ? "编辑中转站" : "新增中转站";
  $("#f-name").value = "";
  $("#f-base").value = "";
  $("#f-key").value = "";
  $("#f-protocol").value = "auto";
  $("#key-hint").textContent = isEdit ? "留空则保持原密钥不变" : "";
  $("#f-key").required = !isEdit;

  if (isEdit) {
    const s = state.stations.find((x) => x.id === id);
    if (s) {
      $("#f-name").value = s.name;
      $("#f-base").value = s.base_url;
      $("#f-protocol").value = s.protocol;
    }
  }
  $("#modal").classList.remove("hidden");
  $("#f-name").focus();
}

function closeModal() {
  $("#modal").classList.add("hidden");
}

async function saveStation(e) {
  e.preventDefault();
  const payload = {
    name: $("#f-name").value.trim(),
    base_url: $("#f-base").value.trim(),
    protocol: $("#f-protocol").value,
  };
  const key = $("#f-key").value.trim();
  if (state.editingId) {
    if (key) payload.api_key = key;
    await api(`/api/stations/${state.editingId}`, {
      method: "PUT", body: JSON.stringify(payload),
    });
  } else {
    if (!key) { alert("请填写 API 密钥"); return; }
    payload.api_key = key;
    await api("/api/stations", { method: "POST", body: JSON.stringify(payload) });
  }
  closeModal();
  await loadStations();
}

// ---------- 模型 ----------
function setStatus(text, cls = "") {
  const el = $("#status-line");
  el.textContent = text;
  el.className = "status-line " + cls;
}

async function fetchModels() {
  if (!state.currentId) return;
  setStatus("正在拉取模型列表…", "loading");
  try {
    const data = await api(`/api/stations/${state.currentId}/models`, { method: "POST" });
    if (data.error) {
      setStatus("拉取失败：" + data.error, "error");
      return;
    }
    state.models = data.models;
    state.results = {};
    renderModels();
    if (state.models.length === 0) {
      setStatus("该中转站没有返回可用模型", "warn");
    } else {
      setStatus(`已获取 ${state.models.length} 个模型（协议：${data.protocol}），可点击「测试全部」实测`, "ok");
    }
  } catch (err) {
    setStatus("拉取失败：" + err.message, "error");
  }
}

async function testAll() {
  if (!state.currentId || state.busy) return;
  state.busy = true;
  setStatus("正在测试全部模型…", "loading");
  setButtonsDisabled(true);
  try {
    const data = await api(`/api/stations/${state.currentId}/test`, {
      method: "POST", body: JSON.stringify({}),
    });
    if (data.error) {
      setStatus("测试失败：" + data.error, "error");
      return;
    }
    state.models = data.models;
    state.results = {};
    data.results.forEach((r) => { state.results[r.model] = r; });
    renderModels();
    setStatus(`测试完成：${data.available}/${data.total} 个模型可用`, data.available === data.total ? "ok" : "warn");
  } catch (err) {
    setStatus("测试失败：" + err.message, "error");
  } finally {
    state.busy = false;
    setButtonsDisabled(false);
  }
}

async function testOne(model) {
  if (!state.currentId || state.busy) return;
  state.busy = true;
  setStatus(`正在测试 ${model} …`, "loading");
  setButtonsDisabled(true);
  state.results[model] = { available: null };
  renderModels();
  try {
    const data = await api(`/api/stations/${state.currentId}/test`, {
      method: "POST", body: JSON.stringify({ models: [model] }),
    });
    if (data.error) {
      setStatus("测试失败：" + data.error, "error");
      delete state.results[model];
    } else if (data.results[0]) {
      state.results[model] = data.results[0];
      setStatus(`${model}：${data.results[0].available ? "✅ 可用" : "❌ 不可用"}`, data.results[0].available ? "ok" : "warn");
    }
    renderModels();
  } catch (err) {
    setStatus("测试失败：" + err.message, "error");
  } finally {
    state.busy = false;
    setButtonsDisabled(false);
  }
}

function setButtonsDisabled(disabled) {
  ["#btn-test-all", "#btn-fetch"].forEach((sel) => {
    const b = $(sel);
    if (b) b.disabled = disabled;
  });
}

function renderModels() {
  const wrap = $("#table-wrap");
  const summary = $("#summary");
  const tbody = $("#model-body");

  if (state.models.length === 0) {
    wrap.classList.add("hidden");
    summary.classList.add("hidden");
    return;
  }

  wrap.classList.remove("hidden");
  const tested = Object.values(state.results).filter((r) => r && r.available !== null && r.available !== undefined).length;
  const available = Object.values(state.results).filter((r) => r && r.available === true).length;
  const unavailable = Object.values(state.results).filter((r) => r && r.available === false).length;

  if (tested > 0) {
    summary.classList.remove("hidden");
    summary.innerHTML = `
      <span class="stat">共 ${state.models.length} 个模型</span>
      <span class="stat ok">✅ 可用 ${available}</span>
      <span class="stat bad">❌ 不可用 ${unavailable}</span>
      <span class="stat">未测试 ${state.models.length - tested}</span>
    `;
  } else {
    summary.classList.add("hidden");
  }

  tbody.innerHTML = "";
  state.models.forEach((model) => {
    const r = state.results[model];
    const tr = document.createElement("tr");

    let statusHtml, latencyHtml, errHtml;
    if (!r || r.available === null || r.available === undefined) {
      statusHtml = '<span class="badge badge-idle">未测试</span>';
      latencyHtml = "—";
      errHtml = "";
    } else if (r.available) {
      statusHtml = '<span class="badge badge-ok">✅ 可用</span>';
      latencyHtml = r.latency_ms ?? "—";
      errHtml = "";
    } else {
      statusHtml = '<span class="badge badge-bad">❌ 不可用</span>';
      latencyHtml = r.latency_ms ?? "—";
      errHtml = `<span class="err">${escapeHtml(r.error || "")}</span>`;
    }

    tr.innerHTML = `
      <td class="model-name">${escapeHtml(model)}</td>
      <td>${statusHtml}</td>
      <td>${latencyHtml}</td>
      <td>${errHtml}</td>
      <td><button class="btn btn-sm test-btn" data-model="${escapeHtml(model)}">测试</button></td>
    `;
    tr.querySelector(".test-btn").addEventListener("click", () => testOne(model));
    tbody.appendChild(tr);
  });
}

// ---------- 删除 ----------
async function deleteCurrent() {
  if (!state.currentId) return;
  const s = state.stations.find((x) => x.id === state.currentId);
  if (!confirm(`确定删除中转站「${s.name}」吗？`)) return;
  await api(`/api/stations/${state.currentId}`, { method: "DELETE" });
  state.currentId = null;
  await loadStations();
}

// ---------- 初始化 ----------
function bindEvents() {
  $("#btn-add").addEventListener("click", () => openModal(null));
  $("#btn-cancel").addEventListener("click", closeModal);
  $("#station-form").addEventListener("submit", saveStation);
  $("#btn-fetch").addEventListener("click", fetchModels);
  $("#btn-test-all").addEventListener("click", testAll);
  $("#btn-edit").addEventListener("click", () => openModal(state.currentId));
  $("#btn-delete").addEventListener("click", deleteCurrent);
  $("#modal").addEventListener("click", (e) => {
    if (e.target === $("#modal")) closeModal();
  });
}

bindEvents();
loadStations().catch((err) => setStatus("加载中转站列表失败：" + err.message, "error"));
