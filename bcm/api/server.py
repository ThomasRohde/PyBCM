from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
import os
import socket
import pyperclip
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Set
from bcm.models import (
    CapabilityCreate,
    CapabilityUpdate,
    LayoutModel,
    SettingsModel,
    TemplateSettings,
    get_db,
    AsyncSessionLocal,
)
from bcm.layout_manager import process_layout
from bcm.api.export_handler import format_capability
from bcm.settings import Settings
from bcm.database import DatabaseOperations
import uuid

def get_all_ipv4_addresses():
    """Get all available IPv4 addresses including VPN."""
    ip_addresses = []
    try:
        # Get all network interfaces
        interfaces = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)  # AF_INET for IPv4 only
        for interface in interfaces:
            ip = interface[4][0]
            # Only include IPv4 addresses and exclude localhost
            if ip and not ip.startswith('127.'):
                ip_addresses.append(ip)
        # Remove duplicates while preserving order
        return list(dict.fromkeys(ip_addresses))
    except Exception:
        # Fallback to basic hostname resolution
        try:
            return [socket.gethostbyname(socket.gethostname())]
        except Exception:
            return ['127.0.0.1']  # Last resort fallback

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Get port from uvicorn command arguments
    import sys
    port = 8080  # Default port
    
    # Check if running with uvicorn CLI
    if 'uvicorn' in sys.argv[0]:
        try:
            # Find --port argument
            port_index = sys.argv.index('--port') + 1
            if port_index < len(sys.argv):
                port = int(sys.argv[port_index])
        except (ValueError, IndexError):
            pass
    
    # Get all available IPv4 addresses
    ip_addresses = get_all_ipv4_addresses()
    
    print("\nAvailable network URLs:")
    urls = [f"http://{ip}:{port}" for ip in ip_addresses]
    
    for url in urls:
        print(f"- {url}")
    
    print("\nShare any of these URLs with other users to access the application")
    
    # Find the best URL to copy to clipboard
    # Prefer non-192.* addresses first
    preferred_urls = [url for url in urls if not url.startswith('http://192.')]
    fallback_urls = [url for url in urls if url.startswith('http://192.')]
    
    if preferred_urls:
        pyperclip.copy(preferred_urls[0])
        print("First non-192.* URL copied to clipboard!")
    elif fallback_urls:
        pyperclip.copy(fallback_urls[0])
        print("Local network URL copied to clipboard (no VPN/external IPs found)")
    
    yield  # Server is running
    # Shutdown: Nothing to clean up

# Initialize FastAPI app
app = FastAPI(title="Business Capability Model API", lifespan=lifespan)
api_app = FastAPI(title="Business Capability Model API")

# Add CORS middleware
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Mount API routes
app.mount("/api", api_app)

# Mount static files
static_client_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "client")
app.mount("/assets", StaticFiles(directory=os.path.join(static_client_dir, "assets")), name="assets")

@app.get("/")
async def serve_spa():
    return FileResponse(os.path.join(static_client_dir, "index.html"))

@app.get("/{full_path:path}")
async def serve_spa_routes(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(os.path.join(static_client_dir, "index.html"))

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_model_change(self, user_nickname: str, action: str):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "model_changed",
                    "user": user_nickname,
                    "action": action
                })
            except WebSocketDisconnect:
                self.disconnect(connection)

    async def broadcast_user_event(self, user_nickname: str, event_type: str):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "user_event",
                    "user": user_nickname,
                    "event": event_type
                })
            except WebSocketDisconnect:
                self.disconnect(connection)

manager = ConnectionManager()

@api_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Initialize database operations
db_ops = DatabaseOperations(AsyncSessionLocal)

# In-memory user session storage
active_users: Dict[str, dict] = {}

class User(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)

class UserSession(BaseModel):
    session_id: str
    nickname: str
    locked_capabilities: List[int] = Field(default_factory=list)

class CapabilityMove(BaseModel):
    new_parent_id: Optional[int] = None
    new_order: int

class PromptUpdate(BaseModel):
    prompt: str
    capability_id: int
    prompt_type: str = Field(..., pattern="^(first-level|expansion)$")

class FormatRequest(BaseModel):
    format: str = Field(..., pattern="^(archimate|powerpoint|svg|markdown|word|html|mermaid|plantuml)$")

class ImportData(BaseModel):
    data: List[dict]

