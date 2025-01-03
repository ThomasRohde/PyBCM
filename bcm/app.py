import asyncio
import json
import os
import threading
from tkinter import filedialog
from typing import Dict
import ttkbootstrap as ttk
from sqlalchemy import select

from .models import (
    init_db,
    get_db,
    CapabilityCreate,
    AsyncSessionLocal,
    Capability,
    LayoutModel
)
from .database import DatabaseOperations
from .dialogs import create_dialog, CapabilityConfirmDialog
from .settings import Settings, SettingsDialog
from .ui import BusinessCapabilityUI
from .utils import expand_capability_ai, generate_first_level_capabilities
from .pb import ProgressWindow
from .audit_view import AuditLogViewer
from .visualizer import CapabilityVisualizer

async def anext(iterator):
    """Helper function for async iteration compatibility."""
    return await iterator.__anext__()

class App:
    def __init__(self):
        # Add async event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Add shutdown event
        self.shutdown_event = asyncio.Event()
        
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
        self.loading_complete = threading.Event()  # Add this line after self.db_ops initialization

        # Initialize UI
        self.ui = BusinessCapabilityUI(self)
        
        self.root.position_center()  # Position window while it's hidden
        self.root.deiconify()  # Show window in final position

    def _convert_to_layout_format(self, node_data, level=0):
        """Convert a node and its children to the layout format using LayoutModel.
        
        Args:
            node_data: The node data to convert
            level: Current level relative to start node
        """
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

    def _export_capability_model(self, export_type, export_func, file_extension, file_type_name):
        """Base method for exporting capability model to different formats."""
        # Get selected node or use root if none selected
        selected = self.ui.tree.selection()
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
            title=f"Export to {export_type}",
            initialdir=app_dir,
            defaultextension=file_extension,
            filetypes=[(f"{file_type_name} files", f"*{file_extension}"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Generate content using provided export function
                content = export_func(layout_model, self.settings)
                
                # Handle different save methods
                if isinstance(content, str):
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    # Assume it's a PowerPoint presentation or similar object with save method
                    content.save(filename)
                
                create_dialog(
                    self.root,
                    "Success",
                    f"Capabilities exported to {export_type} format successfully",
                    ok_only=True
                )
                
            except Exception as e:
                create_dialog(
                    self.root,
                    "Error",
                    f"Failed to export capabilities to {export_type} format: {str(e)}",
                    ok_only=True
                )

    def _export_to_archimate(self):
        """Export capabilities to Archimate Open Exchange format starting from selected node."""
        from .archimate_export import export_to_archimate
        self._export_capability_model("Archimate", export_to_archimate, ".xml", "XML")

    def _export_to_pptx(self):
        """Export capabilities to PowerPoint visualization starting from selected node."""
        from .pptx_export import export_to_pptx
        self._export_capability_model("PowerPoint", export_to_pptx, ".pptx", "PowerPoint")

    def _export_to_svg(self):
        """Export capabilities to SVG visualization starting from selected node."""
        from .svg_export import export_to_svg
        self._export_capability_model("SVG", export_to_svg, ".svg", "SVG")
    
    def _export_capabilities(self):
        """Export capabilities to JSON file."""
        from .io import export_capabilities
        export_capabilities(self.root, self.db_ops, self.loop)

    def _import_capabilities(self):
        """Import capabilities from JSON file."""
        from .io import import_capabilities
        if import_capabilities(self.root, self.db_ops, self.loop):
            self.ui.tree.refresh_tree()

    async def _save_description_async(self, capability_id: int, description: str, session) -> bool:
        """Helper to save description and create audit log within a single session."""
        # Get current capability within this session
        stmt = select(Capability).where(Capability.id == capability_id)
        result = await session.execute(stmt)
        capability = result.scalar_one_or_none()
        
        if not capability:
            return False
            
        # Store old values for audit
        old_values = {
            "description": capability.description
        }
        
        # Update description
        capability.description = description
        
        # Add audit log
        await self.db_ops.log_audit(
            session,
            "UPDATE",
            capability_id=capability_id,
            capability_name=capability.name,
            old_values=old_values,
            new_values={"description": description}
        )
        
        return True

    def _save_description(self):
        """Save the current description to the database."""
        selected = self.ui.tree.selection()
        if not selected:
            return

        capability_id = int(selected[0])
        description = self.ui.desc_text.get('1.0', 'end-1c')
        
        # Create async function to update description
        async def update_description():
            async with await self.db_ops._get_session() as session:
                try:
                    success = await self._save_description_async(capability_id, description, session)
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
        if dialog.result:
            # Update UI with new settings
            self.ui.update_font_sizes()
            create_dialog(
                self.root,
                "Settings Saved",
                "Settings have been saved and applied.",
                ok_only=True
            )

    async def _expand_capability_async(self, context: str, capability_name: str) -> Dict[str, str]:
        """Use PydanticAI to expand a capability into sub-capabilities with descriptions."""
        selected = self.ui.tree.selection()
        capability_id = int(selected[0])
        capability = await self.db_ops.get_capability(capability_id)

        # Check if this is a root capability (no parent) AND has no children
        if not capability.parent_id and not self.ui.tree.get_children(capability_id):
            # Use the capability's actual name and description for first-level generation
            return await generate_first_level_capabilities(
                capability.name,
                capability.description or f"An organization focused on {capability.name}"
            )
        
        # For non-root capabilities or those with existing children, use regular expansion
        return await expand_capability_ai(context, capability_name, self.settings.get("max_ai_capabilities"))

    def _expand_capability(self):
        """Expand the selected capability using AI."""
        
        selected = self.ui.tree.selection()
        if not selected:
            create_dialog(
                self.root,
                "Error",
                "Please select a capability to expand",
                ok_only=True
            )
            return

        capability_id = int(selected[0])
        
        progress = None
        try:
            progress = ProgressWindow(self.root)
            
            # Get context and expand capability
            async def expand():
                from .utils import get_capability_context
                capability = await self.db_ops.get_capability(capability_id)
                if not capability:
                    return None
                    
                context = await get_capability_context(self.db_ops, capability_id)
                return await self._expand_capability_async(context, capability.name)

            # Run expansion with progress
            subcapabilities = progress.run_with_progress(expand())
            
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
                    
                    # Run creation with progress
                    progress.run_with_progress(create_subcapabilities())
                    self.ui.tree.refresh_tree()
            
        except Exception as e:
            create_dialog(
                self.root,
                "Error",
                f"Failed to expand capability: {str(e)}",
                ok_only=True
            )
        finally:
            if progress:
                progress.close()

    def _view_audit_logs(self):
        """Show the audit log viewer."""
        AuditLogViewer(self.root, self.db_ops)

    def _export_audit_logs(self):
        """Export audit logs to JSON file."""
        user_dir = os.path.expanduser('~')
        app_dir = os.path.join(user_dir, '.pybcm')
        os.makedirs(app_dir, exist_ok=True)
        filename = filedialog.asksaveasfilename(
            title="Export Audit Logs",
            initialdir=app_dir,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return

        try:
            # Create coroutine for export operation
            async def export_async():
                logs = await self.db_ops.export_audit_logs()
                with open(filename, 'w') as f:
                    json.dump(logs, f, indent=2)
            
            # Run the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(
                export_async(),
                self.loop
            )
            future.result()  # Wait for completion
            
            create_dialog(
                self.root,
                "Success",
                "Audit logs exported successfully",
                ok_only=True
            )
            
        except Exception as e:
            create_dialog(
                self.root,
                "Error",
                f"Failed to export audit logs: {str(e)}",
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
        
        # Get selected node or use root if none selected
        selected = self.ui.tree.selection()
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

    async def periodic_shutdown_check(self):
        """Periodically check if shutdown has been requested."""
        while True:
            try:
                await asyncio.sleep(0.5)  # Check every half second
                if self.shutdown_event.is_set():
                    await self._on_closing_async()
                    break
            except Exception as e:
                print(f"Error during shutdown check: {e}")

    async def _on_closing_async(self):
        """Async cleanup operations."""
        try:
            # First cancel any ongoing tree loading operations
            current_task = asyncio.current_task()
            tree_tasks = [task for task in asyncio.all_tasks(self.loop) 
                         if task is not current_task 
                         and task.get_name() != 'periodic_shutdown_check'
                         and 'load_tree' in str(task.get_coro())]
            
            if tree_tasks:
                for task in tree_tasks:
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=0.5)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
            
            # Then close the database pool to prevent new operations
            if self.db:
                try:
                    await self.db.close()
                except Exception:
                    pass

            # Finally cancel remaining tasks
            for task in asyncio.all_tasks(self.loop):
                if (task is not current_task and 
                    task.get_name() != 'periodic_shutdown_check' and
                    not task.done()):
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=0.5)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                
        finally:
            # Signal the event loop to stop
            self.loop.call_soon_threadsafe(self.loop.stop)

    def _on_closing(self):
        """Handle application closing."""
        try:
            # Disable all UI elements to prevent new operations
            for widget in self.root.winfo_children():
                try:
                    widget.configure(state='disabled')
                except:
                    pass

            # Set shutdown event to trigger async cleanup
            self.shutdown_event.set()

            # Give async cleanup a chance to complete
            import time
            timeout = time.time() + 2  # 2 second timeout
            while not self.loop.is_closed() and time.time() < timeout:
                time.sleep(0.1)

        finally:
            try:
                # Ensure the root is destroyed and app quits
                self.root.quit()
                self.root.destroy()
            except:
                pass

    def run(self):
        """Run the application with async support."""
        def run_async_loop():
            """Run the async event loop in a separate thread."""
            try:
                asyncio.set_event_loop(self.loop)
                # Start periodic shutdown check
                shutdown_check_task = self.loop.create_task(
                    self.periodic_shutdown_check(),
                    name='periodic_shutdown_check'
                )
                self.loop.run_forever()
            except Exception as e:
                print(f"Error in async loop: {e}")
            finally:
                try:
                    # Clean up any remaining tasks
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()
                    # Give tasks a chance to respond to cancellation
                    if pending:
                        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    self.loop.close()
                except Exception as e:
                    print(f"Error cleaning up async loop: {e}")

        try:
            # Start the async event loop in a separate thread
            thread = threading.Thread(target=run_async_loop, daemon=True)
            thread.start()

            # Run the Tkinter main loop
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_closing()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self._on_closing()

def main():
    # Set up asyncio policy for Windows if needed
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    app = App()
    app.run()

if __name__ == "__main__":
    main()
