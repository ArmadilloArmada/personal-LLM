/** Persona interactive app — cartoon crew UI */

const state = {
  mode: "solo",
  personas: [],
  selectedId: "byte",
  activeIds: [],
  projectId: null,
  loading: false,
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

// --- Cartoon SVG avatars per persona shape ---

function svgAvatar(persona, size = 52) {
  const { color, accent, shape, emoji } = persona;
  const eye = `<circle cx="0" cy="0" r="4" fill="#2d1b4e"/>`;
  const blush = `<ellipse cx="-12" cy="8" rx="5" ry="3" fill="#ff9eb5" opacity="0.6"/>
                 <ellipse cx="12" cy="8" rx="5" ry="3" fill="#ff9eb5" opacity="0.6"/>`;

  let body = "";
  if (shape === "square") {
    // Byte — boxy coder with glasses
    body = `
      <rect x="6" y="10" width="40" height="36" rx="8" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <rect x="12" y="22" width="28" height="10" rx="3" fill="${accent}" opacity="0.5"/>
      <circle cx="18" cy="26" r="5" fill="white" stroke="#2d1b4e" stroke-width="1.5"/>
      <circle cx="34" cy="26" r="5" fill="white" stroke="#2d1b4e" stroke-width="1.5"/>
      <line x1="23" y1="26" x2="29" y2="26" stroke="#2d1b4e" stroke-width="1.5"/>
      <text x="26" y="42" text-anchor="middle" font-size="10" fill="white" font-family="monospace">{}</text>
    `;
  } else if (shape === "round") {
    // Sunny — sun rays
    body = `
      ${[0, 45, 90, 135, 180, 225, 270, 315]
        .map(
          (a) =>
            `<line x1="26" y1="26" x2="${26 + 20 * Math.cos((a * Math.PI) / 180)}" y2="${
              26 + 20 * Math.sin((a * Math.PI) / 180)
            }" stroke="${color}" stroke-width="3" stroke-linecap="round"/>`
        )
        .join("")}
      <circle cx="26" cy="26" r="18" fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="19" cy="24" r="3" fill="#2d1b4e"/>
      <circle cx="33" cy="24" r="3" fill="#2d1b4e"/>
      <path d="M18 32 Q26 40 34 32" fill="none" stroke="#2d1b4e" stroke-width="2" stroke-linecap="round"/>
    `;
  } else if (shape === "star") {
    // Nova — star body
    body = `
      <polygon points="26,4 31,18 46,18 34,28 39,42 26,33 13,42 18,28 6,18 21,18"
        fill="${color}" stroke="${accent}" stroke-width="2" stroke-linejoin="round"/>
      <circle cx="20" cy="24" r="2.5" fill="#2d1b4e"/>
      <circle cx="32" cy="24" r="2.5" fill="#2d1b4e"/>
      <circle cx="38" cy="14" r="6" fill="none" stroke="white" stroke-width="2" opacity="0.8"/>
      <line x1="42" y1="18" x2="46" y2="22" stroke="white" stroke-width="2"/>
    `;
  } else if (shape === "blob") {
    // Sketch — wobbly blob
    body = `
      <path d="M26 8 C8 8 4 28 10 38 C6 48 16 50 26 46 C36 52 48 44 44 30 C50 16 38 6 26 8 Z"
        fill="${color}" stroke="${accent}" stroke-width="2"/>
      <ellipse cx="19" cy="26" rx="3" ry="4" fill="#2d1b4e"/>
      <ellipse cx="33" cy="26" rx="3" ry="4" fill="#2d1b4e"/>
      <path d="M20 34 Q26 38 32 34" fill="none" stroke="#2d1b4e" stroke-width="1.5"/>
      <rect x="30" y="4" width="4" height="14" rx="1" fill="${accent}" transform="rotate(25 32 11)"/>
    `;
  } else {
    // Captain — shield
    body = `
      <path d="M26 6 L42 14 L42 30 C42 40 26 48 26 48 C26 48 10 40 10 30 L10 14 Z"
        fill="${color}" stroke="${accent}" stroke-width="2"/>
      <circle cx="26" cy="24" r="10" fill="white" opacity="0.9"/>
      <polygon points="26,18 29,24 35,24 30,28 32,34 26,30 20,34 22,28 17,24 23,24"
        fill="${accent}"/>
      <circle cx="20" cy="20" r="2" fill="#2d1b4e"/>
      <circle cx="32" cy="20" r="2" fill="#2d1b4e"/>
    `;
  }

  return `<svg viewBox="0 0 52 52" width="${size}" height="${size}" class="avatar-svg" aria-hidden="true">${body}</svg>`;
}

function personaById(id) {
  return state.personas.find((p) => p.id === id);
}

// --- UI rendering ---

function renderPersonaGrid() {
  grid.innerHTML = "";
  state.personas.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "persona-card";
    btn.style.setProperty("--persona-color", p.color);
    btn.dataset.id = p.id;

    if (state.mode === "solo" && p.id === state.selectedId) btn.classList.add("selected");
    if (state.mode !== "solo" && state.activeIds.includes(p.id)) btn.classList.add("in-group");
    if (state.mode !== "solo" && state.activeIds.length && !state.activeIds.includes(p.id)) {
      btn.classList.add("dimmed");
    }

    btn.innerHTML = `
      <div class="persona-avatar">${svgAvatar(p)}</div>
      <div class="persona-info">
        <h3>${p.emoji} ${p.name}</h3>
        <p>${p.role} — ${p.tagline}</p>
      </div>
    `;

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
  if (!ids.length && state.mode !== "solo") {
    ids = state.personas.map((p) => p.id);
  }

  ids.forEach((id) => {
    const p = personaById(id);
    if (!p) return;
    const div = document.createElement("div");
    div.className = "stage-char";
    div.dataset.id = id;
    div.innerHTML = `${svgAvatar(p, 64)}<span class="char-name">${p.name}</span>`;
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

function addMessage({ role, personaId, content, phase }) {
  const welcome = messages.querySelector(".welcome-bubble");
  if (welcome) welcome.remove();

  const div = document.createElement("div");
  div.className = `msg ${role}`;

  if (role === "assistant" && personaId) {
    const p = personaById(personaId);
    const phaseLabel = phase && phase !== "response" ? `<span class="phase-tag">${phase}</span>` : "";
    div.innerHTML = `
      <div class="mini-avatar">${p ? svgAvatar(p, 36) : ""}</div>
      <div>
        <div class="meta" style="--persona-color:${p?.color || "#666"}">${p?.emoji || ""} ${p?.name || "Crew"}${phaseLabel}</div>
        <div class="bubble" style="--persona-color:${p?.color || "#666"}">${escapeHtml(content)}</div>
      </div>
    `;
  } else {
    div.innerHTML = `<div class="bubble">${escapeHtml(content)}</div>`;
  }

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

function showTyping() {
  const el = document.createElement("div");
  el.className = "msg assistant";
  el.id = "typing";
  el.innerHTML = `
    <div class="bubble">
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    </div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function hideTyping() {
  document.getElementById("typing")?.remove();
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });

  const hints = {
    solo: "Pick a persona to chat one-on-one.",
    roundtable: "The crew hears you — relevant personas chime in.",
    project: "Captain takes the lead and the crew ships your project.",
  };
  modeHint.textContent = hints[mode];
  projectsPanel.hidden = mode !== "project";
  renderPersonaGrid();
  renderStage();
}

