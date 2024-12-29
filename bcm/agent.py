import asyncio
import threading
import tkinter as tk
import ttkbootstrap as ttk
from pydantic_ai import Agent
from typing import List
from datetime import datetime

# Initialize the agent at module level
agent = Agent('ollama:llama3.2', system_prompt='You are a helpful assistant.')

class Message:
    def __init__(self, content: str, is_user: bool, timestamp: datetime = None):
        self.content = content
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()

class ChatDialog(ttk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("AI Chat")
        
        # Initialize message history
        self.messages: List[Message] = []
        self.ai_response_labels = {}  # Dictionary to store AI response labels
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
        
        # Canvas to hold the chat messages
        self.chat_canvas = tk.Canvas(self.chat_frame, yscrollcommand=self.scrollbar.set)
        self.chat_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.chat_canvas.yview)
        
        # Frame inside the canvas to hold the messages
        self.messages_frame = ttk.Frame(self.chat_canvas)
        self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        
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
            # Create a new label for the AI response
            ai_label = ttk.Label(
                self.messages_frame,
                text=f"{sender}: {message}",
                wraplength=self.chat_canvas.winfo_width()-20,
                anchor="w",
                justify="left"
            )
            ai_label.pack(fill="x", expand=True, padx=5, pady=2)
            self.ai_response_labels[len(self.messages)] = ai_label
        else:
            # Display user messages
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
        """Update an AI response label with new content."""
        if message_index in self.ai_response_labels:
            label = self.ai_response_labels[message_index]
            label.config(text=f"{sender}: {message}")
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
            # Re-enable input in main thread
            self.after(0, lambda: [
                self.entry.configure(state="normal"),
                self.send_button.configure(state="normal"),
                self.entry.focus_set()
            ])
    
    def _on_closing(self):
        """Handle window closing."""
        self.destroy()

def show_chat_dialog(parent):
    """Show the chat dialog."""
    try:
        dialog = ChatDialog(parent)
        return dialog
    except Exception as e:
        raise e
