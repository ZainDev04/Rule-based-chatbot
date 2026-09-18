/* Nova chat interface
 *
 * Plain JavaScript, no build step. Responsibilities:
 *   - send messages to /api/chat and render replies with their intent tag
 *   - show the match trace (tier, confidence, entities) for the last reply
 *   - keep the conversation in localStorage so a refresh does not lose it
 *   - keyboard support: Enter sends, Shift+Enter newline, Escape clears,
 *     "/" focuses the box, arrow keys move between suggestion chips
 *   - light and dark theme with the system preference as the default
 */
(function () {
  "use strict";

  var CONFIG = window.NOVA_CONFIG || { botName: "Nova", maxLength: 500 };
  var STORAGE = { session: "nova.session", history: "nova.history", theme: "nova.theme" };
  var HISTORY_LIMIT = 60;
  var THINK_DELAY_MS = 350; // small pause so the typing indicator is visible

  var $ = function (id) { return document.getElementById(id); };
  var els = {
    messages: $("messages"),
    welcome: $("welcome-message"),
    form: $("composer"),
    input: $("message"),
    send: $("send"),
    charUsed: $("char-used"),
    charCount: $("char-count"),
    formError: $("form-error"),
    chips: $("chips"),
    clear: $("clear-chat"),
    statusText: $("status-text"),
    status: document.querySelector(".status"),
    themeToggle: $("theme-toggle"),
    themeLabel: $("theme-label"),
    traceToggle: $("trace-toggle"),
    traceClose: $("trace-close"),
    tracePanel: $("trace-panel"),
    scrim: $("scrim"),
    traceEmpty: $("trace-empty"),
    traceList: $("trace-list"),
    traceRaw: $("trace-raw"),
    traceClean: $("trace-clean"),
    traceTier: $("trace-tier"),
    traceIntent: $("trace-intent"),
    tracePhrase: $("trace-phrase"),
    traceMeter: $("trace-meter"),
    traceMeterFill: $("trace-meter-fill"),
    traceConfidence: $("trace-confidence-label"),
    traceEntities: $("trace-entities"),
    traceMs: $("trace-ms"),
    pipeline: $("pipeline"),
    sessionName: $("session-name"),
    sessionTurns: $("session-turns"),
    sessionLast: $("session-last"),
    intentList: $("intent-list"),
    template: $("message-template")
  };

  // ------------------------------------------------------------ storage

  function readStorage(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (err) {
      return fallback;
    }
  }

  function writeStorage(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (err) { /* private mode */ }
  }

  function removeStorage(key) {
    try { localStorage.removeItem(key); } catch (err) { /* ignore */ }
  }

  function newSessionId() {
    var bytes = new Uint8Array(16);
    if (window.crypto && crypto.getRandomValues) {
      crypto.getRandomValues(bytes);
    } else {
      for (var i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
    }
    return Array.prototype.map.call(bytes, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
  }

  var state = {
    sessionId: readStorage(STORAGE.session, null) || newSessionId(),
    history: readStorage(STORAGE.history, []),
    busy: false
  };
  writeStorage(STORAGE.session, state.sessionId);

  // ------------------------------------------------------------- theme

  function currentTheme() {
    var explicit = document.documentElement.getAttribute("data-theme");
    if (explicit) return explicit;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyThemeButton() {
    var dark = currentTheme() === "dark";
    els.themeToggle.setAttribute("aria-pressed", String(dark));
    els.themeToggle.setAttribute("data-current", dark ? "dark" : "light");
    els.themeLabel.textContent = dark ? "Light theme" : "Dark theme";
    els.themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    document.querySelector('meta[name="theme-color"]').setAttribute("content", "#000000");
  }

  els.themeToggle.addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    writeStorage(STORAGE.theme, next);
    applyThemeButton();
  });

  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyThemeButton);
  }
  applyThemeButton();

  // ------------------------------------------------------- trace sheet

  var lastFocusBeforeTrace = null;

  function openTrace() {
    els.tracePanel.classList.add("is-open");
    els.traceToggle.setAttribute("aria-expanded", "true");
    els.scrim.hidden = false;
    lastFocusBeforeTrace = document.activeElement;
    els.tracePanel.focus();
  }

  function closeTrace() {
    if (!els.tracePanel.classList.contains("is-open")) return;
    els.tracePanel.classList.remove("is-open");
    els.traceToggle.setAttribute("aria-expanded", "false");
    els.scrim.hidden = true;
    if (lastFocusBeforeTrace && lastFocusBeforeTrace.focus) lastFocusBeforeTrace.focus();
  }

  els.traceToggle.addEventListener("click", function () {
    if (els.tracePanel.classList.contains("is-open")) closeTrace(); else openTrace();
  });
  els.traceClose.addEventListener("click", closeTrace);
  els.scrim.addEventListener("click", closeTrace);

  // ---------------------------------------------------------- messages

  function formatTime(iso) {
    var d = iso ? new Date(iso) : new Date();
    var h = d.getHours(), m = d.getMinutes();
    var suffix = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return h + ":" + (m < 10 ? "0" : "") + m + " " + suffix;
  }

  function scrollToBottom() {
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function renderMessage(entry) {
    var node = els.template.content.firstElementChild.cloneNode(true);
    var isUser = entry.role === "user";
    node.classList.add(isUser ? "msg-user" : "msg-bot");
    if (entry.kind === "system") node.classList.add("msg-system");
    if (entry.kind === "error") node.classList.add("msg-error");

    node.querySelector(".msg-sender").textContent = isUser ? "You" : CONFIG.botName;
    node.querySelector(".msg-bubble").textContent = entry.text;

    var timeEl = node.querySelector(".msg-time");
    timeEl.textContent = formatTime(entry.at);
    if (entry.at) timeEl.setAttribute("datetime", entry.at);

    var tag = node.querySelector(".intent-tag");
    if (!isUser && entry.intent) {
      tag.hidden = false;
      tag.textContent = entry.intent;
      if (entry.tier && entry.tier !== "none" && entry.intent !== "exit") {
        tag.textContent += " " + Math.round((entry.confidence || 0) * 100) + "%";
        tag.title = "Matched in the " + entry.tier + " tier";
      }
      if (entry.intent === "fallback") tag.classList.add("intent-tag-fallback");
      if (entry.kind === "system") tag.classList.add("intent-tag-system");
      if (entry.kind === "error") tag.classList.add("intent-tag-error");
    }

    els.messages.appendChild(node);
    scrollToBottom();
    return node;
  }

  function pushHistory(entry) {
    state.history.push(entry);
    if (state.history.length > HISTORY_LIMIT) state.history.splice(0, state.history.length - HISTORY_LIMIT);
    writeStorage(STORAGE.history, state.history);
  }

  function addMessage(entry) {
    entry.at = entry.at || new Date().toISOString();
    renderMessage(entry);
    if (entry.kind !== "error") pushHistory(entry);
  }

  var typingNode = null;
  function showTyping() {
    typingNode = els.template.content.firstElementChild.cloneNode(true);
    typingNode.classList.add("msg-bot");
    typingNode.setAttribute("aria-hidden", "true");
    typingNode.querySelector(".msg-sender").textContent = CONFIG.botName;
    typingNode.querySelector(".msg-time").remove();
    var bubble = typingNode.querySelector(".msg-bubble");
    bubble.className = "msg-bubble typing";
    bubble.innerHTML = "<span></span><span></span><span></span>";
    els.messages.appendChild(typingNode);
    scrollToBottom();
  }
  function hideTyping() {
    if (typingNode) { typingNode.remove(); typingNode = null; }
  }

  // ------------------------------------------------------------- trace

  var PIPELINE_ORDER = ["exact", "pattern", "keyword", "fuzzy"];

  function updatePipeline(tier, intent) {
    var items = els.pipeline.querySelectorAll("li");
    var hitStep = intent === "fallback" ? "fallback" : tier;
    var reached = false;
    items.forEach(function (li) {
      var step = li.getAttribute("data-step");
      li.classList.remove("is-tried", "is-hit");
      if (step === "sanitize") { li.classList.add("is-tried"); return; }
      if (reached) return;
      if (step === hitStep) { li.classList.add("is-hit"); reached = true; return; }
      if (PIPELINE_ORDER.indexOf(step) !== -1) li.classList.add("is-tried");
    });
  }

  function updateTrace(data) {
    els.traceEmpty.hidden = true;
    els.traceList.hidden = false;
    els.traceRaw.textContent = data.raw_input;
    els.traceClean.textContent = data.cleaned_input || "(empty)";
    els.traceTier.textContent = data.tier;
    els.traceIntent.textContent = "";
    var tag = document.createElement("span");
    tag.className = "intent-tag" + (data.intent === "fallback" ? " intent-tag-fallback" : "");
    tag.textContent = data.intent;
    els.traceIntent.appendChild(tag);
    els.tracePhrase.textContent = data.matched_phrase || "none";

    var percent = Math.round((data.confidence || 0) * 100);
    els.traceMeterFill.style.width = percent + "%";
    els.traceMeter.setAttribute("aria-valuenow", String(percent));
    els.traceConfidence.textContent = percent + "%";

    var entities = data.entities && Object.keys(data.entities).length
      ? Object.keys(data.entities).map(function (k) { return k + " = " + data.entities[k]; }).join(", ")
      : "none";
    els.traceEntities.textContent = entities;
    els.traceMs.textContent = data.processing_ms + " ms";

    updatePipeline(data.tier, data.intent);

    if (data.session) {
      els.sessionName.textContent = data.session.user_name || "unknown";
      els.sessionTurns.textContent = data.session.turn_count;
      els.sessionLast.textContent = data.session.last_intent || "none";
    }
  }

  // ------------------------------------------------------------- intents

  function loadIntents() {
    fetch("/api/intents").then(function (res) { return res.json(); }).then(function (body) {
      els.intentList.innerHTML = "";
      body.intents.forEach(function (item) {
        var li = document.createElement("li");
        var name = document.createElement("span");
        name.className = "intent-name";
        name.textContent = item.name + (item.dynamic ? " (dynamic)" : "");
        var desc = document.createElement("span");
        desc.className = "intent-desc";
        desc.textContent = item.description;
        li.appendChild(name);
        li.appendChild(desc);
        item.examples.forEach(function (example) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "intent-example";
          btn.textContent = example;
          btn.setAttribute("aria-label", "Send: " + example);
          btn.addEventListener("click", function () { closeTrace(); sendMessage(example); });
          li.appendChild(btn);
        });
        els.intentList.appendChild(li);
      });
      $("intent-count").textContent = body.count;
      $("intent-count-detail").textContent = body.count;
    }).catch(function () {
      els.intentList.innerHTML = "<li>Could not load the intent list.</li>";
    });
  }

  // -------------------------------------------------------------- status

  function setOnline(online) {
    els.statusText.textContent = online ? "Online" : "Offline";
    els.status.classList.toggle("is-offline", !online);
  }

  // ---------------------------------------------------------------- send

  function setBusy(busy) {
    state.busy = busy;
    els.send.disabled = busy;
    els.send.classList.toggle("is-loading", busy);
    els.send.setAttribute("aria-busy", String(busy));
    els.chips.querySelectorAll(".chip").forEach(function (chip) { chip.disabled = busy; });
  }

  function showFormError(message) {
    els.formError.textContent = message;
    els.formError.hidden = false;
    els.input.setAttribute("aria-invalid", "true");
  }
  function clearFormError() {
    els.formError.hidden = true;
    els.formError.textContent = "";
    els.input.removeAttribute("aria-invalid");
  }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function sendMessage(text) {
    text = (text || "").trim();
    if (!text || state.busy) return;
    if (text.length > CONFIG.maxLength) {
      showFormError("Messages are limited to " + CONFIG.maxLength + " characters.");
      return;
    }
    clearFormError();

    addMessage({ role: "user", text: text });
    els.input.value = "";
    updateCharCount();
    autosize();
    setBusy(true);
    showTyping();

    var request = fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: state.sessionId })
    });

    Promise.all([request, sleep(THINK_DELAY_MS)]).then(function (results) {
      var res = results[0];
      return res.json().then(function (body) { return { ok: res.ok, status: res.status, body: body }; });
    }).then(function (result) {
      hideTyping();
      setOnline(true);
      if (!result.ok) {
        var message = (result.body && result.body.error && result.body.error.message) || "The server returned an error.";
        addMessage({ role: "bot", kind: "error", intent: "error", text: message });
        if (result.status === 413) showFormError(message);
        return;
      }
      var data = result.body;
      addMessage({
        role: "bot",
        text: data.response,
        intent: data.intent,
        tier: data.tier,
        confidence: data.confidence,
        kind: data.intent === "exit" ? "system" : undefined
      });
      updateTrace(data);
      if (data.session_ended) {
        // The server dropped this session; start a fresh one for the next message.
        state.sessionId = newSessionId();
        writeStorage(STORAGE.session, state.sessionId);
        addMessage({ role: "bot", kind: "system", intent: "system", text: "Session ended. Your next message starts a new one." });
        els.sessionName.textContent = "unknown";
        els.sessionTurns.textContent = "0";
        els.sessionLast.textContent = "none";
      }
    }).catch(function () {
      hideTyping();
      setOnline(false);
      addMessage({ role: "bot", kind: "error", intent: "error", text: "Could not reach the server. Check your connection and try again." });
    }).then(function () {
      setBusy(false);
      // Keep focus in the box on desktop; on phones this would pop the keyboard up again.
      if (window.matchMedia("(min-width: 768px)").matches) els.input.focus();
    });
  }

  // ------------------------------------------------------------ composer

  function updateCharCount() {
    var used = els.input.value.length;
    els.charUsed.textContent = used;
    els.charCount.classList.toggle("is-near-limit", used >= CONFIG.maxLength * 0.9);
  }

  function autosize() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 144) + "px";
    els.input.style.overflowY = els.input.scrollHeight > 144 ? "auto" : "hidden";
  }

  els.form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!els.input.value.trim()) {
      showFormError("Type a message first.");
      els.input.focus();
      return;
    }
    sendMessage(els.input.value);
  });

  els.input.addEventListener("input", function () {
    updateCharCount();
    autosize();
    if (els.input.value.trim()) clearFormError();
  });

  els.input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.form.requestSubmit ? els.form.requestSubmit() : els.form.dispatchEvent(new Event("submit", { cancelable: true }));
    } else if (event.key === "Escape") {
      els.input.value = "";
      updateCharCount();
      autosize();
      clearFormError();
    }
  });

  // Global shortcuts: "/" focuses the box, Escape closes the trace sheet.
  document.addEventListener("keydown", function (event) {
    var inField = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if (event.key === "/" && !inField && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      els.input.focus();
    } else if (event.key === "Escape") {
      closeTrace();
    }
  });

  // --------------------------------------------------------------- chips

  var chips = Array.prototype.slice.call(els.chips.querySelectorAll(".chip"));
  chips.forEach(function (chip, index) {
    chip.setAttribute("tabindex", index === 0 ? "0" : "-1");
    chip.addEventListener("click", function () { sendMessage(chip.getAttribute("data-message")); });
    chip.addEventListener("keydown", function (event) {
      var next = null;
      if (event.key === "ArrowRight") next = chips[(index + 1) % chips.length];
      else if (event.key === "ArrowLeft") next = chips[(index - 1 + chips.length) % chips.length];
      else if (event.key === "Home") next = chips[0];
      else if (event.key === "End") next = chips[chips.length - 1];
      if (next) {
        event.preventDefault();
        chips.forEach(function (c) { c.setAttribute("tabindex", "-1"); });
        next.setAttribute("tabindex", "0");
        next.focus();
        next.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
    });
  });

  // --------------------------------------------------------------- clear

  els.clear.addEventListener("click", function () {
    fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId })
    }).catch(function () { /* offline: local clear still happens */ });

    state.history = [];
    removeStorage(STORAGE.history);
    state.sessionId = newSessionId();
    writeStorage(STORAGE.session, state.sessionId);

    els.messages.innerHTML = "";
    els.welcome.hidden = false;
    els.messages.appendChild(els.welcome);
    els.traceList.hidden = true;
    els.traceEmpty.hidden = false;
    updatePipeline("none", "none");
    els.sessionName.textContent = "unknown";
    els.sessionTurns.textContent = "0";
    els.sessionLast.textContent = "none";
    clearFormError();
    els.input.focus();
  });

  // ---------------------------------------------------------------- init

  function restoreHistory() {
    if (!state.history.length) return;
    els.welcome.hidden = true;
    state.history.forEach(renderMessage);
    var lastBot = null;
    for (var i = state.history.length - 1; i >= 0; i--) {
      if (state.history[i].role === "bot" && state.history[i].tier) { lastBot = state.history[i]; break; }
    }
    if (lastBot) updatePipeline(lastBot.tier, lastBot.intent);
  }

  restoreHistory();
  loadIntents();
  updateCharCount();
  fetch("/api/health").then(function (r) { setOnline(r.ok); }).catch(function () { setOnline(false); });
})();