@api_app.get("/settings", response_model=SettingsModel)
async def get_settings():
    """Get current application settings."""
    settings = Settings()
    
    # Get available templates from templates directory
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    available_templates = [f for f in os.listdir(templates_dir) if f.endswith('.j2')]
    
    # Create template settings objects
    first_level_template = TemplateSettings(
        selected=settings.get("first_level_template"),
        available=available_templates
    )
    normal_template = TemplateSettings(
        selected=settings.get("normal_template"),
        available=available_templates
    )
    
    return SettingsModel(
        theme=settings.get("theme"),
        max_ai_capabilities=settings.get("max_ai_capabilities"),
        first_level_range=settings.get("first_level_range"),
        first_level_template=first_level_template,
        normal_template=normal_template,
        font_size=settings.get("font_size"),
        model=settings.get("model"),
        context_include_parents=settings.get("context_include_parents"),
        context_include_siblings=settings.get("context_include_siblings"),
        context_first_level=settings.get("context_first_level"),
        context_tree=settings.get("context_tree"),
        layout_algorithm=settings.get("layout_algorithm"),
        root_font_size=settings.get("root_font_size"),
        box_min_width=settings.get("box_min_width"),
        box_min_height=settings.get("box_min_height"),
        horizontal_gap=settings.get("horizontal_gap"),
        vertical_gap=settings.get("vertical_gap"),
        padding=settings.get("padding"),
        top_padding=settings.get("top_padding"),
        target_aspect_ratio=settings.get("target_aspect_ratio"),
        max_level=settings.get("max_level"),
        color_0=settings.get("color_0"),
        color_1=settings.get("color_1"),
        color_2=settings.get("color_2"),
        color_3=settings.get("color_3"),
        color_4=settings.get("color_4"),
        color_5=settings.get("color_5"),
        color_6=settings.get("color_6"),
        color_leaf=settings.get("color_leaf")
    )

@api_app.put("/settings", response_model=SettingsModel)
async def update_settings(settings_update: SettingsModel):
    """Update application settings."""
    settings = Settings()
    
    # Update each setting
    settings.set("theme", settings_update.theme)
    settings.set("max_ai_capabilities", settings_update.max_ai_capabilities)
    settings.set("first_level_range", settings_update.first_level_range)
    settings.set("first_level_template", 
                settings_update.first_level_template.selected 
                if isinstance(settings_update.first_level_template, TemplateSettings) 
                else settings_update.first_level_template)
    settings.set("normal_template", 
                settings_update.normal_template.selected 
                if isinstance(settings_update.normal_template, TemplateSettings) 
                else settings_update.normal_template)
    settings.set("font_size", settings_update.font_size)
    settings.set("model", settings_update.model)
    settings.set("context_include_parents", settings_update.context_include_parents)
    settings.set("context_include_siblings", settings_update.context_include_siblings)
    settings.set("context_first_level", settings_update.context_first_level)
    settings.set("context_tree", settings_update.context_tree)
    settings.set("layout_algorithm", settings_update.layout_algorithm)
    settings.set("root_font_size", settings_update.root_font_size)
    settings.set("box_min_width", settings_update.box_min_width)
    settings.set("box_min_height", settings_update.box_min_height)
    settings.set("horizontal_gap", settings_update.horizontal_gap)
    settings.set("vertical_gap", settings_update.vertical_gap)
    settings.set("padding", settings_update.padding)
    settings.set("top_padding", settings_update.top_padding)
    settings.set("target_aspect_ratio", settings_update.target_aspect_ratio)
    settings.set("max_level", settings_update.max_level)
    settings.set("color_0", settings_update.color_0)
    settings.set("color_1", settings_update.color_1)
    settings.set("color_2", settings_update.color_2)
    settings.set("color_3", settings_update.color_3)
    settings.set("color_4", settings_update.color_4)
    settings.set("color_5", settings_update.color_5)
    settings.set("color_6", settings_update.color_6)
    settings.set("color_leaf", settings_update.color_leaf)
    
    return settings_update

@api_app.post("/users", response_model=UserSession)
async def create_user_session(user: User):
    """Create a new user session."""
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "nickname": user.nickname,
        "locked_capabilities": []
    }
    active_users[session_id] = session
    # Broadcast user joined event
    await manager.broadcast_user_event(user.nickname, "joined")
    return UserSession(**session)

@api_app.get("/users", response_model=List[UserSession])
async def get_active_users():
    """Get all active users and their locked capabilities."""
    return [UserSession(**session) for session in active_users.values()]

