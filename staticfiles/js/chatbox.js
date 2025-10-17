document.addEventListener("DOMContentLoaded", () => {
  const chatToggle = document.getElementById("chatToggle");
  const chatModal = document.getElementById("chatModal");
  const closeChat = document.getElementById("closeChat");
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const chatMessages = document.getElementById("chatMessages");

  chatToggle.addEventListener("click", () => {
    chatModal.classList.toggle("translate-x-full");
  });

  closeChat.addEventListener("click", () => {
    chatModal.classList.add("translate-x-full");
  });

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;

    const userMsg = document.createElement("div");
    userMsg.className = "bg-blue-500 text-white p-2 rounded-lg self-end max-w-[70%]";
    userMsg.textContent = msg;
    chatMessages.appendChild(userMsg);

    chatMessages.scrollTop = chatMessages.scrollHeight;
    chatInput.value = "";
  });
});

document.getElementById("chatForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    let input = document.getElementById("chatInput");
    let message = input.value.trim();
    if (!message) return;

    let chatBox = document.getElementById("chatMessages");

    // Append user message
    let userMsg = document.createElement("div");
    userMsg.className = "bg-blue-500 text-white p-2 rounded-lg self-end max-w-[70%]";
    userMsg.innerText = message;
    chatBox.appendChild(userMsg);

    input.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // Send to Django backend
    let formData = new FormData();
    formData.append("query", message);

    try {
        let response = await fetch("/chat-assistant/", {
            method: "POST",
            body: formData
        });
        let data = await response.json();

        let botMsg = document.createElement("div");
        botMsg.className = "bg-gray-200 dark:bg-gray-700 p-2 rounded-lg self-start max-w-[70%]";
        botMsg.innerText = data.response || "Error: No response";
        chatBox.appendChild(botMsg);
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (err) {
        console.error(err);
    }
});