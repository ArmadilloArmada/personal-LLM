/** Persona — modern UI v0.9 */

const state = {
  mode: "solo",
  personas: [],
  selectedId: "byte",
  activeIds: [],
  projectId: null,
  workspaceId: "default",
  loading: false,
  voiceEnabled: false,
  listening: false,
  boardProject: null,
  streamBubble: null,
  streamPersonaId: null,
  streamRawText: "",
  chatHistory: [],
  savedProvider: "auto",
  appVersion: "0.9.0",
  view: "chat",
  lastUserMessage: "",
  lastAssistantMessage: "",
  brainCaptureEnabled: true,
};

const COLUMN_LABELS = {
  backlog: "Backlog",
  in_progress: "In Progress",
  review: "Review",
  done: "Done",
};

const $ = (sel) => document.querySelector(sel);
const grid = $("#persona-grid");
const messages = $("#messages");
const activeAgents = $("#active-agents");
const modeHint = $("#mode-hint");
const projectsPanel = $("#projects-panel");
const projectList = $("#project-list");
const composer = $("#composer");
const input = $("#input");
const sendBtn = $("#send-btn");
const micBtn = $("#mic-btn");
const voiceToggle = $("#voice-toggle");
const chatPanel = $("#chat-panel");
const boardPanel = $("#board-panel");
const brainPanel = $("#brain-panel");
const brainFrame = $("#brain-frame");
const brainLoadMsg = $("#brain-load-msg");
const brainStatusOverlay = $("#brain-status-overlay");
const brainBanner = $("#brain-banner");
const chatModes = $("#chat-modes");
const crewPanel = $("#crew-panel");
const kanban = $("#kanban");
const boardSelect = $("#board-project-select");
const personaDialog = $("#persona-dialog");
const personaForm = $("#persona-form");
const workspaceSelect = $("#workspace-select");
const docUpload = $("#doc-upload");
const docList = $("#doc-list");
const splash = $("#startup-splash");
const splashStatus = $("#splash-status");

function avatarHtml(persona, size = 40) {
  if (persona?.avatar_url) {
    return `<img src="${persona.avatar_url}?t=${Date.now()}" width="${size}" height="${size}" alt="${persona.name}" />`;
  }
  const initials = (persona?.name || "?").slice(0, 2).toUpperCase();
  return `<div class="avatar-initials" style="--persona-color:${persona?.color || "#6366f1"};width:${size}px;height:${size}px">${initials}</div>`;
}

function personaMetaLabel(p) {
  if (!p) return "Agent";
  return `<strong>${escapeHtml(p.name)}</strong> · ${escapeHtml(p.role)}`;
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text ?? "";
  return d.innerHTML;
}

function renderMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre class="md-code"><code>${code.trim()}</code></pre>`
  );
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/^[-*] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );
  html = html.replace(/\n/g, "<br>");
  return html;
}

function setBubbleContent(bubble, text, asMarkdown = true) {
  if (!bubble) return;
  if (asMarkdown) {
    bubble.innerHTML = renderMarkdown(text);
    bubble.classList.add("md-content");
  } else {
    bubble.textContent = text;
  }
}

function hideSplash() {
  if (!splash) return;
  splash.classList.add("hidden");
  setTimeout(() => splash.remove(), 400);
}

function setSplashStatus(text) {
  if (splashStatus) splashStatus.textContent = text;
}

// --- UI ---

function renderPersonaGrid() {
  grid.innerHTML = "";
  state.personas.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "persona-card";
    btn.style.setProperty("--persona-color", p.color);
    btn.dataset.id = p.id;
    if (state.mode === "solo" && p.id === state.selectedId) btn.classList.add("selected");
    if (state.mode !== "solo" && state.mode !== "board" && state.activeIds.includes(p.id)) {
      btn.classList.add("in-group");
    }
    const badge = p.is_custom ? `<span class="custom-badge">${p.company || "custom"}</span>` : "";
    const deleteBtn = p.is_custom
      ? `<button type="button" class="persona-delete" data-id="${p.id}" title="Delete agent">×</button>`
      : "";
    btn.innerHTML = `
      ${deleteBtn}
      <div class="persona-avatar">${avatarHtml(p)}</div>
      <div class="persona-info">
        <h3>${p.name}${badge}</h3>
        <p>${p.role}</p>
      </div>`;
    btn.addEventListener("click", (e) => {
      if (e.target.closest(".persona-delete")) return;
      if (state.mode === "solo") {
        state.selectedId = p.id;
        renderPersonaGrid();
        renderActiveAgents();
        loadChatHistory();
      }
    });
    const del = btn.querySelector(".persona-delete");
    del?.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`Delete custom agent "${p.name}"?`)) return;
      await fetch(`/api/personas/${p.id}`, { method: "DELETE" });
      if (state.selectedId === p.id) state.selectedId = "byte";
      await loadPersonas();
    });
    grid.appendChild(btn);
  });
}

function renderActiveAgents() {
  if (!activeAgents) return;
  activeAgents.innerHTML = "";
  let ids = state.mode === "solo" ? [state.selectedId] : state.activeIds;
  if ((!ids.length && state.mode !== "solo") || state.mode === "board") {
    ids = state.personas.slice(0, 5).map((p) => p.id);
  }
  ids.forEach((id) => {
    const p = personaById(id);
    if (!p) return;
    const chip = document.createElement("div");
    chip.className = "agent-chip";
    chip.dataset.id = id;
    chip.style.setProperty("--persona-color", p.color);
    chip.innerHTML = `
      <div class="chip-avatar">${avatarHtml(p, 24)}</div>
      <span>${escapeHtml(p.name)}</span>`;
    activeAgents.appendChild(chip);
  });
}

function personaById(id) {
  return state.personas.find((p) => p.id === id);
}

function setTalking(personaId) {
  document.querySelectorAll(".agent-chip").forEach((el) => {
    el.classList.toggle("is-active", el.dataset.id === personaId);
  });
}

function clearTalking() {
  document.querySelectorAll(".agent-chip").forEach((el) => el.classList.remove("is-active"));
}

function addMessage({ role, personaId, content, phase, streaming = false, persist = true }) {
  messages.querySelector(".welcome-bubble")?.remove();
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  if (role === "assistant" && personaId) {
    const p = personaById(personaId);
    const phaseLabel = phase && phase !== "response" ? `<span class="phase-tag">${phase}</span>` : "";
    div.innerHTML = `
      <div class="mini-avatar">${p ? avatarHtml(p, 32) : ""}</div>
      <div>
        <div class="meta" style="--persona-color:${p?.color || "#666"}">${personaMetaLabel(p)}${phaseLabel}</div>
        <div class="bubble${streaming ? " streaming" : ""}"></div>
      </div>`;
    const bubble = div.querySelector(".bubble");
    setBubbleContent(bubble, content, !streaming);
  } else {
    div.innerHTML = `<div class="bubble"></div>`;
    setBubbleContent(div.querySelector(".bubble"), content, true);
  }
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  if (persist) {
    const entry = { role, personaId: personaId || null, content, phase: phase || null };
    state.chatHistory.push(entry);
    persistChatHistory();
  }
  return div.querySelector(".bubble");
}

function startStreamBubble(personaId, phase) {
  messages.querySelector(".welcome-bubble")?.remove();
  const div = document.createElement("div");
  div.className = "msg assistant";
  const p = personaById(personaId);
  const phaseLabel = phase && phase !== "response" ? `<span class="phase-tag">${phase}</span>` : "";
  div.innerHTML = `
    <div class="mini-avatar">${p ? avatarHtml(p, 32) : ""}</div>
    <div>
      <div class="meta" style="--persona-color:${p?.color || "#666"}">${personaMetaLabel(p)}${phaseLabel}</div>
      <div class="bubble streaming"></div>
    </div>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  state.streamBubble = div.querySelector(".bubble");
  state.streamPersonaId = personaId;
  state.streamRawText = "";
  setTalking(personaId);
  return state.streamBubble;
}

function appendStreamToken(text) {
  if (!state.streamBubble) return;
  state.streamRawText += text;
  state.streamBubble.textContent = state.streamRawText;
  messages.scrollTop = messages.scrollHeight;
}

function finishStreamBubble() {
  if (state.streamBubble && state.streamRawText) {
    setBubbleContent(state.streamBubble, state.streamRawText, true);
    const entry = {
      role: "assistant",
      personaId: state.streamPersonaId,
      content: state.streamRawText,
      phase: null,
    };
    state.chatHistory.push(entry);
    state.lastAssistantMessage = state.streamRawText;
    persistChatHistory();
    if (state.voiceEnabled) speak(state.streamRawText, state.streamPersonaId);
  }
  state.streamBubble?.classList.remove("streaming");
  state.streamBubble = null;
  state.streamPersonaId = null;
  state.streamRawText = "";
  clearTalking();
}

const BRAIN_EMBED_URL = "/brain/embed";

function initBrainFrame() {
  if (!brainFrame || brainFrame.dataset.loaded === "1") return;
  if (brainStatusOverlay) brainStatusOverlay.hidden = false;
  if (brainLoadMsg) brainLoadMsg.textContent = "Starting Big Brain…";
  brainFrame.onload = () => {
    if (brainStatusOverlay) brainStatusOverlay.hidden = true;
    brainFrame.dataset.loaded = "1";
  };
  brainFrame.onerror = () => {
    if (brainLoadMsg) {
      brainLoadMsg.textContent =
        "Big Brain failed to load. Rebuild with: npm run build (from Persona folder).";
    }
    if (brainStatusOverlay) brainStatusOverlay.hidden = false;
  };
  brainFrame.src = BRAIN_EMBED_URL;
}

