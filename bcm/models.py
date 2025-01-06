import os
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, RootModel
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, text, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    """SQLAlchemy model for audit logging."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    operation = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, MOVE
    capability_id = Column(
        Integer, nullable=True
    )  # Can be null for imports/clear operations
    capability_name = Column(String(255), nullable=True)
    old_values = Column(Text, nullable=True)  # JSON string of old values
    new_values = Column(Text, nullable=True)  # JSON string of new values
    timestamp = Column(DateTime, default=datetime.utcnow)


class Capability(Base):
    """SQLAlchemy model for capabilities in the database."""

    __tablename__ = "capabilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(
        Integer, ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=True
    )
    order_position = Column(
        Integer, default=0
    )  # Changed from 'order' which is a reserved word
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

    # Add indexes
    __table_args__ = (
        Index("ix_capabilities_name", "name"),
        Index("ix_capabilities_description", "description"),
        Index("ix_capabilities_parent_id", "parent_id"),
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
    id: int
    name: str
    description: Optional[str] = None
    children: Optional[List["LayoutModel"]] = None
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
    description: str = Field(
        description="Clear description of the sub-capability's purpose and scope"
    )


class CapabilityExpansion(BaseModel):
    subcapabilities: List[SubCapability] = Field(
        description="List of sub-capabilities that would logically extend the given capability"
    )


class FirstLevelCapability(BaseModel):
    name: str = Field(description="Name of the first-level capability")
    description: str = Field(
        description="Description of the first-level capability's purpose and scope"
    )


class FirstLevelCapabilities(BaseModel):
    capabilities: List[FirstLevelCapability] = Field(
        description="List of first-level capabilities for the organization"
    )


# Database setup
def get_db_path():
    """Get absolute path to database file."""
    user_dir = os.path.expanduser("~")
    app_dir = os.path.join(user_dir, ".pybcm")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "bcm.db")


DATABASE_URL = f"sqlite+aiosqlite:///{get_db_path()}"


def create_engine_instance():
    return create_async_engine(
        DATABASE_URL,
        echo=False,
    )


engine = create_engine_instance()
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Initialize the database by creating all tables."""
    db_path = get_db_path()

    # Only create tables if database doesn't exist
    if not os.path.exists(db_path):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Enable foreign keys for new database
        async with AsyncSessionLocal() as session:
            await session.execute(text("PRAGMA foreign_keys = ON"))
            await session.commit()


async def get_db():
    """Get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
