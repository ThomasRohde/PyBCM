import asyncio
import threading
import tkinter as tk
import ttkbootstrap as ttk
from tkinterweb import HtmlFrame
import re
import markdown
from pydantic_ai import Agent, RunContext
from typing import List, Optional, Dict
from datetime import datetime
from .database import DatabaseOperations
from sqlalchemy.orm import Session

from .models import get_db, SessionLocal
import threading
import sys

# Version check to ensure we're using latest code
_MODULE_VERSION = "2.0.0"
if not hasattr(sys.modules[__name__], '_LOADED_VERSION') or sys.modules[__name__]._LOADED_VERSION != _MODULE_VERSION:
    sys.modules[__name__]._LOADED_VERSION = _MODULE_VERSION

# Create thread-local storage for database sessions
thread_local = threading.local()

def get_thread_db():
    """Get a database session for the current thread."""
    if not hasattr(thread_local, "db"):
        thread_local.db = SessionLocal()
    return thread_local.db

# Initialize the agent at module level
agent = Agent('openai:gpt-4o-mini', system_prompt="""You are a Business Capability Model assistant. You can help users by:
- Retrieving capability information
- Searching capabilities
- Viewing capability hierarchies
- Providing capability insights

Available tools:
- get_capability: Get details about a specific capability by ID
- get_capability_by_name: Get a capability by its name
- get_capabilities: Get capabilities under a specific parent
- get_capability_with_children: Get a capability and its children
- search_capabilities: Search capabilities by name/description
- get_markdown_hierarchy: Get a markdown representation of the hierarchy
""", retries=3)

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

class ChatDialogV2(ttk.Toplevel):
    def __init__(self, parent, db_session: Session):
        super().__init__(parent)
        self.title("AI Chat")
        
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
        
        # Add CSS styling for the HTML content
        self.html_style = """
        <style>
            body { 
                font-family: TkDefaultFont; 
                font-size: 10pt; 
                margin: 0; 
                padding: 8px; 
            }
            h1 { font-size: 14pt; font-weight: bold; margin: 8px 0; }
            h2 { font-size: 12pt; font-weight: bold; margin: 8px 0; }
            h3 { font-size: 11pt; font-weight: bold; margin: 8px 0; }
            pre { 
                background: #f5f5f5; 
                padding: 8px; 
                border-radius: 4px; 
                margin: 8px 0;
            }
            code { 
                font-family: "Courier New", Courier, monospace; 
                background: #f0f0f0; 
                padding: 2px 4px; 
                border-radius: 3px;
            }
            ul, ol { margin: 8px 0 8px 20px; padding: 0; }
            li { margin: 4px 0; }
            p { margin: 8px 0; }
            blockquote {
                margin: 8px 0;
                padding-left: 12px;
                border-left: 3px solid #ccc;
                color: #666;
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
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Protocol handler for window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Focus entry
        self.entry.focus_set()
        
        # Set initial size and position
        self.geometry("800x600")
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
        # Welcome message
        self.display_message("Assistant", "Hello! I'm your AI assistant. How can I help you today?")
    
    def _on_scroll_start(self, event):
        self.is_scrolling = True
    
    def _on_scroll_end(self, event):
        self.is_scrolling = False
    
    def _on_frame_configure(self, event):
        if not self.is_scrolling:
            self._update_scroll_region()
    
    def _on_canvas_configure(self, event):
        # Adjust the width of the messages_frame to match the canvas width
        self.chat_canvas.itemconfig(
            self.chat_canvas.find_withtag("all")[0],
            width=event.width
        )
        self._update_scroll_region()
    
    def _update_scroll_region(self):
        self.update_idletasks()
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
    
    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown to HTML with extended features."""
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
        return f"{self.html_style}<div class='markdown-body'>{html_content}</div>"

    def display_message(self, sender: str, message: str):
        """Display a message in the chat."""
        if sender == "Assistant":
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
            
            # HTML frame for rendered markdown
            html_frame = HtmlFrame(container, messages_enabled=False)
            html_frame.pack(fill="x", expand=True, padx=5)
            
            # Convert markdown to HTML with extended features and display
            html_content = self._convert_markdown_to_html(message)
            html_frame.load_html(html_content)
            
            # Store reference to container
            self.ai_response_frames[len(self.messages)] = (container, html_frame)
        else:
            # Display user messages as before
            message_label = ttk.Label(
                self.messages_frame,
                text=f"{sender}: {message}",
                wraplength=self.chat_canvas.winfo_width()-20,
                anchor="w",
                justify="left"
            )
            message_label.pack(fill="x", expand=True, padx=5, pady=2)
        
        self._update_scroll_region()
        self.chat_canvas.yview_moveto(1.0)
    
    def _update_label(self, message_index: int, sender: str, message: str):
        """Update an AI response with new content."""
        if message_index in self.ai_response_frames:
            _, html_frame = self.ai_response_frames[message_index]
            
            # Convert markdown to HTML with extended features and update
            html_content = self._convert_markdown_to_html(message)
            html_frame.load_html(html_content)
            
            self._update_scroll_region()
            self.chat_canvas.yview_moveto(1.0)

    def _send_message(self):
        """Handle sending a message."""
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
    
    def _handle_ai_response(self, message: str):
        """Handle getting AI response in background thread."""
        asyncio.run(self._fetch_and_display_response(message))
    
    async def _fetch_and_display_response(self, message: str):
        """Fetch and display the AI response with streaming."""
        try:
            async with agent.run_stream(message, message_history=self.messages) as result:
                response_text = ""
                message_index = len(self.messages)
                
                # Create initial empty response
                self.display_message("Assistant", "")
                
                # Stream response
                async for chunk in result.stream_text(delta=True):
                    response_text += chunk
                    # Update UI in main thread
                    self.after(0, self._update_label, message_index, "Assistant", response_text)
                
                # Add to message history
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
        self.destroy()

def show_chat_dialog(parent, db_session: Session):
    """Show the chat dialog."""
    try:
        dialog = ChatDialogV2(parent, db_session)
        return dialog
    except Exception as e:
        raise e
