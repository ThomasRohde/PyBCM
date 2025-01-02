from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.websockets import WebSocketState
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Optional, Dict
from datetime import datetime, timezone
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader
import os
from pathlib import Path

from .database import DatabaseOperations
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
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
    db_factory: AsyncSession  # This will actually hold the session factory

# Set up Jinja environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = Environment(loader=FileSystemLoader(template_dir))

# Load system prompt template
system_prompt_template = jinja_env.get_template('system_prompt.j2')
system_prompt = system_prompt_template.render()

# Initialize the agent
agent = Agent('openai:gpt-4o-mini', system_prompt=system_prompt, retries=3, deps_type=Deps)

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

# Agent tools
@agent.tool
async def get_capability(ctx: RunContext[Deps], capability_id: int) -> Optional[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db_factory)
    capability = await db_ops.get_capability(capability_id)
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
    db_ops = DatabaseOperations(ctx.deps.db_factory)
    capabilities = await db_ops.get_capabilities(parent_id)
    return [{
        "id": cap.id,
        "name": cap.name,
        "description": cap.description,
        "parent_id": cap.parent_id,
        "order_position": cap.order_position
    } for cap in capabilities]

@agent.tool
async def get_capability_with_children(ctx: RunContext[Deps], capability_id: int) -> Optional[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db_factory)
    return await db_ops.get_capability_with_children(capability_id)

@agent.tool
async def search_capabilities(ctx: RunContext[Deps], query: str) -> List[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db_factory)
    capabilities = await db_ops.search_capabilities(query)
    return [{
        "id": cap.id,
        "name": cap.name,
        "description": cap.description,
        "parent_id": cap.parent_id,
        "order_position": cap.order_position
    } for cap in capabilities]

@agent.tool
async def get_markdown_hierarchy(ctx: RunContext[Deps]) -> str:
    db_ops = DatabaseOperations(ctx.deps.db_factory)
    return await db_ops.get_markdown_hierarchy()

@agent.tool
async def get_capability_by_name(ctx: RunContext[Deps], name: str) -> Optional[Dict]:
    db_ops = DatabaseOperations(ctx.deps.db_factory)
    capability = await db_ops.get_capability_by_name(name)
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

# Load chat template
chat_template = jinja_env.get_template('chat.html')

@app.get("/", response_class=HTMLResponse)
async def get():
    return chat_template.render()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
                from .models import AsyncSessionLocal
                deps = Deps(db_factory=AsyncSessionLocal)
                print("  preparing model and tools")
                # Initialize an empty string to collect the full response
                full_response = ""
                
                async with agent.run_stream(user_content, message_history=chat_history, deps=deps) as result:
                    print("  model request started")
                    async for text in result.stream(debounce_by=0.01):
                        if websocket.client_state != WebSocketState.CONNECTED:
                            break
                        # Accumulate the full response
                        full_response += text
                        # Create a ModelResponse with TextPart for each chunk
                        msg = ModelResponse(
                            parts=[TextPart(content=text)],
                            timestamp=result.timestamp()
                        )
                        await websocket.send_json(to_chat_message(msg))
                    
                    if websocket.client_state == WebSocketState.CONNECTED:
                        # Create and add the final complete response to history
                        final_response = ModelResponse(
                            parts=[TextPart(content=full_response)],
                            timestamp=result.timestamp()
                        )
                        chat_history.append(final_response)
                        
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
