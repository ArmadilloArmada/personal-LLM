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
  appVersion: "1.0.1",
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
    persistChatHistory();
    if (state.voiceEnabled) speak(state.streamRawText, state.streamPersonaId);
  }
  state.streamBubble?.classList.remove("streaming");
  state.streamBubble = null;
  state.streamPersonaId = null;
  state.streamRawText = "";
  clearTalking();
}

function setMode(mode) {
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
  chatPanel.hidden = mode === "board";
  boardPanel.hidden = mode !== "board";
  crewPanel.hidden = mode === "board";
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
    welcome.id = "welcome-bubble";
    welcome.innerHTML = `
      <h3>What would you like to work on?</h3>
      <p>Pick a template — Captain and the crew will plan it with you in Project mode.</p>
      <div class="template-grid" id="template-grid"></div>`;
    messages.appendChild(welcome);
    renderTemplates();
  }
}

// --- Project templates ---

let projectTemplates = [];

async function loadTemplates() {
  const res = await fetch("/api/templates");
  if (!res.ok) return;
  const data = await res.json();
  projectTemplates = data.templates || [];
}

function renderTemplates() {
  const grid = $("#template-grid");
  if (!grid || !projectTemplates.length) return;
  grid.innerHTML = "";
  projectTemplates.forEach((t) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "template-card";
    btn.innerHTML = `
      <span class="template-emoji">${t.emoji || "✨"}</span>
      <strong>${escapeHtml(t.title)}</strong>
      <span class="template-desc">${escapeHtml(t.description || "")}</span>`;
    btn.addEventListener("click", () => startTemplate(t));
    grid.appendChild(btn);
  });
}

