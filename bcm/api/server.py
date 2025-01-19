from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
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

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_model_change(self):
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "model_changed"})
            except WebSocketDisconnect:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

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

class CapabilityPaste(BaseModel):
    source_id: int
    target_id: Optional[int] = None
    position: Optional[int] = None

class PromptUpdate(BaseModel):
    prompt: str
    capability_id: int
    prompt_type: str = Field(..., pattern="^(first-level|expansion)$")

@app.post("/users", response_model=UserSession)
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

@app.get("/users", response_model=List[UserSession])
async def get_active_users():
    """Get all active users and their locked capabilities."""
    return [UserSession(**session) for session in active_users.values()]

@app.delete("/users/{session_id}")
async def remove_user_session(session_id: str):
    """Remove a user session."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    del active_users[session_id]
    return {"message": "Session removed"}

@app.post("/capabilities/lock/{capability_id}")
async def lock_capability(capability_id: int, session_id: str):
    """Lock a capability for editing."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is already locked
    for user in active_users.values():
        if capability_id in user["locked_capabilities"]:
            raise HTTPException(status_code=409, detail="Capability is already locked")
    
    active_users[session_id]["locked_capabilities"].append(capability_id)
    return {"message": "Capability locked"}

@app.post("/capabilities/unlock/{capability_id}")
async def unlock_capability(capability_id: int, session_id: str):
    """Unlock a capability."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if capability_id in active_users[session_id]["locked_capabilities"]:
        active_users[session_id]["locked_capabilities"].remove(capability_id)
        return {"message": "Capability unlocked"}
    
    raise HTTPException(status_code=404, detail="Capability not locked by this session")

@app.post("/capabilities", response_model=dict)
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
    await manager.broadcast_model_change()
    return {
        "id": result.id,
        "name": result.name,
        "description": result.description,
        "parent_id": result.parent_id
    }

@app.get("/capabilities/{capability_id}", response_model=dict)
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

@app.get("/capabilities/{capability_id}/context", response_model=dict)
async def get_capability_context(
    capability_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a capability's context (parent and children)."""
    result = await db_ops.get_capability_with_children(capability_id)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    return result

@app.put("/capabilities/{capability_id}", response_model=dict)
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
    for user_id, user in active_users.items():
        if capability_id in user["locked_capabilities"] and user_id != session_id:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    result = await db_ops.update_capability(capability_id, capability, db)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    # Notify all clients about model change
    await manager.broadcast_model_change()
    return {
        "id": result.id,
        "name": result.name,
        "description": result.description,
        "parent_id": result.parent_id
    }

@app.delete("/capabilities/{capability_id}")
async def delete_capability(
    capability_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a capability."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is locked by another user
    for user_id, user in active_users.items():
        if capability_id in user["locked_capabilities"] and user_id != session_id:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    result = await db_ops.delete_capability(capability_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    # Notify all clients about model change
    await manager.broadcast_model_change()
    return {"message": "Capability deleted"}

@app.post("/capabilities/{capability_id}/move")
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
    for user_id, user in active_users.items():
        if capability_id in user["locked_capabilities"] and user_id != session_id:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    result = await db_ops.update_capability_order(
        capability_id,
        move.new_parent_id,
        move.new_order
    )
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    # Notify all clients about model change
    await manager.broadcast_model_change()
    return {"message": "Capability moved successfully"}

@app.post("/capabilities/paste")
async def paste_capability(
    paste: CapabilityPaste,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Paste a capability and its children to a new location."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get source capability with children
    source = await db_ops.get_capability_with_children(paste.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source capability not found")
    
    # Create new capability at target location
    new_cap = CapabilityCreate(
        name=source["name"],
        description=source["description"],
        parent_id=paste.target_id
    )
    result = await db_ops.create_capability(new_cap, db)
    
    # Recursively create children
    async def paste_children(children: List[dict], parent_id: int):
        for child in children:
            new_child = CapabilityCreate(
                name=child["name"],
                description=child["description"],
                parent_id=parent_id
            )
            child_result = await db_ops.create_capability(new_child, db)
            if child["children"]:
                await paste_children(child["children"], child_result.id)
    
    if source["children"]:
        await paste_children(source["children"], result.id)
    
    # Notify all clients about model change
    await manager.broadcast_model_change()
    return {"message": "Capability pasted successfully", "new_id": result.id}

@app.put("/capabilities/{capability_id}/description")
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
    for user_id, user in active_users.items():
        if capability_id in user["locked_capabilities"] and user_id != session_id:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    result = await db_ops.save_description(capability_id, description)
    if not result:
        raise HTTPException(status_code=404, detail="Capability not found")
    return {"message": "Description updated successfully"}

@app.put("/capabilities/{capability_id}/prompt")
async def update_prompt(
    capability_id: int,
    prompt_update: PromptUpdate,
    session_id: str
):
    """Update a capability's first-level or expansion prompt."""
    if session_id not in active_users:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if capability is locked by another user
    for user_id, user in active_users.items():
        if capability_id in user["locked_capabilities"] and user_id != session_id:
            raise HTTPException(status_code=409, detail="Capability is locked by another user")
    
    # In a real implementation, this would update the prompt in a database
    # For now, we'll just return success
    return {"message": f"{prompt_update.prompt_type} prompt updated successfully"}

@app.get("/capabilities", response_model=List[dict])
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
        uvicorn.run(app, host="127.0.0.1", port=8080)
    except OSError as e:
        print("ERROR: Could not start server on port 8080 - port is already in use.")
        print("Please ensure no other instance of the server is running and try again.")
        import sys
        sys.exit(1)
