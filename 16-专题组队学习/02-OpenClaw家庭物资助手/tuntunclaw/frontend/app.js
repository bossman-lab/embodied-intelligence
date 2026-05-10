const STORAGE_KEY = "openclaw.apiBase";
const DEFAULT_API_BASE = "/api";

const PRESETS = [
  "请把玻璃杯扔到地上",
  "请把巧克力放到盘里",
  "将菜板上的苹果放置有苹果的架子上保存",
];

const BLOCKLIST = ["self-harm", "suicide", "weapon", "bomb"];

const OBJECT_ALIASES = {
  apple: ["apple", "pingguo", "苹果", "apple_2"],
  banana: ["banana", "bananas", "xiangjiao", "香蕉"],
  chocolate: ["chocolate", "choco", "chocolate bar", "巧克力", "巧克力棒", "巧克力块"],
  duck: ["duck", "yellow duck", "toy duck", "duckie", "鸭子"],
  hammer: ["hammer", "锤子"],
  knife: ["knife", "刀", "小刀"],
  plate: ["plate", "dish", "saucer", "盘子", "盘里", "盘中", "盘上"],
  shelf: ["shelf", "rack", "架子", "搁架"],
  glass_cup: ["glass cup", "glass", "cup", "玻璃杯", "杯子"],
  flower_vase: ["flower vase", "vase", "花瓶"],
};

const RELATION_ALIASES = [
  { key: "in", terms: ["in", "into", "inside", "里面", "里", "放进", "放入", "放到里", "放到里面"] },
  { key: "on_top_of", terms: ["on top of", "on", "upon", "放到上", "放到桌面上", "放到盘子上", "放到盘上"] },
  { key: "next_to", terms: ["next to", "beside", "near", "旁边", "附近"] },
  { key: "left_of", terms: ["left of", "to the left of", "左边"] },
  { key: "right_of", terms: ["right of", "to the right of", "右边"] },
  { key: "in_front_of", terms: ["in front of", "front of", "前面"] },
  { key: "behind", terms: ["behind", "at the back of", "后面"] },
];

const STEP_LIBRARY = {
  grasp: [
    "收到用户输入",
    "语言解析",
    "任务调度",
    "场景采集",
    "抓取目标估计",
    "IK 求解",
    "动作执行",
    "结果",
  ],
  pick_place: [
    "收到用户输入",
    "语言解析",
    "任务调度",
    "目标分割",
    "抓取目标估计",
    "放置目标估计",
    "IK 求解",
    "动作执行",
    "结果",
  ],
  teleop: ["收到用户输入", "语言解析", "任务调度", "遥操作切换", "结果"],
  dance: ["收到用户输入", "语言解析", "任务调度", "轨迹回放", "结果"],
  blocked: ["收到用户输入", "策略检查", "结果"],
  interrupted: ["收到用户输入", "任务调度", "会话结束"],
};

const refs = {};
const state = {
  apiBase: readApiBase(),
  connection: "mock",
  envBadge: inferEnvBadge(),
  mode: "idle",
  sessionId: "-",
  task: null,
  command: "",
  trace: [],
  logs: [],
  result: "暂无结果。",
  dispatch: "等待中",
  preview: null,
  livePreviewUrl: "",
  previewImageStatus: "idle",
  inventory: {
    items: [
      {
        key: "chocolate",
        label: "巧克力",
        count: 12,
        threshold: 3,
        reorder_qty: 10,
        unit: "块",
        status: "ok",
        low_stock: false,
        alert_sent: false,
        order_pending: false,
        order_url: "",
        last_updated_at: "",
        last_alert_at: "",
        last_alert_token: "",
        last_order_at: "",
      },
    ],
    alerts: [],
    orders: [],
    history: [],
    updated_at: "",
  },
  isRunning: false,
  stopRequested: false,
  lastError: "",
};

const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

function readApiBase() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) || DEFAULT_API_BASE;
  } catch {
    return DEFAULT_API_BASE;
  }
}