function showBrainBanner(message) {
  if (!brainBanner || !message) return;
  brainBanner.textContent = message;
  brainBanner.hidden = false;
}

function hideBrainBanner() {
  if (brainBanner) brainBanner.hidden = true;
}

async function checkBrainErrors() {
  try {
    const res = await fetch("/api/brain/last-error");
    if (!res.ok) return;
    const data = await res.json();
    if (data.capture) showBrainBanner(`Vault capture failed: ${data.capture}`);
    else if (data.rag) showBrainBanner(`Vault context failed: ${data.rag}`);
    else hideBrainBanner();
  } catch {
    /* ignore */
  }
}

function setView(view) {
  state.view = view;
  const isBrain = view === "brain";
  const mainEl = document.querySelector(".main");
  mainEl?.classList.toggle("brain-view", isBrain);
  brainPanel.hidden = !isBrain;
  chatPanel.hidden = isBrain || state.mode === "board";
  boardPanel.hidden = isBrain || state.mode !== "board";
  crewPanel.hidden = isBrain || state.mode === "board";
  chatModes?.classList.toggle("hidden", isBrain);
  document.querySelectorAll(".app-nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
  if (isBrain) initBrainFrame();
}

function showBrain() {
  setView("brain");
}

function showChat() {
  setView("chat");
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === state.mode);
  });
}

function setMode(mode) {
  if (state.view === "brain") {
    showChat();
  }
  state.mode = mode;
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  const hints = {
    solo: "Select an agent for one-on-one chat.",
    roundtable: "Relevant agents respond based on your message.",
    project: "Captain leads; tasks appear on the board.",
    board: "Drag tasks between columns. Run a project first to populate.",
  };
  modeHint.textContent = hints[mode] || "";
  projectsPanel.hidden = mode !== "project" && mode !== "board";
  chatPanel.hidden = state.view === "brain" || mode === "board";
  boardPanel.hidden = state.view === "brain" || mode !== "board";
  crewPanel.hidden = state.view === "brain" || mode === "board";
  if (mode === "board") loadBoard();
  renderPersonaGrid();
  renderActiveAgents();
  if (mode !== "board") loadChatHistory();
}

function restoreMessagesFromHistory(history) {
  messages.querySelectorAll(".msg").forEach((el) => el.remove());
  if (!history.length) return;
  messages.querySelector(".welcome-bubble")?.remove();
  history.forEach((m) => {
    addMessage({
      role: m.role,
      personaId: m.personaId,
      content: m.content,
      phase: m.phase,
      persist: false,
    });
  });
}

async function loadChatHistory() {
  const params = new URLSearchParams({
    workspace_id: state.workspaceId,
    mode: state.mode,
  });
  if (state.mode === "solo") params.set("persona_id", state.selectedId);
  const res = await fetch(`/api/chat/history?${params}`);
  if (!res.ok) return;
  const data = await res.json();
  state.chatHistory = data.messages || [];
  restoreMessagesFromHistory(state.chatHistory);
  state.chatHistory = [...(data.messages || [])];
}

async function persistChatHistory() {
  await fetch("/api/chat/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: state.workspaceId,
      mode: state.mode,
      persona_id: state.mode === "solo" ? state.selectedId : null,
      messages: state.chatHistory,
    }),
  });
}

async function clearChatHistory() {
  const params = new URLSearchParams({
    workspace_id: state.workspaceId,
    mode: state.mode,
  });
  if (state.mode === "solo") params.set("persona_id", state.selectedId);
  await fetch(`/api/chat/history?${params}`, { method: "DELETE" });
  state.chatHistory = [];
  messages.querySelectorAll(".msg").forEach((el) => el.remove());
  if (!messages.querySelector(".welcome-bubble")) {
    const welcome = document.createElement("div");
    welcome.className = "welcome-bubble";
    welcome.innerHTML = `
      <h3>Welcome to Persona</h3>
      <p>Start chatting immediately — demo mode works out of the box.</p>
      <p>Select an agent, try Solo or Project mode, and connect a real LLM in Settings when ready.</p>`;
    messages.appendChild(welcome);
  }
}

// --- Voice ---

function speak(text, personaId) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text.slice(0, 800));
  const p = personaById(personaId);
  utter.rate = p?.id === "sunny" ? 1.05 : 0.95;
  utter.pitch = p?.id === "sketch" ? 1.2 : 1;
  window.speechSynthesis.speak(utter);
}

function setupVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.title = "Voice not supported in this browser";
    micBtn.disabled = true;
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;

  micBtn.addEventListener("click", () => {
    if (state.listening) {
      recognition.stop();
      return;
    }
    recognition.start();
  });

  recognition.onstart = () => {
    state.listening = true;
    micBtn.classList.add("listening");
  };
  recognition.onend = () => {
    state.listening = false;
    micBtn.classList.remove("listening");
  };
  recognition.onresult = (e) => {
    const transcript = Array.from(e.results).map((r) => r[0].transcript).join("");
    input.value = transcript;
    if (e.results[0].isFinal) composer.requestSubmit();
  };
}

voiceToggle.addEventListener("click", () => {
  state.voiceEnabled = !state.voiceEnabled;
  voiceToggle.classList.toggle("active", state.voiceEnabled);
});

// --- Streaming SSE ---

function showToolWarning(name, args) {
  if (name !== "run_shell") return;
  const banner = document.createElement("div");
  banner.className = "tool-warning";
  banner.innerHTML = `<strong>Shell command requested:</strong> <code>${escapeHtml(args?.command || "")}</code>`;
  messages.appendChild(banner);
  messages.scrollTop = messages.scrollHeight;
}

async function consumeSSE(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, stream: true, workspace_id: state.workspaceId }),
  });
  if (!res.ok) throw new Error(await res.text());

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.split("\n");
      let eventType = "message";
      let data = {};
      for (const line of lines) {
        if (line.startsWith("event: ")) eventType = line.slice(7);
        if (line.startsWith("data: ")) data = JSON.parse(line.slice(6));
      }
      handleStreamEvent(eventType, data);
    }
  }
  finishStreamBubble();
}

function handleStreamEvent(eventType, data) {
  if (eventType === "persona_start") {
    finishStreamBubble();
    startStreamBubble(data.persona_id, data.phase);
    return;
  }
  if (eventType === "token") {
    appendStreamToken(data.text || "");
    return;
  }
  if (eventType === "tool") {
    showToolWarning(data.name, data.args);
    appendStreamToken(`\n[${data.name}]...\n`);
    return;
  }
  if (eventType === "done") {
    finishStreamBubble();
    return;
  }
  if (eventType === "project") {
    state.projectId = data.project_id;
    loadProjects();
    loadBoard();
    return;
  }
  if (eventType === "complete") {
    if (data.mode === "roundtable" || data.mode === "project") {
      loadProjects();
      if (state.mode === "board") loadBoard();
    }
  }
  if (eventType === "error") {
    finishStreamBubble();
    addMessage({ role: "assistant", personaId: "captain", content: data.message });
  }
}

async function handleBrainCommand(text) {
  const parts = text.trim().split(/\s+/);
  const cmd = (parts[1] || "").toLowerCase();
  const rest = parts.slice(2).join(" ");

  const reply = (msg) =>
    addMessage({ role: "assistant", personaId: "captain", content: msg, persist: false });

  switch (cmd) {
    case "save": {
      if (!state.lastUserMessage || !state.lastAssistantMessage) {
        reply("Nothing to save yet.");
        return;
      }
      const saveRes = await fetch("/api/brain/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          persona_id: state.selectedId,
          user_message: state.lastUserMessage,
          assistant_message: state.lastAssistantMessage,
          workspace_id: state.workspaceId,
          mode: state.mode,
          force: true,
          starred: true,
        }),
      });
      if (!saveRes.ok) {
        const err = await saveRes.json().catch(() => ({}));
        reply(`Save failed: ${err.detail || saveRes.statusText}`);
        await checkBrainErrors();
        return;
      }
      reply("Saved last exchange to Big Brain.");
      return;
    }
    case "on":
      await saveBrainSettings({ captureEnabled: true });
      state.brainCaptureEnabled = true;
      if ($("#brain-capture-enabled")) $("#brain-capture-enabled").checked = true;
      reply("Big Brain capture enabled.");
      return;
    case "off":
      await saveBrainSettings({ captureEnabled: false });
      state.brainCaptureEnabled = false;
      if ($("#brain-capture-enabled")) $("#brain-capture-enabled").checked = false;
      reply("Big Brain capture disabled.");
      return;
    case "graph":
    case "open":
      showBrain();
      reply("Opened Big Brain.");
      return;
    case "search":
      if (!rest) {
        reply("Usage: /brain search <query>");
        return;
      }
      try {
        const res = await fetch(`/brain/api/brain/rag?q=${encodeURIComponent(rest)}`);
        const data = await res.json();
        const preview = (data.chunks || [])
          .slice(0, 3)
          .map((c) => `• ${c.title}: ${c.snippet}`)
          .join("\n");
        reply(preview || "No vault matches.");
      } catch {
        reply("Brain search failed — is Big Brain running?");
      }
      return;
    case "mode":
      if (rest) {
        await saveBrainSettings({ captureMode: rest });
        reply(`Capture mode set to ${rest}`);
      } else {
        reply("Usage: /brain mode every_turn|starred|manual|session_end");
      }
      return;
    default:
      reply("Commands: /brain save | on | off | graph | search <q> | mode <mode>");
  }
}

