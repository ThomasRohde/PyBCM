import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import MessageDialog
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json

from .models import init_db, get_db, CapabilityCreate, CapabilityUpdate
from .database import DatabaseOperations

class CapabilityTreeview(ttk.Treeview):
    def __init__(self, master, db_ops: DatabaseOperations, **kwargs):
        super().__init__(master, **kwargs)
        self.db_ops = db_ops
        self.drag_source: Optional[str] = None
        self.drop_target: Optional[str] = None

        # Configure treeview
        self["columns"] = ("description",)
        self.heading("#0", text="Capability")
        self.heading("description", text="Description")
        self.column("#0", width=300)
        self.column("description", width=400)

        # Bind events
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_drop)
        
        # Load initial data
        self.refresh_tree()

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
                        values=(cap.description or "",),
                        open=True
                    )
                    self._load_capabilities(item_id, cap.id)
        except Exception as e:
            print(f"Error loading capabilities for parent {parent_id}: {e}")

    def on_click(self, event):
        """Handle mouse click event."""
        self.drag_source = self.identify_row(event.y)

    def on_drag(self, event):
        """Handle drag event."""
        if self.drag_source:
            self.configure(cursor="fleur")

    def on_drop(self, event):
        """Handle drop event."""
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

class CapabilityForm(ttk.Frame):
    def __init__(self, master, db_ops: DatabaseOperations, tree: CapabilityTreeview):
        super().__init__(master)
        self.db_ops = db_ops
        self.tree = tree
        self.selected_id: Optional[int] = None

        # Create widgets
        self._create_widgets()
        self._create_layout()

    def _create_widgets(self):
        """Create form widgets."""
        # Labels
        self.name_label = ttk.Label(self, text="Name:")
        self.desc_label = ttk.Label(self, text="Description:")
        
        # Entry fields
        self.name_var = ttk.StringVar()
        self.name_entry = ttk.Entry(self, textvariable=self.name_var)
        
        self.desc_var = ttk.StringVar()
        self.desc_entry = ttk.Entry(self, textvariable=self.desc_var)

        # Buttons
        self.add_btn = ttk.Button(
            self,
            text="Add New",
            command=self.add_capability,
            style="primary.TButton"
        )
        self.update_btn = ttk.Button(
            self,
            text="Update",
            command=self.update_capability,
            state="disabled",
            style="info.TButton"
        )
        self.delete_btn = ttk.Button(
            self,
            text="Delete",
            command=self.delete_capability,
            state="disabled",
            style="danger.TButton"
        )
        self.clear_btn = ttk.Button(
            self,
            text="Clear",
            command=self.clear_form,
            style="secondary.TButton"
        )

    def _create_layout(self):
        """Create form layout."""
        # Form fields
        self.name_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        self.desc_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.desc_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Buttons
        self.add_btn.grid(row=2, column=0, padx=5, pady=10)
        self.update_btn.grid(row=2, column=1, padx=5, pady=10)
        self.delete_btn.grid(row=2, column=2, padx=5, pady=10)
        self.clear_btn.grid(row=2, column=3, padx=5, pady=10)

        # Configure grid
        self.columnconfigure(1, weight=1)

    def clear_form(self):
        """Clear form fields and selection."""
        self.name_var.set("")
        self.desc_var.set("")
        self.selected_id = None
        self.update_btn.configure(state="disabled")
        self.delete_btn.configure(state="disabled")
        self.add_btn.configure(state="normal")

    def add_capability(self):
        """Add a new capability."""
        name = self.name_var.get().strip()
        if not name:
            return

        # Get selected item as parent
        selected = self.tree.selection()
        parent_id = int(selected[0]) if selected else None

        # Create capability
        capability = CapabilityCreate(
            name=name,
            description=self.desc_var.get().strip(),
            parent_id=parent_id
        )
        self.db_ops.create_capability(capability)
        
        # Refresh tree and clear form
        self.tree.refresh_tree()
        self.clear_form()

    def update_capability(self):
        """Update selected capability."""
        if not self.selected_id:
            return

        name = self.name_var.get().strip()
        if not name:
            return

        # Update capability
        capability = CapabilityUpdate(
            name=name,
            description=self.desc_var.get().strip()
        )
        self.db_ops.update_capability(self.selected_id, capability)
        
        # Refresh tree and clear form
        self.tree.refresh_tree()
        self.clear_form()

    def delete_capability(self):
        """Delete selected capability."""
        if not self.selected_id:
            return

        # Confirm deletion
        dialog = MessageDialog(
            title="Delete Capability",
            message="Are you sure you want to delete this capability and all its children?",
            buttons=["Yes", "No"],
        )
        if dialog.show() == "Yes":
            self.db_ops.delete_capability(self.selected_id)
            self.tree.refresh_tree()
            self.clear_form()

    def load_capability(self, event=None):
        """Load selected capability into form."""
        selected = self.tree.selection()
        if not selected:
            self.clear_form()
            return

        capability_id = int(selected[0])
        capability = self.db_ops.get_capability(capability_id)
        if capability:
            self.selected_id = capability_id
            self.name_var.set(capability.name)
            self.desc_var.set(capability.description or "")
            self.update_btn.configure(state="normal")
            self.delete_btn.configure(state="normal")
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import MessageDialog
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json

