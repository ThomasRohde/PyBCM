import ttkbootstrap as ttk
from datetime import datetime
import json
from sqlalchemy import select
from .models import Capability

class AuditLogViewer(ttk.Toplevel):
    def __init__(self, parent, db_ops):
        """Initialize the audit log viewer window."""
        super().__init__(parent)
        self.db_ops = db_ops
        
        # Store reference to parent's event loop if available
        if hasattr(parent, 'loop'):
            self._loop = parent.loop
        
        # Configure window
        self.title("Audit Log Viewer")
        self.geometry("800x600")
        self.iconbitmap("./bcm/business_capability_model.ico")
        
        # Create main text widget with scrollbar
        self.text_frame = ttk.Frame(self)
        self.text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.text = ttk.Text(
            self.text_frame,
            wrap="word",
            font=("TkDefaultFont", 10),
            width=80,
            height=30
        )
        self.scrollbar = ttk.Scrollbar(
            self.text_frame,
            orient="vertical",
            command=self.text.yview
        )
        self.text.configure(yscrollcommand=self.scrollbar.set)
        
        # Layout
        self.text.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Add initial loading message
        self.text.insert('end', "Loading audit logs...\n")
        
        # Load and display logs
        self.after(100, self.load_logs)  # Schedule log loading after window creation
        
        # Center window
        self.position_center()
        
    def position_center(self):
        """Center the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
    def format_log_entry(self, log):
        """Format a single log entry into readable text."""
        timestamp = datetime.fromisoformat(log["timestamp"])
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Start with timestamp and operation
        text = f"[{formatted_time}] {log['operation']}\n"
        
        # Add capability info if present
        if log["capability_name"]:
            text += f"Capability: {log['capability_name']}"
            if log["capability_id"]:
                text += f" (ID: {log['capability_id']})"
            text += "\n"
        
        # Format changes - values are already parsed from JSON
        if log["old_values"]:
            text += "Old values:\n"
            for key, value in log["old_values"].items():
                if key == 'parent_id' and value is not None:
                    # Get parent capability name if possible
                    parent_name = self.capability_names.get(value, f"Unknown (ID: {value})")
                    text += f"  {key}: {value} - {parent_name}\n"
                else:
                    text += f"  {key}: {value}\n"
                
        if log["new_values"]:
            text += "New values:\n"
            for key, value in log["new_values"].items():
                if key == 'parent_id' and value is not None:
                    # Get parent capability name if possible
                    parent_name = self.capability_names.get(value, f"Unknown (ID: {value})")
                    text += f"  {key}: {value} - {parent_name}\n"
                else:
                    text += f"  {key}: {value}\n"
                
        return text + "\n"
        
    async def get_logs(self):
        """Retrieve logs from database."""
        # First get all capabilities to build name mapping
        self.capability_names = {}
        async with await self.db_ops._get_session() as session:
            stmt = select(Capability.id, Capability.name)
            result = await session.execute(stmt)
            for id, name in result:
                self.capability_names[id] = name
        
        return await self.db_ops.export_audit_logs()
        
    def load_logs(self):
        """Load and display all audit logs."""
        import asyncio
        
        async def load_async():
            logs = await self.get_logs()
            
            # Clear existing text
            self.text.delete('1.0', 'end')
            
            # Add formatted logs in chronological order (oldest first)
            for log in logs:
                formatted = self.format_log_entry(log)
                self.text.insert('end', formatted)
            
            # Make text read-only
            self.text.configure(state="disabled")

        # Get the event loop
        if hasattr(self, '_loop'):
            loop = self._loop
        else:
            loop = asyncio.get_event_loop()
            self._loop = loop

        # Run the async operation
        try:
            asyncio.run_coroutine_threadsafe(load_async(), loop)
        except Exception as e:
            print(f"Error loading logs: {str(e)}")
            self.text.delete('1.0', 'end')
            self.text.insert('end', f"Error loading logs: {str(e)}\n")
