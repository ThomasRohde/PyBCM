from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, create_engine, text
from sqlalchemy.orm import declarative_base, relationship, Session

Base = declarative_base()

class CapabilityDB(Base):
    """SQLAlchemy model for capabilities in the database."""
    __tablename__ = "capabilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("capabilities.id"), nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("CapabilityDB", remote_side=[id], back_populates="children")
    children = relationship("CapabilityDB", back_populates="parent")

class CapabilityCreate(BaseModel):
    """Pydantic model for creating a new capability."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    order: Optional[int] = None

class CapabilityUpdate(BaseModel):
    """Pydantic model for updating an existing capability."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    order: Optional[int] = None

class Capability(BaseModel):
    """Pydantic model for capability responses."""
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Database setup
DATABASE_URL = "sqlite:///bcm.db"
engine = create_engine(DATABASE_URL)

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
    
    # Reset SQLite sequence if it exists
    with Session(engine) as session:
        try:
            session.execute(text("DELETE FROM sqlite_sequence WHERE name='capabilities'"))
            session.commit()
        except:
            # sqlite_sequence table doesn't exist yet, which is fine
            pass

def get_db():
    """Get a database session."""
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