from .models import init_db, get_db, CapabilityCreate, CapabilityUpdate
from .database import DatabaseOperations

class CapabilityTreeview(ttk.Treeview):
    def __init__(self, master, db_ops: DatabaseOperations, **kwargs):
        super().__init__(master, **kwargs)
        self.db_ops = db_ops
        self.drag_source: Optional[str] = None
        self.drop_target: Optional[str] = None

        # Configure treeview
        self["columns"] = ("description",)
        self.heading("#0", text="Capability")
        self.heading("description", text="Description")
        self.column("#0", width=300)
        self.column("description", width=400)

        # Bind events
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_drop)
        
        # Load initial data
        self.refresh_tree()

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
                        values=(cap.description or "",),
                        open=True
                    )
                    self._load_capabilities(item_id, cap.id)
        except Exception as e:
            print(f"Error loading capabilities for parent {parent_id}: {e}")

    def on_click(self, event):
        """Handle mouse click event."""
        self.drag_source = self.identify_row(event.y)

    def on_drag(self, event):
        """Handle drag event."""
        if self.drag_source:
            self.configure(cursor="fleur")

    def on_drop(self, event):
        """Handle drop event."""
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

class CapabilityForm(ttk.Frame):
    def __init__(self, master, db_ops: DatabaseOperations, tree: CapabilityTreeview):
        super().__init__(master)
        self.db_ops = db_ops
        self.tree = tree
        self.selected_id: Optional[int] = None

        # Create widgets
        self._create_widgets()
        self._create_layout()

    def _create_widgets(self):
        """Create form widgets."""
        # Labels
        self.name_label = ttk.Label(self, text="Name:")
        self.desc_label = ttk.Label(self, text="Description:")
        
        # Entry fields
        self.name_var = ttk.StringVar()
        self.name_entry = ttk.Entry(self, textvariable=self.name_var)
        
        self.desc_var = ttk.StringVar()
        self.desc_entry = ttk.Entry(self, textvariable=self.desc_var)

        # Buttons
        self.add_btn = ttk.Button(
            self,
            text="Add New",
            command=self.add_capability,
            style="primary.TButton"
        )
        self.update_btn = ttk.Button(
            self,
            text="Update",
            command=self.update_capability,
            state="disabled",
            style="info.TButton"
        )
        self.delete_btn = ttk.Button(
            self,
            text="Delete",
            command=self.delete_capability,
            state="disabled",
            style="danger.TButton"
        )
        self.clear_btn = ttk.Button(
            self,
            text="Clear",
            command=self.clear_form,
            style="secondary.TButton"
        )

    def _create_layout(self):
        """Create form layout."""
        # Form fields
        self.name_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        self.desc_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.desc_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Buttons
        self.add_btn.grid(row=2, column=0, padx=5, pady=10)
        self.update_btn.grid(row=2, column=1, padx=5, pady=10)
        self.delete_btn.grid(row=2, column=2, padx=5, pady=10)
        self.clear_btn.grid(row=2, column=3, padx=5, pady=10)

        # Configure grid
        self.columnconfigure(1, weight=1)

    def clear_form(self):
        """Clear form fields and selection."""
        self.name_var.set("")
        self.desc_var.set("")
        self.selected_id = None
        self.update_btn.configure(state="disabled")
        self.delete_btn.configure(state="disabled")
        self.add_btn.configure(state="normal")

    def add_capability(self):
        """Add a new capability."""
        name = self.name_var.get().strip()
        if not name:
            return

        # Get selected item as parent
        selected = self.tree.selection()
        parent_id = int(selected[0]) if selected else None

        # Create capability
        capability = CapabilityCreate(
            name=name,
            description=self.desc_var.get().strip(),
            parent_id=parent_id
        )
        self.db_ops.create_capability(capability)
        
        # Refresh tree and clear form
        self.tree.refresh_tree()
        self.clear_form()

    def update_capability(self):
        """Update selected capability."""
        if not self.selected_id:
            return

        name = self.name_var.get().strip()
        if not name:
            return

        # Update capability
        capability = CapabilityUpdate(
            name=name,
            description=self.desc_var.get().strip()
        )
        self.db_ops.update_capability(self.selected_id, capability)
        
        # Refresh tree and clear form
        self.tree.refresh_tree()
        self.clear_form()

    def delete_capability(self):
        """Delete selected capability."""
        if not self.selected_id:
            return

        # Confirm deletion
        dialog = MessageDialog(
            title="Delete Capability",
            message="Are you sure you want to delete this capability and all its children?",
            buttons=["Yes", "No"],
        )
        if dialog.show() == "Yes":
            self.db_ops.delete_capability(self.selected_id)
            self.tree.refresh_tree()
            self.clear_form()

    def load_capability(self, event=None):
        """Load selected capability into form."""
        selected = self.tree.selection()
        if not selected:
            self.clear_form()
            return

        capability_id = int(selected[0])
        capability = self.db_ops.get_capability(capability_id)
        if capability:
            self.selected_id = capability_id
            self.name_var.set(capability.name)
            self.desc_var.set(capability.description or "")
            self.update_btn.configure(state="normal")
            self.delete_btn.configure(state="normal")

