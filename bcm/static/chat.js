    // Initialize highlight.js for JavaScript syntax if you like
    if (window.hljs) {
        hljs.registerLanguage('javascript', window.hljsJavascript);
      }
  
      // Configure marked.js
      marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function (code, lang) {
          if (window.hljs && lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
          }
          return code;
        },
      });
  
      let ws = null;
      const messagesDiv = document.getElementById('messages');
      const messageInput = document.getElementById('message-input');
      const sendButton = document.getElementById('send-button');
  
      function connectWebSocket() {
        ws = new WebSocket(`ws://${window.location.host}/ws`);
  
        // We keep track of the "current" assistant message if we are receiving streaming chunks
        let currentAssistantMessage = null;
  
        ws.onmessage = function (event) {
          const data = JSON.parse(event.data);
  
          // If server sends history, rebuild it
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
            return;
          }
  
          // User message from server
          if (data.role === 'user') {
            addMessage(data.content, true, data.timestamp);
            currentAssistantMessage = null;
            return;
          }
  
          // Assistant chunk or final response
          if (data.role === 'assistant') {
            // If we haven't started a new assistant message container yet, create one
            if (!currentAssistantMessage) {
              const messageDiv = document.createElement('div');
              messageDiv.className = 'message assistant-message';
              messageDiv.innerHTML = `
                <img src="/static/assistant_avatar.png" alt="Assistant" class="avatar">
                <div class="message-content"></div>
              `;
              messagesDiv.appendChild(messageDiv);
              currentAssistantMessage = {
                element: messageDiv.querySelector('.message-content'),
                content: '',
              };
            }
  
            // Append the chunk to our "currentAssistantMessage"
            currentAssistantMessage.content += data.content;
            currentAssistantMessage.element.innerHTML = marked.parse(currentAssistantMessage.content);
  
            // If there's a timestamp and we haven't added it yet, append it
            if (data.timestamp && !currentAssistantMessage.element.querySelector('.timestamp')) {
              const timestamp = document.createElement('div');
              timestamp.className = 'timestamp';
              timestamp.textContent = new Date(data.timestamp).toLocaleTimeString();
              currentAssistantMessage.element.appendChild(timestamp);
            }
          }
  
          // Always scroll to bottom after updating
          messagesDiv.scrollTop = messagesDiv.scrollHeight;
        };
  
        ws.onclose = function () {
          // Attempt to reconnect after a short delay
          setTimeout(connectWebSocket, 1000);
        };
  
        ws.onerror = function (err) {
          console.error('WebSocket error:', err);
        };
      }
  
      function addMessage(content, isUser, timestamp) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
  
        let avatarSrc = isUser ? '/static/user_avatar.png' : '/static/assistant_avatar.png';
        let avatarAlt = isUser ? 'User' : 'Assistant';
  
        messageDiv.innerHTML = `
          <img src="${avatarSrc}" alt="${avatarAlt}" class="avatar">
          <div class="message-content">
            ${
              isUser
                ? content
                : content
                ? marked.parse(content)
                : ''
            }
            ${
              timestamp
                ? `<div class="timestamp">${new Date(timestamp).toLocaleTimeString()}</div>`
                : ''
            }
          </div>
        `;
  
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return messageDiv.querySelector('.message-content'); // For possible streaming updates
      }
  
      function sendMessage() {
        const message = messageInput.value.trim();
        if (message && ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ content: message }));
          messageInput.value = '';
          sendButton.disabled = true;
        }
      }
  
      // Listeners
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
  
      // Connect on load
      connectWebSocket();