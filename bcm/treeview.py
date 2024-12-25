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
        # Initialize with the provided style (if any) for font size support
        super().__init__(master, **kwargs)
        self.db_ops = db_ops
        self.drag_source: Optional[str] = None
        self.drop_target: Optional[str] = None
        
        # Configure item height based on font size
        if 'style' in kwargs:
            style = ttk.Style()
            height = self._calculate_row_height(kwargs['style'])
            style.configure(kwargs['style'], rowheight=height)
        
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
            self.db_ops.create_capability(dialog.result)
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
            try:
                self.db_ops.delete_capability(capability_id)
                self.refresh_tree()
            except Exception as e:
                print(f"Error deleting capability: {e}")
                create_dialog(
                    self,
                    "Error",
                    f"Failed to delete capability: {str(e)}",
                    ok_only=True
                )

    def refresh_tree(self):
        """Refresh the treeview with current data."""
        # Clear selection and items
        self.selection_remove(self.selection())
        self.delete(*self.get_children())
        
        # Reload data
        try:
            self._load_capabilities()
        except Exception as e:
            print(f"Error refreshing tree: {e}")

    def _load_capabilities(self, parent: str = "", parent_id: Optional[int] = None):
        """Recursively load capabilities into the treeview."""
        try:
            capabilities = self.db_ops.get_capabilities(parent_id)
            for cap in capabilities:
                item_id = str(cap.id)
                # Check if item already exists
                if item_id not in self.get_children(parent):
                    self.insert(
                        parent,
                        END,
                        iid=item_id,
                        text=cap.name,
                        open=True
                    )
                    self._load_capabilities(item_id, cap.id)
        except Exception as e:
            print(f"Error loading capabilities for parent {parent_id}: {e}")

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
            if target and target != self.drag_source:
                self._set_drop_target(target)
            else:
                self._clear_drop_mark()

    def on_drop(self, event):
        """Handle drop event."""
        self._clear_drop_mark()  # Clear drop mark
        if not self.drag_source:
            return

        self.configure(cursor="")
        target = self.identify_row(event.y)
        if not target or target == self.drag_source:
            self.drag_source = None
            return

        # Get drop position relative to target
        target_y = self.bbox(target)[1]
        is_above_middle = event.y < target_y + self.bbox(target)[3] // 2

        # Convert IDs
        source_id = int(self.drag_source)
        target_id = int(target)

        if is_above_middle:
            # Drop above target - make siblings
            new_parent_id = self.parent(target)
            new_parent_id = int(new_parent_id) if new_parent_id else None
            target_index = self.index(target)
        else:
            # Drop below middle - make child
            new_parent_id = target_id
            target_index = len(self.get_children(target))

        # Update in database
        self.db_ops.update_capability_order(source_id, new_parent_id, target_index)
        
        # Refresh the tree to show the new order
        self.refresh_tree()
        self.drag_source = None