function resolveApiBase(base) {
  const value = (base || "").trim() || DEFAULT_API_BASE;
  if (value === "/api" && window.location.origin && window.location.origin !== "null") {
    return `${window.location.origin}/api`;
  }
  return value;
}

function writeApiBase(value) {
  const next = (value || "").trim() || DEFAULT_API_BASE;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Ignore storage failures in file:// or restricted browser contexts.
  }
  state.apiBase = next;
  renderConnection();
}

async function probeBackend() {
  try {
    const base = resolveApiBase(state.apiBase).replace(/\/api$/, "");
    const response = await fetch(`${base}/healthz`, { cache: "no-store" });
    if (!response.ok) {
      return;
    }
    state.connection = "live";
    renderConnection();
  } catch {
    // Keep mock mode if the backend is not running yet.
  }
}

function inferEnvBadge() {
  if (window.location.protocol === "file:") {
    return "本地文件";
  }
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "本地";
  }
  return "开发";
}

function normalizeText(value) {
  return (value || "").trim().toLowerCase();
}

function checkBlocked(command) {
  const text = normalizeText(command);
  return BLOCKLIST.find((token) => text.includes(token)) || "";
}

function extractObjects(text) {
  const hits = [];
  for (const [canonical, aliases] of Object.entries(OBJECT_ALIASES)) {
    for (const alias of aliases) {
      const idx = text.indexOf(alias);
      if (idx >= 0) {
        hits.push({ idx, canonical });
        break;
      }
    }
  }
  hits.sort((a, b) => a.idx - b.idx);
  return [...new Set(hits.map((item) => item.canonical))];
}

function inferTask(command) {
  const text = normalizeText(command);
  if (!text) {
    return { type: "idle", source: null, destination: null, relation: null };
  }
  if (text === "exit" || text === "quit") {
    return { type: "interrupted", source: null, destination: null, relation: null };
  }
  if (text.includes("teleop") || text.includes("manual") || text.includes("keyboard") || text.includes("遥操作") || text.includes("手动")) {
    return { type: "teleop", source: null, destination: null, relation: null };
  }
  if (text.includes("dance") || text.includes("wave") || text.includes("跳舞") || text.includes("挥手")) {
    return { type: "dance", source: null, destination: null, relation: null };
  }

  const relation = RELATION_ALIASES.find((item) => item.terms.some((term) => text.includes(term)))?.key || "place";
  const objects = extractObjects(text);

  if (objects.length >= 2 || text.includes("place") || text.includes("put") || text.includes("move") || text.includes("放") || text.includes("移")) {
    return {
      type: "pick_place",
      source: objects[0] || "object",
      destination: objects[1] || "target",
      relation,
    };
  }

  return {
    type: "grasp",
    source: objects[0] || "object",
    destination: null,
    relation: null,
  };
}

function stepDetail(step, task, blockedReason) {
  const parts = [];
  if (task.type === "pick_place") {
    parts.push(`source=${task.source}`);
    parts.push(`destination=${task.destination}`);
    parts.push(`relation=${task.relation}`);
  } else if (task.source) {
    parts.push(`target=${task.source}`);
  }
  if (blockedReason && step === "policy gate") {
    parts.push(`blocked by ${blockedReason}`);
  }
  if (step === "result") {
    parts.push("awaiting execution summary");
  }
  return parts.join(" | ") || "queued";
}

function buildTrace(task, status = "pending", blockedReason = "") {
  const steps = STEP_LIBRARY[task.type] || STEP_LIBRARY.grasp;
  return steps.map((name, index) => ({
    name,
    status:
      status === "blocked"
        ? index === 1
          ? "failed"
          : index === 0
            ? "done"
            : "pending"
        : index === 0
          ? "done"
          : index === 1
            ? "running"
            : "pending",
    detail: stepDetail(name, task, blockedReason),
  }));
}

function logLine(level, message) {
  const stamp = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  return `[${stamp}] ${level.toUpperCase()}: ${message}`;
}

function setConnection(mode, label) {
  state.connection = mode;
  refs.connectionDot.className = `status-dot status-${mode}`;
  refs.connectionLabel.textContent = label;
}

