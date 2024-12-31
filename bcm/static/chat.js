// Initialize marked.js with options
marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function(code, lang) {
        if (window.hljs && lang) {
            try {
                return hljs.highlight(code, { language: lang }).value;
            } catch (e) {
                return code;
            }
        }
        return code;
    }
});

let ws = null;
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');

function connectWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    let currentAssistantMessage = null;
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'history') {
            messagesDiv.innerHTML = '';
            // Add welcome message if history is empty
            if (data.messages.length === 0) {
                const welcomeDiv = document.createElement('div');
                welcomeDiv.className = 'welcome-message';
                welcomeDiv.textContent = 'Welcome! How can I assist you today?';
                messagesDiv.appendChild(welcomeDiv);
            } else {
                data.messages.forEach(msg => addMessage(msg.content, msg.role === 'user', msg.timestamp));
            }
            currentAssistantMessage = null;
        } else {
            if (data.role === 'user') {
                addMessage(data.content, true, data.timestamp);
                currentAssistantMessage = null;
            } else {
                if (!currentAssistantMessage) {
                    currentAssistantMessage = addMessage('', false, data.timestamp);
                }
                // Parse markdown and sanitize HTML
                const formattedContent = marked.parse(data.content);
                currentAssistantMessage.innerHTML = formattedContent;
            }
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    };

    ws.onclose = function() {
        setTimeout(connectWebSocket, 1000);
    };

    ws.onerror = function(err) {
        console.error('WebSocket error:', err);
    };
}

function addMessage(content, isUser, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
    
    if (isUser) {
        messageDiv.textContent = content;
    } else {
        messageDiv.innerHTML = content ? marked.parse(content) : '';
    }
    
    if (timestamp) {
        const timeDiv = document.createElement('div');
        timeDiv.className = 'timestamp';
        const date = new Date(timestamp);
        timeDiv.textContent = date.toLocaleTimeString();
        messageDiv.appendChild(timeDiv);
    }
    
    messagesDiv.appendChild(messageDiv);
    return messageDiv;
}

function sendMessage() {
    const message = messageInput.value.trim();
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ content: message }));
        messageInput.value = '';
        sendButton.disabled = true;
    }
}

messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendButton.addEventListener('click', sendMessage);

messageInput.addEventListener('input', function() {
    sendButton.disabled = !this.value.trim();
});

// Initialize the connection
connectWebSocket();
