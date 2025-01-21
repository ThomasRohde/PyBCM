import asyncio
import json
import os
import threading
from tkinter import filedialog
from typing import Dict
import ttkbootstrap as ttk
from sqlalchemy import select
import json_repair

from bcm.models import (
    init_db,
    get_db,
    CapabilityCreate,
    AsyncSessionLocal,
    Capability,
    LayoutModel,
)
from bcm.database import DatabaseOperations
from bcm.dialogs import create_dialog, CapabilityConfirmDialog
from bcm.settings import Settings, SettingsDialog
from bcm.ui import BusinessCapabilityUI
from bcm.utils import expand_capability_ai, generate_first_level_capabilities, init_user_templates, get_capability_context, jinja_env
from bcm.pb import ProgressWindow
from bcm.audit_view import AuditLogViewer
from bcm.visualizer import CapabilityVisualizer
from dotenv import load_dotenv
import logfire

# Load .env from user directory
user_dir = os.path.expanduser("~")
app_dir = os.path.join(user_dir, ".pybcm")
os.makedirs(app_dir, exist_ok=True)
env_path = os.path.join(app_dir, ".env")
load_dotenv(env_path)

logfire.configure()
logfire.instrument_openai()

async def anext(iterator):
    """Helper function for async iteration compatibility."""
    return await iterator.__anext__()