async function loadBrainSettings() {
  try {
    const res = await fetch("/api/brain/status");
    if (!res.ok) return;
    const data = await res.json();
    const cfg = data.config || {};
    state.brainCaptureEnabled = cfg.captureEnabled !== false;
    $("#brain-status").textContent = data.available
      ? "Big Brain connected"
      : "Big Brain offline — check %USERPROFILE%\\.persona\\brain.log";
    if (!data.available) {
      showBrainBanner("Big Brain is offline. Vault capture and RAG are paused.");
    } else {
      await checkBrainErrors();
    }
    $("#brain-capture-enabled").checked = cfg.captureEnabled !== false;
    $("#brain-rag-enabled").checked = cfg.ragEnabled !== false;
    if (cfg.captureMode) $("#brain-capture-mode").value = cfg.captureMode;
  } catch {
    $("#brain-status").textContent = "Big Brain status unavailable";
  }
}

async function saveBrainSettings(patch) {
  await fetch("/brain/api/brain/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      captureEnabled: patch.captureEnabled ?? $("#brain-capture-enabled")?.checked,
      ragEnabled: patch.ragEnabled ?? $("#brain-rag-enabled")?.checked,
      captureMode: patch.captureMode ?? $("#brain-capture-mode")?.value,
      ...patch,
    }),
  });
  if (patch.captureEnabled !== undefined) {
    state.brainCaptureEnabled = patch.captureEnabled;
  }
}

async function sendMessage(text) {
  if (text.toLowerCase().startsWith("/brain")) {
    state.lastUserMessage = text;
    await handleBrainCommand(text);
    return;
  }
  state.loading = true;
  sendBtn.disabled = true;
  sendBtn.classList.add("loading");
  state.lastUserMessage = text;
  addMessage({ role: "user", content: text });

  try {
    if (state.mode === "solo") {
      await consumeSSE("/api/chat", { message: text, persona_id: state.selectedId });
    } else if (state.mode === "roundtable" || state.mode === "project") {
      await consumeSSE("/api/group", {
        message: text,
        mode: state.mode,
        project_id: state.projectId,
      });
    }
  } catch (err) {
    finishStreamBubble();
    addMessage({
      role: "assistant",
      personaId: "captain",
      content: `Something went wrong. Check Settings or logs.\n\n${err.message}`,
    });
  } finally {
    state.loading = false;
    sendBtn.disabled = false;
    sendBtn.classList.remove("loading");
  }
}

// --- Kanban board ---

async function loadBoard() {
  const res = await fetch("/api/projects");
  const data = await res.json();
  const projects = data.projects || [];
  boardSelect.innerHTML = "";
  projects.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.title;
    boardSelect.appendChild(opt);
  });
  if (!projects.length) {
    kanban.innerHTML = `<p style="padding:1rem;color:var(--muted)">No projects yet — use <strong>Project</strong> mode to create one.</p>`;
    return;
  }
  state.boardProject = projects.find((p) => p.id === state.projectId) || projects[0];
  state.projectId = state.boardProject.id;
  boardSelect.value = state.projectId;
  renderBoard(state.boardProject);
}

function renderBoard(project) {
  kanban.innerHTML = "";
  const board = project.board || {};
  Object.keys(COLUMN_LABELS).forEach((col) => {
    const column = document.createElement("div");
    column.className = "kanban-col";
    column.dataset.column = col;
    column.innerHTML = `<h4>${COLUMN_LABELS[col]}</h4>`;
    column.addEventListener("dragover", (e) => {
      e.preventDefault();
      column.classList.add("drag-over");
    });
    column.addEventListener("dragleave", () => column.classList.remove("drag-over"));
    column.addEventListener("drop", (e) => onTaskDrop(e, col, project.id));
    (board[col] || []).forEach((task) => column.appendChild(renderTaskCard(task)));
    kanban.appendChild(column);
  });
}

function renderTaskCard(task) {
  const p = personaById(task.assignee);
  const card = document.createElement("div");
  card.className = "task-card";
  card.draggable = true;
  card.dataset.taskId = task.id;
  if (p) card.style.setProperty("--persona-color", p.color);
  card.innerHTML = `
    <div class="task-title">${escapeHtml(task.title)}</div>
    <div class="task-assignee">${p ? p.name : task.assignee}</div>`;
  card.addEventListener("dragstart", (e) => {
    e.dataTransfer.setData("text/task-id", task.id);
    e.dataTransfer.setData("text/project-id", state.projectId);
  });
  return card;
}