// --- API ---

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
    li.textContent = `${proj.title} (${proj.status})`;
    li.addEventListener("click", () => {
      state.projectId = proj.id;
      addMessage({
        role: "assistant",
        personaId: "captain",
        content: `Resuming project "${proj.title}". What's the next step?`,
        phase: "plan",
      });
    });
    projectList.appendChild(li);
  });
}

async function sendMessage(text) {
  state.loading = true;
  sendBtn.disabled = true;
  sendBtn.classList.add("loading");
  addMessage({ role: "user", content: text });
  showTyping();

  try {
    let data;
    if (state.mode === "solo") {
      setTalking(state.selectedId);
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, persona_id: state.selectedId }),
      });
      if (!res.ok) throw new Error(await res.text());
      data = await res.json();
      hideTyping();
      clearTalking();
      (data.messages || []).forEach((m) => {
        addMessage({ role: "assistant", personaId: m.persona_id, content: m.content, phase: m.phase });
      });
    } else {
      const res = await fetch("/api/group", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          mode: state.mode,
          project_id: state.projectId,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      data = await res.json();
      hideTyping();

      state.activeIds = [...new Set((data.messages || []).map((m) => m.persona_id))];
      if (data.project_id) state.projectId = data.project_id;
      renderPersonaGrid();
      renderStage();

      for (const m of data.messages || []) {
        setTalking(m.persona_id);
        await delay(400);
        addMessage({
          role: "assistant",
          personaId: m.persona_id,
          content: m.content,
          phase: m.phase,
        });
      }
      clearTalking();
      if (state.mode === "project") loadProjects();
    }
  } catch (err) {
    hideTyping();
    clearTalking();
    addMessage({
      role: "assistant",
      personaId: "captain",
      content: `Oops — something went wrong. Is your LLM provider running?\n\n${err.message}`,
    });
  } finally {
    state.loading = false;
    sendBtn.disabled = false;
    sendBtn.classList.remove("loading");
  }
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
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

loadPersonas();
loadProjects();