class App:
    def __init__(self):
        self.root = ttk.Window(
            title="Business Capability Modeler",
            themename="litera",
            size=(800, 600)
        )
        self.root.position_center()

        # Initialize database
        init_db()
        self.db = next(get_db())
        self.db_ops = DatabaseOperations(self.db)

        self._create_widgets()
        self._create_layout()
        self._bind_events()

    def _create_widgets(self):
        """Create main application widgets."""
        # Create main container
        self.main_container = ttk.Frame(self.root, padding=10)

        # Create treeview
        self.tree = CapabilityTreeview(
            self.main_container,
            self.db_ops,
            show="tree headings",
            selectmode="browse"
        )

        # Create scrollbar for treeview
        self.tree_scroll = ttk.Scrollbar(
            self.main_container,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.tree_scroll.set)

        # Create form
        self.form = CapabilityForm(self.main_container, self.db_ops, self.tree)

    def _create_layout(self):
        """Create main application layout."""
        self.main_container.pack(fill="both", expand=True)

        # Layout treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.tree_scroll.grid(row=0, column=1, sticky="ns")

        # Layout form
        self.form.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # Configure grid
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(0, weight=1)

    def _bind_events(self):
        """Bind application events."""
        self.tree.bind("<<TreeviewSelect>>", self.form.load_capability)

    def run(self):
        """Run the application."""
        self.root.mainloop()

def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
