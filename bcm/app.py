import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip
from typing import Dict
from tkinter import filedialog
import json

from .models import init_db, get_db, CapabilityCreate, CapabilityUpdate
from .database import DatabaseOperations
from .dialogs import create_dialog, CapabilityConfirmDialog
from .treeview import CapabilityTreeview

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
        self.edit_menu.add_command(
            label="Expand",
            command=self._expand_capability
        )

    def _create_toolbar(self):
        """Create toolbar with expand/collapse buttons."""
        self.toolbar = ttk.Frame(self.root)
        
        # Add expand capability button
        self.expand_cap_btn = ttk.Button(
            self.toolbar,
            text="✨",  # Sparkles emoji for AI expansion
            command=self._expand_capability,
            style="info-outline.TButton",
            width=3,
            bootstyle="info-outline",
            padding=3
        )
        ToolTip(self.expand_cap_btn, text="AI Expand Capability")
        
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

        self.expand_btn.pack(side="left", padx=2)
        self.collapse_btn.pack(side="left", padx=2)
        self.expand_cap_btn.pack(side="left", padx=2)
        self.save_desc_btn.pack(side="right", padx=2)

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

    async def _expand_capability_async(self, context: str, capability_name: str) -> Dict[str, str]:
        """Use PydanticAI to expand a capability into sub-capabilities with descriptions."""
        from .utils import expand_capability_ai
        return await expand_capability_ai(context, capability_name)

    def _expand_capability(self):
        """Expand the selected capability using AI."""
        import asyncio
        from .pb import ProgressWindow
        
        selected = self.tree.selection()
        if not selected:
            create_dialog(
                self.root,
                "Error",
                "Please select a capability to expand",
                ok_only=True
            )
            return

        capability_id = int(selected[0])
        capability = self.db_ops.get_capability(capability_id)
        if not capability:
            return

        progress = ProgressWindow(self.root)
        try:
            # Get context
            from .utils import get_capability_context
            context = get_capability_context(self.db_ops, capability_id)
            
            # Run async expansion with progress
            async def expand():
                return await self._expand_capability_async(context, capability.name)

            subcapabilities = asyncio.run(progress.run_with_progress(expand()))

            # Show confirmation dialog with checkboxes
            dialog = CapabilityConfirmDialog(self.root, subcapabilities)
            self.root.wait_window(dialog)
            
            # If user clicked OK and selected some capabilities
            if dialog.result:
                # Create selected sub-capabilities with descriptions
                for name, description in dialog.result.items():
                    self.db_ops.create_capability(CapabilityCreate(
                        name=name,
                        description=description,
                        parent_id=capability_id
                    ))
                self.tree.refresh_tree()
                
        except Exception as e:
            create_dialog(
                self.root,
                "Error",
                f"Failed to expand capability: {str(e)}",
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
