import asyncio
import threading
import tkinter as tk
import ttkbootstrap as ttk
from tkinterweb import HtmlLabel
import markdown
from pydantic_ai import Agent, RunContext
from typing import List, Optional, Dict
from datetime import datetime
from .database import DatabaseOperations
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader
import os

from .models import SessionLocal

# Set up Jinja environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = Environment(loader=FileSystemLoader(template_dir))

# Load system prompt template
system_prompt_template = jinja_env.get_template('system_prompt.j2')
system_prompt = system_prompt_template.render()

# Initialize the agent at module level with deps_type
agent = Agent('openai:gpt-4o-mini', system_prompt=system_prompt, retries=3, deps_type=str)

@agent.system_prompt
def add_user_name() -> str:
    """Add the user's name to system prompt."""
    # Get system username using os.getlogin() or fallback to environment variable
    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get('USERNAME', 'User')
    print(f"User: {username}")
    return f"The user's system name is {username}."

@agent.system_prompt
def add_current_time() -> str:
    """Add the current time to system prompt."""
    return f"The current time and date is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."

# Create thread-local storage for database sessions
thread_local = threading.local()

def get_thread_db():
    """Get a database session for the current thread."""
    if not hasattr(thread_local, "db"):
        thread_local.db = SessionLocal()
    return thread_local.db

def cleanup_thread_db():
    """Clean up thread-local database session."""
    if hasattr(thread_local, "db"):
        thread_local.db.close()
        delattr(thread_local, "db")

@agent.tool
async def get_capability(ctx: RunContext, capability_id: int) -> Optional[Dict]:
    """Get details about a specific capability by ID."""
    try:
        db = get_thread_db()
        db_ops = DatabaseOperations(db)
        capability = db_ops.get_capability(capability_id)
        if capability:
            return {
                "id": capability.id,
                "name": capability.name,
                "description": capability.description,
                "parent_id": capability.parent_id,
                "order_position": capability.order_position
            }
        return None
    finally:
        cleanup_thread_db()

@agent.tool
async def get_capabilities(ctx: RunContext, parent_id: Optional[int] = None) -> List[Dict]:
    """Get all capabilities under a specific parent ID."""
    try:
        db = get_thread_db()
        db_ops = DatabaseOperations(db)
        capabilities = db_ops.get_capabilities(parent_id)
        return [{
            "id": cap.id,
            "name": cap.name,
            "description": cap.description,
            "parent_id": cap.parent_id,
            "order_position": cap.order_position
        } for cap in capabilities]
    finally:
        cleanup_thread_db()

@agent.tool
async def get_capability_with_children(ctx: RunContext, capability_id: int) -> Optional[Dict]:
    """Get a capability and its full hierarchy of children."""
    try:
        db = get_thread_db()
        db_ops = DatabaseOperations(db)
        return db_ops.get_capability_with_children(capability_id)
    finally:
        cleanup_thread_db()

@agent.tool
async def search_capabilities(ctx: RunContext, query: str) -> List[Dict]:
    """Search capabilities by name or description."""
    try:
        db = get_thread_db()
        db_ops = DatabaseOperations(db)
        capabilities = db_ops.search_capabilities(query)
        return [{
            "id": cap.id,
            "name": cap.name,
            "description": cap.description,
            "parent_id": cap.parent_id,
            "order_position": cap.order_position
        } for cap in capabilities]
    finally:
        cleanup_thread_db()

@agent.tool
async def get_markdown_hierarchy(ctx: RunContext) -> str:
    """Get a markdown representation of the capability hierarchy."""
    try:
        db = get_thread_db()
        db_ops = DatabaseOperations(db)
        return db_ops.get_markdown_hierarchy()
    finally:
        cleanup_thread_db()

@agent.tool
async def get_capability_by_name(ctx: RunContext, name: str) -> Optional[Dict]:
    """Get a capability by its name (case insensitive)."""
    try:
        db = get_thread_db()
        db_ops = DatabaseOperations(db)
        capability = db_ops.get_capability_by_name(name)
        if capability:
            return {
                "id": capability.id,
                "name": capability.name,
                "description": capability.description,
                "parent_id": capability.parent_id,
                "order_position": capability.order_position
            }
        return None
    finally:
        cleanup_thread_db()

class Message:
    def __init__(self, content: str, is_user: bool, timestamp: datetime = None):
        self.content = content
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()

