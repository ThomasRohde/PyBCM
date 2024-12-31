from fastapi import FastAPI, WebSocket, Depends, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
from typing import List, Optional, Dict, AsyncIterator
from datetime import datetime, timezone
from dataclasses import dataclass
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader
import os
from pathlib import Path
from contextlib import asynccontextmanager

from .models import SessionLocal
from .database import DatabaseOperations
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.exceptions import UnexpectedModelBehavior

def to_chat_message(m: ModelMessage) -> dict:
    """Convert a ModelMessage to a chat message dict for the frontend."""
    first_part = m.parts[0]
    if isinstance(m, ModelRequest):
        if isinstance(first_part, UserPromptPart):
            return {
                "role": "user",
                "timestamp": first_part.timestamp.isoformat(),
                "content": first_part.content,
            }
    elif isinstance(m, ModelResponse):
        if isinstance(first_part, TextPart):
            return {
                "role": "assistant",
                "timestamp": m.timestamp.isoformat(),
                "content": first_part.content,
            }
    raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")

# Create FastAPI app
app = FastAPI()

# Set up static files serving
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@dataclass
class Deps:
    db: Session

# Set up Jinja environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = Environment(loader=FileSystemLoader(template_dir))

# Load system prompt template
system_prompt_template = jinja_env.get_template('system_prompt.j2')
system_prompt = system_prompt_template.render()

# Initialize the agent
agent = Agent('openai:gpt-4-mini', system_prompt=system_prompt, retries=3, deps_type=Deps)

@agent.system_prompt
def add_user_name() -> str:
    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get('USERNAME', 'User')
    return f"The user's system name is {username}."

@agent.system_prompt
def add_current_time() -> str:
    return f"The current time and date is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Agent tools
@agent.tool
async def get_capability(ctx: RunContext[Deps], capability_id: int) -> Optional[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db)
    capability = db_ops.get_capability(capability_id)
    if capability:
        return {
            "id": capability.id,
            "name": capability.name,
            "description": capability.description,
            "parent_id": capability.parent_id,
            "order_position": capability.order_position
        }
    return None

@agent.tool
async def get_capabilities(ctx: RunContext[Deps], parent_id: Optional[int] = None) -> List[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db)
    capabilities = db_ops.get_capabilities(parent_id)
    return [{
        "id": cap.id,
        "name": cap.name,
        "description": cap.description,
        "parent_id": cap.parent_id,
        "order_position": cap.order_position
    } for cap in capabilities]

@agent.tool
async def get_capability_with_children(ctx: RunContext[Deps], capability_id: int) -> Optional[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db)
    return db_ops.get_capability_with_children(capability_id)

@agent.tool
async def search_capabilities(ctx: RunContext[Deps], query: str) -> List[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db)
    capabilities = db_ops.search_capabilities(query)
    return [{
        "id": cap.id,
        "name": cap.name,
        "description": cap.description,
        "parent_id": cap.parent_id,
        "order_position": cap.order_position
    } for cap in capabilities]

@agent.tool
async def get_markdown_hierarchy(ctx: RunContext[Deps]) -> str:
    db_ops = DatabaseOperations(ctx.deps.db)
    return db_ops.get_markdown_hierarchy()

@agent.tool
async def get_capability_by_name(ctx: RunContext[Deps], name: str) -> Optional[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db)
    capability = db_ops.get_capability_by_name(name)
    if capability:
        return {
            "id": capability.id,
            "name": capability.name,
            "description": capability.description,
            "parent_id": capability.parent_id,
            "order_position": capability.order_position
        }
    return None

# Chat history storage
chat_history = []

# HTML template for the chat interface
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Assistant Chat</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }
        #chat-container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            height: 90vh;
        }
        #messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin: 10px 0;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 80%;
        }
        .user-message {
            background-color: #0d6efd;
            color: white;
            margin-left: auto;
        }
        .assistant-message {
            background-color: #f0f2f5;
            color: #1c1e21;
            margin-right: auto;
        }
        #input-container {
            display: flex;
            padding: 20px;
            border-top: 1px solid #dee2e6;
        }
        #message-input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #dee2e6;
            border-radius: 20px;
            margin-right: 10px;
        }
        #send-button {
            padding: 10px 20px;
            background-color: #0d6efd;
            color: white;
            border: none;
            border-radius: 20px;
            cursor: pointer;
        }
        #send-button:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        pre {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        code {
            font-family: 'Consolas', monospace;
        }
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="messages"></div>
        <div id="input-container">
            <input type="text" id="message-input" placeholder="Type your message...">
            <button id="send-button">Send</button>
        </div>
    </div>
    <script>
        let ws = null;
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');

        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'history') {
                    messagesDiv.innerHTML = '';
                    data.messages.forEach(msg => addMessage(msg.content, msg.is_user));
                } else {
                    addMessage(data.content, data.is_user);
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

        function addMessage(content, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
            messageDiv.innerHTML = content;
            messagesDiv.appendChild(messageDiv);
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
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        sendButton.addEventListener('click', sendMessage);

        messageInput.addEventListener('input', function() {
            sendButton.disabled = !this.value.trim();
        });

        connectWebSocket();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get():
    return CHAT_HTML

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    try:
        await websocket.accept()
        
        # Send chat history
        await websocket.send_json({
            "type": "history",
            "messages": [to_chat_message(msg) for msg in chat_history]
        })
        
        while True:
            try:
                message = await websocket.receive_json()
                user_content = message["content"]
                
                # Create and send user message with proper parts
                user_msg = ModelRequest(
                    parts=[UserPromptPart(
                        content=user_content,
                        timestamp=datetime.now(tz=timezone.utc)
                    )]
                )
                await websocket.send_json(to_chat_message(user_msg))
                chat_history.append(user_msg)

                # Process with AI using the properly structured chat history
=======>>>>>>> REPLACE
```

bcm\web_agent.py
```python
<<<<<<< SEARCH
                        # Create a ModelResponse for each chunk
                        msg = ModelResponse.from_text(
                            content=text,
                            timestamp=result.timestamp()
                        )
                deps = Deps(db=db)
                print("  preparing model and tools")
                async with agent.run_stream(user_content, message_history=chat_history, deps=deps) as result:
                    print("  model request started")
                    async for text in result.stream(debounce_by=0.01):
                        if websocket.client_state != WebSocketState.CONNECTED:
                            break
                        # Create a ModelResponse for each chunk
                        msg = ModelResponse.from_text(
                            content=text,
                            timestamp=result.timestamp()
                        )
                        await websocket.send_json(to_chat_message(msg))
                    
                    if websocket.client_state == WebSocketState.CONNECTED:
                        # Add the final complete response to history
                        chat_history.append(result.response)
                    
            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                print(f"Error type: {type(e)}")
                import traceback
                print(f"Traceback:\n{traceback.format_exc()}")
                if websocket.client_state == WebSocketState.CONNECTED:
                    error_msg = f"Error: {str(e)}"
                    error_response = ModelResponse(
                        parts=[TextPart(content=error_msg)],
                        timestamp=datetime.now(tz=timezone.utc)
                    )
                    await websocket.send_json(to_chat_message(error_response))
                    chat_history.append(error_response)
    except Exception as e:
        print(f"WebSocket connection error: {e}")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()

def start_server():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    start_server()
