const state = {
  password: "",
  socket: null,
  events: [],
  activeTab: "chat",
};

const statusBar = document.getElementById("statusBar");
const eventsBox = document.getElementById("events");
const chatView = document.getElementById("chatView");
const messageInput = document.getElementById("messageInput");
const chatTabBtn = document.getElementById("chatTabBtn");
const debugTabBtn = document.getElementById("debugTabBtn");

function setStatus(text) {
  statusBar.textContent = text;
}

function extractNestedMessage(text) {
  if (!text || typeof text !== "string") {
    return "";
  }
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && typeof parsed.message === "string") {
      return parsed.message;
    }
  } catch (error) {
    // Ignore invalid nested JSON and return the original text.
  }
  return text;
}

function setTab(tab) {
  state.activeTab = tab;
  const isChat = tab === "chat";
  chatView.classList.toggle("hidden", !isChat);
  eventsBox.classList.toggle("hidden", isChat);
  chatTabBtn.classList.toggle("active", isChat);
  debugTabBtn.classList.toggle("active", !isChat);
}

function bubble(kind, text) {
  const div = document.createElement("div");
  div.className = `bubble bubble-${kind}`;
  div.textContent = text;
  return div;
}

function renderChat() {
  chatView.textContent = "";
  for (const event of state.events) {
    if (event.type === "user_message") {
      chatView.appendChild(bubble("user", event.text || ""));
      continue;
    }
    if (event.type === "ask_user") {
      chatView.appendChild(bubble("agent", event.question || ""));
      continue;
    }
    if (event.type === "finish") {
      chatView.appendChild(bubble("agent", extractNestedMessage(event.message || "")));
      continue;
    }
    if (event.type === "notify_user") {
      chatView.appendChild(bubble("status", event.message || ""));
      continue;
    }
    if (event.type === "tool_started" && event.tool === "bash") {
      chatView.appendChild(bubble("status", `Running command: ${event.command || ""}`));
      continue;
    }
  }
  chatView.scrollTop = chatView.scrollHeight;
}

function renderDebug() {
  eventsBox.textContent = "";
  for (const payload of state.events) {
    const line = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
    eventsBox.textContent += line + "\n\n";
  }
  eventsBox.scrollTop = eventsBox.scrollHeight;
}

function renderAll() {
  renderChat();
  renderDebug();
}

function appendEvent(payload) {
  state.events.push(payload);
  renderAll();
}

async function api(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (state.password) {
    headers["X-Agent-Password"] = state.password;
  }
  const response = await fetch(path, Object.assign({}, options, { headers }));
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function refreshSession() {
  const data = await api("/api/session");
  state.events = data.events || [];
  renderAll();
}

function connectSocket() {
  if (!state.password) {
    return;
  }
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${scheme}://${location.host}/api/ws?password=${encodeURIComponent(state.password)}`);
  state.socket.onopen = () => setStatus("Connected");
  state.socket.onmessage = (event) => appendEvent(JSON.parse(event.data));
  state.socket.onclose = () => setStatus("Disconnected");
}

document.getElementById("connectBtn").addEventListener("click", async () => {
  const password = prompt("Agent password");
  if (password === null) {
    return;
  }
  state.password = password;
  await refreshSession();
  connectSocket();
  const status = await api("/api/status");
  setStatus(status.session_state);
});

document.getElementById("sendBtn").addEventListener("click", async () => {
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }
  await api("/api/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  messageInput.value = "";
  await refreshSession();
});

document.getElementById("newSessionBtn").addEventListener("click", async () => {
  await api("/api/new-session", { method: "POST" });
  await refreshSession();
});

chatTabBtn.addEventListener("click", () => setTab("chat"));
debugTabBtn.addEventListener("click", () => setTab("debug"));
