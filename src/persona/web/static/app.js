/** Persona v0.4 — teams, RAG docs, custom avatars */

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
};

const COLUMN_LABELS = {
  backlog: "📋 Backlog",
  in_progress: "🚀 In Progress",
  review: "👀 Review",
  done: "✅ Done",
};

const $ = (sel) => document.querySelector(sel);
const grid = $("#persona-grid");
const messages = $("#messages");
const stageChars = $("#stage-characters");
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

function avatarHtml(persona, size = 52) {
  if (persona?.avatar_url) {
    return `<img src="${persona.avatar_url}?t=${Date.now()}" width="${size}" height="${size}" alt="${persona.name}" />`;
  }
  return svgAvatar(persona, size);
}

// --- Cartoon SVG avatars ---

function svgAvatar(persona, size = 52) {
  const { color, accent, shape } = persona;
  let body = "";

  if (shape === "square") {
    body = `
      <rect x="6" y="10" width="40" height="36" rx="8" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="18" cy="26" r="5" fill="white" stroke="#2d1b4e" stroke-width="1.5"/>
      <circle cx="34" cy="26" r="5" fill="white" stroke="#2d1b4e" stroke-width="1.5"/>
      <line x1="23" y1="26" x2="29" y2="26" stroke="#2d1b4e" stroke-width="1.5"/>
    `;
  } else if (shape === "round") {
    body = `
      ${[0, 45, 90, 135, 180, 225, 270, 315]
        .map((a) => `<line x1="26" y1="26" x2="${26 + 20 * Math.cos((a * Math.PI) / 180)}" y2="${26 + 20 * Math.sin((a * Math.PI) / 180)}" stroke="${color}" stroke-width="3" stroke-linecap="round"/>`)
        .join("")}
      <circle cx="26" cy="26" r="18" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="19" cy="24" r="3" fill="#2d1b4e"/><circle cx="33" cy="24" r="3" fill="#2d1b4e"/>
      <path d="M18 32 Q26 40 34 32" fill="none" stroke="#2d1b4e" stroke-width="2"/>
    `;
  } else if (shape === "star") {
    body = `
      <polygon points="26,4 31,18 46,18 34,28 39,42 26,33 13,42 18,28 6,18 21,18" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="20" cy="24" r="2.5" fill="#2d1b4e"/><circle cx="32" cy="24" r="2.5" fill="#2d1b4e"/>
    `;
  } else if (shape === "blob") {
    body = `
      <path d="M26 8 C8 8 4 28 10 38 C6 48 16 50 26 46 C36 52 48 44 44 30 C50 16 38 6 26 8 Z" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <ellipse cx="19" cy="26" rx="3" ry="4" fill="#2d1b4e"/><ellipse cx="33" cy="26" rx="3" ry="4" fill="#2d1b4e"/>
    `;
  } else if (shape === "hexagon") {
    body = `
      <polygon points="26,4 44,14 44,34 26,44 8,34 8,14" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="20" cy="24" r="3" fill="#2d1b4e"/><circle cx="32" cy="24" r="3" fill="#2d1b4e"/>
      <path d="M20 32 Q26 36 32 32" fill="none" stroke="#2d1b4e" stroke-width="1.5"/>
    `;
  } else if (shape === "diamond") {
    body = `
      <polygon points="26,6 42,26 26,46 10,26" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="20" cy="24" r="2.5" fill="#2d1b4e"/><circle cx="32" cy="24" r="2.5" fill="#2d1b4e"/>
    `;
  } else {
    body = `
      <path d="M26 6 L42 14 L42 30 C42 40 26 48 26 48 C26 48 10 40 10 30 L10 14 Z" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="20" cy="20" r="2" fill="#2d1b4e"/><circle cx="32" cy="20" r="2" fill="#2d1b4e"/>
    `;
  }

  return `<svg viewBox="0 0 52 52" width="${size}" height="${size}">${body}</svg>`;
}

function personaById(id) {
  return state.personas.find((p) => p.id === id);
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
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
    if (state.mode !== "solo" && state.mode !== "board" && state.activeIds.includes(p.id)) btn.classList.add("in-group");
    const badge = p.is_custom ? `<span class="custom-badge">${p.company || "custom"}</span>` : "";
    btn.innerHTML = `
      <div class="persona-avatar">${avatarHtml(p)}</div>
      <div class="persona-info">
        <h3>${p.emoji} ${p.name}${badge}</h3>
        <p>${p.role} — ${p.tagline}</p>
      </div>`;
    btn.addEventListener("click", () => {
      if (state.mode === "solo") {
        state.selectedId = p.id;
        renderPersonaGrid();
        renderStage();
      }
    });
    grid.appendChild(btn);
  });
}

function renderStage() {
  stageChars.innerHTML = "";
  let ids = state.mode === "solo" ? [state.selectedId] : state.activeIds;
  if ((!ids.length && state.mode !== "solo") || state.mode === "board") {
    ids = state.personas.slice(0, 5).map((p) => p.id);
  }
  ids.forEach((id) => {
    const p = personaById(id);
    if (!p) return;
    const div = document.createElement("div");
    div.className = "stage-char";
    div.dataset.id = id;
    div.innerHTML = `${avatarHtml(p, 64)}<span class="char-name">${p.name}</span>`;
    stageChars.appendChild(div);
  });
}

function setTalking(personaId) {
  document.querySelectorAll(".stage-char").forEach((el) => {
    el.classList.toggle("talking", el.dataset.id === personaId);
  });
}