function renderConnection() {
  refs.envBadge.textContent = state.envBadge;
  refs.sessionChip.textContent = `会话：${state.sessionId || "-"}`;
  if (state.connection === "live") {
    setConnection("live", "真实接口");
  } else if (state.connection === "fail") {
    setConnection("fail", "接口离线");
  } else {
    setConnection("mock", "模拟模式就绪");
  }
}

function renderPresets() {
  const chips = refs.presetList.querySelectorAll(".preset-chip");
  if (chips.length) {
    chips.forEach((chip, index) => {
      const preset = PRESETS[index] || chip.textContent.trim();
      chip.dataset.preset = preset;
      chip.textContent = preset;
    });
    return;
  }

  refs.presetList.innerHTML = PRESETS
    .map((preset) => `<button class="preset-chip" type="button" data-preset="${preset}">${preset}</button>`)
    .join("");
}

function applyPresetToInput(preset) {
  refs.commandInput.value = preset;
  refs.commandInput.focus();
  refs.commandInput.setSelectionRange(preset.length, preset.length);
  refs.commandInput.dispatchEvent(new Event("input", { bubbles: true }));
}

function renderTrace() {
  const template = document.getElementById("trace-template");
  refs.traceList.innerHTML = "";

  refs.traceCount.textContent = `${state.trace.length} events`;
  refs.traceEmpty.style.display = state.trace.length ? "none" : "block";

  state.trace.forEach((entry, index) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".trace-index").textContent = String(index + 1).padStart(2, "0");
    node.querySelector(".trace-name").textContent = entry.name;
    node.querySelector(".trace-state").textContent = entry.status;
    node.querySelector(".trace-detail").textContent = entry.detail;
    node.classList.add(`is-${entry.status}`);
    refs.traceList.appendChild(node);
  });
}