async function onTaskDrop(e, column, projectId) {
  e.preventDefault();
  e.currentTarget.classList.remove("drag-over");
  const taskId = e.dataTransfer.getData("text/task-id");
  if (!taskId) return;
  const res = await fetch(`/api/projects/${projectId}/tasks/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ column }),
  });
  if (res.ok) {
    const project = await res.json();
    renderBoard(project);
  }
}

boardSelect?.addEventListener("change", async () => {
  state.projectId = boardSelect.value;
  const res = await fetch(`/api/projects/${state.projectId}`);
  if (res.ok) renderBoard(await res.json());
});

$("#add-task-btn")?.addEventListener("click", () => {
  if (!state.projectId) {
    alert("Create a project in Project mode first.");
    return;
  }
  const assigneeSelect = $("#task-assignee");
  assigneeSelect.innerHTML = "";
  state.personas.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    assigneeSelect.appendChild(opt);
  });
  $("#task-dialog").showModal();
});

$("#cancel-task")?.addEventListener("click", () => $("#task-dialog").close());

$("#task-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData($("#task-form"));
  const payload = Object.fromEntries(fd.entries());
  const res = await fetch(`/api/projects/${state.projectId}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    $("#task-dialog").close();
    $("#task-form").reset();
    renderBoard(await res.json());
  }
});

// --- API helpers ---

async function loadPersonas() {
  const res = await fetch("/api/personas");
  const data = await res.json();
  state.personas = data.personas;
  renderPersonaGrid();
  renderActiveAgents();
}

async function loadProjects() {
  const res = await fetch("/api/projects");
  const data = await res.json();
  projectList.innerHTML = "";
  (data.projects || []).slice(0, 8).forEach((proj) => {
    const li = document.createElement("li");
    li.textContent = `${proj.title} (${proj.status}) — ${(proj.tasks || []).length} tasks`;
    li.addEventListener("click", () => {
      state.projectId = proj.id;
      setMode("board");
    });
    projectList.appendChild(li);
  });
}

// --- Custom persona dialog ---

$("#add-persona-btn").addEventListener("click", () => personaDialog.showModal());
$("#cancel-persona").addEventListener("click", () => personaDialog.close());

personaForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(personaForm);
  const avatarFile = fd.get("avatar");
  fd.delete("avatar");
  const payload = Object.fromEntries(fd.entries());
  payload.specialties = [payload.role.toLowerCase()];
  payload.tools = ["remember", "forget", "search_docs"];
  const res = await fetch("/api/personas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    const data = await res.json();
    const personaId = data.persona?.id;
    if (avatarFile && avatarFile.size > 0 && personaId) {
      const form = new FormData();
      form.append("file", avatarFile);
      await fetch(`/api/personas/${personaId}/avatar`, { method: "POST", body: form });
    }
    personaDialog.close();
    personaForm.reset();
    await loadPersonas();
  }
});

// --- Team workspaces ---

async function loadWorkspaces() {
  const res = await fetch("/api/workspaces");
  const data = await res.json();
  state.workspaceId = data.active || "default";
  workspaceSelect.innerHTML = "";
  (data.workspaces || []).forEach((ws) => {
    const opt = document.createElement("option");
    opt.value = ws.id;
    opt.textContent = ws.company ? `${ws.name} (${ws.company})` : ws.name;
    if (ws.id === state.workspaceId) opt.selected = true;
    workspaceSelect.appendChild(opt);
  });
}

workspaceSelect?.addEventListener("change", async () => {
  state.workspaceId = workspaceSelect.value;
  await fetch(`/api/workspaces/${state.workspaceId}/activate`, { method: "POST" });
  await loadDocs();
  await loadProjects();
  await loadChatHistory();
  if (state.mode === "board") loadBoard();
});

const workspaceDialog = $("#workspace-dialog");
$("#new-workspace-btn")?.addEventListener("click", () => workspaceDialog.showModal());
$("#cancel-workspace")?.addEventListener("click", () => workspaceDialog.close());

$("#workspace-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData($("#workspace-form"));
  const payload = Object.fromEntries(fd.entries());
  await fetch("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  workspaceDialog.close();
  $("#workspace-form").reset();
  await loadWorkspaces();
});

// --- Company docs (RAG) ---

