import asyncio
import threading
from typing import Dict, Optional
from datetime import datetime
import json
import os
from pathlib import Path
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip

from .models import init_db, get_db, CapabilityCreate, CapabilityUpdate, AsyncSessionLocal
from .database import DatabaseOperations
from .dialogs import create_dialog, CapabilityConfirmDialog
from .treeview import CapabilityTreeview
from .settings import Settings, SettingsDialog
async def anext(iterator):
    """Helper function for async iteration compatibility."""
    return await iterator.__anext__()

import logfire

logfire.configure()
logfire.instrument_openai()
class App:

    def __init__(self):
        # Add async event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Load settings
        self.settings = Settings()
        
        self.root = ttk.Window(
            title="Business Capability Modeler",
            themename=self.settings.get("theme")
        )
        
        # Get screen dimensions and calculate 50% size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.5)
        window_height = int(screen_height * 0.5)
        
        # Set window size
        self.root.geometry(f"{window_width}x{window_height}")
        
        self.root.withdraw()  # Hide window temporarily
        self.root.iconbitmap("./bcm/business_capability_model.ico")
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Initialize database asynchronously
        self.loop.run_until_complete(init_db())
        self.db = self.loop.run_until_complete(anext(get_db()))
        self.db_ops = DatabaseOperations(AsyncSessionLocal)

        self.current_description = ""  # Add this to track changes

        self._create_menu()
        self._create_toolbar()  # Add this line
        self._create_widgets()
        self._create_layout()
        
        self.root.position_center()  # Position window while it's hidden
        self.root.deiconify()  # Show window in final position

    def _create_menu(self):
        """Create application menu bar."""
        self.menubar = ttk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        self.file_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Import...", command=self._import_capabilities)
        self.file_menu.add_command(label="Export...", command=self._export_capabilities)
        # self.file_menu.add_command(label="Export to HTML...", command=self._export_to_html)
        self.file_menu.add_command(label="Export to SVG...", command=self._export_to_svg)
        self.file_menu.add_command(label="Export to PowerPoint...", command=self._export_to_pptx)
        self.file_menu.add_command(label="Export to Archimate...", command=self._export_to_archimate)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Settings", command=self._show_settings)
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

        # Add visualize button
        self.visualize_btn = ttk.Button(
            self.toolbar,
            text="🗺️",  # Map emoji
            command=self._show_visualizer,
            style="info-outline.TButton",
            width=3,
            bootstyle="info-outline",
            padding=3
        )
        ToolTip(self.visualize_btn, text="Visualize Model")
        
        # Add chat button
        self.chat_btn = ttk.Button(
            self.toolbar,
            text="🤖",  # Chat emoji
            command=self._show_chat,
            style="info-outline.TButton",
            width=3,
            bootstyle="info-outline",
            padding=3
        )
        ToolTip(self.chat_btn, text="AI Chat")
        
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

        # Add search entry to toolbar
        self.search_var = ttk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        self.search_entry = ttk.Entry(
            self.toolbar,
            textvariable=self.search_var,
            width=30
        )
        ToolTip(self.search_entry, text="Search capabilities")

        # Add clear search button
        self.clear_search_btn = ttk.Button(
            self.toolbar,
            text="✕",
            command=self._clear_search,
            style="info-outline.TButton",
            width=3,
            bootstyle="info-outline",
            padding=3
        )
        ToolTip(self.clear_search_btn, text="Clear search")
        self.clear_search_btn.configure(state="disabled")

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
        self.visualize_btn.pack(side="left", padx=2)
        self.chat_btn.pack(side="left", padx=2)
        ttk.Label(self.toolbar, text="Search:").pack(side="left", padx=(10, 2))
        self.search_entry.pack(side="left", padx=2)
        self.clear_search_btn.pack(side="left", padx=2)
        self.save_desc_btn.pack(side="right", padx=2)

    def _clear_search(self):
        """Clear the search entry and restore the full tree."""
        self.search_var.set("")
        self.clear_search_btn.configure(state="disabled")
        self.tree.refresh_tree()

    def _on_search(self, *args):
        """Handle search input changes."""
        search_text = self.search_var.get().strip()
        self.clear_search_btn.configure(state="normal" if search_text else "disabled")
        
        if not search_text:
            self.tree.refresh_tree()
            return
            
        # Search capabilities
        results = self.db_ops.search_capabilities(search_text)
        
        # Clear current tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add search results
        for cap in results:
            self.tree.insert(
                parent="",
                index="end",
                iid=str(cap.id),
                text=cap.name,
                open=True
            )

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
        user_dir = os.path.expanduser('~')
        app_dir = os.path.join(user_dir, '.pybcm')
        os.makedirs(app_dir, exist_ok=True)
        filename = filedialog.askopenfilename(
            title="Import Capabilities",
            initialdir=app_dir,
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
                # Create coroutine for import operation
                async def import_async():
                    await self.db_ops.clear_all_capabilities()
                    await self.db_ops.import_capabilities(data)
            
                # Run the coroutine in the event loop
                future = asyncio.run_coroutine_threadsafe(
                    import_async(),
                    self.loop
                )
                future.result()  # Wait for completion
            
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

    def _convert_to_layout_format(self, node_data, level=0):
        """Convert a node and its children to the layout format using LayoutModel.
        
        Args:
            node_data: The node data to convert
            level: Current level relative to start node
        """
        from .models import LayoutModel
        
        # Only create children if we haven't reached max_level
        max_level = self.settings.get("max_level", 6)
        children = None
        if node_data["children"] and level < max_level:
            children = [self._convert_to_layout_format(child, level + 1) 
                       for child in node_data["children"]]
        
        return LayoutModel(
            name=node_data["name"],
            description=node_data.get("description", ""),
            children=children
        )

    def _export_to_archimate(self):
        """Export capabilities to Archimate Open Exchange format starting from selected node."""
        from .archimate_export import export_to_archimate
        
        # Get selected node or use root if none selected
        selected = self.tree.selection()
        if selected:
            start_node_id = int(selected[0])
        else:
            # Find root node - using async method properly
            async def get_root_node():
                capabilities = await self.db_ops.get_all_capabilities()
                root_nodes = [cap for cap in capabilities if not cap.get("parent_id")]
                if not root_nodes:
                    return None
                return root_nodes[0]["id"]
                
            # Run the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(
                get_root_node(),
                self.loop
            )
            start_node_id = future.result()  # Wait for completion
            
            if not start_node_id:
                return

        # Get hierarchical data starting from selected node
        async def get_node_data():
            return await self.db_ops.get_capability_with_children(start_node_id)
            
        # Run the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(
            get_node_data(),
            self.loop
        )
        node_data = future.result()  # Wait for completion
        
        # Convert to layout format starting from selected node
        layout_model = self._convert_to_layout_format(node_data)
        
        # Get save location from user
        user_dir = os.path.expanduser('~')
        app_dir = os.path.join(user_dir, '.pybcm')
        os.makedirs(app_dir, exist_ok=True)
        filename = filedialog.asksaveasfilename(
            title="Export to Archimate",
            initialdir=app_dir,
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Generate Archimate content
                archimate_content = export_to_archimate(layout_model, self.settings)
                
                # Write to file
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(archimate_content)
                
                create_dialog(
                    self.root,
                    "Success",
                    "Capabilities exported to Archimate format successfully",
                    ok_only=True
                )
                
            except Exception as e:
                create_dialog(
                    self.root,
                    "Error",
                    f"Failed to export capabilities to Archimate format: {str(e)}",
                    ok_only=True
                )

    def _export_to_pptx(self):
        """Export capabilities to PowerPoint visualization starting from selected node."""
        from .pptx_export import export_to_pptx
        
        # Get selected node or use root if none selected
        selected = self.tree.selection()
        if selected:
            start_node_id = int(selected[0])
        else:
            # Find root node - using async method properly
            async def get_root_node():
                capabilities = await self.db_ops.get_all_capabilities()
                root_nodes = [cap for cap in capabilities if not cap.get("parent_id")]
                if not root_nodes:
                    return None
                return root_nodes[0]["id"]
                
            # Run the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(
                get_root_node(),
                self.loop
            )
            start_node_id = future.result()  # Wait for completion
            
            if not start_node_id:
                return

        # Get hierarchical data starting from selected node
        async def get_node_data():
            return await self.db_ops.get_capability_with_children(start_node_id)
            
        # Run the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(
            get_node_data(),
            self.loop
        )
        node_data = future.result()  # Wait for completion
        
        # Convert to layout format starting from selected node
        layout_model = self._convert_to_layout_format(node_data)
        
        # Get save location from user
        user_dir = os.path.expanduser('~')
        app_dir = os.path.join(user_dir, '.pybcm')
        os.makedirs(app_dir, exist_ok=True)
        filename = filedialog.asksaveasfilename(
            title="Export to PowerPoint",
            initialdir=app_dir,
            defaultextension=".pptx",
            filetypes=[("PowerPoint files", "*.pptx"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Generate PowerPoint presentation
                prs = export_to_pptx(layout_model, self.settings)
                
                # Save presentation
                prs.save(filename)
                
                create_dialog(
                    self.root,
                    "Success",
                    "Capabilities exported to PowerPoint successfully",
                    ok_only=True
                )
                
            except Exception as e:
                create_dialog(
                    self.root,
                    "Error",
                    f"Failed to export capabilities to PowerPoint: {str(e)}",
                    ok_only=True
                )

    def _export_to_svg(self):
        """Export capabilities to SVG visualization starting from selected node."""
        from .svg_export import export_to_svg
        
        # Get selected node or use root if none selected
        selected = self.tree.selection()
        if selected:
            start_node_id = int(selected[0])
        else:
            # Find root node - using async method properly
            async def get_root_node():
                capabilities = await self.db_ops.get_all_capabilities()
                root_nodes = [cap for cap in capabilities if not cap.get("parent_id")]
                if not root_nodes:
                    return None
                return root_nodes[0]["id"]
                
            # Run the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(
                get_root_node(),
                self.loop
            )
            start_node_id = future.result()  # Wait for completion
            
            if not start_node_id:
                return

        # Get hierarchical data starting from selected node
        async def get_node_data():
            return await self.db_ops.get_capability_with_children(start_node_id)
            
        # Run the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(
            get_node_data(),
            self.loop
        )
        node_data = future.result()  # Wait for completion
        
        # Convert to layout format starting from selected node
        layout_model = self._convert_to_layout_format(node_data)
        
        # Get save location from user
        user_dir = os.path.expanduser('~')
        app_dir = os.path.join(user_dir, '.pybcm')
        os.makedirs(app_dir, exist_ok=True)
        filename = filedialog.asksaveasfilename(
            title="Export to SVG",
            initialdir=app_dir,
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Generate SVG content
                svg_content = export_to_svg(layout_model, self.settings)
                
                # Write to file
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                create_dialog(
                    self.root,
                    "Success",
                    "Capabilities exported to SVG successfully",
                    ok_only=True
                )
                
            except Exception as e:
                create_dialog(
                    self.root,
                    "Error",
                    f"Failed to export capabilities to SVG: {str(e)}",
                    ok_only=True
                )
    
    def _export_capabilities(self):
        """Export capabilities to JSON file."""
        user_dir = os.path.expanduser('~')
        app_dir = os.path.join(user_dir, '.pybcm')
        os.makedirs(app_dir, exist_ok=True)
        filename = filedialog.asksaveasfilename(
            title="Export Capabilities",
            initialdir=app_dir,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return

        try:
            # Create coroutine for export operation
            async def export_async():
                data = await self.db_ops.export_capabilities()
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
            
            # Run the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(
                export_async(),
                self.loop
            )
            future.result()  # Wait for completion
            
            create_dialog(
                self.root,
                "Success",
                "Capabilities exported successfully",
                ok_only=True
            )
            
        except Exception as e:
            create_dialog(
                self.root,
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
        
        # Create treeview with current font size
        font_size = self.settings.get("font_size")
        style = ttk.Style()
        style.configure(
            f"font{font_size}.Treeview",
            font=("TkDefaultFont", font_size)
        )
        # Configure the item text style as well
        style.configure(
            f"font{font_size}.Treeview.Item",
            font=("TkDefaultFont", font_size)
        )
        self.tree = CapabilityTreeview(
            self.left_panel,
            self.db_ops,
            show="tree",
            selectmode="browse",
            style=f"font{font_size}.Treeview"  # Custom style for font size
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
        # Create text widget with current font size
        font_size = self.settings.get("font_size")
        self.desc_text = ttk.Text(
            self.right_panel,
            wrap="word",
            width=40,
            height=20,
            font=("TkDefaultFont", font_size)
        )
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
        
        # Create coroutine for getting capability
        async def get_capability_async():
            capability = await self.db_ops.get_capability(capability_id)
            if capability:
                self.current_description = capability.description or ""
                self.desc_text.delete('1.0', 'end')
                self.desc_text.insert('1.0', self.current_description)
                self.desc_text.edit_modified(False)
                self.save_desc_btn.configure(state="disabled")
        
        # Run the coroutine in the event loop
        asyncio.run_coroutine_threadsafe(
            get_capability_async(),
            self.loop
        )

    def _save_description(self):
        """Save the current description to the database."""
        selected = self.tree.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        description = self.desc_text.get('1.0', 'end-1c')
        
        # Create async function to get and update capability
        async def update_description():
            # Get current capability
            capability = await self.db_ops.get_capability(capability_id)
            if not capability:
                return False
                
            # Create update data
            update_data = CapabilityUpdate(
                name=capability.name,
                description=description
            )
            
            # Update capability
            await self.db_ops.update_capability(capability_id, update_data)
            return True
        
        # Run the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(
            update_description(),
            self.loop
        )
        
        success = future.result()  # Wait for completion
        
        if success:
            create_dialog(
                self.root,
                "Success",
                "Description saved successfully",
                ok_only=True
            )
        else:
            create_dialog(
                self.root,
                "Error", 
                "Failed to save description - capability not found",
                ok_only=True
            )

    def _show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self.root, self.settings)
        self.root.wait_window(dialog)
        if (dialog.result):
            # Update font sizes immediately
            font_size = self.settings.get("font_size")
            
            # Update treeview font
            style = ttk.Style()
            style.configure(
                f"font{font_size}.Treeview",
                font=("TkDefaultFont", font_size)
            )
            style.configure(
                f"font{font_size}.Treeview.Item",
                font=("TkDefaultFont", font_size)
            )
            self.tree.configure(style=f"font{font_size}.Treeview")
            # Update row height for the new font size through the style
            height = self.tree._calculate_row_height(f"font{font_size}.Treeview")
            style.configure(f"font{font_size}.Treeview", rowheight=height)
            
            # Update description text font
            self.desc_text.configure(font=("TkDefaultFont", font_size))
            
            create_dialog(
                self.root,
                "Settings Saved",
                "Settings have been saved and applied.",
                ok_only=True
            )

    async def _expand_capability_async(self, context: str, capability_name: str) -> Dict[str, str]:
        """Use PydanticAI to expand a capability into sub-capabilities with descriptions."""
        from .utils import expand_capability_ai, generate_first_level_capabilities
        selected = self.tree.selection()
        capability_id = int(selected[0])
        capability = await self.db_ops.get_capability(capability_id)

        # Check if this is a root capability (no parent) AND has no children
        if not capability.parent_id and not self.tree.get_children(capability_id):
            # Use the capability's actual name and description for first-level generation
            return await generate_first_level_capabilities(
                capability.name,
                capability.description or f"An organization focused on {capability.name}"
            )
        
        # For non-root capabilities or those with existing children, use regular expansion
        return await expand_capability_ai(context, capability_name, self.settings.get("max_ai_capabilities"))

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
        
        progress = ProgressWindow(self.root)
        try:
            # Get context and expand capability
            async def expand():
                from .utils import get_capability_context
                capability = await self.db_ops.get_capability(capability_id)
                if not capability:
                    return None
                    
                context = await get_capability_context(self.db_ops, capability_id)
                return await self._expand_capability_async(context, capability.name)

            subcapabilities = asyncio.run(progress.run_with_progress(expand()))
            
            if subcapabilities:

                # Show confirmation dialog with checkboxes
                dialog = CapabilityConfirmDialog(self.root, subcapabilities)
                self.root.wait_window(dialog)
                
                # If user clicked OK and selected some capabilities
                if dialog.result:
                    # Create selected sub-capabilities with descriptions
                    async def create_subcapabilities():
                        for name, description in dialog.result.items():
                            await self.db_ops.create_capability(CapabilityCreate(
                                name=name,
                                description=description,
                                parent_id=capability_id
                            ))
                    
                    # Run creation in event loop
                    future = asyncio.run_coroutine_threadsafe(
                        create_subcapabilities(),
                        self.loop
                    )
                    future.result()  # Wait for completion
                    self.tree.refresh_tree()
                
        except Exception as e:
            create_dialog(
                self.root,
                "Error",
                f"Failed to expand capability: {str(e)}",
                ok_only=True
            )

    def _show_chat(self):
        """Show the AI chat dialog."""
        import threading
        import webbrowser
        from .web_agent import start_server
        import asyncio
        import sys
        
        def run_server():
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            start_server()
        
        # Start the FastAPI server in a background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Give the server a moment to start
        import time
        time.sleep(1)
        
        # Launch web browser to chat interface
        webbrowser.open('http://127.0.0.1:8000')
        
    def _show_visualizer(self):
        """Show the capability model visualizer starting from selected node."""
        from .visualizer import CapabilityVisualizer
        
        # Get selected node or use root if none selected
        selected = self.tree.selection()
        if selected:
            start_node_id = int(selected[0])
        else:
            # Find root node - using async method properly
            async def get_root_node():
                capabilities = await self.db_ops.get_all_capabilities()
                root_nodes = [cap for cap in capabilities if not cap.get("parent_id")]
                if not root_nodes:
                    return None
                return root_nodes[0]["id"]
                
            # Run the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(
                get_root_node(),
                self.loop
            )
            start_node_id = future.result()  # Wait for completion
            
            if not start_node_id:
                return

        # Get hierarchical data starting from selected node
        async def get_node_data():
            return await self.db_ops.get_capability_with_children(start_node_id)
            
        # Run the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(
            get_node_data(),
            self.loop
        )
        node_data = future.result()  # Wait for completion
        
        # Convert to layout format starting from selected node
        layout_model = self._convert_to_layout_format(node_data)
        
        # Create and show visualizer window
        CapabilityVisualizer(self.root, layout_model)

    async def _on_closing_async(self):
        """Async cleanup operations."""
        try:
            if self.db:
                await self.db.close()
        except Exception as e:
            print(f"Error closing database: {e}")
        finally:
            # Signal the event loop to stop
            self.loop.call_soon_threadsafe(self.loop.stop)

    def _on_closing(self):
        """Handle application closing."""
        try:
            # Create a new task for closing and wait for it
            future = asyncio.run_coroutine_threadsafe(
                self._on_closing_async(),
                self.loop
            )
            # Wait for the closing task to complete with a timeout
            future.result(timeout=5)  # 5 second timeout
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            # Ensure the root is destroyed and app quits
            self.root.quit()
            self.root.destroy()

    def run(self):
        """Run the application with async support."""
        try:
            # Start the async event loop in a separate thread
            def run_async_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()

            thread = threading.Thread(target=run_async_loop, daemon=True)
            thread.start()

            # Run the Tkinter main loop
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_closing()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self._on_closing()
        finally:
            # Ensure the loop is stopped and closed
            if not self.loop.is_closed():
                try:
                    # Stop the loop if it's still running
                    if self.loop.is_running():
                        self.loop.call_soon_threadsafe(self.loop.stop)
                    # Wait a moment for the loop to actually stop
                    import time
                    time.sleep(0.1)
                    # Now we can safely close it
                    self.loop.close()
                except Exception as e:
                    print(f"Error closing event loop: {e}")

def main():
    # Set up asyncio policy for Windows if needed
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    app = App()
    app.run()

if __name__ == "__main__":
    main()
