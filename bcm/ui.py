import asyncio
import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip
from tkhtmlview import HTMLScrolledText
import markdown

from bcm.dialogs import create_dialog
from bcm.treeview import CapabilityTreeview


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
        self.file_menu.add_command(
            label="Import...", command=self.app._import_capabilities
        )
        self.file_menu.add_command(
            label="Export...", command=self.app._export_capabilities
        )
        self.file_menu.add_command(
            label="Export to SVG...", command=self.app._export_to_svg
        )
        self.file_menu.add_command(
            label="Export to HTML...", command=self.app._export_to_html
        )
        self.file_menu.add_command(
            label="Export to PowerPoint...", command=self.app._export_to_pptx
        )
        self.file_menu.add_command(
            label="Export to Archimate...", command=self.app._export_to_archimate
        )
        self.file_menu.add_command(
            label="Export to Markdown...", command=self.app._export_to_markdown
        )
        self.file_menu.add_command(
            label="Export to Word...", command=self.app._export_to_word
        )
        self.file_menu.add_command(
            label="Export to Mermaid...", command=self.app._export_to_mermaid
        )
        self.file_menu.add_command(
            label="Export to PlantUML...", command=self.app._export_to_plantuml
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="View Audit Logs", command=self.app._view_audit_logs
        )
        self.file_menu.add_command(
            label="Export Audit Logs...", command=self.app._export_audit_logs
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Settings", command=self.app._show_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.app._on_closing)

        # Edit menu
        self.edit_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(
            label="New", command=lambda: self.tree.new_capability()
        )
        self.edit_menu.add_command(
            label="Edit", command=lambda: self.tree.edit_capability()
        )
        self.edit_menu.add_command(label="Expand", command=self.app._expand_capability)

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
            padding=3,
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
            padding=3,
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
            padding=3,
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
            padding=3,
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
            padding=3,
        )
        ToolTip(self.collapse_btn, text="Collapse All")

        # Add search entry to toolbar
        self.search_var = ttk.StringVar()
        self.search_entry = ttk.Entry(
            self.toolbar, textvariable=self.search_var, width=30
        )
        self.search_entry.bind("<Return>", self._on_search)
        ToolTip(self.search_entry, text="Search capabilities (press Enter)")

        # Add clear search button
        self.clear_search_btn = ttk.Button(
            self.toolbar,
            text="✕",
            command=self._clear_search,
            style="info-outline.TButton",
            width=3,
            bootstyle="info-outline",
            padding=3,
        )
        ToolTip(self.clear_search_btn, text="Clear search")
        self.clear_search_btn.configure(state="disabled")

        # Add edit/save buttons to toolbar
        self.edit_desc_btn = ttk.Button(
            self.toolbar,
            text="Edit",
            command=self._toggle_edit_mode,
            style="info-outline.TButton",
            padding=3,
        )
        ToolTip(self.edit_desc_btn, text="Edit description markdown")

        self.save_desc_btn = ttk.Button(
            self.toolbar,
            text="Save",
            command=self._save_description,
            style="primary.TButton",
            state="disabled",
            padding=3,
        )
        ToolTip(self.save_desc_btn, text="Save description")

        self.expand_btn.pack(side="left", padx=2)
        self.collapse_btn.pack(side="left", padx=2)
        self.expand_cap_btn.pack(side="left", padx=2)
        self.visualize_btn.pack(side="left", padx=2)
        self.chat_btn.pack(side="left", padx=2)
        ttk.Label(self.toolbar, text="Search:").pack(side="left", padx=(10, 2))
        self.search_entry.pack(side="left", padx=2)
        self.clear_search_btn.pack(side="left", padx=2)
        self.edit_desc_btn.pack(side="right", padx=2)
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
        style.configure(f"font{font_size}.Treeview", font=("TkDefaultFont", font_size))
        style.configure(
            f"font{font_size}.Treeview.Item", font=("TkDefaultFont", font_size)
        )
        self.tree = CapabilityTreeview(
            self.left_panel,
            self.db_ops,
            show="tree",
            selectmode="browse",
            style=f"font{font_size}.Treeview",
        )

        self.tree_scroll = ttk.Scrollbar(
            self.left_panel, orient="vertical", command=self.tree.yview
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

        # Create HTML viewer for markdown rendering
        self.desc_viewer = HTMLScrolledText(
            self.right_panel, width=40, height=20, font=("TkDefaultFont", font_size)
        )
        # Get colors from current theme
        style = ttk.Style()
        bg_color = style.lookup("TFrame", "background")

        # Configure HTMLScrolledText
        self.desc_viewer.configure(
            state="disabled",  # Disable editing
            background=bg_color,
        )
        # Create text widget for editing
        self.desc_text = ttk.Text(
            self.right_panel,
            wrap="word",
            width=40,
            height=20,
            font=("TkDefaultFont", font_size),
        )

        # Initially show viewer
        self.editing_mode = False
        self.desc_viewer.pack(fill="both", expand=True)

        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.desc_text.bind("<<Modified>>", self._on_text_modified)
        
        # Bind treeview-specific copy/paste
        self.tree.bind("<Control-c>", self.app._export_to_clipboard)
        self.tree.bind("<Control-v>", self.app._paste_capability)
        self.tree.bind("<Control-m>", self.app._copy_to_mermaid)  # Add Mermaid copy shortcut
        self.tree.bind("<Control-d>", self.app._copy_to_plantuml)  # Add PlantUML copy shortcut

    def update_font_sizes(self):
        """Update font sizes for UI elements based on current settings."""
        font_size = self.settings.get("font_size")

        # Update treeview font
        style = ttk.Style()
        style.configure(f"font{font_size}.Treeview", font=("TkDefaultFont", font_size))
        style.configure(
            f"font{font_size}.Treeview.Item", font=("TkDefaultFont", font_size)
        )
        self.tree.configure(style=f"font{font_size}.Treeview")

        # Update row height for the new font size through the style
        height = self.tree._calculate_row_height(f"font{font_size}.Treeview")
        style.configure(f"font{font_size}.Treeview", rowheight=height)

        # Update description text font
        self.desc_text.configure(font=("TkDefaultFont", font_size))

        # Update HTML viewer font
        self.desc_viewer.configure(font=("TkDefaultFont", font_size))

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
        # Initially show viewer (edit mode text widget is handled by toggle)
        self.desc_viewer.pack(fill="both", expand=True)

        # Add panels to PanedWindow
        self.main_container.add(self.left_panel, weight=1)
        self.main_container.add(self.right_panel, weight=1)

        # Initially hide tree scrollbar if not needed
        if self.tree.yview() == (0.0, 1.0):
            self.tree_scroll.grid_remove()

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

    def _toggle_edit_mode(self):
        """Toggle between edit and view modes."""
        self.editing_mode = not self.editing_mode

        if self.editing_mode:
            # Switch to edit mode
            self.desc_viewer.pack_forget()
            self.desc_text.pack(fill="both", expand=True)
            self.desc_text.delete("1.0", "end")
            self.desc_text.insert("1.0", self.app.current_description)
            self.edit_desc_btn.configure(text="View")
        else:
            # Switch to view mode
            self.desc_text.pack_forget()
            self.desc_viewer.pack(fill="both", expand=True)
            style = ttk.Style()
            bg_color = style.lookup("TFrame", "background")
            fg_color = style.lookup("TFrame", "foreground")
            font_size = self.settings.get("font_size")
            markdown_html = f'<div style="color: {fg_color}; background-color: {bg_color}; font-family: TkDefaultFont; font-size: {font_size}px; margin: 0; padding: 0;">{markdown.markdown(self.desc_text.get("1.0", "end-1c"))}</div>'
            self.desc_viewer.set_html(markdown_html)
            self.edit_desc_btn.configure(text="Edit")

    def _on_text_modified(self, event):
        """Handle text modifications."""
        if self.desc_text.edit_modified():
            current_text = self.desc_text.get("1.0", "end-1c")
            self.save_desc_btn.configure(
                state="normal"
                if current_text != self.app.current_description
                else "disabled"
            )
            self.desc_text.edit_modified(False)

    def _on_tree_select(self, event):
        """Handle tree selection event."""
        selected = self.tree.selection()
        if not selected:
            self.desc_text.delete("1.0", "end")
            self.desc_viewer.set_html("")
            self.save_desc_btn.configure(state="disabled")
            self.app.current_description = ""
            return

        capability_id = int(selected[0])

        async def get_capability_async():
            capability = await self.db_ops.get_capability(capability_id)
            if capability:
                self.app.current_description = capability.description or ""
                if self.editing_mode:
                    self.desc_text.delete("1.0", "end")
                    self.desc_text.insert("1.0", self.app.current_description)
                    self.desc_text.edit_modified(False)
                else:
                    style = ttk.Style()
                    bg_color = style.lookup("TFrame", "background")
                    fg_color = style.lookup("TFrame", "foreground")
                    font_size = self.settings.get("font_size")
                    markdown_html = f'<div style="color: {fg_color}; background-color: {bg_color}; font-family: TkDefaultFont; font-size: {font_size}px; margin: 0; padding: 0;">{markdown.markdown(self.app.current_description)}</div>'
                    self.desc_viewer.set_html(markdown_html)
                self.save_desc_btn.configure(state="disabled")

        # Run the coroutine in the event loop
        asyncio.run_coroutine_threadsafe(get_capability_async(), self.app.loop)

    def _save_description(self):
        """Save the current description to the database."""
        selected = self.tree.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        description = self.desc_text.get("1.0", "end-1c")

        async def save():
            return await self.app.db_ops.save_description(capability_id, description)

        def on_save_complete(future):
            try:
                success = future.result()
                if success:
                    self.app.current_description = description
                    self.root.after(0, lambda: [
                        create_dialog(
                            self.root, "Success", "Description saved successfully", ok_only=True
                        ),
                        self._toggle_edit_mode() if self.editing_mode else None
                    ])
                else:
                    self.root.after(0, lambda: create_dialog(
                        self.root,
                        "Error",
                        "Failed to save description - capability not found",
                        ok_only=True,
                    ))
            except Exception:
                self.root.after(0, lambda: create_dialog(
                    self.root,
                    "Error",
                    f"Failed to save description: {str(future.exception())}",
                    ok_only=True,
                ))
            finally:
                # Re-enable UI elements
                self.root.after(0, lambda: [
                    self.edit_desc_btn.configure(state="normal"),
                    self.save_desc_btn.configure(state="normal"),
                    self.desc_text.configure(state="normal")
                ])

        # Disable UI elements during save
        self.edit_desc_btn.configure(state="disabled")
        self.save_desc_btn.configure(state="disabled") 
        self.desc_text.configure(state="disabled")

        # Run the coroutine in the event loop with callback
        future = asyncio.run_coroutine_threadsafe(save(), self.app.loop)
        future.add_done_callback(on_save_complete)

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
                opened_items = {
                    item
                    for item in self.tree.get_children()
                    if self.tree.item(item, "open")
                }

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
                        open=item_id in opened_items,
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
                            open=child_id in opened_items,
                        )
                        await load_children(child.id, child_id)

                for root in roots:
                    await load_children(root.id, str(root.id))

                if selected_id:
                    try:
                        self.tree.selection_set(selected_id)
                        self.tree.see(selected_id)
                        self._on_tree_select(None)
                    except Exception:
                        pass

            finally:
                self.root.after(
                    0,
                    lambda: [
                        self.tree.configure(cursor=""),
                        self.search_entry.configure(state="normal"),
                        self.app.loading_complete.set(),
                    ],
                )

        self.app.loading_complete.clear()

        asyncio.run_coroutine_threadsafe(load_tree_async(), self.app.loop)

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
                    parent="", index="end", iid=str(cap.id), text=cap.name, open=True
                )

            if selected_id and any(str(cap.id) == selected_id for cap in results):
                self.tree.selection_set(selected_id)
                self.tree.see(selected_id)
                self._on_tree_select(None)

        asyncio.run_coroutine_threadsafe(search_async(), self.app.loop)
