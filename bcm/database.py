from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, or_
from .models import Capability, CapabilityCreate, CapabilityUpdate  # Changed from CapabilityDB
from uuid import uuid4

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

    def get_capability_by_name(self, name: str) -> Optional[Capability]:
        """Get a capability by name (case insensitive)."""
        stmt = select(Capability).where(func.lower(Capability.name) == func.lower(name)).limit(1)
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
            raise e

    def get_all_capabilities(self) -> List[dict]:
        """Get all capabilities in a hierarchical structure."""
        def build_hierarchy(parent_id: Optional[int] = None) -> List[dict]:
            capabilities = self.get_capabilities(parent_id)
            result = []
            for cap in capabilities:
                cap_dict = {
                    "id": cap.id,
                    "name": cap.name,
                    "description": cap.description,
                    "order_position": cap.order_position,
                    "children": build_hierarchy(cap.id)
                }
                result.append(cap_dict)
            return result
        
        return build_hierarchy()

    def get_capability_with_children(self, capability_id: int) -> Optional[dict]:
        """Get a capability and its children in a hierarchical structure."""
        def build_hierarchy(parent_id: int) -> List[dict]:
            capabilities = self.get_capabilities(parent_id)
            result = []
            for cap in capabilities:
                cap_dict = {
                    "id": cap.id,
                    "name": cap.name,
                    "description": cap.description,
                    "order_position": cap.order_position,
                    "children": build_hierarchy(cap.id)
                }
                result.append(cap_dict)
            return result

        # Get the starting capability
        capability = self.get_capability(capability_id)
        if not capability:
            return None

        # Return the capability with its children
        return {
            "id": capability.id,
            "name": capability.name,
            "description": capability.description,
            "order_position": capability.order_position,
            "children": build_hierarchy(capability.id)
        }

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
            self.session.execute(text("PRAGMA foreign_keys = ON"))
            self.session.commit()
            
            capability = self.get_capability(capability_id)
            
            if not capability:
                return False
                
            self.session.delete(capability)
            self.session.commit()
            return True

        except Exception as e:
            print(f"Error in delete_capability: {str(e)}")
            self.session.rollback()
            raise

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

    def export_capabilities(self) -> List[dict]:
        """Export all capabilities in the external format."""
        # Get all capabilities without hierarchy
        stmt = select(Capability).order_by(Capability.order_position)
        capabilities = self.session.execute(stmt).scalars().all()
        export_data = []
        
        # First create mapping of DB IDs to new UUIDs
        id_mapping = {cap.id: str(uuid4()) for cap in capabilities}
        
        # Then create export data with correct parent references
        for cap in capabilities:
            export_data.append({
                "id": id_mapping[cap.id],  # Use mapped UUID
                "name": cap.name,
                "capability": 0,
                "description": cap.description or "",
                "parent": id_mapping.get(cap.parent_id) if cap.parent_id else None  # Map parent ID to UUID
            })
            
        return export_data

    def search_capabilities(self, query: str) -> List[Capability]:
        """Search capabilities by name or description."""
        search_term = f"%{query}%"
        stmt = select(Capability).where(
            or_(
                Capability.name.ilike(search_term),
                Capability.description.ilike(search_term)
            )
        )
        return self.session.execute(stmt).scalars().all()

    def clear_all_capabilities(self) -> None:
        """Clear all capabilities from the database."""
        try:
            self.session.query(Capability).delete()
            self.session.commit()
        except Exception as e:
            print(f"Error clearing capabilities: {e}")
            self.session.rollback()
            raise

    def import_capabilities(self, data: List[dict]) -> None:
        """Import capabilities from external format."""
        if not data:
            print("No data received for import")
            return
        
        try:
            # Start transaction
            self.session.begin()
            
            # Clear existing capabilities
            self.clear_all_capabilities()
            
            # Create mapping of external IDs to new database IDs
            id_mapping = {}
            
            # First pass: Create all capabilities without parents
            for item in data:
                try:
                    cap = CapabilityCreate(
                        name=item["name"],
                        description=item.get("description", ""),
                        parent_id=None
                    )
                    db_capability = self.create_capability(cap)
                    id_mapping[item["id"]] = db_capability.id
                except Exception:
                    raise
            
            # Second pass: Update parent relationships
            for item in data:
                try:
                    if item.get("parent"):
                        capability_id = id_mapping.get(item["id"])
                        parent_id = id_mapping.get(item["parent"])
                        
                        if capability_id and parent_id:
                            capability = self.get_capability(capability_id)
                            if capability:
                                capability.parent_id = parent_id
                except Exception as e:
                    print(f"Error updating parent for {item.get('name')}: {e}")
                    raise
            
            # Commit all changes
            self.session.commit()
            
        except Exception as e:
            print(f"Error during import: {str(e)}")
            self.session.rollback()
            raise

    def get_markdown_hierarchy(self) -> str:
        """Generate a markdown representation of the capability hierarchy."""
        def build_hierarchy(parent_id: Optional[int] = None, level: int = 0) -> str:
            capabilities = self.get_capabilities(parent_id)
            result = []
            for cap in capabilities:
                indent = "  " * level
                result.append(f"{indent}- {cap.name}")
                result.append(build_hierarchy(cap.id, level + 1))
            return "\n".join(result)
        
        return build_hierarchy()
