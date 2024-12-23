from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .models import CapabilityDB, CapabilityCreate, CapabilityUpdate

class DatabaseOperations:
    def __init__(self, session: Session):
        self.session = session

    def create_capability(self, capability: CapabilityCreate) -> CapabilityDB:
        """Create a new capability."""
        # Get max order for the parent
        stmt = select(func.max(CapabilityDB.order)).where(
            CapabilityDB.parent_id == capability.parent_id
        )
        max_order = self.session.execute(stmt).scalar() or -1
        
        # Create new capability with next order
        db_capability = CapabilityDB(
            name=capability.name,
            description=capability.description,
            parent_id=capability.parent_id,
            order=max_order + 1
        )
        self.session.add(db_capability)
        self.session.commit()
        self.session.refresh(db_capability)
        return db_capability

    def get_capability(self, capability_id: int) -> Optional[CapabilityDB]:
        """Get a capability by ID."""
        return self.session.get(CapabilityDB, capability_id)

    def get_capabilities(self, parent_id: Optional[int] = None) -> List[CapabilityDB]:
        """Get all capabilities, optionally filtered by parent_id."""
        query = (
            select(CapabilityDB)
            .where(CapabilityDB.parent_id == parent_id)
            .order_by(CapabilityDB.order)
            .distinct()
        )
        return list(self.session.execute(query).scalars())

    def update_capability(self, capability_id: int, capability: CapabilityUpdate) -> Optional[CapabilityDB]:
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
        db_capability = self.get_capability(capability_id)
        if not db_capability:
            return False

        # Recursively delete children
        for child in db_capability.children:
            self.delete_capability(child.id)

        self.session.delete(db_capability)
        self.session.commit()
        return True

    def update_capability_order(self, capability_id: int, new_parent_id: Optional[int], new_order: int) -> Optional[CapabilityDB]:
        """Update a capability's parent and order."""
        db_capability = self.get_capability(capability_id)
        if not db_capability:
            return None

        # Update order of other capabilities
        if db_capability.parent_id == new_parent_id:
            # Same parent, just reorder
            if new_order > db_capability.order:
                stmt = (
                    select(CapabilityDB)
                    .where(
                        CapabilityDB.parent_id == new_parent_id,
                        CapabilityDB.order <= new_order,
                        CapabilityDB.order > db_capability.order,
                        CapabilityDB.id != capability_id
                    )
                )
                capabilities = self.session.execute(stmt).scalars().all()
                for cap in capabilities:
                    cap.order -= 1
            else:
                stmt = (
                    select(CapabilityDB)
                    .where(
                        CapabilityDB.parent_id == new_parent_id,
                        CapabilityDB.order >= new_order,
                        CapabilityDB.order < db_capability.order,
                        CapabilityDB.id != capability_id
                    )
                )
                capabilities = self.session.execute(stmt).scalars().all()
                for cap in capabilities:
                    cap.order += 1
        else:
            # Moving to new parent
            # Decrease order of capabilities in old parent
            # Decrease order of capabilities in old parent
            stmt = (
                select(CapabilityDB)
                .where(
                    CapabilityDB.parent_id == db_capability.parent_id,
                    CapabilityDB.order > db_capability.order
                )
            )
            capabilities = self.session.execute(stmt).scalars().all()
            for cap in capabilities:
                cap.order -= 1

            # Increase order of capabilities in new parent
            stmt = (
                select(CapabilityDB)
                .where(
                    CapabilityDB.parent_id == new_parent_id,
                    CapabilityDB.order >= new_order
                )
            )
            capabilities = self.session.execute(stmt).scalars().all()
            for cap in capabilities:
                cap.order += 1

        db_capability.parent_id = new_parent_id
        db_capability.order = new_order
        self.session.commit()
        self.session.refresh(db_capability)
        return db_capability