@api_app.delete("/users/{session_id}")
async def remove_user_session(session_id: str):
    """Remove a user session."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    nickname = active_users[session_id]["nickname"]
    del active_users[session_id]
    # Broadcast user left event
    await manager.broadcast_user_event(nickname, "left")
    return {"message": "Session removed"}

@api_app.post("/capabilities/lock/{capability_id}")
async def lock_capability(capability_id: int, nickname: str, db: AsyncSession = Depends(get_db)):
    """Lock a capability for editing."""
    # Find user by nickname
    user_session = next((session for session in active_users.values() if session["nickname"] == nickname), None)
    if not user_session:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the capability to check its ancestors
    capability = await db_ops.get_capability(capability_id, db)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Check if any ancestor capabilities are locked
    current_parent_id = capability.parent_id
    while current_parent_id is not None:
        # Check if parent is locked by any user
        for user in active_users.values():
            if current_parent_id in user["locked_capabilities"]:
                # Parent is locked, silently ignore the lock request
                return {"message": "Capability is already locked by inheritance"}
        
        # Move up to next parent
        parent = await db_ops.get_capability(current_parent_id, db)
        if not parent:
            break
        current_parent_id = parent.parent_id
    
    # Check if capability itself is already locked
    for user in active_users.values():
        if capability_id in user["locked_capabilities"]:
            raise HTTPException(status_code=409, detail="Capability is already locked")
    
    # No ancestor locks found, proceed with locking
    user_session["locked_capabilities"].append(capability_id)
    return {"message": "Capability locked"}

@api_app.post("/capabilities/unlock/{capability_id}")
async def unlock_capability(capability_id: int, nickname: str):
    """Unlock a capability."""
    # Find user by nickname
    user_session = next((session for session in active_users.values() if session["nickname"] == nickname), None)
    if not user_session:
        raise HTTPException(status_code=404, detail="User not found")
    
    if capability_id in user_session["locked_capabilities"]:
        user_session["locked_capabilities"].remove(capability_id)
        return {"message": "Capability unlocked"}
    
    raise HTTPException(status_code=404, detail="Capability not locked by this user")

@api_app.post("/capabilities", response_model=dict)
async def create_capability(
    capability: CapabilityCreate,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Create a new capability."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await db_ops.create_capability(capability, db)
    # Notify all clients about model change
    await manager.broadcast_model_change(
        active_users[session_id]["nickname"],
        f"created capability '{result.name}'"
    )
    return {
        "id": result.id,
        "name": result.name,
        "description": result.description,
        "parent_id": result.parent_id
    }

@api_app.post("/capabilities/import")
async def import_capabilities(
    import_data: ImportData,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Import capabilities from JSON data."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        await db_ops.import_capabilities(import_data.data)
        # Notify all clients about model change
        await manager.broadcast_model_change(
            active_users[session_id]["nickname"],
            "imported capabilities"
        )
        return {"message": "Capabilities imported successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_app.get("/capabilities/export")
async def export_capabilities(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Export capabilities to JSON."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        data = await db_ops.export_capabilities()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_app.get("/capabilities/{capability_id}", response_model=dict)
async def get_capability(
    capability_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a capability by ID."""
    result = await db_ops.get_capability(capability_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    return {
        "id": result.id,
        "name": result.name,
        "description": result.description,
        "parent_id": result.parent_id
    }

@api_app.get("/capabilities/{capability_id}/context")
async def get_capability_context_endpoint(
    capability_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a capability's context rendered in template format for clipboard."""
    from bcm.utils import get_capability_context, jinja_env
    from bcm.settings import Settings

    # Get capability info
    capability = await db_ops.get_capability(capability_id, db)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get context
    context = await get_capability_context(db_ops, capability_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")

    # Get settings
    settings = Settings()

    # Determine if this is a first-level capability
    is_first_level = not capability.parent_id

    # Render appropriate template
    if is_first_level:
        template = jinja_env.get_template(settings.get("first_level_template"))
        rendered_context = template.render(
            organisation_name=capability.name,
            organisation_description=capability.description or f"An organization focused on {capability.name}",
            first_level=settings.get("first_level_range")
        )
    else:
        template = jinja_env.get_template(settings.get("normal_template"))
        rendered_context = template.render(
            capability_name=capability.name,
            context=context,
            max_capabilities=settings.get("max_ai_capabilities")
        )

    return {"rendered_context": rendered_context}

@api_app.put("/capabilities/{capability_id}", response_model=dict)
async def update_capability(
    capability_id: int,
    capability: CapabilityUpdate,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Update a capability."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is locked by another user
    current_user = active_users[session_id]
    for user in active_users.values():
        if capability_id in user["locked_capabilities"] and user["nickname"] != current_user["nickname"]:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    result = await db_ops.update_capability(capability_id, capability, db)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    # Notify all clients about model change
    await manager.broadcast_model_change(
        active_users[session_id]["nickname"],
        f"updated capability '{result.name}'"
    )
    return {
        "id": result.id,
        "name": result.name,
        "description": result.description,
        "parent_id": result.parent_id
    }

@api_app.delete("/capabilities/{capability_id}")
async def delete_capability(
    capability_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a capability."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is locked by another user
    current_user = active_users[session_id]
    for user in active_users.values():
        if capability_id in user["locked_capabilities"] and user["nickname"] != current_user["nickname"]:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    # Get capability name before deletion
    capability = await db_ops.get_capability(capability_id, db)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    result = await db_ops.delete_capability(capability_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    # Notify all clients about model change
    await manager.broadcast_model_change(
        active_users[session_id]["nickname"],
        f"deleted capability '{capability.name}'"
    )
    return {"message": "Capability deleted"}

@api_app.post("/capabilities/{capability_id}/move")
async def move_capability(
    capability_id: int,
    move: CapabilityMove,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Move a capability to a new parent and/or position."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is locked by another user
    current_user = active_users[session_id]
    for user in active_users.values():
        if capability_id in user["locked_capabilities"] and user["nickname"] != current_user["nickname"]:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    # Get capability name before move
    capability = await db_ops.get_capability(capability_id, db)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    result = await db_ops.update_capability_order(
        capability_id,
        move.new_parent_id,
        move.new_order
    )
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    # Notify all clients about model change
    await manager.broadcast_model_change(
        active_users[session_id]["nickname"],
        f"moved capability '{capability.name}'"
    )
    return {"message": "Capability moved successfully"}

@api_app.put("/capabilities/{capability_id}/description")
async def update_description(
    capability_id: int,
    description: str,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
  
    """Update a capability's description."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is locked by another user
    current_user = active_users[session_id]
    for user in active_users.values():
        if capability_id in user["locked_capabilities"] and user["nickname"] != current_user["nickname"]:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    result = await db_ops.save_description(capability_id, description)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    return {"message": "Description updated successfully"}

@api_app.put("/capabilities/{capability_id}/prompt")
async def update_prompt(
    capability_id: int,
    prompt_update: PromptUpdate,
    session_id: str
):
    """Update a capability's first-level or expansion prompt."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is locked by another user
    current_user = active_users[session_id]
    for user in active_users.values():
        if capability_id in user["locked_capabilities"] and user["nickname"] != current_user["nickname"]:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    # In a real implementation, this would update the prompt in a database
    # For now, we'll just return success
    return {"message": f"{prompt_update.prompt_type} prompt updated successfully"}

@api_app.get("/layout/{node_id}", response_model=LayoutModel)
async def get_layout(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get layouted model starting from the specified node ID."""
    # Get hierarchical data starting from node
    node_data = await db_ops.get_capability_with_children(node_id)
    if not node_data:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Convert to layout format using shared method
    settings = Settings()
    max_level = settings.get("max_level", 6)
    layout_model = LayoutModel.convert_to_layout_format(node_data, max_level)
    return process_layout(layout_model, settings)

@api_app.post("/format/{node_id}")
async def format_node(
    node_id: int,
    format_request: FormatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Format a node and its children in the specified format."""
    # Get hierarchical data starting from node
    node_data = await db_ops.get_capability_with_children(node_id)
    if not node_data:
        raise HTTPException(status_code=404, detail="Node not found")

    # Convert to layout format
    settings = Settings()
    max_level = settings.get("max_level", 6)
    layout_model = LayoutModel.convert_to_layout_format(node_data, max_level)

    return format_capability(node_id, format_request.format, layout_model, settings)

@api_app.get("/capabilities", response_model=List[dict])
async def get_capabilities(
    parent_id: Optional[int] = None,
    hierarchical: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Get capabilities, optionally filtered by parent_id.
    If hierarchical=True, returns full tree structure under the parent_id.
    If hierarchical=False, returns flat list of immediate children.
    """
    if hierarchical:
        if parent_id is None:
            # Get full hierarchy starting from root
            return await db_ops.get_all_capabilities()
        else:
            # Get hierarchy starting from specific parent
            result = await db_ops.get_capability_with_children(parent_id)
            return [result] if result else []
    else:
        # Original flat list behavior
        capabilities = await db_ops.get_capabilities(parent_id, db)
        return [
            {
                "id": cap.id,
                "name": cap.name,
                "description": cap.description,
                "parent_id": cap.parent_id,
                "order_position": cap.order_position
            }
            for cap in capabilities
        ]

if __name__ == "__main__":
    import uvicorn
    import sys

    # Default port
    port = 8080

    # Check for port argument
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)

    try:
        # Store the port in app state for lifespan to access
        app.state.port = port
        print(f"Starting server on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    except OSError as e:
        print(f"ERROR: Could not start server on port {port} - port is already in use.")
        print("Please ensure no other instance of the server is running and try again.")
        sys.exit(1)
