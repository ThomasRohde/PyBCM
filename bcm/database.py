from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .models import Capability, CapabilityCreate, CapabilityUpdate  # Changed from CapabilityDB

class DatabaseOperations:
    def __init__(self, session: Session):
        self.session = session

    def create_capability(self, capability: CapabilityCreate) -> Capability:
        """Create a new capability."""
        # Get max order for the parent
        stmt = select(func.max(Capability.order_position)).where(
            Capability.parent_id == capability.parent_id
        )
        max_order = self.session.execute(stmt).scalar() or -1
        
        # Create new capability with next order
        db_capability = Capability(
            name=capability.name,
            description=capability.description,
            parent_id=capability.parent_id,
            order_position=max_order + 1
        )
        self.session.add(db_capability)
        self.session.commit()
        self.session.refresh(db_capability)
        return db_capability

    def get_capability(self, capability_id: int) -> Optional[Capability]:
        """Get a capability by ID."""
        stmt = select(Capability).where(Capability.id == capability_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_capabilities(self, parent_id: Optional[int] = None) -> List[Capability]:
        """Get all capabilities, optionally filtered by parent_id."""
        try:
            query = self.session.query(Capability).filter(
                Capability.parent_id == parent_id
            ).order_by(Capability.order_position)
            return query.all()
        except Exception as e:
            print(f"Error in get_capabilities: {e}")
            return []

    def update_capability(self, capability_id: int, capability: CapabilityUpdate) -> Optional[Capability]:
        """Update a capability."""
        db_capability = self.get_capability(capability_id)
        if not db_capability:
            return None

        update_data = capability.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_capability, key, value)

        self.session.commit()
        self.session.refresh(db_capability)
        return db_capability

    def delete_capability(self, capability_id: int) -> bool:
        """Delete a capability and its children."""
        try:
            # Enable foreign key support for this session
            self.session.execute(text("PRAGMA foreign_keys = ON"))
            
            # Get the capability
            capability = self.session.get(Capability, capability_id)
            if not capability:
                print(f"No capability found with ID {capability_id}")
                return False

            print(f"Deleting capability {capability_id} with name: {capability.name}")
            
            # The cascade should handle children automatically
            self.session.delete(capability)
            self.session.commit()
            print(f"Successfully deleted capability {capability_id}")
            return True

        except Exception as e:
            print(f"Error in delete_capability: {str(e)}")
            self.session.rollback()
            return False

    def update_capability_order(self, capability_id: int, new_parent_id: Optional[int], new_order: int) -> Optional[Capability]:
        """Update a capability's parent and order."""
        db_capability = self.get_capability(capability_id)
        if not db_capability:
            return None

        # Update order of other capabilities
        if db_capability.parent_id == new_parent_id:
            if new_order > db_capability.order_position:
                stmt = select(Capability).where(
                    Capability.parent_id == new_parent_id,
                    Capability.order_position <= new_order,
                    Capability.order_position > db_capability.order_position,
                    Capability.id != capability_id
                )
                capabilities = self.session.execute(stmt).scalars().all()
                for cap in capabilities:
                    cap.order_position -= 1
            else:
                stmt = select(Capability).where(
                    Capability.parent_id == new_parent_id,
                    Capability.order_position >= new_order,
                    Capability.order_position < db_capability.order_position,
                    Capability.id != capability_id
                )
                capabilities = self.session.execute(stmt).scalars().all()
                for cap in capabilities:
                    cap.order_position += 1
        else:
            # Moving to new parent
            # Decrease order of capabilities in old parent
            stmt = select(Capability).where(
                Capability.parent_id == db_capability.parent_id,
                Capability.order_position > db_capability.order_position
            )
            capabilities = self.session.execute(stmt).scalars().all()
            for cap in capabilities:
                cap.order_position -= 1

            # Increase order of capabilities in new parent
            stmt = select(Capability).where(
                Capability.parent_id == new_parent_id,
                Capability.order_position >= new_order
            )
            capabilities = self.session.execute(stmt).scalars().all()
            for cap in capabilities:
                cap.order_position += 1

        db_capability.parent_id = new_parent_id
        db_capability.order_position = new_order
        self.session.commit()
        self.session.refresh(db_capability)
        return db_capability