async function loadDocs() {
  const res = await fetch("/api/docs");
  const data = await res.json();
  docList.innerHTML = "";
  (data.documents || []).forEach((doc) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${doc.filename} (${doc.chunks} chunks)</span>`;
    const btn = document.createElement("button");
    btn.textContent = "Remove";
    btn.addEventListener("click", async () => {
      await fetch(`/api/docs/${doc.id}`, { method: "DELETE" });
      loadDocs();
    });
    li.appendChild(btn);
    docList.appendChild(li);
  });
}

docUpload?.addEventListener("change", async () => {
  const file = docUpload.files?.[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  await fetch("/api/docs", { method: "POST", body: form });
  docUpload.value = "";
  loadDocs();
});

// --- Memory ---

async function loadMemory() {
  const res = await fetch("/api/memory");
  const data = await res.json();
  const list = $("#memory-list");
  list.innerHTML = "";
  (data.entries || []).forEach((entry) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${escapeHtml(entry.key)}</strong>: ${escapeHtml(entry.value)}`;
    const btn = document.createElement("button");
    btn.textContent = "Delete";
    btn.addEventListener("click", async () => {
      await fetch(`/api/memory/${encodeURIComponent(entry.key)}`, { method: "DELETE" });
      loadMemory();
    });
    li.appendChild(btn);
    list.appendChild(li);
  });
}

$("#memory-btn")?.addEventListener("click", () => {
  loadMemory();
  $("#memory-dialog").showModal();
});
$("#close-memory")?.addEventListener("click", () => $("#memory-dialog").close());

$("#memory-add-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData($("#memory-add-form"));
  await fetch("/api/memory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.fromEntries(fd.entries())),
  });
  $("#memory-add-form").reset();
  loadMemory();
});

// --- Status & settings ---

const statusBanner = $("#status-banner");
const updateBanner = $("#update-banner");
const settingsDialog = $("#settings-dialog");
const settingsForm = $("#settings-form");
const providerSelect = $("#provider-select");
const providerStatus = $("#provider-status");

async function loadAppSettings() {
  const res = await fetch("/api/settings");
  if (!res.ok) return null;
  return res.json();
}

function fillSettingsForm(data) {
  if (!data) return;
  state.savedProvider = data.provider || "auto";
  providerSelect.value = state.savedProvider;
  $("#ollama-url").value = data.ollama_base_url || "";
  $("#ollama-model").value = data.ollama_model || "";
  $("#openai-url").value = data.openai_base_url || "";
  $("#openai-model").value = data.openai_model || "";
  $("#openai-key").value = "";
  $("#openai-key").placeholder = data.openai_api_key_set ? "•••••••• (leave blank to keep)" : "sk-…";
  $("#allow-shell").checked = !!data.allow_shell_commands;
  $("#app-version").textContent = data.version || state.appVersion;
  const datalist = $("#ollama-models-list");
  datalist.innerHTML = "";
  (data.ollama_models || []).forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m;
    datalist.appendChild(opt);
  });
}

async function loadAppStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();
  const info = data.provider_info || {};
  const mode = data.provider || "demo";
  state.appVersion = data.version || state.appVersion;

  statusBanner.hidden = false;
  if (mode === "demo") {
    statusBanner.className = "status-banner demo";
    statusBanner.innerHTML =
      "<strong>Demo mode</strong> — works without setup. " +
      '<button type="button" class="inline-link" id="banner-settings">Open Settings</button> to connect Ollama or a cloud API.';
    $("#banner-settings")?.addEventListener("click", () => {
      loadAppSettings().then((s) => {
        fillSettingsForm(s);
        settingsDialog.showModal();
      });
    });
  } else if (mode === "ollama" && info.ollama_available && !info.ollama_model_ready) {
    statusBanner.className = "status-banner demo";
    const model = info.ollama_model || "llama3.2";
    statusBanner.innerHTML =
      `<strong>Ollama is running</strong> but model <code>${model}</code> is not installed. ` +
      `Run <code>ollama pull ${model.split(":")[0]}</code> or switch to Demo in Settings.`;
  } else if (mode === "ollama") {
    statusBanner.className = "status-banner live";
    statusBanner.innerHTML = "<strong>Ollama connected.</strong> Using local AI.";
  } else {
    statusBanner.className = "status-banner live";
    statusBanner.innerHTML = `<strong>${mode === "openai" ? "Cloud AI" : mode}</strong> connected.`;
  }

  if (providerStatus) {
    providerStatus.textContent =
      `Active: ${mode} | Ollama: ${info.ollama_available ? "yes" : "no"} | ` +
      `Model: ${info.ollama_model_ready ? "ready" : "missing"} | ` +
      `API key: ${info.openai_configured ? "yes" : "no"}`;
  }

  return data;
}

async function checkUpdates(showInSettings = false) {
  const res = await fetch("/api/updates");
  const data = await res.json();
  if (data.available) {
    const msg = `Update available: v${data.latest} (you have v${data.current})`;
    if (showInSettings) {
      $("#update-info").innerHTML = `${msg} — <a href="${data.url}" target="_blank" rel="noopener">Download</a>`;
    } else {
      updateBanner.hidden = false;
      updateBanner.className = "status-banner update";
      updateBanner.innerHTML = `${msg} — <a href="${data.url}" target="_blank" rel="noopener">Get update</a>`;
    }
  } else if (showInSettings) {
    $("#update-info").textContent = `You're on the latest version (v${data.current || state.appVersion}).`;
  }
  return data;
}

