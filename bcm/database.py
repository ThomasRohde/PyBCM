from typing import List, Optional
import json
from datetime import datetime
from sqlalchemy import select, func, text, or_
from bcm.models import (
    Capability,
    CapabilityCreate,
    CapabilityUpdate,
    AuditLog,
)  # Changed from CapabilityDB
from uuid import uuid4


class DatabaseOperations:
    def __init__(self, session_factory):
        """Initialize with session factory instead of session."""
        self.session_factory = session_factory

    async def log_audit(
        self,
        session,
        operation: str,
        capability_id: Optional[int] = None,
        capability_name: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ):
        """Add an audit log entry."""
        audit = AuditLog(
            operation=operation,
            capability_id=capability_id,
            capability_name=capability_name,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
        )
        session.add(audit)

    async def _get_session(self):
        """Get a fresh session for operations."""
        return self.session_factory()

    async def create_capability(
        self, capability: CapabilityCreate, session=None
    ) -> Capability:
        """Create a new capability."""
        if session is None:
            async with await self._get_session() as session:
                return await self._create_capability_impl(capability, session)
        else:
            return await self._create_capability_impl(capability, session)

    async def _create_capability_impl(
        self, capability: CapabilityCreate, session
    ) -> Capability:
        # Get max order for the parent
        result = await session.execute(
            select(func.max(Capability.order_position)).where(
                Capability.parent_id == capability.parent_id
            )
        )
        max_order = result.scalar() or -1

        # Create new capability with next order
        db_capability = Capability(
            name=capability.name,
            description=capability.description,
            parent_id=capability.parent_id,
            order_position=max_order + 1,
        )
        session.add(db_capability)

        # Add audit log
        await self.log_audit(
            session,
            "CREATE",
            capability_name=capability.name,
            new_values={
                "name": capability.name,
                "description": capability.description,
                "parent_id": capability.parent_id,
                "order_position": max_order + 1,
            },
        )

        await session.commit()
        await session.refresh(db_capability)

        # Update audit log with actual ID
        await self.log_audit(
            session,
            "ID_ASSIGN",
            capability_id=db_capability.id,
            capability_name=capability.name,
            new_values={"id": db_capability.id},
        )
        await session.commit()

        return db_capability

    async def get_capability(
        self, capability_id: int, session=None
    ) -> Optional[Capability]:
        """Get a capability by ID."""
        if session is None:
            async with await self._get_session() as session:
                return await self._get_capability_impl(capability_id, session)
        else:
            return await self._get_capability_impl(capability_id, session)

    async def _get_capability_impl(
        self, capability_id: int, session
    ) -> Optional[Capability]:
        stmt = select(Capability).where(Capability.id == capability_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_capability_by_name(self, name: str) -> Optional[Capability]:
        """Get a capability by name (case insensitive)."""
        async with await self._get_session() as session:
            stmt = (
                select(Capability)
                .where(func.lower(Capability.name) == func.lower(name))
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_capabilities(
        self, parent_id: Optional[int] = None, session=None
    ) -> List[Capability]:
        """Get all capabilities, optionally filtered by parent_id."""
        if session is None:
            async with await self._get_session() as session:
                return await self._get_capabilities_impl(parent_id, session)
        else:
            return await self._get_capabilities_impl(parent_id, session)

    async def _get_capabilities_impl(
        self, parent_id: Optional[int], session
    ) -> List[Capability]:
        try:
            stmt = (
                select(Capability)
                .where(Capability.parent_id == parent_id)
                .order_by(Capability.order_position)
            )
            result = await session.execute(stmt)
            capabilities = result.scalars().all()
            return list(capabilities) if capabilities else []
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
                    "parent_id": cap.parent_id,
                    "order_position": cap.order_position,
                    "children": await build_hierarchy(cap.id),
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
                    "parent_id": cap.parent_id,
                    "order_position": cap.order_position,
                    "children": await build_hierarchy(cap.id),
                }
                result.append(cap_dict)
            return result

        async with await self._get_session() as session:
            stmt = select(Capability).where(Capability.id == capability_id)
            result = await session.execute(stmt)
            capability = result.scalar_one_or_none()
            if not capability:
                return None

            return {
                "id": capability.id,
                "name": capability.name,
                "description": capability.description,
                "parent_id": capability.parent_id,
                "order_position": capability.order_position,
                "children": await build_hierarchy(capability.id),
            }

    async def save_description(self, capability_id: int, description: str) -> bool:
        """Save capability description and create audit log."""
        async with await self._get_session() as session:
            try:
                # Get current capability within this session
                stmt = select(Capability).where(Capability.id == capability_id)
                result = await session.execute(stmt)
                capability = result.scalar_one_or_none()

                if not capability:
                    return False

                # Store old values for audit
                old_values = {"description": capability.description}

                # Update description
                capability.description = description

                # Add audit log
                await self.log_audit(
                    session,
                    "UPDATE",
                    capability_id=capability_id,
                    capability_name=capability.name,
                    old_values=old_values,
                    new_values={"description": description},
                )

                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def update_capability(
        self, capability_id: int, capability: CapabilityUpdate, session=None
    ) -> Optional[Capability]:
        """Update a capability."""
        if session is None:
            async with await self._get_session() as session:
                return await self._update_capability_impl(
                    capability_id, capability, session
                )
        else:
            return await self._update_capability_impl(
                capability_id, capability, session
            )

    async def _update_capability_impl(
        self, capability_id: int, capability: CapabilityUpdate, session
    ) -> Optional[Capability]:
        try:
            # Enable foreign key constraints
            await session.execute(text("PRAGMA foreign_keys = ON"))
            await session.commit()

            # Get capability within this session
            stmt = select(Capability).where(Capability.id == capability_id)
            result = await session.execute(stmt)
            db_capability = result.scalar_one_or_none()
            if not db_capability:
                return None

            # Store old values for audit log
            old_values = {
                "name": db_capability.name,
                "description": db_capability.description,
                "parent_id": db_capability.parent_id,
            }

            # Add old parent name if it exists
            if db_capability.parent_id:
                parent_stmt = select(Capability).where(
                    Capability.id == db_capability.parent_id
                )
                parent_result = await session.execute(parent_stmt)
                old_parent = parent_result.scalar_one_or_none()
                if old_parent:
                    old_values["parent_name"] = old_parent.name

            # Convert capability model to dict for updates
            update_data = capability.model_dump(exclude_unset=True)

            # Update fields if present in update data
            if "name" in update_data:
                db_capability.name = update_data["name"]
            if "description" in update_data:
                db_capability.description = update_data["description"]

            # If updating parent_id, validate it exists
            if "parent_id" in update_data:
                new_parent_id = update_data["parent_id"]
                if new_parent_id is not None:
                    # Check if parent exists
                    stmt = select(Capability).where(Capability.id == new_parent_id)
                    result = await session.execute(stmt)
                    parent = result.scalar_one_or_none()
                    if not parent:
                        raise ValueError(
                            f"Parent capability with ID {new_parent_id} does not exist"
                        )
                    # Store new parent name in update data
                    update_data["parent_name"] = parent.name

                    # Check for circular reference
                    if new_parent_id == capability_id:
                        raise ValueError("Cannot set capability as its own parent")

                    # Check if new parent would create a circular reference through children
                    async def is_descendant(parent_id: int, child_id: int) -> bool:
                        if parent_id == child_id:
                            return True
                        stmt = select(Capability).where(
                            Capability.parent_id == child_id
                        )
                        result = await session.execute(stmt)
                        children = result.scalars().all()
                        for child in children:
                            if await is_descendant(parent_id, child.id):
                                return True
                        return False

                    if await is_descendant(capability_id, new_parent_id):
                        raise ValueError(
                            "Cannot create circular reference in capability hierarchy"
                        )

            for key, value in update_data.items():
                setattr(db_capability, key, value)

            # Add audit log for the update
            await self.log_audit(
                session,
                "UPDATE",
                capability_id=capability_id,
                capability_name=db_capability.name,
                old_values=old_values,
                new_values=update_data,
            )

            await session.commit()
            await session.refresh(db_capability)
            return db_capability
        except Exception:
            await session.rollback()
            raise

    async def delete_capability(self, capability_id: int, session=None) -> bool:
        """Delete a capability and its children."""
        if session is None:
            async with await self._get_session() as session:
                return await self._delete_capability_impl(capability_id, session)
        else:
            return await self._delete_capability_impl(capability_id, session)

    async def _delete_capability_impl(self, capability_id: int, session) -> bool:
        try:
            # Enable foreign key constraints for this session
            await session.execute(text("PRAGMA foreign_keys = ON"))
            await session.commit()

            # Get the capability within this session
            stmt = select(Capability).where(Capability.id == capability_id)
            result = await session.execute(stmt)
            capability = result.scalar_one_or_none()
            if not capability:
                return False

            # Log deletion with old values
            old_values = {
                "name": capability.name,
                "description": capability.description,
                "parent_id": capability.parent_id,
                "order_position": capability.order_position,
            }
            await self.log_audit(
                session,
                "DELETE",
                capability_id=capability_id,
                capability_name=capability.name,
                old_values=old_values,
            )

            # Get all descendants to ensure they're properly deleted
            async def get_descendants(cap_id: int) -> List[int]:
                stmt = select(Capability).where(Capability.parent_id == cap_id)
                result = await session.execute(stmt)
                children = result.scalars().all()
                ids = [cap.id for cap in children]
                for (
                    child_id
                ) in ids.copy():  # Use copy to avoid modifying list during iteration
                    ids.extend(await get_descendants(child_id))
                return ids

            # Get all descendant IDs
            descendant_ids = await get_descendants(capability_id)

            # Delete all descendants first (bottom-up deletion)
            for desc_id in reversed(descendant_ids):
                stmt = select(Capability).where(Capability.id == desc_id)
                result = await session.execute(stmt)
                desc = result.scalar_one_or_none()
                if desc:
                    await session.delete(desc)

            # Finally delete the capability itself
            await session.delete(capability)
            await session.commit()
            return True
        except Exception as e:
            print(f"Error in delete_capability: {str(e)}")
            await session.rollback()
            raise

    async def update_capability_order(
        self, capability_id: int, new_parent_id: Optional[int], new_order: int
    ) -> Optional[Capability]:
        """Update a capability's parent and order."""
        async with await self._get_session() as session:
            try:
                # Enable foreign key constraints
                await session.execute(text("PRAGMA foreign_keys = ON"))
                await session.commit()

                # Get capability
                stmt = select(Capability).where(Capability.id == capability_id)
                result = await session.execute(stmt)
                db_capability = result.scalar_one_or_none()
                if not db_capability:
                    return None

                # Store old values for audit
                old_values = {
                    "parent_id": db_capability.parent_id,
                    "order_position": db_capability.order_position,
                }

                # Add old parent name if it exists
                if db_capability.parent_id:
                    parent_stmt = select(Capability).where(
                        Capability.id == db_capability.parent_id
                    )
                    parent_result = await session.execute(parent_stmt)
                    old_parent = parent_result.scalar_one_or_none()
                    if old_parent:
                        old_values["parent_name"] = old_parent.name

                # Get new parent name if applicable
                new_values = {"parent_id": new_parent_id, "order_position": new_order}
                if new_parent_id:
                    parent_stmt = select(Capability).where(
                        Capability.id == new_parent_id
                    )
                    parent_result = await session.execute(parent_stmt)
                    new_parent = parent_result.scalar_one_or_none()
                    if new_parent:
                        new_values["parent_name"] = new_parent.name

                # Update order of other capabilities
                if db_capability.parent_id == new_parent_id:
                    # Moving within same parent
                    if new_order > db_capability.order_position:
                        stmt = select(Capability).where(
                            Capability.parent_id == new_parent_id,
                            Capability.order_position <= new_order,
                            Capability.order_position > db_capability.order_position,
                            Capability.id != capability_id,
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
                            Capability.id != capability_id,
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
                        Capability.order_position > db_capability.order_position,
                    )
                    result = await session.execute(stmt)
                    capabilities = result.scalars().all()
                    for cap in capabilities:
                        cap.order_position -= 1

                    # Increase order of capabilities in new parent
                    stmt = select(Capability).where(
                        Capability.parent_id == new_parent_id,
                        Capability.order_position >= new_order,
                    )
                    result = await session.execute(stmt)
                    capabilities = result.scalars().all()
                    for cap in capabilities:
                        cap.order_position += 1

                # Update the capability's parent and position
                db_capability.parent_id = new_parent_id
                db_capability.order_position = new_order

                # Add audit log for the move operation
                await self.log_audit(
                    session,
                    "MOVE",
                    capability_id=capability_id,
                    capability_name=db_capability.name,
                    old_values=old_values,
                    new_values=new_values,
                )

                await session.commit()
                await session.refresh(db_capability)
                return db_capability

            except Exception as e:
                await session.rollback()
                raise e

    async def export_capabilities(self) -> List[dict]:
        """Export all capabilities in the external format."""
        async with await self._get_session() as session:
            # Enable foreign key constraints
            await session.execute(text("PRAGMA foreign_keys = ON"))
            await session.commit()

            # Get all capabilities and verify their parent relationships
            stmt = select(Capability).order_by(Capability.order_position)
            result = await session.execute(stmt)
            capabilities = result.scalars().all()

            # Create mapping of valid DB IDs to new UUIDs
            id_mapping = {}
            export_data = []

            # First pass: Map IDs and validate parent relationships
            for cap in capabilities:
                # Only include capabilities that either:
                # 1. Have no parent (root capabilities)
                # 2. Have a parent that exists in our capabilities list
                if cap.parent_id is None or any(
                    p.id == cap.parent_id for p in capabilities
                ):
                    id_mapping[cap.id] = str(uuid4())

            # Second pass: Create export data with validated parent references
            for cap in capabilities:
                if cap.id in id_mapping:  # Only include validated capabilities
                    export_data.append(
                        {
                            "id": id_mapping[cap.id],
                            "name": cap.name,
                            "capability": 0,
                            "description": cap.description or "",
                            "parent": id_mapping.get(cap.parent_id)
                            if cap.parent_id in id_mapping
                            else None,
                        }
                    )

            return export_data

    async def search_capabilities(self, query: str) -> List[Capability]:
        """Search capabilities by name or description."""
        async with await self._get_session() as session:
            search_term = f"%{query}%"
            stmt = select(Capability).where(
                or_(
                    Capability.name.ilike(search_term),
                    Capability.description.ilike(search_term),
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def clear_all_capabilities(self) -> None:
        """Clear all capabilities from the database."""
        async with await self._get_session() as session:
            try:
                # Enable foreign key constraints
                await session.execute(text("PRAGMA foreign_keys = ON"))
                await session.commit()

                # Get all root capabilities
                stmt = select(Capability).where(Capability.parent_id.is_(None))
                result = await session.execute(stmt)
                root_capabilities = result.scalars().all()

                # Delete each root capability (which will cascade to children)
                for root in root_capabilities:
                    await session.delete(root)

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
                # Enable foreign key constraints
                await session.execute(text("PRAGMA foreign_keys = ON"))

                # Clear existing audit logs
                await session.execute(text("DELETE FROM audit_log"))

                # Clear existing capabilities within the same transaction
                stmt = select(Capability).where(Capability.parent_id.is_(None))
                result = await session.execute(stmt)
                root_capabilities = result.scalars().all()
                for root in root_capabilities:
                    await session.delete(root)
                await session.flush()

                # Create mapping of external IDs to new database IDs
                id_mapping = {}
                parent_updates = []

                # First pass: Create all capabilities and store parent updates
                for item in data:
                    try:
                        cap = CapabilityCreate(
                            name=item["name"],
                            description=item.get("description", ""),
                            parent_id=None,  # Initially create without parent
                        )
                        db_capability = Capability(
                            name=cap.name,
                            description=cap.description,
                            parent_id=None,
                            order_position=0,  # Reset order position
                        )
                        session.add(db_capability)
                        await session.flush()  # Flush to get the ID

                        # Store in mapping
                        id_mapping[item["id"]] = db_capability.id

                        # Store parent update if needed
                        if item.get("parent"):
                            parent_updates.append((db_capability, item["parent"]))

                    except Exception as e:
                        print(f"Error creating capability {item.get('name')}: {e}")
                        await session.rollback()
                        raise

                # Second pass: Update parent relationships
                for capability, parent_ext_id in parent_updates:
                    parent_id = id_mapping.get(parent_ext_id)
                    if parent_id is None:
                        await session.rollback()
                        raise ValueError(
                            f"Invalid parent reference for capability {capability.name}"
                        )
                    capability.parent_id = parent_id

                # Add a single audit log entry for the import
                await self.log_audit(
                    session,
                    "IMPORT",
                    capability_name="SYSTEM",
                    new_values={"message": f"Imported {len(data)} capabilities"},
                )

                # Commit all changes in one transaction
                await session.commit()

            except Exception as e:
                print(f"Error during import: {str(e)}")
                await session.rollback()
                raise

    async def get_markdown_hierarchy(self) -> str:
        """Generate a markdown representation of the capability hierarchy."""

        async def build_hierarchy(
            parent_id: Optional[int] = None, level: int = 0
        ) -> str:
            capabilities = await self.get_capabilities(parent_id)
            result = []
            for cap in capabilities:
                indent = "  " * level
                result.append(f"{indent}- {cap.name}")
                child_hierarchy = await build_hierarchy(cap.id, level + 1)
                if child_hierarchy:
                    result.append(child_hierarchy)
            return "\n".join(result)

        return await build_hierarchy()

    async def export_audit_logs(
        self, start_date: Optional[datetime] = None
    ) -> List[dict]:
        """Export audit logs in a readable format."""
        async with await self._get_session() as session:
            query = select(AuditLog).order_by(AuditLog.timestamp)
            if start_date:
                query = query.where(AuditLog.timestamp >= start_date)

            result = await session.execute(query)
            logs = result.scalars().all()

            export_data = []
            for log in logs:
                # Parse JSON values once
                old_values = json.loads(log.old_values) if log.old_values else None
                new_values = json.loads(log.new_values) if log.new_values else None

                # Remove order_position from values if present
                if old_values and "order_position" in old_values:
                    del old_values["order_position"]
                if new_values and "order_position" in new_values:
                    del new_values["order_position"]

                entry = {
                    "timestamp": log.timestamp.isoformat(),
                    "operation": log.operation,
                    "capability_id": log.capability_id,
                    "capability_name": log.capability_name,
                    "old_values": old_values,
                    "new_values": new_values,
                }
                export_data.append(entry)

            return export_data

    async def import_audit_logs(self, logs: List[dict]) -> None:
        """Import audit logs from exported format."""
        async with await self._get_session() as session:
            for log_entry in logs:
                audit = AuditLog(
                    operation=log_entry["operation"],
                    capability_id=log_entry["capability_id"],
                    capability_name=log_entry["capability_name"],
                    old_values=json.dumps(log_entry["old_values"])
                    if log_entry["old_values"]
                    else None,
                    new_values=json.dumps(log_entry["new_values"])
                    if log_entry["new_values"]
                    else None,
                    timestamp=datetime.fromisoformat(log_entry["timestamp"]),
                )
                session.add(audit)
            await session.commit()
