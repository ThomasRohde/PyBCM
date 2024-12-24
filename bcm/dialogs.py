import ttkbootstrap as ttk
from ttkbootstrap.constants import END
from typing import Optional
from .models import CapabilityCreate, CapabilityUpdate
from .database import DatabaseOperations

def create_dialog(
    parent,
    title: str,
    message: str,
    default_result: bool = False,
    ok_only: bool = False
) -> bool:
    """Create a generic dialog."""
    dialog = ttk.Toplevel(parent)
    dialog.withdraw()  # Hide the window initially
    dialog.title(title)
    
    # Remove window controls
    dialog.resizable(False, False)
    dialog.overrideredirect(True)
    
    # Create border frame
    border_frame = ttk.Frame(dialog, borderwidth=1, relief="solid")
    border_frame.pack(fill="both", expand=True, padx=2, pady=2)
    
    # Create content frame
    frame = ttk.Frame(border_frame, padding=20)
    frame.pack(fill="both", expand=True)
    
    msg_label = ttk.Label(
        frame,
        text=message,
        justify="center",
        wraplength=400  # Set wrap length to accommodate text
    )
    msg_label.pack(expand=True)
    
    dialog.result = default_result
    
    if ok_only:
        ttk.Button(
            frame,
            text="OK",
            command=lambda: [setattr(dialog, 'result', True), dialog.destroy()],
            style="primary.TButton",
            width=10
        ).pack(pady=(0, 10))
    else:
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="Yes",
            command=lambda: [setattr(dialog, 'result', True), dialog.destroy()],
            style="primary.TButton",
            width=10
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="No",
            command=lambda: [setattr(dialog, 'result', False), dialog.destroy()],
            style="secondary.TButton",
            width=10
        ).pack(side="left", padx=5)
    
    # Show the window and adjust size to content
    dialog.deiconify()
    
    # Update dialog to calculate required size
    dialog.update_idletasks()
    
    # Get required size
    width = max(400, frame.winfo_reqwidth() + 44)  # Add padding
    height = frame.winfo_reqheight() + 44  # Add padding
    
    # Set size and center
    dialog.geometry(f"{width}x{height}")
    dialog.position_center()
    
    dialog.wait_window()
    return dialog.result

class CapabilityDialog(ttk.Toplevel):
    def __init__(self, parent, db_ops: DatabaseOperations, capability=None, parent_id=None):
        super().__init__(parent)
        self.db_ops = db_ops
        self.capability = capability
        self.parent_id = parent_id
        self.result = None

        self.title("Edit Capability" if capability else "New Capability")
        self.geometry("400x200")
        self.position_center()

        self._create_widgets()
        self._create_layout()

        if capability:
            self.name_var.set(capability.name)
            self.desc_var.set(capability.description or "")

    def _create_widgets(self):
        # Labels
        self.name_label = ttk.Label(self, text="Name:")
        self.desc_label = ttk.Label(self, text="Description:")
        
        # Entry fields
        self.name_var = ttk.StringVar()
        self.name_entry = ttk.Entry(self, textvariable=self.name_var)
        
        self.desc_var = ttk.StringVar()
        self.desc_entry = ttk.Entry(self, textvariable=self.desc_var)

        # Buttons
        self.ok_btn = ttk.Button(
            self,
            text="OK",
            command=self._on_ok,
            style="primary.TButton"
        )
        self.cancel_btn = ttk.Button(
            self,
            text="Cancel",
            command=self.destroy,
            style="secondary.TButton"
        )

    def _create_layout(self):
        self.name_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        self.desc_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.desc_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        self.ok_btn.grid(row=2, column=1, padx=5, pady=10)
        self.cancel_btn.grid(row=2, column=2, padx=5, pady=10)

        self.columnconfigure(1, weight=1)

    def _on_ok(self):
        name = self.name_var.get().strip()
        if not name:
            return

        if self.capability:
            self.result = CapabilityUpdate(
                name=name,
                description=self.desc_var.get().strip()
            )
        else:
            self.result = CapabilityCreate(
                name=name,
                description=self.desc_var.get().strip(),
                parent_id=self.parent_id
            )
        self.destroy()