function startTemplate(template) {
  setMode(template.mode || "project");
  messages.querySelector(".welcome-bubble")?.remove();
  input.value = template.prompt || "";
  input.focus();
  composer.requestSubmit();
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

async function sendMessage(text) {
  state.loading = true;
  sendBtn.disabled = true;
  sendBtn.classList.add("loading");
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

// --- Persona packs ---

$("#export-pack-btn")?.addEventListener("click", async () => {
  const custom = state.personas.filter((p) => p.is_custom);
  if (!custom.length) {
    alert("No custom agents to export. Create an agent or import a pack first.");
    return;
  }
  const name = prompt("Pack name:", "My Persona Pack") || "My Persona Pack";
  const res = await fetch("/api/personas/pack/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      persona_ids: custom.map((p) => p.id),
      name,
      description: `Exported from Persona on ${new Date().toLocaleDateString()}`,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "Export failed");
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "persona-pack"}.yaml`;
  a.click();
  URL.revokeObjectURL(url);
});

$("#pack-import")?.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/personas/pack/import", { method: "POST", body: form });
  e.target.value = "";
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "Import failed");
    return;
  }
  const data = await res.json();
  await loadPersonas();
  alert(`Imported ${data.count} agent${data.count === 1 ? "" : "s"} from pack.`);
});

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
const bundledSettings = $("#bundled-settings");
const modelTierList = $("#model-tier-list");
const ramStatus = $("#ram-status");
const downloadStatus = $("#download-status");
const bundledThreads = $("#bundled-threads");
const bundledGpuLayers = $("#bundled-gpu-layers");

let selectedModelTier = "balanced";
let downloadPollTimer = null;

async function fetchBundledStatus() {
  const res = await fetch("/api/bundled/status");
  return res.json();
}

function renderModelTiers(bundled) {
  if (!modelTierList || !bundled?.models) return;
  selectedModelTier = bundled.active_tier || "balanced";
  modelTierList.innerHTML = "";
  bundled.models.forEach((tier) => {
    const card = document.createElement("div");
    card.className = `model-tier-card${tier.active ? " active" : ""}`;
    const size = tier.size_mb ? `${tier.size_mb} MB` : tier.bundled ? "bundled" : "download";
    const ramNote = tier.ram_ok ? "" : " — needs more RAM";
    card.innerHTML = `
      <h5>${tier.label}${tier.active ? " (active)" : ""}</h5>
      <p>${tier.description} · ${size}${ramNote}</p>
      <div class="model-tier-actions"></div>
    `;
    const actions = card.querySelector(".model-tier-actions");
    if (tier.installed) {
      const useBtn = document.createElement("button");
      useBtn.textContent = tier.active ? "Selected" : "Use this model";
      useBtn.className = tier.active ? "" : "primary";
      useBtn.disabled = tier.active;
      useBtn.addEventListener("click", () => {
        selectedModelTier = tier.id;
        renderModelTiers({ ...bundled, active_tier: tier.id, models: bundled.models.map((m) => ({
          ...m,
          active: m.id === tier.id,
        })) });
      });
      actions.appendChild(useBtn);
    } else {
      const dlBtn = document.createElement("button");
      dlBtn.textContent = "Download";
      dlBtn.className = "primary";
      dlBtn.addEventListener("click", () => startModelDownload(tier.id));
      actions.appendChild(dlBtn);
    }
    modelTierList.appendChild(card);
  });
}

async function startModelDownload(tier) {
  await fetch("/api/bundled/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tier }),
  });
  pollDownloadStatus();
}

function pollDownloadStatus() {
  if (downloadPollTimer) clearInterval(downloadPollTimer);
  downloadPollTimer = setInterval(async () => {
    const res = await fetch("/api/bundled/download");
    const dl = await res.json();
    if (!downloadStatus) return;
    if (dl.active) {
      downloadStatus.hidden = false;
      downloadStatus.textContent = `Downloading ${dl.tier}… ${dl.progress || 0}%`;
    } else {
      downloadStatus.hidden = !dl.error;
      downloadStatus.textContent = dl.error ? `Download failed: ${dl.error}` : "";
      if (!dl.error) {
        clearInterval(downloadPollTimer);
        downloadPollTimer = null;
        await loadBundledSettings();
        await loadAppStatus();
      }
    }
  }, 1500);
}

async function loadBundledSettings() {
  const bundled = await fetchBundledStatus();
  if (ramStatus) {
    ramStatus.textContent =
      `System RAM: ${bundled.system_ram_gb} GB` +
      (bundled.ram_warning ? " — 8 GB+ recommended for larger models" : "");
  }
  if (bundledThreads) bundledThreads.value = bundled.threads || 0;
  if (bundledGpuLayers) bundledGpuLayers.value = bundled.gpu_layers ?? -1;
  renderModelTiers(bundled);
  return bundled;
}

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
  const bundled = info.bundled || {};
  state.appVersion = data.version || state.appVersion;

  statusBanner.hidden = false;
  if (mode === "bundled") {
    statusBanner.className = "status-banner live";
    const tier = (bundled.models || []).find((m) => m.active);
    statusBanner.innerHTML =
      `<strong>Built-in AI</strong> — offline, no Ollama needed. ` +
      `Model: <code>${tier?.label || bundled.active_tier || "balanced"}</code>`;
  } else if (mode === "demo") {
    statusBanner.className = "status-banner demo";
    statusBanner.innerHTML =
      "<strong>Demo mode</strong> — works without setup. " +
      '<button type="button" class="inline-link" id="banner-settings">Open Settings</button> ' +
      "to enable built-in AI, Ollama, or a cloud API.";
    $("#banner-settings")?.addEventListener("click", () => {
      loadAppSettings().then((s) => {
        fillSettingsForm(s);
        loadBundledSettings();
        settingsDialog.showModal();
      });
    });
  } else if (mode === "ollama" && info.ollama_available && !info.ollama_model_ready) {
    statusBanner.className = "status-banner demo";
    const model = info.ollama_model || "llama3.2";
    const using = info.ollama_model_resolved || model;
    statusBanner.innerHTML =
      `<strong>Ollama is running</strong> — using <code>${using}</code> ` +
      `(configured <code>${model}</code> not found). ` +
      `Run <code>ollama pull ${model.split(":")[0]}</code> or use Built-in AI.`;
  } else if (mode === "ollama" && !info.ollama_tools_supported) {
    statusBanner.className = "status-banner demo";
    statusBanner.innerHTML =
      `<strong>Ollama connected</strong> — model <code>${info.ollama_model_resolved || info.ollama_model}</code> ` +
      "does not support tools. Chat works, but file/memory tools are disabled.";
  } else if (mode === "ollama") {
    statusBanner.className = "status-banner live";
    statusBanner.innerHTML = "<strong>Ollama connected.</strong> Using local AI.";
  } else {
    statusBanner.className = "status-banner live";
    statusBanner.innerHTML = `<strong>${mode === "openai" ? "Cloud AI" : mode}</strong> connected.`;
  }

  if (providerSelect) {
    if (info.active === "bundled") providerSelect.value = "bundled";
    else if (info.active === "demo") providerSelect.value = "demo";
    else if (info.active === "ollama") providerSelect.value = "ollama";
    else if (info.active === "openai") providerSelect.value = "openai";
    else providerSelect.value = "auto";
  }
  if (providerStatus) {
    const builtin = info.bundled_available ? "yes" : "no";
    providerStatus.textContent =
      `Active: ${mode} | Built-in AI: ${builtin} | Ollama: ${info.ollama_available ? "yes" : "no"} | ` +
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
  const info = statusData?.provider_info || {};
  const builtinEl = $("#onboarding-builtin-status");
  if (info.bundled_available) {
    builtinEl.textContent = "Built-in offline AI is ready — no install needed.";
  } else {
    builtinEl.textContent = "Built-in AI ships with the Windows app. Demo mode works everywhere else.";
  }
  const ollamaEl = $("#onboarding-ollama-status");
  if (info.ollama_available && info.ollama_model_ready) {
    ollamaEl.textContent = "Ollama detected — local AI is ready!";
  } else if (info.ollama_available) {
    ollamaEl.textContent = "Ollama is running. Pull a model (e.g. ollama pull llama3.2) for full AI.";
  } else {
    ollamaEl.textContent = "Install Ollama from ollama.com for advanced local models.";
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
  setMode("project");
  renderTemplates();
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
  await loadBundledSettings();
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
  await fetch("/api/bundled/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bundled_model_tier: selectedModelTier,
      bundled_threads: Number(bundledThreads?.value || 0),
      bundled_gpu_layers: Number(bundledGpuLayers?.value ?? -1),
    }),
  });
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
    await loadTemplates();
    renderTemplates();
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
}

boot();
