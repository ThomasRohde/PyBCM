import asyncio
import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip

from .dialogs import create_dialog
from .treeview import CapabilityTreeview

class BusinessCapabilityUI:
    def __init__(self, app):
        self.app = app  # Reference to main App instance
        self.settings = app.settings
        self.root = app.root
        self.db_ops = app.db_ops
        
        self._create_menu()
        self._create_toolbar()
        self._create_widgets()
        self._create_layout()

    def _create_menu(self):
        """Create application menu bar."""
        self.menubar = ttk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        self.file_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Import...", command=self.app._import_capabilities)
        self.file_menu.add_command(label="Export...", command=self.app._export_capabilities)
        self.file_menu.add_command(label="Export to SVG...", command=self.app._export_to_svg)
        self.file_menu.add_command(label="Export to PowerPoint...", command=self.app._export_to_pptx)
        self.file_menu.add_command(label="Export to Archimate...", command=self.app._export_to_archimate)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="View Audit Logs", command=self.app._view_audit_logs)
        self.file_menu.add_command(label="Export Audit Logs...", command=self.app._export_audit_logs)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Settings", command=self.app._show_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.app._on_closing)

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
            command=self.app._expand_capability
        )

    def _create_toolbar(self):
        """Create toolbar with expand/collapse buttons."""
        self.toolbar = ttk.Frame(self.root)
        
        # Add expand capability button
        self.expand_cap_btn = ttk.Button(
            self.toolbar,
            text="✨",  # Sparkles emoji for AI expansion
            command=self.app._expand_capability,
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
            command=self.app._show_visualizer,
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
            command=self.app._show_chat,
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
        ToolTip(self.expand_btn, text="Expand All")
        
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
        ToolTip(self.collapse_btn, text="Collapse All")

        # Add search entry to toolbar
        self.search_var = ttk.StringVar()
        self.search_entry = ttk.Entry(
            self.toolbar,
            textvariable=self.search_var,
            width=30
        )
        self.search_entry.bind('<Return>', self._on_search)
        ToolTip(self.search_entry, text="Search capabilities (press Enter)")

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
        style.configure(
            f"font{font_size}.Treeview.Item",
            font=("TkDefaultFont", font_size)
        )
        self.tree = CapabilityTreeview(
            self.left_panel,
            self.db_ops,
            show="tree",
            selectmode="browse",
            style=f"font{font_size}.Treeview"
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
        
        # Create text widget with current font size
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

    def update_font_sizes(self):
        """Update font sizes for UI elements based on current settings."""
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

    def _create_layout(self):
        """Create main application layout."""
        # Layout toolbar
        self.toolbar.pack(fill="x", padx=10, pady=(5, 0))
        
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

    def _on_text_modified(self, event):
        """Handle text modifications."""
        if self.desc_text.edit_modified():
            current_text = self.desc_text.get('1.0', 'end-1c')
            self.save_desc_btn.configure(
                state="normal" if current_text != self.app.current_description else "disabled"
            )
            self.desc_text.edit_modified(False)

    def _on_tree_select(self, event):
        """Handle tree selection event."""
        selected = self.tree.selection()
        if not selected:
            self.desc_text.delete('1.0', 'end')
            self.save_desc_btn.configure(state="disabled")
            self.app.current_description = ""
            return

        capability_id = int(selected[0])
        
        async def get_capability_async():
            capability = await self.db_ops.get_capability(capability_id)
            if capability:
                self.app.current_description = capability.description or ""
                self.desc_text.delete('1.0', 'end')
                self.desc_text.insert('1.0', self.app.current_description)
                self.desc_text.edit_modified(False)
                self.save_desc_btn.configure(state="disabled")
        
        # Run the coroutine in the event loop
        asyncio.run_coroutine_threadsafe(
            get_capability_async(),
            self.app.loop
        )

    def _save_description(self):
        """Save the current description to the database."""
        selected = self.tree.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        description = self.desc_text.get('1.0', 'end-1c')
        
        async def update_description():
            async with await self.db_ops._get_session() as session:
                try:
                    success = await self.app._save_description_async(capability_id, description, session)
                    if success:
                        await session.commit()
                        return True
                    return False
                except Exception as e:
                    await session.rollback()
                    raise e
        
        # Run the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(
            update_description(),
            self.app.loop
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

    def _clear_search(self):
        """Clear the search entry and restore the full tree."""
        selected_id = None
        selected = self.tree.selection()
        if selected:
            selected_id = selected[0]

        self.search_var.set("")
        self.clear_search_btn.configure(state="disabled")

        # Show loading indicator
        self.tree.configure(cursor="watch")
        self.search_entry.configure(state="disabled")
        
        async def load_tree_async():
            try:
                # Get all capabilities in chunks
                opened_items = {item for item in self.tree.get_children() 
                              if self.tree.item(item, 'open')}
                
                # Clear current tree
                for item in self.tree.get_children():
                    self.tree.delete(item)
                    
                # Load root nodes first
                roots = await self.db_ops.get_capabilities(None)
                for root in roots:
                    item_id = str(root.id)
                    self.tree.insert(
                        "",
                        "end",
                        iid=item_id,
                        text=root.name,
                        open=item_id in opened_items
                    )
                
                async def load_children(parent_id, parent_item):
                    children = await self.db_ops.get_capabilities(parent_id)
                    for child in children:
                        child_id = str(child.id)
                        self.tree.insert(
                            parent_item,
                            "end",
                            iid=child_id,
                            text=child.name,
                            open=child_id in opened_items
                        )
                        await load_children(child.id, child_id)
                
                for root in roots:
                    await load_children(root.id, str(root.id))
                
                if selected_id:
                    try:
                        self.tree.selection_set(selected_id)
                        self.tree.see(selected_id)
                        self._on_tree_select(None)
                    except:
                        pass
                
            finally:
                self.root.after(0, lambda: [
                    self.tree.configure(cursor=""),
                    self.search_entry.configure(state="normal"),
                    self.app.loading_complete.set()
                ])

        self.app.loading_complete.clear()
        
        asyncio.run_coroutine_threadsafe(
            load_tree_async(),
            self.app.loop
        )

    def _on_search(self, *args):
        """Handle search when Enter is pressed."""
        search_text = self.search_var.get().strip()
        self.clear_search_btn.configure(state="normal" if search_text else "disabled")
        
        if not search_text:
            self.tree.refresh_tree()
            return
            
        async def search_async():
            selected_id = None
            selected = self.tree.selection()
            if selected:
                selected_id = selected[0]
                
            results = await self.db_ops.search_capabilities(search_text)
            
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            for cap in results:
                self.tree.insert(
                    parent="",
                    index="end",
                    iid=str(cap.id),
                    text=cap.name,
                    open=True
                )
            
            if selected_id and any(str(cap.id) == selected_id for cap in results):
                self.tree.selection_set(selected_id)
                self.tree.see(selected_id)
                self._on_tree_select(None)
        
        asyncio.run_coroutine_threadsafe(
            search_async(),
            self.app.loop
        )
