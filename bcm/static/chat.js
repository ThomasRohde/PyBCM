// Initialize marked.js with options
marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
        if (window.hljs && lang) {
            try {
                return hljs.highlight(code, { language: lang }).value;
            } catch (e) {
                console.error("Highlighting error:", e);
                return code;
            }
        }
        return code;
    },
});

// Initialize highlight.js and register languages
hljs.highlightAll();

// Get elements
let ws = null;
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');

// Function to apply syntax highlighting to new content
function applySyntaxHighlighting(node) {
    node.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

// Set up the MutationObserver
function mutationCallback(mutationsList) {
    for (const mutation of mutationsList) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    applySyntaxHighlighting(node);
                }
            });
        }
    }
}

const observer = new MutationObserver(mutationCallback);
observer.observe(messagesDiv, { childList: true, subtree: true });

// Function to add messages to the chat
function addMessage(content, isUser, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;

    let avatarSrc = isUser ? '/static/user_avatar.png' : '/static/assistant_avatar.png';
    let avatarAlt = isUser ? 'User' : 'Assistant';

    messageDiv.innerHTML = `
        <img src="${avatarSrc}" alt="${avatarAlt}" class="avatar">
        <div class="message-content">
            ${isUser ? content : marked.parse(content)}
            ${timestamp ? `<div class="timestamp">${new Date(timestamp).toLocaleTimeString()}</div>` : ''}
        </div>
    `;

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// WebSocket setup
function connectWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);

    let currentAssistantMessage = null;

    ws.onmessage = function (event) {
        const data = JSON.parse(event.data);
        if (data.type === 'history') {
            messagesDiv.innerHTML = '';
            if (data.messages.length === 0) {
                const welcomeDiv = document.createElement('div');
                welcomeDiv.className = 'message assistant-message welcome-message';
                welcomeDiv.innerHTML = `
                    <img src="/static/assistant_avatar.png" alt="Assistant" class="avatar">
                    <div class="message-content">Welcome! How can I assist you today?</div>
                `;
                messagesDiv.appendChild(welcomeDiv);
            } else {
                data.messages.forEach((msg) =>
                    addMessage(msg.content, msg.role === 'user', msg.timestamp)
                );
            }
            currentAssistantMessage = null;
        } else {
            if (data.role === 'user') {
                addMessage(data.content, true, data.timestamp);
                currentAssistantMessage = null;
            } else {
                if (!currentAssistantMessage) {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message assistant-message';
                    messageDiv.innerHTML = `
                        <img src="/static/assistant_avatar.png" alt="Assistant" class="avatar">
                        <div class="message-content"></div>
                    `;
                    messagesDiv.appendChild(messageDiv);
                    currentAssistantMessage = messageDiv.querySelector('.message-content');
                }
                currentAssistantMessage.innerHTML = marked.parse(data.content);
                if (data.timestamp && !currentAssistantMessage.querySelector('.timestamp')) {
                    const timestamp = document.createElement('div');
                    timestamp.className = 'timestamp';
                    timestamp.textContent = new Date(data.timestamp).toLocaleTimeString();
                    currentAssistantMessage.appendChild(timestamp);
                }
            }
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    };

    ws.onclose = function () {
        setTimeout(connectWebSocket, 1000);
    };

    ws.onerror = function (err) {
        console.error('WebSocket error:', err);
    };
}

// Function to send messages
function sendMessage() {
    const message = messageInput.value.trim();
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ content: message }));
        messageInput.value = '';
        sendButton.disabled = true;
    }
}

// Event listeners
messageInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendButton.addEventListener('click', sendMessage);

messageInput.addEventListener('input', function () {
    sendButton.disabled = !this.value.trim();
});

// Connect WebSocket on load
connectWebSocket();
