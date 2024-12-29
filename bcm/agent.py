import asyncio
import threading
import tkinter as tk
import ttkbootstrap as ttk
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
    
    def display_message(self, sender: str, message: str):
        """Display a message in the chat."""
        if sender == "Assistant":
            # Convert markdown to plain text
            text_content = message
            
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
            
            # Text widget with matching background
            text_widget = tk.Text(
                container,
                wrap="word",
                height=1,
                borderwidth=0,
                highlightthickness=0,
                relief="flat",
                font=("TkDefaultFont", 10),
                background='#ffffff'  # match container bg
            )
            
            # Configure tags for markdown formatting
            text_widget.tag_configure("h1", font=("TkDefaultFont", 14, "bold"))
            text_widget.tag_configure("h2", font=("TkDefaultFont", 12, "bold"))
            text_widget.tag_configure("h3", font=("TkDefaultFont", 11, "bold"))
            text_widget.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
            text_widget.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
            text_widget.tag_configure("code", font=("Courier", 9), background="#f0f0f0")
            text_widget.tag_configure("bullet", lmargin1=20, lmargin2=20)
            text_widget.tag_configure("link", foreground="blue", underline=True)
            
            text_widget.pack(fill="x", expand=True, padx=5)
            
            # Apply markdown formatting
            lines = text_content.split('\n')
            for line in lines:
                # Handle headers
                if line.startswith('### '):
                    text_widget.insert("end", line[4:] + "\n", "h3")
                    continue
                if line.startswith('## '):
                    text_widget.insert("end", line[3:] + "\n", "h2")
                    continue
                if line.startswith('# '):
                    text_widget.insert("end", line[2:] + "\n", "h1")
                    continue
                
                # Handle bullet points
                if line.strip().startswith('- '):
                    text_widget.insert("end", line + "\n", "bullet")
                    continue
                
                # Handle code blocks
                if line.strip().startswith('`') and line.strip().endswith('`'):
                    code = line.strip()[1:-1]
                    text_widget.insert("end", code + "\n", "code")
                    continue
                
                # Handle bold
                while '**' in line:
                    start = line.find('**')
                    end = line.find('**', start + 2)
                    if end == -1: break
                    text_widget.insert("end", line[:start])
                    text_widget.insert("end", line[start+2:end], "bold")
                    line = line[end+2:]
                
                # Handle italic
                while '*' in line:
                    start = line.find('*')
                    end = line.find('*', start + 1)
                    if end == -1: break
                    text_widget.insert("end", line[:start])
                    text_widget.insert("end", line[start+1:end], "italic")
                    line = line[end+1:]
                
                # Handle links
                while '[' in line and '](' in line and ')' in line:
                    start = line.find('[')
                    mid = line.find('](', start)
                    end = line.find(')', mid)
                    if mid == -1 or end == -1: break
                    text_widget.insert("end", line[:start])
                    text_widget.insert("end", line[start+1:mid], "link")
                    line = line[end+1:]
                
                text_widget.insert("end", line + "\n")
            
            # Calculate required height based on content
            text_height = int(text_widget.index('end-1c').split('.')[0])
            text_widget.configure(height=text_height)
            text_widget.configure(state="disabled")
            
            # Store reference to container
            self.ai_response_frames[len(self.messages)] = (container, text_widget)
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
            _, text_widget = self.ai_response_frames[message_index]
            text_widget.configure(state="normal", relief="flat")
            text_widget.delete("1.0", "end")
            
            # Apply markdown formatting
            lines = message.split('\n')
            for line in lines:
                # Handle headers
                if line.startswith('### '):
                    text_widget.insert("end", line[4:] + "\n", "h3")
                    continue
                if line.startswith('## '):
                    text_widget.insert("end", line[3:] + "\n", "h2")
                    continue
                if line.startswith('# '):
                    text_widget.insert("end", line[2:] + "\n", "h1")
                    continue
                
                # Handle bullet points
                if line.strip().startswith('- '):
                    text_widget.insert("end", line + "\n", "bullet")
                    continue
                
                # Handle code blocks
                if line.strip().startswith('`') and line.strip().endswith('`'):
                    code = line.strip()[1:-1]
                    text_widget.insert("end", code + "\n", "code")
                    continue
                
                # Handle bold
                while '**' in line:
                    start = line.find('**')
                    end = line.find('**', start + 2)
                    if end == -1: break
                    text_widget.insert("end", line[:start])
                    text_widget.insert("end", line[start+2:end], "bold")
                    line = line[end+2:]
                
                # Handle italic
                while '*' in line:
                    start = line.find('*')
                    end = line.find('*', start + 1)
                    if end == -1: break
                    text_widget.insert("end", line[:start])
                    text_widget.insert("end", line[start+1:end], "italic")
                    line = line[end+1:]
                
                # Handle links
                while '[' in line and '](' in line and ')' in line:
                    start = line.find('[')
                    mid = line.find('](', start)
                    end = line.find(')', mid)
                    if mid == -1 or end == -1: break
                    text_widget.insert("end", line[:start])
                    text_widget.insert("end", line[start+1:mid], "link")
                    line = line[end+1:]
                
                text_widget.insert("end", line + "\n")
            
            # Calculate required height based on content
            text_height = int(text_widget.index('end-1c').split('.')[0])
            text_widget.configure(height=text_height)
            text_widget.configure(state="disabled")
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
