import ttkbootstrap as ttk
from datetime import datetime
from sqlalchemy import select
from ttkbootstrap.tableview import Tableview
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
        self.geometry("1000x600")  # Made wider to accommodate table
        self.iconbitmap("./bcm/business_capability_model.ico")
        
        # Create main frame with table
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Define columns with correct properties
        columns = [
            {"text": "Timestamp", "stretch": False, "width": 150},
            {"text": "Operation", "stretch": False, "width": 100},
            {"text": "Capability", "stretch": True, "width": 200},
            {"text": "Changes", "stretch": True, "width": 400}
        ]
        
        # Configure style for taller rows
        style = ttk.Style()
        style.configure('Treeview', rowheight=60)  # Set row height through style
        
        # Create table with scrollbars and additional configuration
        self.table = Tableview(
            self.main_frame,
            coldata=columns,
            searchable=True,
            autofit=False,
            height=20,
            bootstyle="primary"  # Add bootstyle for better rendering
        )
        
        # Pack the table
        self.table.pack(fill="both", expand=True)
        
        # Add initial loading message
        self.table.insert_row("end", ["Loading audit logs...", "", "", ""])
        
        # Load and display logs
        self.after(100, self.load_logs)
        
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

    def format_changes(self, old_values: dict, new_values: dict) -> str:
        """Format the changes in a readable way."""
        changes = []
        
        if old_values and new_values:
            # Handle updates - show what changed
            for key in set(old_values.keys()) | set(new_values.keys()):
                old_val = old_values.get(key)
                new_val = new_values.get(key)
                if old_val != new_val:
                    if key == 'parent_id':
                        old_name = self.capability_names.get(old_val, f"Unknown (ID: {old_val})") if old_val else "None"
                        new_name = self.capability_names.get(new_val, f"Unknown (ID: {new_val})") if new_val else "None"
                        changes.append(f"Parent: {old_name} → {new_name}")
                    else:
                        changes.append(f"{key}: {old_val} → {new_val}")
        elif new_values:
            # Handle creation - show new values
            for key, value in new_values.items():
                if key == 'parent_id' and value:
                    parent_name = self.capability_names.get(value, f"Unknown (ID: {value})")
                    changes.append(f"Parent: {parent_name}")
                elif key != 'id':  # Skip ID assignments
                    changes.append(f"{key}: {value}")
        elif old_values:
            # Handle deletion - show what was deleted
            for key, value in old_values.items():
                if key == 'parent_id' and value:
                    parent_name = self.capability_names.get(value, f"Unknown (ID: {value})")
                    changes.append(f"Parent was: {parent_name}")
                else:
                    changes.append(f"{key}: {value}")
                    
        return "\n".join(changes)

    async def get_logs(self):
        """Retrieve logs from database."""
        # First get all capabilities to build name mapping
        self.capability_names = {}
        async with await self.db_ops._get_session() as session:
            stmt = select(Capability.id, Capability.name)
            result = await session.execute(stmt)
            for id, name in result:
                self.capability_names[id] = name
        
        logs = await self.db_ops.export_audit_logs()
        
        # Combine CREATE and ID_ASSIGN operations
        combined_logs = []
        create_log = None
        
        for log in logs:
            if log["operation"] == "CREATE":
                create_log = log
            elif log["operation"] == "ID_ASSIGN" and create_log:
                # Merge ID_ASSIGN info into CREATE log
                if create_log["capability_name"] == log["capability_name"]:
                    create_log["capability_id"] = log["capability_id"]
                    continue
            
            if create_log:
                combined_logs.append(create_log)
                create_log = None
            
            if log["operation"] != "ID_ASSIGN":
                combined_logs.append(log)
                
        return combined_logs

    def load_logs(self):
        """Load and display all audit logs."""
        import asyncio
        
        async def load_async():
            try:
                logs = await self.get_logs()
                
                # Use after() to update GUI from the main thread
                self.after(0, lambda: self._populate_table(logs))
                
            except Exception as e:
                print(f"Error loading logs: {str(e)}")
                error_msg = str(e)  # Capture error message
                self.after(0, lambda: self._show_error(error_msg))

        # Get the event loop
        if hasattr(self, '_loop'):
            loop = self._loop
        else:
            loop = asyncio.get_event_loop()
            self._loop = loop

        # Run the async operation
        asyncio.run_coroutine_threadsafe(load_async(), loop)

    def _populate_table(self, logs):
        """Populate the table with logs (runs in main thread)."""
        try:
            # Create list of rows for batch insertion
            rows = []
            for log in logs:
                timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                operation = log["operation"]
                capability = f"{log['capability_name']}"
                if log["capability_id"]:
                    capability += f" (ID: {log['capability_id']})"
                    
                changes = self.format_changes(log["old_values"], log["new_values"])
                
                # Add row to list
                rows.append([timestamp, operation, capability, changes])

            # Clear the loading message and existing data
            self.table.delete_rows()  # This removes all rows including the loading message
            
            if rows:
                # Insert all rows at once
                self.table.insert_rows("end", rows)
                # Load the data into view
                self.table.load_table_data()
            else:
                # Show "No logs found" message if there are no logs
                self.table.insert_row("end", ["No audit logs found", "", "", ""])
                self.table.load_table_data()
                
        except Exception as e:
            print(f"Error populating table: {str(e)}")
            self._show_error(str(e))

    def _show_error(self, error_message):
        """Show error in table (runs in main thread)."""
        self.table.delete_rows()
        self.table.insert_row("end", ["Error", "", "", error_message])