async function showOnboarding(statusData) {
  if (statusData?.onboarding_completed) return;
  const ollamaEl = $("#onboarding-ollama-status");
  const info = statusData?.provider_info || {};
  if (info.ollama_available && info.ollama_model_ready) {
    ollamaEl.textContent = "Ollama detected — local AI is ready!";
  } else if (info.ollama_available) {
    ollamaEl.textContent = "Ollama is running. Pull a model (e.g. ollama pull llama3.2) for full AI.";
  } else {
    ollamaEl.textContent = "Install Ollama from ollama.com for private local AI.";
  }
  $("#onboarding-dialog").showModal();
}

$("#onboarding-done")?.addEventListener("click", async () => {
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: state.savedProvider || "auto", onboarding_completed: true }),
  });
  $("#onboarding-dialog").close();
});

document.querySelectorAll(".settings-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".settings-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".settings-panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`.settings-panel[data-panel="${tab.dataset.tab}"]`)?.classList.add("active");
  });
});

$("#settings-btn")?.addEventListener("click", async () => {
  const s = await loadAppSettings();
  fillSettingsForm(s);
  await loadBrainSettings();
  await checkUpdates(true);
  settingsDialog.showModal();
});
$("#cancel-settings")?.addEventListener("click", () => settingsDialog.close());

$("#test-provider-btn")?.addEventListener("click", async () => {
  const payload = collectSettingsPayload();
  const res = await fetch("/api/settings/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  const el = $("#test-result");
  el.hidden = false;
  el.className = `test-result ${data.ok ? "ok" : "err"}`;
  el.textContent = data.message;
});

function collectSettingsPayload() {
  return {
    provider: providerSelect.value,
    ollama_base_url: $("#ollama-url").value,
    ollama_model: $("#ollama-model").value,
    openai_base_url: $("#openai-url").value,
    openai_api_key: $("#openai-key").value,
    openai_model: $("#openai-model").value,
    allow_shell_commands: $("#allow-shell").checked,
  };
}

settingsForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = collectSettingsPayload();
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const brainTab = document.querySelector('.settings-panel[data-panel="brain"]');
  if (brainTab?.classList.contains("active")) {
    await saveBrainSettings({});
  }
  settingsDialog.close();
  await loadAppStatus();
});

$("#check-updates-btn")?.addEventListener("click", () => checkUpdates(true));

$("#view-logs-btn")?.addEventListener("click", async () => {
  const res = await fetch("/api/logs");
  const data = await res.json();
  const pre = $("#logs-preview");
  pre.hidden = false;
  const parts = [];
  if (data.log_dir) parts.push(`Log directory: ${data.log_dir}\n`);
  for (const [name, text] of Object.entries(data.logs || {})) {
    parts.push(`--- ${name} ---\n${text}`);
  }
  pre.textContent = parts.join("\n\n") || "No logs yet.";
});

$("#clear-chat-btn")?.addEventListener("click", () => {
  if (confirm("Clear chat history for this mode?")) clearChatHistory();
});

// --- Theme toggle ---

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("persona-theme", theme);
}

function initThemeToggle() {
  const btn = $("#theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    applyTheme(next);
  });
}

document.querySelectorAll(".app-nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const view = btn.dataset.view;
    if (view === "brain") showBrain();
    else showChat();
  });
});

// --- Events ---

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => setMode(btn.dataset.mode));
});

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || state.loading) return;
  input.value = "";
  sendMessage(text);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    composer.requestSubmit();
  }
});

// --- Boot ---

async function boot() {
  setupVoiceInput();
  initThemeToggle();
  setSplashStatus("Connecting to Persona…");

  try {
    const statusData = await loadAppStatus();
    setSplashStatus("Loading workspaces…");
    await loadWorkspaces();
    setSplashStatus("Loading agents…");
    await loadPersonas();
    await loadProjects();
    await loadDocs();
    await loadBrainSettings();
    await loadChatHistory();
    const settingsData = await loadAppSettings();
    fillSettingsForm(settingsData);
    checkUpdates(false);
    showOnboarding(statusData);
  } catch (err) {
    setSplashStatus("Could not connect. Retrying…");
    setTimeout(boot, 1500);
    return;
  }

  hideSplash();
  setInterval(checkBrainErrors, 30000);
}

window.addEventListener("beforeunload", () => {
  navigator.sendBeacon?.("/api/brain/session-end", "{}");
});

boot();
