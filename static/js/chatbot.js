/**
 * HEMONEXAS AI Help Chatbot Controller
 * Provides interactive operational guidance and medical safety guardrails.
 */
function initChatbot() {
  const toggleBtn = document.getElementById("chatbotToggleBtn");
  const modal = document.getElementById("chatbotModal");
  const closeBtn = document.getElementById("chatbotCloseBtn");
  const sendBtn = document.getElementById("chatSendBtn");
  const input = document.getElementById("chatInput");
  const messagesBox = document.getElementById("chatMessages");

  if (!toggleBtn || !modal) return;

  toggleBtn.addEventListener("click", () => {
    modal.classList.toggle("active");
    if (modal.classList.contains("active")) {
      input.focus();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      modal.classList.remove("active");
    });
  }

  async function sendMessage(text) {
    const query = text || input.value.trim();
    if (!query) return;

    // Append user message
    appendMessage(query, "user");
    if (!text) input.value = "";

    // Show typing indicator
    const typingId = appendTypingIndicator();

    try {
      const res = await fetch("/api/chatbot/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query })
      });
      const data = await res.json();
      removeTypingIndicator(typingId);

      if (data.success) {
        appendMessage(data.answer, "bot", data.is_medical_refusal);
      } else {
        appendMessage("Sorry, I encountered an issue processing your query.", "bot");
      }
    } catch (err) {
      removeTypingIndicator(typingId);
      appendMessage("Network error. Please try again later.", "bot");
    }
  }

  function appendMessage(content, sender, isMedical = false) {
    const msg = document.createElement("div");
    msg.className = `chat-bubble chat-bubble-${sender} ${isMedical ? 'chat-medical-refusal' : ''}`;
    
    // Simple markdown formatting (bold, italics, newlines)
    let formatted = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
      
    msg.innerHTML = formatted;
    messagesBox.appendChild(msg);
    messagesBox.scrollTop = messagesBox.scrollHeight;
  }

  function appendTypingIndicator() {
    const id = "typing_" + Date.now();
    const ind = document.createElement("div");
    ind.id = id;
    ind.className = "chat-bubble chat-bubble-bot chat-typing";
    ind.innerHTML = "<span>.</span><span>.</span><span>.</span>";
    messagesBox.appendChild(ind);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", () => sendMessage());
  }

  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // Handle suggestion chips
  document.querySelectorAll(".chip-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      sendMessage(prompt);
    });
  });
}

document.addEventListener("DOMContentLoaded", initChatbot);