function renderLogs() {
  refs.logsCount.textContent = `${state.logs.length} 行`;
  refs.logsView.textContent = state.logs.length ? state.logs.join("\n") : "暂无调试输出。";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInventory() {
  const snapshot = state.inventory || {};
  const items = Array.isArray(snapshot.items) ? snapshot.items : [];
  const updatedText = snapshot.updated_at ? new Date(snapshot.updated_at).toLocaleString() : "未加载";
  refs.inventoryUpdated.textContent = updatedText;

  if (!items.length) {
    refs.inventoryAlert.classList.remove("hidden");
    refs.inventoryAlert.textContent = "当前没有可展示的库存数据。";
    refs.inventoryList.innerHTML = '<div class="inventory-empty">暂无库存记录。</div>';
    return;
  }

  const lowItems = items.filter((item) => item.low_stock || item.status === "low_stock");
  if (lowItems.length) {
    refs.inventoryAlert.classList.remove("hidden");
    refs.inventoryAlert.textContent =
      `库存预警：${lowItems
        .map((item) => `${item.label} 剩余 ${item.count}${item.unit}`)
        .join("，")}。`;
  } else {
    refs.inventoryAlert.classList.add("hidden");
    refs.inventoryAlert.textContent = "";
  }

  refs.inventoryList.innerHTML = items
    .map((item) => {
      const low = item.low_stock || item.status === "low_stock";
      const stateText = low ? "低库存" : "正常";
      const orderUrl = item.order_url ? escapeHtml(item.order_url) : "";
      const orderButton = orderUrl
        ? `<a class="secondary-button inventory-order-button" href="${orderUrl}" target="_blank" rel="noreferrer">一键下单</a>`
        : "";
      const orderHint = item.order_pending ? "订单处理中" : low ? "建议补货" : "库存正常";
      return `
        <article class="inventory-card ${low ? "low-stock" : ""}">
          <div class="inventory-card-head">
            <div class="inventory-name">${escapeHtml(item.label || item.key || "物资")}</div>
            <span class="inventory-pill ${low ? "low" : "ok"}">${stateText}</span>
          </div>
          <div class="inventory-meta">
            <span>剩余 ${escapeHtml(item.count)} ${escapeHtml(item.unit || "")}</span>
            <span>阈值 ${escapeHtml(item.threshold)}</span>
            <span>补货 ${escapeHtml(item.reorder_qty)}</span>
            <span>${escapeHtml(orderHint)}</span>
          </div>
          <div class="inventory-actions">
            <span class="inventory-pill ${low ? "low" : "ok"}">最近更新 ${escapeHtml(item.last_updated_at || snapshot.updated_at || "-")}</span>
            ${orderButton}
          </div>
        </article>
      `;
    })
    .join("");
}

function figureTitle() {
  if (!state.task) {
    return "等待指令";
  }
  if (state.mode === "running") {
    return `正在处理 ${state.task.type}`;
  }
  if (state.mode === "failure") {
    return "指令失败";
  }
  if (state.mode === "interrupted") {
    return "会话中断";
  }
  return `任务 ${state.task.type} 完成`;
}

function figureCopy() {
  if (!state.task) {
    return "提交指令后，这里会切换为实时场景数据、叠层和目标标记。";
  }
  if (state.livePreviewUrl && state.previewImageStatus !== "loaded") {
    return state.previewImageStatus === "error"
      ? "实时画面加载失败，已回退到占位画布。"
      : "实时画面正在加载中，请稍候。";
  }
  const base = {
    grasp: `当前流程正在跟踪单一目标：${state.task.source}。`,
    pick_place: `当前流程正在将 ${state.task.source} 调度到 ${state.task.destination}，关系为 ${state.task.relation}。`,
    teleop: "遥操作切换已激活。",
    dance: "动作轨迹正在回放。",
    interrupted: "会话已在执行前结束。",
  }[state.task.type] || "场景正在更新。";
  return base;
}

function modeNoteFor(mode) {
  switch (mode) {
    case "running":
      return "正在实时执行。";
    case "success":
      return "指令执行成功。";
    case "failure":
      return "错误或策略拦截导致执行停止。";
    case "interrupted":
      return "会话已关闭或中断。";
    default:
      return "等待下一条指令。";
  }
}

function taskNoteFor(task) {
  if (!task) {
    return "尚未解析。";
  }
  if (task.type === "pick_place") {
    return `${task.source} -> ${task.destination}`;
  }
  if (task.type === "interrupted") {
    return "收到退出指令。";
  }
  return `${task.type} 路由已选定。`;
}

function renderOverlay() {
  refs.overlayLayer.innerHTML = "";
  const preview = state.preview;
  if (
    !preview ||
    !preview.boxes ||
    !preview.boxes.length ||
    (state.livePreviewUrl && state.previewImageStatus === "loaded")
  ) {
    return;
  }

  for (const box of preview.boxes) {
    const rect = document.createElement("div");
    rect.className = "box-rect";
    rect.style.left = `${box.x}%`;
    rect.style.top = `${box.y}%`;
    rect.style.width = `${box.w}%`;
    rect.style.height = `${box.h}%`;

    const label = document.createElement("div");
    label.className = "box-label";
    label.textContent = box.label;
    rect.appendChild(label);

    refs.overlayLayer.appendChild(rect);
  }
}

function makeMockPreview(task) {
  if (task.type === "pick_place") {
    return {
      boxes: [
        { label: task.source, x: 16, y: 56, w: 18, h: 14 },
        { label: task.destination, x: 63, y: 24, w: 20, h: 16 },
      ],
    };
  }
  if (task.type === "grasp") {
    return {
      boxes: [{ label: task.source, x: 54, y: 40, w: 18, h: 16 }],
    };
  }
  if (task.type === "teleop") {
    return {
      boxes: [{ label: "teleop target", x: 42, y: 36, w: 18, h: 18 }],
    };
  }
  return { boxes: [] };
}

function renderPreview() {
  refs.previewState.textContent = state.mode;
  refs.modeValue.textContent = state.mode;
  refs.modeNote.textContent = modeNoteFor(state.mode);
  refs.taskValue.textContent = state.task ? state.task.type : "-";
  refs.taskNote.textContent = taskNoteFor(state.task);
  refs.resultValue.textContent = state.result;
  refs.dispatchValue.textContent = state.dispatch;

  const imageReady = Boolean(state.livePreviewUrl && state.previewImageStatus === "loaded");
  refs.previewFigure.classList.toggle("hidden", imageReady);
  refs.previewImage.classList.toggle(
    "hidden",
    !state.livePreviewUrl || state.previewImageStatus !== "loaded"
  );

  refs.appShell.classList.toggle("running", state.mode === "running");
  refs.appShell.classList.toggle("success-state", state.mode === "success");
  refs.appShell.classList.toggle("error-state", state.mode === "failure");
  refs.appShell.classList.toggle("interrupted-state", state.mode === "interrupted");

  if (state.livePreviewUrl) {
    if (refs.previewImage.dataset.currentSrc !== state.livePreviewUrl) {
      refs.previewImage.dataset.currentSrc = state.livePreviewUrl;
      refs.previewImage.src = state.livePreviewUrl;
      state.previewImageStatus = "loading";
    }
    refs.previewImage.alt = `Scene preview for ${state.command}`;
  } else {
    refs.previewImage.dataset.currentSrc = "";
    state.previewImageStatus = "idle";
  }

  refs.previewFigure.querySelector(".figure-title").textContent = figureTitle();
  refs.previewFigure.querySelector(".figure-copy").textContent = figureCopy();
  refs.previewFigure.querySelector(".figure-stats").innerHTML = [
    `<span class="figure-stat">状态：${state.mode}</span>`,
    `<span class="figure-stat">轨迹：${state.trace.length} 步</span>`,
  ].join("");

  renderOverlay();
}

async function refreshInventory() {
  const base = resolveApiBase(state.apiBase).replace(/\/$/, "");
  if (!base) {
    return;
  }
  try {
    const response = await fetch(`${base}/inventory`, { cache: "no-store" });
    if (!response.ok) {
      return;
    }
    const snapshot = await response.json();
    state.inventory = snapshot || state.inventory;
    render();
  } catch {
    // Inventory is optional when the backend is offline.
  }
}

function setState(next) {
  Object.assign(state, next);
  render();
}

function render() {
  renderConnection();
  renderTrace();
  renderLogs();
  renderPreview();
  renderInventory();
}

function buildDebugPayload(task, trace, extra = {}) {
  return {
    session_id: state.sessionId,
    command: state.command,
    task,
    trace,
    state: state.mode,
    api_base: state.apiBase,
    ...extra,
  };
}

function extractPreviewUrl(payload) {
  const candidate =
    payload.preview?.image_url ||
    payload.preview?.url ||
    payload.preview_url ||
    payload.image_url ||
    payload.imageUrl ||
    payload.image;

  if (!candidate || typeof candidate !== "string") {
    return "";
  }

  if (/^data:|^https?:|^blob:/.test(candidate)) {
    return candidate;
  }

  try {
    return new URL(candidate, `${window.location.href}`).toString();
  } catch {
    return candidate;
  }
}

function normalizeTerminalMode(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("fail") || text.includes("error")) {
    return "failure";
  }
  if (text.includes("interrupt") || text.includes("cancel")) {
    return "interrupted";
  }
  if (text.includes("run")) {
    return "running";
  }
  return "success";
}