function clearTalking() {
  document.querySelectorAll(".stage-char").forEach((el) => el.classList.remove("talking"));
}

function addMessage({ role, personaId, content, phase, streaming = false }) {
  messages.querySelector(".welcome-bubble")?.remove();
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  if (role === "assistant" && personaId) {
    const p = personaById(personaId);
    const phaseLabel = phase && phase !== "response" ? `<span class="phase-tag">${phase}</span>` : "";
    div.innerHTML = `
      <div class="mini-avatar">${p ? avatarHtml(p, 36) : ""}</div>
      <div>
        <div class="meta" style="--persona-color:${p?.color || "#666"}">${p?.emoji || ""} ${p?.name || "Crew"}${phaseLabel}</div>
        <div class="bubble${streaming ? " streaming" : ""}" style="--persona-color:${p?.color || "#666"}">${escapeHtml(content)}</div>
      </div>`;
  } else {
    div.innerHTML = `<div class="bubble">${escapeHtml(content)}</div>`;
  }
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div.querySelector(".bubble");
}

function startStreamBubble(personaId, phase) {
  messages.querySelector(".welcome-bubble")?.remove();
  const div = document.createElement("div");
  div.className = "msg assistant";
  const p = personaById(personaId);
  const phaseLabel = phase && phase !== "response" ? `<span class="phase-tag">${phase}</span>` : "";
  div.innerHTML = `
    <div class="mini-avatar">${p ? avatarHtml(p, 36) : ""}</div>
    <div>
      <div class="meta" style="--persona-color:${p?.color || "#666"}">${p?.emoji || ""} ${p?.name || "Crew"}${phaseLabel}</div>
      <div class="bubble streaming" style="--persona-color:${p?.color || "#666"}"></div>
    </div>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  state.streamBubble = div.querySelector(".bubble");
  state.streamPersonaId = personaId;
  setTalking(personaId);
  return state.streamBubble;
}

function appendStreamToken(text) {
  if (!state.streamBubble) return;
  state.streamBubble.textContent += text;
  messages.scrollTop = messages.scrollHeight;
}

function finishStreamBubble() {
  state.streamBubble?.classList.remove("streaming");
  const text = state.streamBubble?.textContent || "";
  if (state.voiceEnabled && text) speak(text, state.streamPersonaId);
  state.streamBubble = null;
  state.streamPersonaId = null;
  clearTalking();
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  const hints = {
    solo: "Pick a persona to chat one-on-one.",
    roundtable: "The crew hears you — relevant personas chime in.",
    project: "Captain leads; tasks land on the Board.",
    board: "Drag tasks between columns. Run a Project first to populate.",
  };
  modeHint.textContent = hints[mode] || "";
  projectsPanel.hidden = mode !== "project" && mode !== "board";
  chatPanel.hidden = mode === "board";
  boardPanel.hidden = mode !== "board";
  crewPanel.hidden = mode === "board";
  if (mode === "board") loadBoard();
  renderPersonaGrid();
  renderStage();
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
    appendStreamToken(`\n🔧 ${data.name}...\n`);
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
      content: `Oops — is your LLM provider running?\n\n${err.message}`,
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
    <div class="task-assignee">${p ? `${p.emoji} ${p.name}` : task.assignee}</div>`;
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

// --- API helpers ---

async function loadPersonas() {
  const res = await fetch("/api/personas");
  const data = await res.json();
  state.personas = data.personas;
  renderPersonaGrid();
  renderStage();
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
  if (state.mode === "board") loadBoard();
});

$("#new-workspace-btn")?.addEventListener("click", async () => {
  const name = prompt("Team workspace name:");
  if (!name) return;
  const company = prompt("Company name (optional):") || "";
  await fetch("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, company }),
  });
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
    btn.textContent = "✕";
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

// --- Status & settings ---

const statusBanner = $("#status-banner");
const settingsDialog = $("#settings-dialog");
const settingsForm = $("#settings-form");
const providerSelect = $("#provider-select");
const providerStatus = $("#provider-status");

async function loadAppStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();
  const info = data.provider_info || {};
  const mode = data.provider || "demo";

  statusBanner.hidden = false;
  if (mode === "demo") {
    statusBanner.className = "status-banner demo";
    statusBanner.innerHTML =
      "🎭 <strong>Demo mode</strong> — you're good to go! Chat, projects, and board all work. " +
      "Click ⚙️ to connect Ollama or an API for full AI.";
  } else {
    statusBanner.className = "status-banner live";
    statusBanner.innerHTML = `✨ <strong>${mode === "ollama" ? "Ollama" : "Cloud AI"}</strong> connected — full power enabled.`;
  }

  if (providerSelect) providerSelect.value = info.active === "demo" ? "demo" : (info.ollama_available ? "auto" : "demo");
  if (providerStatus) {
    providerStatus.textContent =
      `Active: ${mode} | Ollama: ${info.ollama_available ? "yes" : "no"} | API key: ${info.openai_configured ? "yes" : "no"}`;
  }
}

$("#settings-btn")?.addEventListener("click", () => {
  loadAppStatus();
  settingsDialog.showModal();
});
$("#cancel-settings")?.addEventListener("click", () => settingsDialog.close());

settingsForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const provider = providerSelect.value;
  await fetch("/api/settings/provider", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  settingsDialog.close();
  loadAppStatus();
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

setupVoiceInput();
loadAppStatus();
loadWorkspaces().then(() => {
  loadPersonas();
  loadProjects();
  loadDocs();
});
