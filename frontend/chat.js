/*
  chat.js
  TOP GRADE chatbot widget.

  Talks to POST /api/chat with { student_id, message } and renders the reply.
  Reads `currentUser` from app.js (same page, same global scope) so the bot
  knows who's asking - Rohan gets answers based on his real enrollment,
  Aman gets answers based on his, and a logged-out visitor gets general answers.

  NO CHAT HISTORY (BY DESIGN, FOR NOW):
  Messages live only in the `messages` array below, in memory. Closing the
  widget or refreshing the page clears it. See chatbot.py on the backend for
  the documented upgrade path to persisted history - once that's added, this
  file only needs a small change: fetch past messages on open and prepend
  them to `messages` before rendering.
*/

const CHAT_API = `${API_BASE}/api/chat`;

let chatMessages = []; // { sender: 'user' | 'bot', text: string }
let chatOpen = false;

const chatBubble = document.getElementById("chatBubble");
const chatPanel = document.getElementById("chatPanel");
const chatClose = document.getElementById("chatClose");
const chatMessagesEl = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSend = document.getElementById("chatSend");

function renderChatMessages() {
  chatMessagesEl.innerHTML = chatMessages
    .map(m => `<div class="chat-msg ${m.sender}">${escapeHtml(m.text)}</div>`)
    .join("");
  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function openChat() {
  chatOpen = true;
  chatPanel.classList.add("open");

  if (chatMessages.length === 0) {
    // currentUser comes from app.js's global scope
    const name = (typeof currentUser !== "undefined" && currentUser) ? currentUser.name : null;
    const greeting = name
      ? `Hi ${name}! Ask me anything about your courses, lessons, or enrollment.`
      : "Hi! Ask me about our courses, pricing, or how to enroll.";
    chatMessages.push({ sender: "bot", text: greeting });
    renderChatMessages();
  }

  chatInput.focus();
}

function closeChat() {
  chatOpen = false;
  chatPanel.classList.remove("open");
}

async function sendChatMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  chatMessages.push({ sender: "user", text });
  renderChatMessages();
  chatInput.value = "";

  const studentId = (typeof currentUser !== "undefined" && currentUser) ? currentUser.id : null;

  chatMessages.push({ sender: "bot", text: "..." });
  renderChatMessages();

  try {
    const res = await fetch(CHAT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, message: text }),
    });
    const data = await res.json();
    chatMessages[chatMessages.length - 1] = { sender: "bot", text: data.reply };
  } catch (err) {
    chatMessages[chatMessages.length - 1] = {
      sender: "bot",
      text: "Sorry, I couldn't reach the server. Is the backend running?",
    };
  }
  renderChatMessages();
}

chatBubble.addEventListener("click", () => {
  chatOpen ? closeChat() : openChat();
});
chatClose.addEventListener("click", closeChat);
chatSend.addEventListener("click", sendChatMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChatMessage();
});
