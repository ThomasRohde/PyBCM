import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, RootModel
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import sqlite3

Base = declarative_base()

class Capability(Base):
    """SQLAlchemy model for capabilities in the database."""
    __tablename__ = "capabilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=True)
    order_position = Column(Integer, default=0)  # Changed from 'order' which is a reserved word
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship(
        "Capability",
        remote_side=[id],
        back_populates="children",
    )
    children = relationship(
        "Capability",
        back_populates="parent",
        cascade="all, delete",  # Changed from "all, delete-orphan"
        passive_deletes=True,
    )

class CapabilityCreate(BaseModel):
    """Pydantic model for creating a new capability."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CapabilityUpdate(BaseModel):
    """Pydantic model for updating an existing capability."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CapabilityExport(BaseModel):
    id: str  # UUID string
    name: str
    capability: int = 0
    description: str = ""
    parent: Optional[str] = None  # Can be string ID or null

# Use RootModel instead of __root__
CapabilityExportList = RootModel[List[CapabilityExport]]

class LayoutModel(BaseModel):
    """Pydantic model for representing the hierarchical layout of capabilities."""
    name: str
    description: Optional[str] = None
    children: Optional[List['LayoutModel']] = None
    # Geometry attributes
    x: float = 0
    y: float = 0
    width: float = 120  # Default to BOX_MIN_WIDTH from template
    height: float = 60  # Default to BOX_MIN_HEIGHT from template

    class Config:
        from_attributes = True

# Required for self-referential Pydantic models
LayoutModel.model_rebuild()

class SubCapability(BaseModel):
    name: str = Field(description="Name of the sub-capability")
    description: str = Field(description="Clear description of the sub-capability's purpose and scope")

class CapabilityExpansion(BaseModel):
    subcapabilities: List[SubCapability] = Field(
        description="List of sub-capabilities that would logically extend the given capability"
    )

class FirstLevelCapability(BaseModel):
    name: str = Field(description="Name of the first-level capability")
    description: str = Field(description="Description of the first-level capability's purpose and scope")

class FirstLevelCapabilities(BaseModel):
    capabilities: List[FirstLevelCapability] = Field(
        description="List of first-level capabilities for the organization"
    )

def capability_to_layout(capability: Capability, settings=None, current_level: int = 0) -> LayoutModel:
    """
    Convert a Capability model instance to a LayoutModel instance.
    Respects max_level setting to limit visualization depth.
    """
    # Get max_level from settings, default to 6 if settings not provided
    max_level = settings.get("max_level", 6) if settings else 6
    
    # Create children only if we haven't reached max_level
    children = None
    if capability.children and current_level < max_level:
        children = [capability_to_layout(child, settings, current_level + 1) 
                   for child in capability.children]
    
    return LayoutModel(
        name=capability.name,
        description=capability.description,
        children=children
    )

# Database setup
def get_db_path():
    """Get absolute path to database file."""
    base_dir = Path(__file__).resolve().parent.parent
    return os.path.join(base_dir, "bcm.db")

DATABASE_URL = f"sqlite:///{get_db_path()}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    # Enable SQLite foreign key support
    creator=lambda: sqlite3.connect(get_db_path(), detect_types=sqlite3.PARSE_DECLTYPES)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize the database by creating all tables."""
    db_path = get_db_path()
    
    # Only create tables if database doesn't exist
    if not os.path.exists(db_path):
        Base.metadata.create_all(bind=engine)
        
        # Enable foreign keys for new database
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
