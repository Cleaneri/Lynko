function sendMessage() {
    const inputElement = document.getElementById("userInput");
    const messageText = inputElement.value.trim();
    
    if (messageText === "") return;

    appendMessage(messageText, "user-message", false);
    inputElement.value = "";

    const loadingId = appendMessage("İdeAI düşünüyor...", "bot-message", false);

    fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: messageText })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById(loadingId).remove();
        appendMessage(data.reply, "bot-message", true);
    })
    .catch(error => {
        document.getElementById(loadingId).remove();
        appendMessage("Bağlantı hatası oluştu.", "bot-message", false);
    });
}

function appendMessage(text, className, shouldFormat) {
    const chatBox = document.getElementById("chatBox");
    const messageDiv = document.createElement("div");
    const uniqueId = "msg-" + Date.now();
    
    messageDiv.className = `message ${className}`;
    messageDiv.id = uniqueId;
    
    if (shouldFormat) {
        messageDiv.innerHTML = text.replace(/\n/g, "<br>");
    } else {
        messageDiv.innerText = text;
    }
    
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    return uniqueId;
}

function handleKeyPress(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}