function normalizeStepStatus(status, index, length) {
  const text = String(status || "").toLowerCase();
  if (text.includes("fail") || text.includes("error") || text.includes("block") || text.includes("cancel")) return "failed";
  if (text.includes("run")) return "running";
  if (text.includes("pend")) return "pending";
  if (text.includes("done") || text.includes("ok") || text.includes("complete")) return "done";
  return index === length - 1 ? "running" : "done";
}

function normalizeTrace(input) {
  if (!Array.isArray(input)) {
    return [];
  }
  return input.map((step, index) => {
    if (typeof step === "string") {
      return {
        name: step,
        status: index === input.length - 1 ? "running" : "done",
        detail: "",
      };
    }
    return {
      name: step.name || step.step || `step ${index + 1}`,
      status: normalizeStepStatus(step.status, index, input.length),
      detail: step.detail || step.message || "",
    };
  });
}

function extractLogs(payload) {
  const logs = payload.logs || payload.debug || payload.events || [];
  if (Array.isArray(logs)) {
    return logs.map((entry) => (typeof entry === "string" ? entry : JSON.stringify(entry)));
  }
  if (typeof logs === "string") {
    return logs.split(/\r?\n/).filter(Boolean);
  }
  return [];
}

function previewFromPayload(payload, task) {
  const preview = payload.preview || {};
  if (Array.isArray(preview.boxes) && preview.boxes.length) {
    return { boxes: preview.boxes };
  }
  if (task?.type === "pick_place") {
    return makeMockPreview(task);
  }
  return preview?.boxes ? preview : makeMockPreview(task);
}

