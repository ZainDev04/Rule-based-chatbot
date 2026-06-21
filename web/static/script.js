const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const sendBtn = chatForm.querySelector(".send-btn");

// Small artificial delay before the bot "replies" - gives the typing
// indicator something to show, and makes the intent-match feel like
// it's actually being computed rather than appearing instantly.
const THINK_DELAY_MS = 550;

function scrollToBottom() {
  chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: "smooth" });
}

function addMessage({ sender, text, intent, isUser }) {
  const msg = document.createElement("div");
  msg.className = "msg msg-new " + (isUser ? "msg-user" : "msg-bot");

  const meta = document.createElement("div");
  meta.className = "msg-meta";

  const senderSpan = document.createElement("span");
  senderSpan.className = "msg-sender";
  senderSpan.textContent = sender;
  meta.appendChild(senderSpan);

  if (intent) {
    const tag = document.createElement("span");
    tag.className = "intent-tag" + (intent === "fallback" ? " intent-tag-fallback" : "");
    tag.textContent = `[${intent}]`;
    meta.appendChild(tag);
  }

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.textContent = text;

  msg.appendChild(meta);
  msg.appendChild(bubble);
  chatWindow.appendChild(msg);
  scrollToBottom();

  // Drop the "-new" class once the entry animation has played, so it
  // doesn't replay if the DOM ever reflows.
  msg.addEventListener("animationend", () => msg.classList.remove("msg-new"), { once: true });
}

function showTypingIndicator() {
  const wrap = document.createElement("div");
  wrap.className = "msg msg-bot msg-new";
  wrap.id = "typing-indicator-wrap";

  const meta = document.createElement("div");
  meta.className = "msg-meta";
  const senderSpan = document.createElement("span");
  senderSpan.className = "msg-sender";
  senderSpan.textContent = "NOVA";
  meta.appendChild(senderSpan);

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble typing-indicator";
  bubble.innerHTML = "<span></span><span></span><span></span>";

  wrap.appendChild(meta);
  wrap.appendChild(bubble);
  chatWindow.appendChild(wrap);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator-wrap");
  if (el) el.remove();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function sendMessage(message) {
  addMessage({ sender: "YOU", text: message, intent: null, isUser: true });
  userInput.value = "";
  sendBtn.disabled = true;

  showTypingIndicator();

  try {
    const [res] = await Promise.all([
      fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      }),
      sleep(THINK_DELAY_MS)
    ]);
    const data = await res.json();

    removeTypingIndicator();
    addMessage({
      sender: "NOVA",
      text: data.response,
      intent: data.intent,
      isUser: false
    });

    if (data.session_ended) {
      userInput.disabled = true;
      sendBtn.disabled = true;
      userInput.placeholder = "Session ended. Refresh to start again.";
    } else {
      sendBtn.disabled = false;
      userInput.focus();
    }
  } catch (err) {
    removeTypingIndicator();
    addMessage({
      sender: "NOVA",
      text: "Connection error — is the Flask server running?",
      intent: "error",
      isUser: false
    });
    sendBtn.disabled = false;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = userInput.value.trim();
  if (!message) return;
  sendMessage(message);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    sendMessage(chip.dataset.msg);
  });
});

userInput.focus();
