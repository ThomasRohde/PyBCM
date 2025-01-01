from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, or_
from sqlalchemy.orm import selectinload
from .models import Capability, CapabilityCreate, CapabilityUpdate  # Changed from CapabilityDB
from uuid import uuid4

class DatabaseOperations:
    def __init__(self, session_factory):
        """Initialize with session factory instead of session."""
        self.session_factory = session_factory

    async def _get_session(self):
        """Get a fresh session for operations."""
        return self.session_factory()

    async def create_capability(self, capability: CapabilityCreate) -> Capability:
        """Create a new capability."""
        async with await self._get_session() as session:
            # Get max order for the parent
            result = await session.execute(
                select(func.max(Capability.order_position))
                .where(Capability.parent_id == capability.parent_id)
            )
            max_order = result.scalar() or -1
            
            # Create new capability with next order
            db_capability = Capability(
                name=capability.name,
                description=capability.description,
                parent_id=capability.parent_id,
                order_position=max_order + 1
            )
            session.add(db_capability)
            await session.commit()
            await session.refresh(db_capability)
            return db_capability

    async def get_capability(self, capability_id: int) -> Optional[Capability]:
        """Get a capability by ID."""
        async with await self._get_session() as session:
            stmt = select(Capability).where(Capability.id == capability_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_capability_by_name(self, name: str) -> Optional[Capability]:
        """Get a capability by name (case insensitive)."""
        async with await self._get_session() as session:
            stmt = select(Capability).where(func.lower(Capability.name) == func.lower(name)).limit(1)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_capabilities(self, parent_id: Optional[int] = None) -> List[Capability]:
        """Get all capabilities, optionally filtered by parent_id."""
        async with await self._get_session() as session:
            try:
                stmt = select(Capability).where(
                    Capability.parent_id == parent_id
                ).order_by(Capability.order_position)
                result = await session.execute(stmt)
                return result.scalars().all()
            except Exception as e:
                raise e

    async def get_all_capabilities(self) -> List[dict]:
        """Get all capabilities in a hierarchical structure."""
        async def build_hierarchy(parent_id: Optional[int] = None) -> List[dict]:
            capabilities = await self.get_capabilities(parent_id)
            result = []
            for cap in capabilities:
                cap_dict = {
                    "id": cap.id,
                    "name": cap.name,
                    "description": cap.description,
                    "order_position": cap.order_position,
                    "children": await build_hierarchy(cap.id)
                }
                result.append(cap_dict)
            return result
        
        return await build_hierarchy()

    async def get_capability_with_children(self, capability_id: int) -> Optional[dict]:
        """Get a capability and its children in a hierarchical structure."""
        async def build_hierarchy(parent_id: int) -> List[dict]:
            capabilities = await self.get_capabilities(parent_id)
            result = []
            for cap in capabilities:
                cap_dict = {
                    "id": cap.id,
                    "name": cap.name,
                    "description": cap.description,
                    "order_position": cap.order_position,
                    "children": await build_hierarchy(cap.id)
                }
                result.append(cap_dict)
            return result

        capability = await self.get_capability(capability_id)
        if not capability:
            return None

        return {
            "id": capability.id,
            "name": capability.name,
            "description": capability.description,
            "order_position": capability.order_position,
            "children": await build_hierarchy(capability.id)
        }

    async def update_capability(self, capability_id: int, capability: CapabilityUpdate) -> Optional[Capability]:
        """Update a capability."""
        async with await self._get_session() as session:
            db_capability = await self.get_capability(capability_id)
            if not db_capability:
                return None

            update_data = capability.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_capability, key, value)

            await session.commit()
            await session.refresh(db_capability)
            return db_capability

    async def delete_capability(self, capability_id: int) -> bool:
        """Delete a capability and its children."""
        async with await self._get_session() as session:
            try:
                await session.execute(text("PRAGMA foreign_keys = ON"))
                await session.commit()
                
                capability = await self.get_capability(capability_id)
                if not capability:
                    return False
                    
                await session.delete(capability)
                await session.commit()
                return True
            except Exception as e:
                print(f"Error in delete_capability: {str(e)}")
                await session.rollback()
                raise

    async def update_capability_order(self, capability_id: int, new_parent_id: Optional[int], new_order: int) -> Optional[Capability]:
        """Update a capability's parent and order."""
        async with await self._get_session() as session:
            try:
                # Get capability
                stmt = select(Capability).where(Capability.id == capability_id)
                result = await session.execute(stmt)
                db_capability = result.scalar_one_or_none()
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
                        result = await session.execute(stmt)
                        capabilities = result.scalars().all()
                        for cap in capabilities:
                            cap.order_position -= 1
                    else:
                        stmt = select(Capability).where(
                            Capability.parent_id == new_parent_id,
                            Capability.order_position >= new_order,
                            Capability.order_position < db_capability.order_position,
                            Capability.id != capability_id
                        )
                        result = await session.execute(stmt)
                        capabilities = result.scalars().all()
                        for cap in capabilities:
                            cap.order_position += 1
                else:
                    # Moving to new parent
                    # Decrease order of capabilities in old parent
                    stmt = select(Capability).where(
                        Capability.parent_id == db_capability.parent_id,
                        Capability.order_position > db_capability.order_position
                    )
                    result = await session.execute(stmt)
                    capabilities = result.scalars().all()
                    for cap in capabilities:
                        cap.order_position -= 1

                    # Increase order of capabilities in new parent
                    stmt = select(Capability).where(
                        Capability.parent_id == new_parent_id,
                        Capability.order_position >= new_order
                    )
                    result = await session.execute(stmt)
                    capabilities = result.scalars().all()
                    for cap in capabilities:
                        cap.order_position += 1

                db_capability.parent_id = new_parent_id
                db_capability.order_position = new_order
                await session.commit()
                return db_capability
            except Exception as e:
                await session.rollback()
                raise e

    async def export_capabilities(self) -> List[dict]:
        """Export all capabilities in the external format."""
        async with await self._get_session() as session:
            # Get all capabilities without hierarchy
            stmt = select(Capability).order_by(Capability.order_position)
            result = await session.execute(stmt)
            capabilities = result.scalars().all()
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

    async def search_capabilities(self, query: str) -> List[Capability]:
        """Search capabilities by name or description."""
        async with await self._get_session() as session:
            search_term = f"%{query}%"
            stmt = select(Capability).where(
                or_(
                    Capability.name.ilike(search_term),
                    Capability.description.ilike(search_term)
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def clear_all_capabilities(self) -> None:
        """Clear all capabilities from the database."""
        async with await self._get_session() as session:
            try:
                await session.execute(text("DELETE FROM capabilities"))
                await session.commit()
            except Exception as e:
                print(f"Error clearing capabilities: {e}")
                await session.rollback()
                raise

    async def import_capabilities(self, data: List[dict]) -> None:
        """Import capabilities from external format."""
        if not data:
            print("No data received for import")
            return
        
        async with await self._get_session() as session:
            try:
                # Clear existing capabilities first
                await self.clear_all_capabilities()
                
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
                        db_capability = await self.create_capability(cap)
                        id_mapping[item["id"]] = db_capability.id
                    except Exception as e:
                        print(f"Error creating capability {item.get('name')}: {e}")
                        raise
                
                # Second pass: Update parent relationships
                for item in data:
                    try:
                        if item.get("parent"):
                            capability_id = id_mapping.get(item["id"])
                            parent_id = id_mapping.get(item["parent"])
                            
                            if capability_id and parent_id:
                                # Get capability and update its parent
                                stmt = select(Capability).where(Capability.id == capability_id)
                                result = await session.execute(stmt)
                                capability = result.scalar_one_or_none()
                                
                                if capability:
                                    capability.parent_id = parent_id
                                    session.add(capability)
                    except Exception as e:
                        print(f"Error updating parent for {item.get('name')}: {e}")
                        raise
                
                # Commit all parent relationship updates
                await session.commit()
                    
            except Exception as e:
                print(f"Error during import: {str(e)}")
                await session.rollback()
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