class ChatDialog(ttk.Toplevel):
    def __init__(self, parent, db_session: Session):
        super().__init__(parent)
        try:
            self.withdraw()  # Hide window initially
            self.iconbitmap("./bcm/business_capability_model.ico")
            self.title("AI Chat")
            
            # Set initial size before creating widgets
            self.geometry("1200x800")
            
            # Calculate position relative to parent
            self.update_idletasks()
            x = parent.winfo_x() + (parent.winfo_width() - 800) // 2
            y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
            self.geometry(f"+{x}+{y}")
            
            # Initialize message history
            self.messages: List[Message] = []

            self.ai_response_frames = {}  # Dictionary to store AI response frames
            self.is_scrolling = False
            
            # Create main container
            self.main_container = ttk.Frame(self)
            self.main_container.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Chat frame with canvas for scrolling
            self.chat_frame = ttk.Frame(self.main_container)
            self.chat_frame.pack(fill="both", expand=True, pady=(0, 10))
            
            # Scrollbar for the chat display
            self.scrollbar = ttk.Scrollbar(self.chat_frame)
            self.scrollbar.pack(side="right", fill="y")
            
            # Canvas to hold the chat messages - remove border and set bg
            self.chat_canvas = tk.Canvas(
                self.chat_frame, 
                yscrollcommand=self.scrollbar.set,
                borderwidth=0,
                highlightthickness=0,
                background='#ffffff'  # or use system color
            )
            self.chat_canvas.pack(side="left", fill="both", expand=True)
            self.scrollbar.config(command=self.chat_canvas.yview)
            
            # Frame inside canvas - set matching background
            self.messages_frame = ttk.Frame(self.chat_canvas, style='chat.TFrame')
            self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
            style = ttk.Style()
            style.configure('chat.TFrame', background='#ffffff')  # match canvas bg
            
            # Update message styles
            self.message_styles = """
                <style>
                    .user-message {
                        background-color: #e3f2fd;
                        border-radius: 8px;
                        padding: 8px;
                        margin: 4px;
                    }
                    .assistant-message {
                        background-color: #f5f5f5;
                        border-radius: 8px;
                        padding: 8px;
                        margin: 4px;
                    }
                </style>
            """
            
            # Input frame
            self.input_frame = ttk.Frame(self.main_container)
            self.input_frame.pack(fill="x", pady=(0, 5))
            
            # Message entry
            self.message_var = tk.StringVar()
            self.entry = ttk.Entry(
                self.input_frame,
                textvariable=self.message_var,
                font=("TkDefaultFont", 10)
            )
            self.send_button = ttk.Button(
                self.input_frame,
                text="Send",
                command=self._send_message,
                style="primary.TButton",
                width=10
            )
            
            # Layout
            self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self.send_button.pack(side="right")
            
            # Bind events
            self.entry.bind("<Return>", lambda e: self._send_message())
            self.messages_frame.bind("<Configure>", self._on_frame_configure)
            self.chat_canvas.bind("<Configure>", self._on_canvas_configure)
            self.chat_canvas.bind("<B1-Motion>", self._on_scroll_start)
            self.chat_canvas.bind("<ButtonRelease-1>", self._on_scroll_end)
            self.scrollbar.bind("<B1-Motion>", self._on_scroll_start)
            self.scrollbar.bind("<ButtonRelease-1>", self._on_scroll_end)
            
            # Bind mouse wheel event for scrolling
            self.chat_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
            
            # Make dialog modal
            self.transient(parent)
            self.grab_set()
            
            # Protocol handler for window close
            self.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            # Focus entry
            self.entry.focus_set()
            
            # Display welcome message
            self.display_message("Assistant", "Hello! I'm your AI assistant. How can I help you today?")
            
            # Show window after everything is set up
            self.deiconify()
        except Exception as e:
            print(f"Error initializing chat dialog: {e}")
            raise
    
    def _on_scroll_start(self, event):
        self.is_scrolling = True
    
    def _on_scroll_end(self, event):
        self.is_scrolling = False
    
    def _on_frame_configure(self, event):
        if not self.is_scrolling:
            self._update_scroll_region()
    
    def _on_canvas_configure(self, event):
        try:
            # Adjust the width of the messages_frame to match the canvas width
            self.chat_canvas.itemconfig(
                self.chat_canvas.find_withtag("all")[0],
                width=event.width
            )
            self._update_scroll_region()
        except Exception as e:
            print(f"Error configuring canvas: {e}")
    
    def _update_scroll_region(self):
        try:
            self.update_idletasks()
            self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        except Exception as e:
            print(f"Error updating scroll region: {e}")
    
    def _convert_markdown_to_html(self, markdown_text: str, is_user: bool = False) -> str:
        """Convert markdown to HTML with extended features."""
        css_class = "user-message" if is_user else "assistant-message"
        try:
            # Enable common markdown extensions
            html_content = markdown.markdown(
                markdown_text,
                extensions=[
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.tables',
                    'markdown.extensions.nl2br',
                    'markdown.extensions.extra'
                ]
            )
            return f"""{self.message_styles}
<div class="{css_class}">
    {html_content}
</div>"""
        except Exception as e:
            # Fallback to plain text if markdown conversion fails
            return f"""{self.message_styles}
<div class="{css_class}">
    <pre>{markdown_text}</pre>
</div>"""

    def display_message(self, sender: str, message: str):
        """Display a message in the chat."""
        try:
            # Create frame with matching background
            container = ttk.Frame(self.messages_frame, style='chat.TFrame')
            container.pack(fill="x", expand=True, padx=5, pady=2)
            
            # Label with matching background
            sender_label = ttk.Label(
                container, 
                text=f"{sender}:", 
                anchor="w",
                style='chat.TLabel'
            )
            sender_label.pack(fill="x", padx=5)
            
            # Convert markdown to HTML first
            is_user = sender == "You"
            html_content = self._convert_markdown_to_html(message, is_user)
            
            # HTML label for rendered markdown
            html_label = HtmlLabel(container, text=html_content)
            html_label.pack(fill="x", expand=True, padx=5)
            
            # Store reference to container
            self.ai_response_frames[len(self.messages)] = (container, html_label)
            
            self._update_scroll_region()
            self.chat_canvas.yview_moveto(1.0)
        except Exception as e:
            print(f"Error displaying message: {e}")
    
    def _update_label(self, message_index: int, sender: str, message: str):
        """Update an AI response with new content."""
        try:
            if message_index in self.ai_response_frames:
                container, old_label = self.ai_response_frames[message_index]
                
                # Remove old label
                old_label.pack_forget()
                
                # Create new label with updated content
                is_user = sender == "You"
                html_content = self._convert_markdown_to_html(message, is_user)
                html_label = HtmlLabel(container, text=html_content)
                html_label.pack(fill="x", expand=True, padx=5)
                
                # Update reference
                self.ai_response_frames[message_index] = (container, html_label)
                
                self._update_scroll_region()
                self.chat_canvas.yview_moveto(1.0)
        except Exception as e:
            print(f"Error updating label: {e}")

    def _send_message(self):
        """Handle sending a message."""
        try:
            message = self.message_var.get().strip()
            if not message:
                return
            
            # Clear input and disable
            self.message_var.set("")
            self.entry.configure(state="disabled")
            self.send_button.configure(state="disabled")
            
            # Display user message
            self.display_message("You", message)
            
            # Start processing in background thread
            threading.Thread(
                target=self._handle_ai_response,
                args=(message,),
                daemon=True
            ).start()
        except Exception as e:
            print(f"Error sending message: {e}")
            self.entry.configure(state="normal")
            self.send_button.configure(state="normal")
    
    def _handle_ai_response(self, message: str):
        """Handle getting AI response in background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._fetch_and_display_response(message))
        except Exception as e:
            print(f"Error handling AI response: {e}")
            self.after(0, self.display_message, "Assistant", f"Error: {str(e)}")
        finally:
            loop.close()
            cleanup_thread_db()
    
    async def _fetch_and_display_response(self, message: str):
        """Fetch and display the AI response with streaming."""
        response_text = ""
        message_index = len(self.messages)
        result = None
        stream = None
        
        # Create initial empty response
        self.display_message("Assistant", "")
        
        try:
            # Create a lock for thread-safe updates
            update_lock = asyncio.Lock()
            
            async with agent.run_stream(message, message_history=self.messages) as result:
                import time
                last_update = time.time()
                update_interval = 0.05  # 50ms in seconds
                needs_update = False
                
                try:
                    stream = result.stream_text(delta=True)
                    while True:
                        try:
                            chunk = await stream.__anext__()
                            response_text += chunk
                            needs_update = True
                            current_time = time.time()
                            
                            if current_time - last_update >= update_interval:
                                async with update_lock:
                                    # Update UI in main thread
                                    self.after(0, self._update_label, message_index, "Assistant", response_text)
                                    last_update = current_time
                                    needs_update = False
                                
                                # Give other tasks a chance to run
                                await asyncio.sleep(0)
                        except StopAsyncIteration:
                            break
                        except GeneratorExit:
                            # Handle generator cleanup gracefully
                            if needs_update:
                                self.after(0, self._update_label, message_index, "Assistant", response_text)
                            return
                        except Exception as e:
                            self.after(0, self.display_message, "Assistant", f"Error during streaming: {str(e)}")
                            return
                except Exception as e:
                    self.after(0, self.display_message, "Assistant", f"Error in stream handling: {str(e)}")
                    return
                
                # Ensure final state is displayed
                if needs_update:
                    async with update_lock:
                        self.after(0, self._update_label, message_index, "Assistant", response_text)
                
                # Add to message history only if we have a valid result
                if result and hasattr(result, 'new_messages'):
                    self.messages.extend(result.new_messages())
                
        except Exception as e:
            self.after(0, self.display_message, "Assistant", f"Error: {str(e)}")
        finally:
            # Clean up thread-local database session
            cleanup_thread_db()
            # Re-enable input in main thread
            self.after(0, lambda: [
                self.entry.configure(state="normal"),
                self.send_button.configure(state="normal"),
                self.entry.focus_set()
            ])
    
    def _on_closing(self):
        """Handle window closing."""
        try:
            self.destroy()
        except Exception as e:
            print(f"Error closing dialog: {e}")

    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling."""
        try:
            # Windows and MacOS handle scroll direction differently
            # Normalize the delta to work consistently across platforms
            delta = -1 * (event.delta // 120)  # Normalize delta
            self.chat_canvas.yview_scroll(delta, "units")
            return "break"  # Prevent event propagation
        except Exception as e:
            print(f"Error handling mouse wheel: {e}")

def show_chat_dialog(parent, db_session: Session):
    """Show the chat dialog."""
    try:
        dialog = ChatDialog(parent, db_session)
        return dialog
    except Exception as e:
        print(f"Error showing chat dialog: {e}")
        raise e
