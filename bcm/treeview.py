import asyncio
import ttkbootstrap as ttk
from ttkbootstrap.constants import END
from typing import Optional
from .database import DatabaseOperations
from .dialogs import CapabilityDialog, create_dialog

class CapabilityTreeview(ttk.Treeview):
    @staticmethod
    def _calculate_row_height(style_name):
        """Calculate appropriate row height based on font size."""
        style = ttk.Style()
        font = style.lookup(style_name, 'font')
        if font:
            # Add padding to font size for better readability
            # Handle both string and tuple font specifications
            if isinstance(font, tuple):
                font_size = font[1]
            else:
                # Split the font spec and get the size
                font_size = font.split()[-1]
            return int(font_size) + 16  # Add padding to font size
        return 20  # default height

    def _collect_open_items(self, parent='') -> set:
        """Recursively collect IDs of all open items."""
        open_items = set()
        for item in self.get_children(parent):
            if self.item(item, 'open'):
                open_items.add(item)
                # Recursively add open children
                open_items.update(self._collect_open_items(item))
        return open_items

    def __init__(self, master, db_ops: DatabaseOperations, **kwargs):
        # Configure item height based on font size if style provided
        if 'style' in kwargs:
            style = ttk.Style()
            height = self._calculate_row_height(kwargs['style'])
            style.configure(kwargs['style'], rowheight=height)
            
        super().__init__(master, **kwargs)
        self.db_ops = db_ops
        self.drag_source = None
        self.drop_target = None
        
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

        # Bind events
        self.bind("<ButtonPress-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_drop)
        self.bind("<Button-3>", self.show_context_menu)
        
        # Configure drop target style
        self.tag_configure('drop_target', background='lightblue')
        
        # Schedule initial load after widget is ready
        self.after_idle(lambda: self.schedule_async(self.refresh_tree_async()))

    def schedule_async(self, coro, callback=None):
        """Schedule an async operation without blocking the GUI thread."""
        async def wrapped():
            try:
                result = await coro
                if callback:
                    self.after_idle(lambda: callback(result))
            except Exception as e:
                print(f"Async operation failed: {e}")
                # Optionally show error dialog
                self.after_idle(lambda e=e: create_dialog(
                    self,
                    "Error",
                    f"Operation failed: {str(e)}",
                    ok_only=True
                ))
        
        loop = asyncio.get_event_loop()
        return loop.create_task(wrapped())

    def _is_valid_drop_target(self, source: str, target: str) -> bool:
        """Check if target is a valid drop location for source."""
        # Basic validation
        if not source or not target:
            print(f"Basic validation failed - missing source or target: source={source}, target={target}")
            return False
            
        try:
            # Convert IDs to integers for comparison
            source_id = int(source)
            target_id = int(target)
            print(f"Validating drop - source_id={source_id}, target_id={target_id}")
            
            # Get all descendants of source
            def get_descendants(item_id: str) -> set:
                result = set()
                for child in self.get_children(item_id):
                    result.add(child)
                    result.update(get_descendants(child))
                return result
                
            # Get all ancestors of target
            def get_ancestors(item_id: str) -> set:
                result = set()
                parent = self.parent(item_id)
                while parent:
                    result.add(parent)
                    parent = self.parent(parent)
                return result
                
            # Invalid if target is a descendant of source or an ancestor
            descendants = get_descendants(source)
            ancestors = get_ancestors(source)
            
            if target in descendants:
                print(f"Invalid - target {target} is descendant of source {source}")
                return False
                
            if target in ancestors:
                print(f"Invalid - target {target} is ancestor of source {source}")
                return False
                
            return True
                
        except (ValueError, TypeError) as e:
            print(f"Error validating drop target: {e}")
            return False

    def _clear_drop_mark(self):
        """Clear any existing drop mark."""
        if self.drop_target:
            # Reset the item style
            self.item(self.drop_target, tags=())
            self.drop_target = None

    def _set_drop_target(self, target: str):
        """Set the current drop target with visual feedback."""
        if target != self.drop_target and target != self.drag_source:
            self._clear_drop_mark()
            self.drop_target = target
            # Apply the drop target style
            self.item(target, tags=('drop_target',))

    def show_context_menu(self, event):
        item = self.identify_row(event.y)
        if item:
            self.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def new_capability(self, parent_id=None):
        dialog = CapabilityDialog(self, self.db_ops, parent_id=parent_id)
        dialog.wait_window()
        if dialog.result:
            # Create coroutine for capability creation
            async def create_async():
                try:
                    await self.db_ops.create_capability(dialog.result)
                    await self.refresh_tree_async()
                except Exception as e:
                    print(f"Error creating capability: {e}")
            
            # Schedule the async operation without waiting
            loop = asyncio.get_event_loop()
            loop.create_task(create_async())

    def new_child(self):
        selected = self.selection()
        if selected:
            self.new_capability(int(selected[0]))

    def edit_capability(self):
        selected = self.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        capability = self.db_ops.get_capability(capability_id)
        if capability:
            dialog = CapabilityDialog(self, self.db_ops, capability)
            dialog.wait_window()
            if dialog.result:
                self.db_ops.update_capability(capability_id, dialog.result)
                self.refresh_tree()

    def delete_capability(self):
        """Delete selected capability."""
        selected = self.selection()
        if not selected:
            return

        capability_id = int(selected[0])

        if create_dialog(
            self,
            "Delete Capability",
            "Are you sure you want to delete this capability\nand all its children?"
        ):
            async def delete():
                await self.db_ops.delete_capability(capability_id)
                await self.refresh_tree_async()

            self.schedule_async(delete())

    async def refresh_tree_async(self):
        """Async version of refresh tree."""
        # Store currently open items recursively before clearing
        opened_items = self._collect_open_items()
        
        # Clear selection and items
        self.selection_remove(self.selection())
        self.delete(*self.get_children())
        
        # Reload data
        try:
            await self._load_capabilities_async()
            
            # Restore previously opened state
            for item in opened_items:
                if item in self.get_children('', recursive=True):
                    self.item(item, open=True)
        except Exception as e:
            print(f"Error refreshing tree: {e}")

    def refresh_tree(self):
        """Non-blocking refresh of the tree."""
        self.schedule_async(self.refresh_tree_async())

    async def _load_capabilities_async(self, parent: str = "", parent_id: Optional[int] = None):
        """Async version of load capabilities."""
        try:
            capabilities = await self.db_ops.get_capabilities(parent_id)
            for cap in capabilities:
                item_id = str(cap.id)  # Explicitly convert DB ID to string
                print(f"Loading capability: id={cap.id}, item_id={item_id}, name={cap.name}")  # Debug
                self.insert(
                    parent,
                    END,
                    iid=item_id,  # Using string ID from database
                    text=cap.name,
                    open=False  # Start closed, we'll restore state after
                )
                # Recursively load children
                await self._load_capabilities_async(item_id, cap.id)
        except Exception as e:
            print(f"Error loading capabilities for parent {parent_id}: {e}")

    def on_click(self, event):
        """Handle mouse click event."""
        self._clear_drop_mark()  # Clear any existing drop mark
        
        # Only set drag source if clicking on an actual item
        item = self.identify_row(event.y)
        if item:  # Guard check
            self.drag_source = item
            print(f"Click - drag source ID: {self.drag_source}")  # Debug
        else:
            self.drag_source = None

    def on_drag(self, event):
        """Handle drag event."""
        if not self.drag_source:
            return
            
        target = self.identify_row(event.y)
        print(f"Drag - source={self.drag_source}, target={target}")  # Keep debug
        
        # If no target (dragging between items), clear drop mark
        if not target:
            self.configure(cursor="no")
            self._clear_drop_mark()
            return
            
        # Get drop zone before validation
        drop_zone = self._get_drop_zone(event, target)
        print(f"Drop zone: {drop_zone}")  # Debug
        
        # Don't allow dropping onto self, but allow dropping above/below
        if target == self.drag_source and drop_zone == "onto":
            self.configure(cursor="no")
            self._clear_drop_mark()
            return
            
        # Now check if it's a valid target
        if self._is_valid_drop_target(self.drag_source, target):
            self.configure(cursor="arrow")
            self._set_drop_target(target)
        else:
            self.configure(cursor="no")
            self._clear_drop_mark()

    def _get_drop_zone(self, event, target):
        """Determine drop zone based on mouse position relative to target item."""
        target_y = self.bbox(target)[1]
        target_height = self.bbox(target)[3]
        relative_y = event.y - target_y
        
        if relative_y < target_height / 3:
            return "above"
        elif relative_y > (target_height * 2 / 3):
            return "below"
        else:
            return "onto"

    async def _update_capability_position(self, source_id: int, target: str, drop_zone: str):
        """Update capability position based on drop zone."""
        try:
            target_id = int(target)
            
            if drop_zone == "onto":
                # Make it a child of target
                new_parent_id = target_id
                target_index = len(self.get_children(target))
            else:
                # Make it a sibling
                new_parent_id = self.parent(target)
                new_parent_id = int(new_parent_id) if new_parent_id else None
                base_index = self.index(target)
                target_index = base_index if drop_zone == "above" else base_index + 1
            
            # Update database
            await self.db_ops.update_capability_order(source_id, new_parent_id, target_index)
            return new_parent_id
            
        except Exception as e:
            print(f"Error updating capability position: {e}")
            raise


    def on_drop(self, event):
        """Handle drop event."""
        try:
            self._clear_drop_mark()
            if not self.drag_source:
                return

            # Reset cursor
            self.configure(cursor="")
            
            target = self.identify_row(event.y)
            if not target:
                self.drag_source = None
                return

            if not self._is_valid_drop_target(self.drag_source, target):
                self.drag_source = None
                return

            source_id = int(self.drag_source)
            drop_zone = self._get_drop_zone(event, target)

            async def update_tree():
                try:
                    # Update database
                    await self._update_capability_position(source_id, target, drop_zone)
                    # Refresh tree
                    await self.refresh_tree_async()
                    # Ensure dropped item is visible and selected
                    self.selection_set(str(source_id))
                    self.see(str(source_id))
                    self.update_idletasks()
                except Exception as e:
                    print(f"Error during tree update: {e}")
                    await self.refresh_tree_async()

            # Schedule the async operation
            self.schedule_async(update_tree())
        except Exception as e:
            print(f"Error in drag and drop: {e}")
            self.refresh_tree()
        finally:
            self.drag_source = None
            self.configure(cursor="")  # Ensure cursor is reset
    def _update_visual_state(self, item_id: str, parent: str, index: int, expand_parent: bool = False):
        """Handle visual updates for tree operations."""
        try:
            # Perform the move
            self.move(item_id, parent, index)
            
            # Expand parent if requested
            if expand_parent and parent:
                self.item(parent, open=True)
            
            # Ensure item is visible and selected
            self.selection_set(item_id)
            self.see(item_id)
            
            # Force immediate update
            self.update_idletasks()
            
        except Exception as e:
            print(f"Error updating visual state: {e}")
            # If visual update fails, fall back to full refresh
            self.refresh_tree()
