import ttkbootstrap as ttk
from typing import Dict
from .models import CapabilityCreate, CapabilityUpdate
from .database import DatabaseOperations

class CapabilityConfirmDialog(ttk.Toplevel):
    # Window geometry constants
    WINDOW_WIDTH = 600
    WINDOW_HEIGHT = 500
    PADDING = 10
    CONTENT_WIDTH = WINDOW_WIDTH - (2 * PADDING)  # Width minus padding
    DESCRIPTION_INDENT = 20
    
    def __init__(self, parent, capabilities: Dict[str, str]):
        super().__init__(parent)
        self.capabilities = capabilities
        self.result = {}
        
        self.title("Confirm Capabilities")
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.position_center()
        self.minsize(400, 300)  # Set minimum size
        self.resizable(True, True)  # Allow window resizing
        
        self._create_widgets()
        self._create_layout()
        
        # Initialize all checkboxes to checked
        for name in capabilities:
            self.checkbox_vars[name].set(True)

    def _create_widgets(self):
        # Create a frame for the message
        self.msg_frame = ttk.Frame(self, padding=self.PADDING)
        self.msg_label = ttk.Label(
            self.msg_frame,
            text="Select capabilities to add:",
            justify="left",
            wraplength=self.CONTENT_WIDTH
        )
        
        # Create a frame for the scrollable list
        self.list_frame = ttk.Frame(self)
        
        # Create canvas and scrollbar for scrolling
        self.canvas = ttk.Canvas(self.list_frame)
        self.scrollbar = ttk.Scrollbar(
            self.list_frame,
            orient="vertical",
            command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind mouse wheel events to the canvas and its children
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        
        # Create frame for checkboxes inside canvas
        self.checkbox_frame = ttk.Frame(self.canvas)
        self.canvas_frame = self.canvas.create_window(
            (0, 0),
            window=self.checkbox_frame,
            anchor="nw",
            width=self.CONTENT_WIDTH
        )
        
        # Create checkboxes
        self.checkbox_vars = {}
        for name, desc in self.capabilities.items():
            var = ttk.BooleanVar()
            self.checkbox_vars[name] = var
            
            # Create frame for each capability
            cap_frame = ttk.Frame(self.checkbox_frame)
            
            # Create checkbox with name
            cb = ttk.Checkbutton(
                cap_frame,
                text=name,
                variable=var,
                style="primary.TCheckbutton"
            )
            cb.pack(anchor="w")
            
            # Create description label
            if desc:
                desc_label = ttk.Label(
                    cap_frame,
                    text=desc,
                    wraplength=self.CONTENT_WIDTH - self.DESCRIPTION_INDENT,
                    justify="left",
                    font=("TkDefaultFont", 9),
                    foreground="gray"
                )
                desc_label.pack(anchor="w", padx=(20, 0))
            
            cap_frame.pack(fill="x", padx=5, pady=2)
        
        # Buttons
        self.btn_frame = ttk.Frame(self, padding=10)
        self.ok_btn = ttk.Button(
            self.btn_frame,
            text="OK",
            command=self._on_ok,
            style="primary.TButton",
            width=10
        )
        self.cancel_btn = ttk.Button(
            self.btn_frame,
            text="Cancel",
            command=self.destroy,
            style="secondary.TButton",
            width=10
        )
        
        # Bind canvas configuration
        self.checkbox_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _create_layout(self):
        # Layout message
        self.msg_frame.pack(fill="x")
        self.msg_label.pack(anchor="w")
        
        # Layout list
        self.list_frame.pack(fill="both", expand=True, padx=self.PADDING)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Layout buttons
        self.btn_frame.pack(fill="x")
        self.cancel_btn.pack(side="right", padx=5)
        self.ok_btn.pack(side="right", padx=5)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Update the canvas window width and text wrapping when the canvas is resized
        new_width = event.width
        self.canvas.itemconfig(self.canvas_frame, width=new_width)
        
        # Update wraplength for message label
        self.msg_label.configure(wraplength=new_width)
        
        # Update wraplength for all description labels
        for child in self.checkbox_frame.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, ttk.Label):
                    widget.configure(wraplength=new_width - self.DESCRIPTION_INDENT - 20)
        
    def _on_mousewheel(self, event):
        # Scroll 2 units for every mouse wheel click
        self.canvas.yview_scroll(int(-1 * (event.delta/120)), "units")

    def _on_ok(self):
        self.result = {
            name: desc
            for name, desc in self.capabilities.items()
            if self.checkbox_vars[name].get()
        }
        self.destroy()

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
