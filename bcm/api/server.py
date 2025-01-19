from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Set
from bcm.models import (
    CapabilityCreate,
    CapabilityUpdate,
    get_db,
    AsyncSessionLocal,
)
from bcm.database import DatabaseOperations
import uuid

# Initialize FastAPI app
app = FastAPI(title="Business Capability Model API")
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
    del active_users[session_id]
    return {"message": "Session removed"}

@api_app.post("/capabilities/lock/{capability_id}")
async def lock_capability(capability_id: int, nickname: str):
    """Lock a capability for editing."""
    # Find user by nickname
    user_session = next((session for session in active_users.values() if session["nickname"] == nickname), None)
    if not user_session:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if capability is already locked
    for user in active_users.values():
        if capability_id in user["locked_capabilities"]:
            raise HTTPException(status_code=409, detail="Capability is already locked")
    
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
    try:
        print("Starting server on port 8080")
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except OSError as e:
        print("ERROR: Could not start server on port 8080 - port is already in use.")
        print("Please ensure no other instance of the server is running and try again.")
        import sys
        sys.exit(1)