class App:
    def __init__(self):
        # Initialize user templates
        init_user_templates()
        
        # Add async event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Add shutdown event
        self.shutdown_event = asyncio.Event()

        # Load settings
        self.settings = Settings()

        self.root = ttk.Window(
            title="Business Capability Modeler", themename=self.settings.get("theme")
        )

        # Get screen dimensions and calculate 50% size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.5)
        window_height = int(screen_height * 0.5)

        # Set window size
        self.root.geometry(f"{window_width}x{window_height}")

        self.root.withdraw()  # Hide window temporarily
        self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "business_capability_model.ico"))
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Initialize database asynchronously
        self.loop.run_until_complete(init_db())
        self.db = self.loop.run_until_complete(anext(get_db()))
        self.db_ops = DatabaseOperations(AsyncSessionLocal)

        self.current_description = ""  # Add this to track changes
        self.loading_complete = (
            threading.Event()
        )  # Add this line after self.db_ops initialization

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
        max_level = self.settings.get("max_level", 6)
        return LayoutModel.convert_to_layout_format(node_data, max_level, level)

    def _export_capability_model(
        self, export_type, export_func, file_extension, file_type_name, clipboard=False
    ):
        """Base method for exporting capability model to different formats."""
        # Get filename first if not copying to clipboard
        filename = None
        if not clipboard:
            user_dir = os.path.expanduser("~")
            app_dir = os.path.join(user_dir, ".pybcm")
            os.makedirs(app_dir, exist_ok=True)
            filename = filedialog.asksaveasfilename(
                title=f"Export to {export_type}",
                initialdir=app_dir,
                defaultextension=file_extension,
                filetypes=[
                    (f"{file_type_name} files", f"*{file_extension}"),
                    ("All files", "*.*"),
                ],
            )
            if not filename:
                return

        async def export():
            # Get selected node or use root if none selected
            selected = self.ui.tree.selection()
            if selected:
                start_node_id = int(selected[0])
            else:
                # Find root node
                capabilities = await self.db_ops.get_all_capabilities()
                root_nodes = [cap for cap in capabilities if not cap.get("parent_id")]
                if not root_nodes:
                    return None
                start_node_id = root_nodes[0]["id"]

            # Get hierarchical data starting from selected node
            node_data = await self.db_ops.get_capability_with_children(start_node_id)
            if not node_data:
                return None

            # Convert to layout format
            layout_model = self._convert_to_layout_format(node_data)

            # Generate content using provided export function
            content = export_func(layout_model, self.settings)

            return content

        def on_export_complete(future):
            try:
                content = future.result()
                if content is None:
                    self.root.after(0, lambda: create_dialog(
                        self.root,
                        "Error",
                        "No capabilities found to export",
                        ok_only=True,
                    ))
                    return

                if clipboard:
                    try:
                        # Copy to clipboard
                        self.root.clipboard_clear()
                        self.root.clipboard_append(content)
                        
                        self.root.after(0, lambda: create_dialog(
                            self.root,
                            "Success",
                            f"Capabilities exported to clipboard in {export_type} format",
                            ok_only=True,
                        ))
                    except Exception as error:
                        error_msg = str(error)  # Capture error message
                        self.root.after(0, lambda err=error_msg: create_dialog(
                            self.root,
                            "Error", 
                            f"Failed to copy to clipboard: {err}",
                            ok_only=True,
                        ))
                else:
                    try:
                        # Handle different save methods
                        if isinstance(content, str):
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(content)
                        else:
                            # Assume it's a PowerPoint presentation or similar object with save method
                            content.save(filename)

                        self.root.after(0, lambda: create_dialog(
                            self.root,
                            "Success",
                            f"Capabilities exported to {export_type} format successfully",
                            ok_only=True,
                        ))
                    except Exception as error:
                        error_msg = str(error)  # Capture error message
                        self.root.after(0, lambda err=error_msg: create_dialog(
                            self.root,
                            "Error",
                            f"Failed to export capabilities to {export_type} format: {err}",
                            ok_only=True,
                        ))

            except Exception as error:
                error_msg = str(error)  # Capture error message
                self.root.after(0, lambda err=error_msg: create_dialog(
                    self.root,
                    "Error",
                    f"Export failed: {err}",
                    ok_only=True,
                ))

        # Run the export operation
        future = asyncio.run_coroutine_threadsafe(export(), self.loop)
        future.add_done_callback(on_export_complete)

    def _export_to_archimate(self):
        """Export capabilities to Archimate Open Exchange format starting from selected node."""
        from bcm.archimate_export import export_to_archimate

        self._export_capability_model("Archimate", export_to_archimate, ".xml", "XML")

    def _export_to_pptx(self):
        """Export capabilities to PowerPoint visualization starting from selected node."""
        from bcm.pptx_export import export_to_pptx

        self._export_capability_model(
            "PowerPoint", export_to_pptx, ".pptx", "PowerPoint"
        )

    def _export_to_svg(self):
        """Export capabilities to SVG visualization starting from selected node."""
        from bcm.svg_export import export_to_svg

        self._export_capability_model("SVG", export_to_svg, ".svg", "SVG")

    def _export_to_markdown(self):
        """Export capabilities to Markdown format starting from selected node."""
        from bcm.markdown_export import export_to_markdown

        self._export_capability_model("Markdown", export_to_markdown, ".md", "Markdown")

    def _export_to_word(self):
        """Export capabilities to Markdown format starting from selected node."""
        from bcm.word_export import export_to_word

        self._export_capability_model("Word", export_to_word, ".docx", "Word")

    def _export_to_html(self):
        """Export capabilities to HTML visualization starting from selected node."""
        from bcm.html_export import export_to_html

        self._export_capability_model("HTML", export_to_html, ".html", "HTML")

    def _export_to_mermaid(self):
        """Export capabilities to Mermaid mindmap visualization starting from selected node."""
        from bcm.mermaid_export import export_to_mermaid

        self._export_capability_model("Mermaid", export_to_mermaid, ".html", "HTML")

    def _export_to_plantuml(self):
        """Export capabilities to PlantUML mindmap visualization starting from selected node."""
        from bcm.plantuml_export import export_to_plantuml

        self._export_capability_model("PlantUML", export_to_plantuml, ".puml", "PlantUML")

    def _copy_to_plantuml(self, event=None):
        """Copy capabilities to clipboard in PlantUML mindmap format."""
        from bcm.plantuml_export import export_to_plantuml

        self._export_capability_model("PlantUML", export_to_plantuml, ".puml", "PlantUML", clipboard=True)

    def _copy_to_mermaid(self, event=None):
        """Copy capabilities to clipboard in Mermaid mindmap format."""
        from bcm.mermaid_export import export_to_mermaid

        self._export_capability_model("Mermaid", export_to_mermaid, ".html", "HTML", clipboard=True)

    def _paste_capability(self, event=None):
        """Paste sub-capabilities from clipboard JSON under selected capability."""
        selected = self.ui.tree.selection()
        if not selected:
            create_dialog(
                self.root, 
                "Error", 
                "Please select a parent capability first", 
                ok_only=True
            )
            return

        capability_id = int(selected[0])

        # Get clipboard content
        try:
            clipboard_text = self.root.clipboard_get()
            subcapabilities = json_repair.loads(clipboard_text)
            
            if not isinstance(subcapabilities, list):
                raise ValueError("Clipboard content must be a JSON array")
                
            # Convert to name:description dict for CapabilityConfirmDialog
            capabilities_dict = {}
            for cap in subcapabilities:
                if not isinstance(cap, dict) or 'name' not in cap or 'description' not in cap:
                    raise ValueError("Each capability must have 'name' and 'description' fields")
                capabilities_dict[cap['name']] = cap['description']

        except json.JSONDecodeError:
            create_dialog(
                self.root,
                "Error",
                "Clipboard content is not valid JSON",
                ok_only=True
            )
            return
        except Exception as e:
            create_dialog(
                self.root,
                "Error", 
                f"Invalid clipboard content: {str(e)}",
                ok_only=True
            )
            return

        # Show confirmation dialog with checkboxes
        dialog = CapabilityConfirmDialog(self.root, capabilities_dict)
        self.root.wait_window(dialog)

        # If user clicked OK and selected some capabilities
        if dialog.result:
            progress = None
            try:
                progress = ProgressWindow(self.root)

                # Create selected sub-capabilities
                async def create_subcapabilities():
                    for name, description in dialog.result.items():
                        await self.db_ops.create_capability(
                            CapabilityCreate(
                                name=name,
                                description=description,
                                parent_id=capability_id,
                            )
                        )

                # Run creation with progress
                progress.run_with_progress(create_subcapabilities())
                self.ui.tree.refresh_tree()

                create_dialog(
                    self.root,
                    "Success",
                    f"Added {len(dialog.result)} new sub-capabilities",
                    ok_only=True
                )

            except Exception as e:
                create_dialog(
                    self.root,
                    "Error",
                    f"Failed to create sub-capabilities: {str(e)}",
                    ok_only=True
                )
            finally:
                if progress:
                    progress.close()

    def _export_to_clipboard(self, event=None):
        """Export capabilities to clipboard in context format."""
        selected = self.ui.tree.selection()
        if not selected:
            return

        capability_id = int(selected[0])

        # Create async function to get context
        async def get_context():
            return await get_capability_context(self.db_ops, capability_id)

        def on_capability_info_complete(future):
            try:
                capability = future.result()
                # Determine if this is a first-level capability
                is_first_level = not capability.parent_id
                
                # Render template with appropriate context
                if is_first_level:
                    template = jinja_env.get_template(self.settings.get("first_level_template"))
                    rendered_context = template.render(
                        organisation_name=capability.name,
                        organisation_description=capability.description or f"An organization focused on {capability.name}",
                        first_level=self.settings.get("first_level_range")
                    )
                else:
                    template = jinja_env.get_template(self.settings.get("normal_template"))
                    rendered_context = template.render(
                        capability_name=capability.name,
                        context=context_result,
                        max_capabilities=self.settings.get("max_ai_capabilities")
                    )
                
                # Copy to clipboard
                self.root.clipboard_clear()
                self.root.clipboard_append(rendered_context)
                
                self.root.after(0, lambda: create_dialog(
                    self.root,
                    "Success",
                    "Capability context copied to clipboard",
                    ok_only=True,
                ))
            except Exception:
                self.root.after(0, lambda: create_dialog(
                    self.root,
                    "Error",
                    f"Failed to copy to clipboard: {str(future.exception())}",
                    ok_only=True,
                ))

        def on_context_complete(future):
            try:
                global context_result  # Used to share context between callbacks
                context_result = future.result()
                
                # Get capability info
                async def get_capability_info():
                    capability = await self.db_ops.get_capability(capability_id)
                    return capability

                # Run get_capability_info with callback
                future = asyncio.run_coroutine_threadsafe(get_capability_info(), self.loop)
                future.add_done_callback(on_capability_info_complete)
            except Exception:
                self.root.after(0, lambda: create_dialog(
                    self.root,
                    "Error",
                    f"Failed to get context: {str(future.exception())}",
                    ok_only=True,
                ))

        # Run get_context with callback
        future = asyncio.run_coroutine_threadsafe(get_context(), self.loop)
        future.add_done_callback(on_context_complete)

    def _export_capabilities(self):
        """Export capabilities to JSON file."""
        from bcm.io import export_capabilities

        export_capabilities(self.root, self.db_ops, self.loop)

    def _import_capabilities(self):
        """Import capabilities from JSON file."""
        from bcm.io import import_capabilities

        if import_capabilities(self.root, self.db_ops, self.loop):
            self.ui.tree.refresh_tree()

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
                ok_only=True,
            )

    async def _expand_capability_async(
        self, context: str, capability_name: str
    ) -> Dict[str, str]:
        """Use PydanticAI to expand a capability into sub-capabilities with descriptions."""
        selected = self.ui.tree.selection()
        capability_id = int(selected[0])
        capability = await self.db_ops.get_capability(capability_id)

        # Check if this is a root capability (no parent) AND has no children
        if not capability.parent_id and not self.ui.tree.get_children(capability_id):
            # Use the capability's actual name and description for first-level generation
            return await generate_first_level_capabilities(
                capability.name,
                capability.description
                or f"An organization focused on {capability.name}",
            )

        # For non-root capabilities or those with existing children, use regular expansion
        return await expand_capability_ai(
            context, capability_name, self.settings.get("max_ai_capabilities")
        )

    def _expand_capability(self):
        """Expand the selected capability using AI."""

        selected = self.ui.tree.selection()
        if not selected:
            create_dialog(
                self.root, "Error", "Please select a capability to expand", ok_only=True
            )
            return

        capability_id = int(selected[0])

        progress = None
        try:
            progress = ProgressWindow(self.root)

            # Get context and expand capability
            async def expand():
                from bcm.utils import get_capability_context

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
                            await self.db_ops.create_capability(
                                CapabilityCreate(
                                    name=name,
                                    description=description,
                                    parent_id=capability_id,
                                )
                            )

                    # Run creation with progress
                    progress.run_with_progress(create_subcapabilities())
                    self.ui.tree.refresh_tree()

        except Exception as e:
            create_dialog(
                self.root,
                "Error",
                f"Failed to expand capability: {str(e)}",
                ok_only=True,
            )
        finally:
            if progress:
                progress.close()

    def _view_audit_logs(self):
        """Show the audit log viewer."""
        AuditLogViewer(self.root, self.db_ops)

    def _export_audit_logs(self):
        """Export audit logs to JSON file."""
        user_dir = os.path.expanduser("~")
        app_dir = os.path.join(user_dir, ".pybcm")
        os.makedirs(app_dir, exist_ok=True)
        filename = filedialog.asksaveasfilename(
            title="Export Audit Logs",
            initialdir=app_dir,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not filename:
            return

        # Create coroutine for export operation
        async def export_async():
            logs = await self.db_ops.export_audit_logs()
            with open(filename, "w") as f:
                json.dump(logs, f, indent=2)

        def on_export_complete(future):
            try:
                future.result()
                self.root.after(0, lambda: create_dialog(
                    self.root, "Success", "Audit logs exported successfully", ok_only=True
                ))
            except Exception:
                self.root.after(0, lambda: create_dialog(
                    self.root,
                    "Error",
                    f"Failed to export audit logs: {str(future.exception())}",
                    ok_only=True,
                ))

        # Run the coroutine in the event loop with callback
        future = asyncio.run_coroutine_threadsafe(export_async(), self.loop)
        future.add_done_callback(on_export_complete)

    def _show_chat(self):
        """Show the AI chat dialog."""
        import threading
        import webbrowser
        from bcm.web_agent import start_server, get_chat_port
        import asyncio
        import sys

        # Get the port first
        port = get_chat_port()

        def run_server():
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            start_server(port)

        # Start the FastAPI server in a background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Give the server a moment to start
        import time

        time.sleep(1)

        # Launch web browser to chat interface with correct port
        webbrowser.open(f"http://127.0.0.1:{port}", 1)

    def _show_visualizer(self):
        """Show the capability model visualizer starting from selected node."""

        def on_node_data_complete(future):
            try:
                node_data = future.result()
                # Convert to layout format starting from selected node
                layout_model = self._convert_to_layout_format(node_data)
                # Create and show visualizer window
                self.root.after(0, lambda: CapabilityVisualizer(self.root, layout_model))
            except Exception:
                self.root.after(0, lambda: create_dialog(
                    self.root,
                    "Error",
                    f"Failed to get node data: {str(future.exception())}",
                    ok_only=True,
                ))

        def on_root_node_complete(future):
            try:
                start_node_id = future.result()
                if not start_node_id:
                    return

                # Get hierarchical data starting from selected node
                async def get_node_data():
                    return await self.db_ops.get_capability_with_children(start_node_id)

                try:
                    # Run get_node_data with callback
                    future = asyncio.run_coroutine_threadsafe(get_node_data(), self.loop)
                    future.add_done_callback(on_node_data_complete)
                except Exception as e:
                    create_dialog(
                        self.root,
                        "Error",
                        f"Failed to start visualization: {str(e)}",
                        ok_only=True
                    )
            except Exception:
                self.root.after(0, lambda: create_dialog(
                    self.root,
                    "Error",
                    f"Failed to get root node: {str(future.exception())}",
                    ok_only=True,
                ))

        try:
            # Get selected node or use root if none selected
            selected = self.ui.tree.selection()
            if selected:
                start_node_id = int(selected[0])
                # Get hierarchical data starting from selected node
                async def get_node_data():
                    return await self.db_ops.get_capability_with_children(start_node_id)

                # Run get_node_data with callback
                future = asyncio.run_coroutine_threadsafe(get_node_data(), self.loop)
                future.add_done_callback(on_node_data_complete)
            else:
                # Find root node - using async method properly
                async def get_root_node():
                    capabilities = await self.db_ops.get_all_capabilities()
                    root_nodes = [cap for cap in capabilities if not cap.get("parent_id")]
                    if not root_nodes:
                        return None
                    return root_nodes[0]["id"]

                # Run get_root_node with callback
                future = asyncio.run_coroutine_threadsafe(get_root_node(), self.loop)
                future.add_done_callback(on_root_node_complete)
        except Exception as e:
            create_dialog(
                self.root,
                "Error",
                f"Failed to show visualizer: {str(e)}",
                ok_only=True
            )

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
            tree_tasks = [
                task
                for task in asyncio.all_tasks(self.loop)
                if task is not current_task
                and task.get_name() != "periodic_shutdown_check"
                and "load_tree" in str(task.get_coro())
            ]

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
                if (
                    task is not current_task
                    and task.get_name() != "periodic_shutdown_check"
                    and not task.done()
                ):
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
                    widget.configure(state="disabled")
                except:  # noqa: E722
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
            except:  # noqa: E722
                pass

    def run(self):
        """Run the application with async support."""

        def run_async_loop():
            """Run the async event loop in a separate thread."""
            try:
                asyncio.set_event_loop(self.loop)
                # Start periodic shutdown check
                shutdown_check_task = self.loop.create_task(  # noqa: F841
                    self.periodic_shutdown_check(), name="periodic_shutdown_check"
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
                        self.loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
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
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app = App()
    app.run()


if __name__ == "__main__":
    main()