function applyServerPayload(payload, task) {
  const nextSession = payload.session_id || payload.sessionId || payload.id || state.sessionId;
  const parsed = payload.parsed || payload.intent || payload.task || {};
  const steps = normalizeTrace(payload.trace || payload.steps || payload.stage_trace || []);
  const terminalStatus = payload.status || payload.state || (steps.at(-1)?.status === "failed" ? "failure" : "success");
  const previewUrl = extractPreviewUrl(payload);

  state.sessionId = nextSession || state.sessionId;
  state.task = {
    type: parsed.type || task.type,
    source: parsed.source || task.source,
    destination: parsed.destination || task.destination,
    relation: parsed.relation || task.relation,
  };
  state.trace = steps.length ? steps : buildTrace(state.task, "running");
  state.logs = extractLogs(payload);
  state.preview = previewFromPayload(payload, state.task);
  state.inventory = payload.inventory || state.inventory;
  if (payload.inventory_event) {
    state.logs = [
      ...state.logs,
      logLine("库存", `sku=${payload.inventory_event.sku || "-"} remaining=${payload.inventory_event.remaining ?? "-"}`),
    ];
  }
  if (previewUrl) {
    if (previewUrl !== state.livePreviewUrl) {
      state.previewImageStatus = "loading";
    }
    state.livePreviewUrl = previewUrl;
  }
  state.dispatch = payload.current_step || payload.currentStep || "服务端响应";
  state.result =
    payload.result ||
    payload.message ||
    (normalizeTerminalMode(terminalStatus) === "running"
      ? "指令正在执行中..."
      : `指令已完成，状态：${terminalStatus}`);
  state.mode = normalizeTerminalMode(terminalStatus);
  state.isRunning = state.mode === "running";
  render();

  if (state.mode === "running" && state.sessionId && state.sessionId !== "-") {
    maybeSubscribeToEvents(state.sessionId);
  }
}

