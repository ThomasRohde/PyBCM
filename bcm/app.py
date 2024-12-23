import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import MessageDialog
from sqlalchemy.orm import Session
from typing import Optional

from .models import init_db, get_db, CapabilityCreate, CapabilityUpdate
from .database import DatabaseOperations

class CapabilityDialog(ttk.Toplevel):
    def __init__(self, parent, db_ops: DatabaseOperations, capability=None, parent_id=None):
        super().__init__(parent)
        self.db_ops = db_ops
        self.capability = capability
        self.parent_id = parent_id
        self.result = None

        self.title("Edit Capability" if capability else "New Capability")
        self.geometry("400x200")
        self.position_center()

        self._create_widgets()
        self._create_layout()

        if capability:
            self.name_var.set(capability.name)
            self.desc_var.set(capability.description or "")

    def _create_widgets(self):
        # Labels
        self.name_label = ttk.Label(self, text="Name:")
        self.desc_label = ttk.Label(self, text="Description:")
        
        # Entry fields
        self.name_var = ttk.StringVar()
        self.name_entry = ttk.Entry(self, textvariable=self.name_var)
        
        self.desc_var = ttk.StringVar()
        self.desc_entry = ttk.Entry(self, textvariable=self.desc_var)

        # Buttons
        self.ok_btn = ttk.Button(
            self,
            text="OK",
            command=self._on_ok,
            style="primary.TButton"
        )
        self.cancel_btn = ttk.Button(
            self,
            text="Cancel",
            command=self.destroy,
            style="secondary.TButton"
        )

    def _create_layout(self):
        self.name_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        self.desc_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.desc_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        self.ok_btn.grid(row=2, column=1, padx=5, pady=10)
        self.cancel_btn.grid(row=2, column=2, padx=5, pady=10)

        self.columnconfigure(1, weight=1)

    def _on_ok(self):
        name = self.name_var.get().strip()
        if not name:
            return

        if self.capability:
            self.result = CapabilityUpdate(
                name=name,
                description=self.desc_var.get().strip()
            )
        else:
            self.result = CapabilityCreate(
                name=name,
                description=self.desc_var.get().strip(),
                parent_id=self.parent_id
            )
        self.destroy()

class CapabilityTreeview(ttk.Treeview):
    def __init__(self, master, db_ops: DatabaseOperations, **kwargs):
        super().__init__(master, **kwargs)
        self.db_ops = db_ops
        self.drag_source: Optional[str] = None

        # Configure treeview
        self["columns"] = ("description",)
        self.heading("#0", text="Capability")
        self.heading("description", text="Description")
        self.column("#0", width=300)
        self.column("description", width=400)

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
        print(f"Attempting to delete capability ID: {capability_id}")
        
        # Create a regular Toplevel dialog instead of MessageDialog
        dialog = ttk.Toplevel(self)
        dialog.title("Delete Capability")
        dialog.geometry("300x150")
        dialog.position_center()
        
        # Message
        ttk.Label(
            dialog,
            text="Are you sure you want to delete this capability\nand all its children?",
            justify="center",
            padding=20
        ).pack()
        
        # Buttons frame
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def on_yes():
            dialog.result = True
            dialog.destroy()
            
        def on_no():
            dialog.result = False
            dialog.destroy()
            
        ttk.Button(
            btn_frame,
            text="Yes",
            command=on_yes,
            style="danger.TButton",
            width=10
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="No",
            command=on_no,
            style="secondary.TButton",
            width=10
        ).pack(side="left", padx=5)
        
        dialog.result = False
        dialog.wait_window()
        
        if dialog.result:
            try:
                self.db_ops.delete_capability(capability_id)
                print(f"Capability {capability_id} deleted successfully")
                self.refresh_tree()
            except Exception as e:
                print(f"Error deleting capability: {e}")
                MessageDialog(
                    title="Error",
                    message=f"Failed to delete capability: {str(e)}",
                    buttons=["OK"],
                ).show()

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

class App:

    def __init__(self):
        self.root = ttk.Window(
            title="Business Capability Modeler",
            themename="litera",
            size=(1200, 800)
        )
        
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Initialize database
        init_db()
        self.db = next(get_db())
        self.db_ops = DatabaseOperations(self.db)

        self._create_menu()
        self._create_widgets()
        self._create_layout()
        self.root.position_center()

    def _create_menu(self):
        """Create application menu bar."""
        self.menubar = ttk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # Edit menu
        self.edit_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="New", command=lambda: self.tree.new_capability())
        self.edit_menu.add_command(
            label="Edit",
            command=lambda: self.tree.edit_capability()
        )

    def _create_widgets(self):
        """Create main application widgets."""
        self.main_container = ttk.Frame(self.root, padding=10)

        self.tree = CapabilityTreeview(
            self.main_container,
            self.db_ops,
            show="tree headings",
            selectmode="browse"
        )

        self.tree_scroll = ttk.Scrollbar(
            self.main_container,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.tree_scroll.set)

    def _create_layout(self):
        """Create main application layout."""
        self.main_container.pack(fill="both", expand=True)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.tree_scroll.grid(row=0, column=1, sticky="ns")
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(0, weight=1)

    def _on_closing(self):
        """Handle application shutdown."""
        try:
            if self.db:
                self.db.close()
        except Exception as e:
            print(f"Error closing database: {e}")
        finally:
            self.root.destroy()

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_closing()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self._on_closing()

def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
