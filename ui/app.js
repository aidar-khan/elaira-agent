const state = {
  password: "",
  socket: null,
};

const statusBar = document.getElementById("statusBar");
const eventsBox = document.getElementById("events");
const messageInput = document.getElementById("messageInput");

function setStatus(text) {
  statusBar.textContent = text;
}

function appendEvent(payload) {
  const line = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  eventsBox.textContent += line + "\n\n";
  eventsBox.scrollTop = eventsBox.scrollHeight;
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
  eventsBox.textContent = "";
  for (const event of data.events) {
    appendEvent(event);
  }
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
  const result = await api("/api/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  appendEvent(result);
  messageInput.value = "";
});

document.getElementById("newSessionBtn").addEventListener("click", async () => {
  const result = await api("/api/new-session", { method: "POST" });
  appendEvent(result);
  await refreshSession();
});

