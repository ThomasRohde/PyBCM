import ttkbootstrap as ttk
from ttkbootstrap.constants import END
from ttkbootstrap.tooltip import ToolTip  # Add this import
from typing import Optional
from tkinter import filedialog
import json
from ttkbootstrap.constants import *  # Add this import at the top with other imports
from ttkbootstrap.icons import Emoji  # Add this import at the top with other imports

from .models import init_db, get_db, CapabilityCreate, CapabilityUpdate
from .database import DatabaseOperations

def create_dialog(
    parent,
    title: str,
    message: str,
    default_result: bool = False,
    ok_only: bool = False
) -> bool:
    """Create a generic dialog."""
    dialog = ttk.Toplevel(parent)
    dialog.withdraw()  # Hide the window initially
    dialog.title(title)
    dialog.geometry("500x150")  # Increased width from 300 to 500
    dialog.position_center()
    
    # Remove window controls
    dialog.resizable(False, False)
    dialog.overrideredirect(True)
    
    # Create border frame
    border_frame = ttk.Frame(dialog, borderwidth=1, relief="solid")
    border_frame.pack(fill="both", expand=True, padx=2, pady=2)
    
    # Create content frame
    frame = ttk.Frame(border_frame, padding=20)
    frame.pack(fill="both", expand=True)
    
    msg_label = ttk.Label(
        frame,
        text=message,
        justify="center",
        wraplength=400  # Set wrap length to accommodate text
    )
    msg_label.pack(expand=True)
    
    dialog.result = default_result
    
    if ok_only:
        ttk.Button(
            frame,
            text="OK",
            command=lambda: [setattr(dialog, 'result', True), dialog.destroy()],
            style="primary.TButton",
            width=10
        ).pack(pady=(0, 10))
    else:
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="Yes",
            command=lambda: [setattr(dialog, 'result', True), dialog.destroy()],
            style="danger.TButton",
            width=10
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="No",
            command=lambda: [setattr(dialog, 'result', False), dialog.destroy()],
            style="secondary.TButton",
            width=10
        ).pack(side="left", padx=5)
    
    dialog.deiconify()  # Show the window after positioning
    dialog.wait_window()
    return dialog.result

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

        if create_dialog(
            self,
            "Delete Capability",
            "Are you sure you want to delete this capability\nand all its children?"
        ):
            try:
                self.db_ops.delete_capability(capability_id)
                print(f"Capability {capability_id} deleted successfully")
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
            size=(1600, 1000)
        )
        
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Initialize database
        init_db()
        self.db = next(get_db())
        self.db_ops = DatabaseOperations(self.db)

        self.current_description = ""  # Add this to track changes

        self._create_menu()
        self._create_toolbar()  # Add this line
        self._create_widgets()
        self._create_layout()
        self.root.position_center()

    def _create_menu(self):
        """Create application menu bar."""
        self.menubar = ttk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        self.file_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Import...", command=self._import_capabilities)
        self.file_menu.add_command(label="Export...", command=self._export_capabilities)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self._on_closing)

        # Edit menu
        self.edit_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="New", command=lambda: self.tree.new_capability())
        self.edit_menu.add_command(
            label="Edit",
            command=lambda: self.tree.edit_capability()
        )

    def _create_toolbar(self):
        """Create toolbar with expand/collapse buttons."""
        self.toolbar = ttk.Frame(self.root)
        
        # Expand All button with icon
        self.expand_btn = ttk.Button(
            self.toolbar,
            text="⬇",  # Unicode down arrow
            command=self._expand_all,
            style="info-outline.TButton",
            width=3,
            bootstyle="info-outline",
            padding=3
        )
        ToolTip(self.expand_btn, text="Expand All")  # Fixed tooltip
        
        # Collapse All button with icon
        self.collapse_btn = ttk.Button(
            self.toolbar,
            text="⬆",  # Unicode up arrow
            command=self._collapse_all,
            style="info-outline.TButton",
            width=3,
            bootstyle="info-outline",
            padding=3
        )
        ToolTip(self.collapse_btn, text="Collapse All")  # Fixed tooltip

        # Add save button to toolbar
        self.save_desc_btn = ttk.Button(
            self.toolbar,
            text="Save Description",
            command=self._save_description,
            style="primary.TButton",
            state="disabled",
            padding=3
        )
        ToolTip(self.save_desc_btn, text="Save capability description")

    def _expand_all(self):
        """Expand all items in the tree."""
        def expand_recursive(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                expand_recursive(child)

        for item in self.tree.get_children():
            expand_recursive(item)

    def _collapse_all(self):
        """Collapse all items in the tree."""
        def collapse_recursive(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                collapse_recursive(child)

        for item in self.tree.get_children():
            collapse_recursive(item)

    def _import_capabilities(self):
        """Import capabilities from JSON file."""
        filename = filedialog.askopenfilename(
            title="Import Capabilities",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return

        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Confirm import
            if create_dialog(
                self.root,
                "Confirm Import",
                "This will replace all existing capabilities. Continue?"
            ):
                # Clear existing capabilities and import new ones
                self.db_ops.clear_all_capabilities()
                self.db_ops.import_capabilities(data)
                self.tree.refresh_tree()
                
                create_dialog(
                    self.root,
                    "Success",
                    "Capabilities imported successfully",
                    ok_only=True
                )
                
        except Exception as e:
            create_dialog(
                self.root,
                "Error",
                f"Failed to import capabilities: {str(e)}",
                ok_only=True
            )

    def _export_capabilities(self):
        """Export capabilities to JSON file."""
        filename = filedialog.asksaveasfilename(
            title="Export Capabilities",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return

        try:
            data = self.db_ops.export_capabilities()
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            create_dialog(
                self,
                "Success",
                "Capabilities exported successfully",
                ok_only=True
            )
            
        except Exception as e:
            create_dialog(
                self,
                "Error",
                f"Failed to export capabilities: {str(e)}",
                ok_only=True
            )

    def _create_widgets(self):
        """Create main application widgets."""
        # Create main paned window container
        self.main_container = ttk.PanedWindow(self.root, orient="horizontal")

        # Create left panel for tree
        self.left_panel = ttk.Frame(self.main_container)
        
        self.tree = CapabilityTreeview(
            self.left_panel,
            self.db_ops,
            show="tree",
            selectmode="browse"
        )

        self.tree_scroll = ttk.Scrollbar(
            self.left_panel,
            orient="vertical",
            command=self.tree.yview
        )
        
        def tree_scroll_handler(*args):
            if self.tree.yview() == (0.0, 1.0):
                self.tree_scroll.grid_remove()
            else:
                self.tree_scroll.grid()
            self.tree_scroll.set(*args)
        
        self.tree.configure(yscrollcommand=tree_scroll_handler)
        
        # Create right panel for description
        self.right_panel = ttk.Frame(self.main_container)
        
        # Create text widget with scrollbar
        self.desc_text = ttk.Text(self.right_panel, wrap="word", width=40, height=20)
        self.desc_scroll = ttk.Scrollbar(
            self.right_panel,
            orient="vertical",
            command=self.desc_text.yview
        )
        
        def desc_scroll_handler(*args):
            if self.desc_text.yview() == (0.0, 1.0):
                self.desc_scroll.pack_forget()
            else:
                self.desc_scroll.pack(side="right", fill="y")
            self.desc_scroll.set(*args)
        
        self.desc_text.configure(yscrollcommand=desc_scroll_handler)
        
        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.desc_text.bind('<<Modified>>', self._on_text_modified)

    def _create_layout(self):
        """Create main application layout."""
        # Layout toolbar
        self.toolbar.pack(fill="x", padx=10, pady=(5, 0))
        self.expand_btn.pack(side="left", padx=2)
        self.collapse_btn.pack(side="left", padx=2)
        self.save_desc_btn.pack(side="right", padx=2)
        
        # Layout main container
        self.main_container.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Layout left panel
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree_scroll.grid(row=0, column=1, sticky="ns")
        self.left_panel.columnconfigure(0, weight=1)
        self.left_panel.rowconfigure(0, weight=1)

        # Layout right panel
        self.desc_text.pack(side="left", fill="both", expand=True)
        self.desc_scroll.pack(side="right", fill="y")
        
        # Add panels to PanedWindow
        self.main_container.add(self.left_panel, weight=1)
        self.main_container.add(self.right_panel, weight=1)
        
        # Initially hide scrollbars
        if self.tree.yview() == (0.0, 1.0):
            self.tree_scroll.grid_remove()
        
        if self.desc_text.yview() == (0.0, 1.0):
            self.desc_scroll.pack_forget()

    def _on_text_modified(self, event):
        """Handle text modifications."""
        if self.desc_text.edit_modified():
            current_text = self.desc_text.get('1.0', 'end-1c')
            self.save_desc_btn.configure(
                state="normal" if current_text != self.current_description else "disabled"
            )
            self.desc_text.edit_modified(False)

    def _on_tree_select(self, event):
        """Handle tree selection event."""
        selected = self.tree.selection()
        if not selected:
            self.desc_text.delete('1.0', 'end')
            self.save_desc_btn.configure(state="disabled")
            self.current_description = ""
            return

        capability_id = int(selected[0])
        capability = self.db_ops.get_capability(capability_id)
        if capability:
            self.current_description = capability.description or ""
            self.desc_text.delete('1.0', 'end')
            self.desc_text.insert('1.0', self.current_description)
            self.desc_text.edit_modified(False)
            self.save_desc_btn.configure(state="disabled")

    def _save_description(self):
        """Save the current description to the database."""
        selected = self.tree.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        description = self.desc_text.get('1.0', 'end-1c')
        
        update_data = CapabilityUpdate(
            name=self.db_ops.get_capability(capability_id).name,
            description=description
        )
        
        self.db_ops.update_capability(capability_id, update_data)
        create_dialog(
            self,
            "Success",
            "Description saved successfully",
            ok_only=True
        )

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

