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
        self.bind("<Button-1>", self.on_click)
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
        
        # Configure treeview with single column
        self["columns"] = ()  # Remove description column
        self.heading("#0", text="Capability")
        self.column("#0", width=300)

        # Create context menu
        self.context_menu = ttk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="New Child", command=self.new_child)
        self.context_menu.add_command(label="Edit", command=self.edit_capability)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_capability)

        # Bind events
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_drop)
        self.bind("<Button-3>", self.show_context_menu)
        
        self.refresh_tree()

        # Configure drop target style
        self.tag_configure('drop_target', background='lightblue')

    def _is_valid_drop_target(self, source: str, target: str) -> bool:
        """Check if target is a valid drop location for source."""
        if not source or not target or source == target:
            return False
            
        # Check if target is a descendant of source
        current = target
        while current:
            if current == source:
                return False
            current = self.parent(current)
            
        return True

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
        # Store currently open items before clearing
        opened_items = [item for item in self.get_children('') if self.item(item, 'open')]
        
        # Clear selection and items
        self.selection_remove(self.selection())
        self.delete(*self.get_children())
        
        # Reload data
        try:
            await self._load_capabilities_async()
            
            # Restore previously opened state
            for item in opened_items:
                if item in self.get_children(''):
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
                item_id = str(cap.id)
                self.insert(
                    parent,
                    END,
                    iid=item_id,
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
        self.drag_source = self.identify_row(event.y)

    def on_drag(self, event):
        """Handle drag event."""
        if self.drag_source:
            target = self.identify_row(event.y)
            if target and self._is_valid_drop_target(self.drag_source, target):
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
        
        await self.db_ops.update_capability_order(source_id, new_parent_id, target_index)
        return new_parent_id

    async def _on_drop_async(self, source_id: int, new_parent_id: Optional[int], target_index: int):
        """Async handler for drop operation."""
        try:
            await self.db_ops.update_capability_order(source_id, new_parent_id, target_index)
            # Immediately refresh the tree after successful update
            await self.refresh_tree_async()
            return True
        except Exception as e:
            print(f"Error in drop operation: {e}")
            return False

    def on_drop(self, event):
        """Handle drop event."""
        self._clear_drop_mark()
        if not self.drag_source:
            return

        self.configure(cursor="")
        target = self.identify_row(event.y)
        
        if not target or not self._is_valid_drop_target(self.drag_source, target):
            self.drag_source = None
            return

        try:
            # Store current state
            source_id = int(self.drag_source)
            open_items = {item: self.item(item, 'open') 
                         for item in self.get_children('')}
            scroll_pos = self.yview()
            
            # Determine drop zone
            drop_zone = self._get_drop_zone(event, target)
            
            async def update_tree():
                # Update database
                new_parent_id = await self._update_capability_position(source_id, target, drop_zone)
                # Refresh tree
                await self.refresh_tree_async()
                return source_id, new_parent_id, open_items, scroll_pos

            def after_update(result):
                if not result:
                    return
                    
                source_id, new_parent_id, open_items, scroll_pos = result
                
                # Restore open states
                for item, was_open in open_items.items():
                    if item in self.get_children('') or any(item in self.get_children(p) for p in self.get_children('')):
                        self.item(item, open=was_open)
                
                # Ensure parent is expanded
                if new_parent_id:
                    parent_item = str(new_parent_id)
                    if parent_item in self.get_children(''):
                        self.item(parent_item, open=True)
                
                # Select and show the dropped item
                self.selection_set(str(source_id))
                self.see(str(source_id))
                
                # Restore scroll position
                self.yview_moveto(scroll_pos[0])
                
                # Force update
                self.update_idletasks()

            # Schedule the async operation
            self.schedule_async(update_tree(), after_update)
        except Exception as e:
            print(f"Error in drag and drop: {e}")
            self.refresh_tree()
        finally:
            self.drag_source = None
