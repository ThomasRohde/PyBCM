import ttkbootstrap as ttk
from ttkbootstrap.constants import END
from typing import Optional
from bcm.database import DatabaseOperations
from bcm.dialogs import CapabilityDialog, create_dialog


class CapabilityTreeview(ttk.Treeview):
    @staticmethod
    def _calculate_row_height(style_name):
        """Calculate appropriate row height based on font size and DPI scaling."""
        style = ttk.Style()
        font = style.lookup(style_name, "font")
        
        # Get DPI scaling factor using tk scaling
        try:
            # Get the root window through style's master
            root = style.master
            if root:
                scaling = root.tk.call('tk', 'scaling')
            else:
                scaling = 1.0
        except:  # noqa: E722
            scaling = 1.0  # Fallback scaling factor
            
        if font:
            # Handle both string and tuple font specifications
            if isinstance(font, tuple):
                font_size = float(font[1])
            else:
                # Split the font spec and get the size
                try:
                    font_size = float(font.split()[-1])
                except (IndexError, ValueError):
                    font_size = 10.0  # Default font size if parsing fails
                    
            # Calculate base height with DPI awareness
            base_height = int(font_size * scaling)
            padding = int(2 * scaling)  # Scale padding too
            return base_height + padding
            
        # Default height with DPI awareness
        return int(20 * scaling)

    def __init__(self, master, db_ops: DatabaseOperations, **kwargs):
        # Initialize with the provided style (if any) for font size support
        super().__init__(master, **kwargs)
        self.db_ops = db_ops
        self.drag_source: Optional[str] = None
        self.drop_target: Optional[str] = None

        # Configure item height based on font size
        if "style" in kwargs:
            style = ttk.Style()
            height = self._calculate_row_height(kwargs["style"])
            style.configure(kwargs["style"], rowheight=height)

        # Configure treeview with single column
        self["columns"] = () 
        self.heading("#0", text="Capability")
        self.column("#0", width=300)

        # Create context menu
        self.context_menu = ttk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="New Child", command=self.new_child)
        self.context_menu.add_command(label="Edit", command=self.edit_capability)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_capability)
        self.context_menu.add_command(label="Delete Children", command=self.delete_children)

        # Bind events
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_drop)
        self.bind("<Button-3>", self.show_context_menu)

        self.refresh_tree()

        # Configure drop target styles
        self.tag_configure("drop_target", background="lightblue")
        self.tag_configure(
            "illegal_drop_target", background="#ffcccc"
        )  # Light red for illegal targets

    def _clear_drop_mark(self):
        """Clear any existing drop mark."""
        if self.drop_target:
            # Reset the item style by removing all relevant tags
            self.item(self.drop_target, tags=())
            self.drop_target = None

    async def _is_valid_drop_target(self, source_id: int, target_id: int) -> bool:
        """Check if target is a valid drop location for source."""
        try:
            # Can't drop on itself
            if source_id == target_id:
                return False

            # Get source capability
            source = await self.db_ops.get_capability(source_id)
            if not source:
                return False

            # Get target capability
            target = await self.db_ops.get_capability(target_id)
            if not target:
                return False

            # If target is current parent, it's always valid
            if target_id == source.parent_id:
                return True

            # Check if target is a descendant of source
            async def get_all_descendants(cap_id: int) -> set:
                result = set()
                children = await self.db_ops.get_capabilities(cap_id)
                for child in children:
                    result.add(child.id)
                    child_descendants = await get_all_descendants(child.id)
                    result.update(child_descendants)
                return result

            # Get all descendants of source
            descendants = await get_all_descendants(source_id)

            # If target is in descendants, it's invalid
            if target_id in descendants:
                return False

            return True

        except Exception:
            return False

    def _set_drop_target(self, target: str):
        """Set the current drop target with visual feedback."""
        if target != self.drop_target and target != self.drag_source:
            self._clear_drop_mark()
            self.drop_target = target
            # Apply the drop target style
            self.item(target, tags=("drop_target",))

    def show_context_menu(self, event):
        item = self.identify_row(event.y)
        if item:
            self.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def new_capability(self, parent_id=None):
        dialog = CapabilityDialog(self, self.db_ops, parent_id=parent_id)
        dialog.wait_window()
        if dialog.result:
            # Use _wrap_async to properly await the async operation
            self._wrap_async(self.db_ops.create_capability(dialog.result))
            self.refresh_tree()

    def new_child(self):
        selected = self.selection()
        if selected:
            self.new_capability(int(selected[0]))

    def edit_capability(self):
        selected = self.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        capability = self._wrap_async(self.db_ops.get_capability(capability_id))
        if capability:
            dialog = CapabilityDialog(self, self.db_ops, capability)
            dialog.wait_window()
            if dialog.result:
                self._wrap_async(
                    self.db_ops.update_capability(capability_id, dialog.result)
                )
                self.refresh_tree()

    async def _delete_capability_async(self, capability_id: int, session) -> bool:
        """Helper to delete capability and create audit log within a single session."""
        try:
            # Delete capability and its children
            success = await self.db_ops.delete_capability(capability_id, session)
            if success:
                return True
            return False
        except Exception as e:
            raise e

    async def _delete_children_async(self, capability_id: int, session) -> bool:
        """Helper to delete all children of a capability within a single session."""
        try:
            # Get all immediate children
            children = await self.db_ops.get_capabilities(capability_id)
            
            # Delete each child (which will cascade to their children)
            for child in children:
                success = await self.db_ops.delete_capability(child.id, session)
                if not success:
                    return False
            return True
        except Exception as e:
            raise e

    def delete_children(self):
        """Delete all children of the selected capability while keeping the parent."""
        selected = self.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        
        if create_dialog(
            self,
            "Delete Children",
            "Are you sure you want to delete all children\nof this capability?",
        ):
            try:
                # Create async function for deletion
                async def delete_async():
                    async with await self.db_ops._get_session() as session:
                        try:
                            success = await self._delete_children_async(
                                capability_id, session
                            )
                            if success:
                                await session.commit()
                                return True
                            return False
                        except Exception as e:
                            await session.rollback()
                            raise e

                # Use _wrap_async to properly await the async operation
                success = self._wrap_async(delete_async())
                if success:
                    self.refresh_tree()
                else:
                    create_dialog(
                        self,
                        "Error",
                        "Failed to delete children",
                        ok_only=True,
                    )
            except Exception as e:
                print(f"Error deleting children: {e}")
                create_dialog(
                    self,
                    "Error",
                    f"Failed to delete children: {str(e)}",
                    ok_only=True,
                )

    def delete_capability(self):
        """Delete selected capability."""
        selected = self.selection()
        if not selected:
            return

        capability_id = int(selected[0])

        if create_dialog(
            self,
            "Delete Capability",
            "Are you sure you want to delete this capability\nand all its children?",
        ):
            try:
                # Create async function for deletion
                async def delete_async():
                    async with await self.db_ops._get_session() as session:
                        try:
                            success = await self._delete_capability_async(
                                capability_id, session
                            )
                            if success:
                                await session.commit()
                                return True
                            return False
                        except Exception as e:
                            await session.rollback()
                            raise e

                # Use _wrap_async to properly await the async operation
                success = self._wrap_async(delete_async())
                if success:
                    self.refresh_tree()
                else:
                    create_dialog(
                        self,
                        "Error",
                        "Failed to delete capability - not found",
                        ok_only=True,
                    )
            except Exception as e:
                print(f"Error deleting capability: {e}")
                create_dialog(
                    self,
                    "Error",
                    f"Failed to delete capability: {str(e)}",
                    ok_only=True,
                )

    def _wrap_async(self, coro):
        """Wrapper to run async code synchronously in a new event loop."""
        import asyncio
        import threading
        import inspect

        result = None
        error = None
        event = threading.Event()

        async def run_coro():
            try:
                if inspect.isasyncgen(coro):
                    # Consume the entire generator and return the last value
                    last_value = None
                    async for item in coro:
                        last_value = item
                    return last_value
                else:
                    return await coro
            except Exception as e:
                raise e

        def run_async():
            nonlocal result, error
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(run_coro())
                finally:
                    loop.close()
            except Exception as e:
                error = e
            finally:
                event.set()

        # Run in a separate thread
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

        # Wait with timeout to prevent hanging
        if not event.wait(timeout=10.0):  # Increased timeout for complex operations
            error = TimeoutError("Async operation timed out")
            return None

        if error:
            raise error
        return result

    def refresh_tree(self):
        """Refresh the treeview with current data."""
        # Store currently open items
        opened_items = set()
        for item in self.get_children():
            if self.item(item, "open"):
                opened_items.add(item)

        # Clear selection and items
        self.selection_remove(self.selection())
        self.delete(*self.get_children())

        # Reload data
        try:
            capabilities = self._wrap_async(self.db_ops.get_capabilities(None))
            for cap in capabilities:
                item_id = str(cap.id)
                self.insert(
                    "", END, iid=item_id, text=cap.name, open=item_id in opened_items
                )
                self._load_capabilities(item_id, cap.id)
        except Exception as e:
            create_dialog(
                self, "Error", f"Failed to refresh tree: {str(e)}", ok_only=True
            )

    def _load_capabilities(self, parent: str = "", parent_id: Optional[int] = None):
        """Recursively load capabilities into the treeview."""
        try:
            capabilities = self._wrap_async(self.db_ops.get_capabilities(parent_id))
            if capabilities:  # Only process if we have capabilities
                for cap in capabilities:
                    item_id = str(cap.id)
                    self.insert(parent, END, iid=item_id, text=cap.name, open=True)
                    self._load_capabilities(item_id, cap.id)
        except Exception as e:
            print(f"Error loading capabilities: {e}")  # Log error for debugging

    def on_click(self, event):
        """Handle mouse click event."""
        self._clear_drop_mark()  # Clear any existing drop mark
        self.drag_source = self.identify_row(event.y)

    def on_drag(self, event):
        """Handle drag event."""
        if self.drag_source:
            self.configure(cursor="fleur")
            # Update drop target visual feedback
            target = self.identify_row(event.y)

            # Clear previous drop mark
            self._clear_drop_mark()

            if target and target != self.drag_source:
                # Check if this would be a valid drop target
                is_valid = self._wrap_async(
                    self._is_valid_drop_target(int(self.drag_source), int(target))
                )

                self.drop_target = target

                # Apply appropriate tag based on validity
                if is_valid:
                    self.item(target, tags=("drop_target",))
                else:
                    self.item(target, tags=("illegal_drop_target",))

    def on_drop(self, event):
        """Handle drop event."""
        self._clear_drop_mark()
        if not self.drag_source:
            return

        self.configure(cursor="")
        target = self.identify_row(event.y)

        try:
            source_id = int(self.drag_source)

            if not target:
                # Dropping outside - make it a root node
                result = self._wrap_async(
                    self.db_ops.update_capability_order(
                        source_id,
                        None,  # No parent = root node
                        0,  # Order position for new root
                    )
                )
            else:
                if target == self.drag_source:
                    self.drag_source = None
                    return

                target_id = int(target)
                # Check if this is a valid drop target
                is_valid = self._wrap_async(
                    self._is_valid_drop_target(source_id, target_id)
                )

                if not is_valid:
                    raise ValueError("Invalid drop target")

                # Get target's current children count for index
                target_index = len(self.get_children(target))

                try:
                    # Update in database
                    result = self._wrap_async(
                        self.db_ops.update_capability_order(
                            source_id, target_id, target_index
                        )
                    )
                except Exception as e:
                    # Convert database errors to ValueError for consistent handling
                    raise ValueError(str(e))

            if result:
                # Only refresh if update was successful
                self.refresh_tree()
                # Ensure the dropped item is visible and selected
                self.selection_set(str(source_id))
                self.see(str(source_id))
            else:
                self.refresh_tree()

        except ValueError as ve:
            # Handle specific validation errors
            create_dialog(self, "Error", str(ve), ok_only=True)
            self.refresh_tree()
        except Exception as e:
            create_dialog(self, "Error", str(e), ok_only=True)
            self.refresh_tree()
        finally:
            self.drag_source = None