async function tryLiveCommand(command, task) {
  const base = resolveApiBase(state.apiBase).replace(/\/$/, "");
  if (!base) {
    return { ok: false, reason: "默认模拟模式" };
  }

  try {
    state.connection = "live";
    const response = await fetch(`${base}/command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        command,
        session_id: state.sessionId === "-" ? null : state.sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    applyServerPayload(payload, task);
    await refreshInventory();
    return { ok: true };
  } catch (error) {
    state.connection = "mock";
    state.lastError = String(error?.message || error);
    return { ok: false, reason: state.lastError };
  }
}

function createSessionId() {
  return `local-${Math.random().toString(36).slice(2, 8)}`;
}

function buildMockSequence(command, task) {
  const base = STEP_LIBRARY[task.type] || STEP_LIBRARY.grasp;
  return base.map((name, index) => ({
    name,
    status: index === base.length - 1 ? "done" : index === 1 ? "running" : "done",
    detail: mockDetail(name, task, command),
    delay: index === 0 ? 240 : index === base.length - 1 ? 220 : 360,
  }));
}

function mockDetail(step, task, command) {
  const snippets = [];
  if (task.source) snippets.push(`source=${task.source}`);
  if (task.destination) snippets.push(`destination=${task.destination}`);
  if (task.relation) snippets.push(`relation=${task.relation}`);
  if (step === "language parse") snippets.push(`command="${command}"`);
  if (step === "result" && task.type === "interrupted") snippets.push("closed by exit command");
  if (step === "policy gate") snippets.push("blocked by local policy");
  return snippets.join(" | ") || "处理中";
}

function finishInterrupted(task, logEntries) {
  state.mode = "interrupted";
  state.dispatch = "会话已关闭";
  state.result = "指令已被用户中断。";
  state.trace = buildTrace({ ...task, type: "interrupted" }, "interrupted");
  state.logs = [...logEntries, logLine("警告", "会话已中断")];
  state.isRunning = false;
  render();
}

async function runMockFlow(command, task) {
  const sequence = buildMockSequence(command, task);
  const logEntries = [...state.logs, logLine("模拟", "后端不可用，使用本地轨迹模拟")];
  state.logs = logEntries;
  state.connection = "mock";
  state.sessionId = state.sessionId === "-" ? createSessionId() : state.sessionId;
  render();

  for (let index = 0; index < sequence.length; index += 1) {
    if (state.stopRequested) {
      finishInterrupted(task, logEntries);
      return;
    }

    const step = sequence[index];
    state.dispatch = step.name;
    state.trace = state.trace.map((item, traceIndex) => {
      if (traceIndex < index) {
        return { ...item, status: "done" };
      }
      if (traceIndex === index) {
        return { ...item, status: step.status };
      }
      return { ...item, status: "pending" };
    });
    state.logs = [...logEntries, logLine("trace", `${step.name}: ${step.detail}`)];
    render();
    await sleep(step.delay);
  }

  const success = task.type !== "interrupted";
  state.mode = success ? "success" : "interrupted";
  state.result = success ? `已通过模拟流程完成 ${task.type}。` : "会话已关闭。";
  state.dispatch = success ? "结果" : "会话结束";
  state.trace = state.trace.map((item) => ({ ...item, status: item.status === "running" ? "done" : item.status }));
  state.logs = [...logEntries, logLine("完成", success ? "模拟流程已完成" : "会话已中断")];
  state.isRunning = false;
  state.livePreviewUrl = "";
  state.previewImageStatus = "idle";
  render();
  refs.commandInput.focus();
}

function stopCommand() {
  if (!state.isRunning) {
    state.mode = "idle";
    state.result = "暂无结果。";
    state.dispatch = "等待中";
    render();
    refs.commandInput.focus();
    return;
  }
  state.stopRequested = true;
  state.result = "已请求停止。";
  state.dispatch = "正在中断";
  state.logs = [...state.logs, logLine("警告", "用户请求停止")];
  render();
  refs.commandInput.focus();
}

function configureApi() {
  const next = window.prompt("请输入接口基址", state.apiBase);
  if (next === null) {
    return;
  }
  writeApiBase(next);
  state.connection = "mock";
  state.logs = [...state.logs, logLine("信息", `接口基址已更新：${state.apiBase}`)];
  render();
  refs.commandInput.focus();
}

function applyLiveResponseFromEvent(event) {
  try {
    const data = JSON.parse(event.data);
    if (!data || !data.session_id || !data.status) {
      return;
    }
    applyServerPayload(data, state.task || inferTask(state.command));
  } catch (error) {
    state.logs = [...state.logs, logLine("警告", `事件解析失败：${String(error.message || error)}`)];
    render();
  }
}

function maybeSubscribeToEvents(sessionId) {
  const base = resolveApiBase(state.apiBase).replace(/\/$/, "");
  if (!base || !sessionId || sessionId === "-") {
    return;
  }
  try {
    const source = new EventSource(`${base}/session/${sessionId}/events`);
    source.onmessage = applyLiveResponseFromEvent;
    source.onerror = () => {
      source.close();
    };
  } catch {
    // Streaming is optional. Fall back to the static response.
  }
}

async function submitCommand(value) {
  const command = (value ?? refs.commandInput.value).trim();
  if (!command || state.isRunning) {
    return;
  }

  const blockedReason = checkBlocked(command);
  const task = inferTask(command);
  const traceStatus = blockedReason ? "blocked" : "running";
  const trace = buildTrace(task, traceStatus, blockedReason);
  const logs = [
    logLine("信息", `已接收指令：${command}`),
    logLine("信息", `接口基址：${resolveApiBase(state.apiBase)}`),
  ];

  refs.commandInput.value = command;
  state.command = command;
  state.task = task;
  state.trace = trace;
  state.logs = logs;
  state.preview = makeMockPreview(task);
  state.livePreviewUrl = "";
  state.previewImageStatus = "idle";
  state.mode = blockedReason ? "failure" : "running";
  state.result = blockedReason ? `已被策略关键字拦截：${blockedReason}` : "正在调度指令...";
  state.dispatch = blockedReason ? "策略检查" : "解析中";
  state.isRunning = !blockedReason;
  state.stopRequested = false;
  state.lastError = "";
  render();

  if (blockedReason) {
    state.logs = [...logs, logLine("警告", `策略拦截关键字：${blockedReason}`)];
    render();
    refs.commandInput.focus();
    return;
  }

  const live = await tryLiveCommand(command, task);
  if (live.ok) {
    state.logs = [...logs, logLine("信息", "已提交到真实后端，等待仿真响应...")];
    render();
    refs.commandInput.focus();
    return;
  }

  state.logs = [...logs, logLine("模拟", `后端不可用：${live.reason}`)];
  render();
  await runMockFlow(command, task);
}

function render() {
  renderConnection();
  renderTrace();
  renderLogs();
  renderPreview();
}

function wireEvents() {
  refs.commandInput.focus();
  refs.commandInput.addEventListener("keydown", (event) => {
    if (event.isComposing) {
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitCommand();
    }
  });

  refs.submitButton.addEventListener("click", () => submitCommand());
  refs.stopButton.addEventListener("click", stopCommand);
  refs.apiButton.addEventListener("click", configureApi);

  window.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "enter") {
      event.preventDefault();
      submitCommand();
    }
  });
}

function bootstrap() {
  refs.appShell = document.querySelector(".app-shell");
  refs.connectionDot = document.getElementById("connection-dot");
  refs.connectionLabel = document.getElementById("connection-label");
  refs.envBadge = document.getElementById("env-badge");
  refs.apiButton = document.getElementById("api-button");
  refs.sessionChip = document.getElementById("session-chip");
  refs.commandInput = document.getElementById("command-input");
  refs.submitButton = document.getElementById("submit-button");
  refs.stopButton = document.getElementById("stop-button");
  refs.presetList = document.getElementById("preset-list");
  refs.modeValue = document.getElementById("mode-value");
  refs.modeNote = document.getElementById("mode-note");
  refs.taskValue = document.getElementById("task-value");
  refs.taskNote = document.getElementById("task-note");
  refs.inventoryUpdated = document.getElementById("inventory-updated");
  refs.inventoryAlert = document.getElementById("inventory-alert");
  refs.inventoryList = document.getElementById("inventory-list");
  refs.previewState = document.getElementById("preview-state");
  refs.previewFigure = document.getElementById("preview-figure");
  refs.previewImage = document.getElementById("preview-image");
  refs.overlayLayer = document.getElementById("overlay-layer");
  refs.resultValue = document.getElementById("result-value");
  refs.dispatchValue = document.getElementById("dispatch-value");
  refs.traceCount = document.getElementById("trace-count");
  refs.traceEmpty = document.getElementById("trace-empty");
  refs.traceList = document.getElementById("trace-list");
  refs.logsCount = document.getElementById("logs-count");
  refs.logsView = document.getElementById("logs-view");

  refs.previewImage.onload = () => {
    if (refs.previewImage.dataset.currentSrc === state.livePreviewUrl && state.livePreviewUrl) {
      state.previewImageStatus = "loaded";
      render();
    }
  };
  refs.previewImage.onerror = () => {
    if (refs.previewImage.dataset.currentSrc === state.livePreviewUrl && state.livePreviewUrl) {
      state.previewImageStatus = "error";
      render();
    }
  };

  state.sessionId = "-";
  state.apiBase = resolveApiBase(state.apiBase);
  renderPresets();
  probeBackend();
  refreshInventory();
  window.__openclawSubmitCommand = submitCommand;
  window.__openclawApplyPreset = applyPresetToInput;
  render();
}

bootstrap();
