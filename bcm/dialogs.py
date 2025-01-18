import asyncio
import ttkbootstrap as ttk
from typing import Dict
from bcm.models import CapabilityCreate, CapabilityUpdate
from bcm.database import DatabaseOperations
import os

class CapabilityConfirmDialog(ttk.Toplevel):
    # Window geometry constants
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    PADDING = 10
    CONTENT_WIDTH = WINDOW_WIDTH - (2 * PADDING)  # Width minus padding

    def __init__(self, parent, capabilities: Dict[str, str]):
        super().__init__(parent)
        self.withdraw()  # Hide the window initially
        self.iconbitmap(os.path.join(os.path.dirname(__file__), "business_capability_model.ico"))
        self.capabilities = capabilities
        self.result = {}

        self.title("Confirm Capabilities")
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.position_center()
        self.minsize(500, 450)  # Set minimum size
        self.resizable(True, True)  # Allow window resizing
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._create_layout()

        # Initialize all checkboxes to checked
        for name in capabilities:
            self.checkbox_vars[name].set(True)

        self.deiconify()  # Show the window

    def _create_widgets(self):
        # Create a frame for the message
        self.msg_frame = ttk.Frame(self, padding=self.PADDING)
        self.msg_label = ttk.Label(
            self.msg_frame,
            text="Select capabilities to add:",
            justify="left",
            wraplength=self.CONTENT_WIDTH,
        )

        # Create a frame for the scrollable list
        self.list_frame = ttk.Frame(self)

        # Create canvas and scrollbar for scrolling
        self.canvas = ttk.Canvas(self.list_frame)
        self.scrollbar = ttk.Scrollbar(
            self.list_frame, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Bind mouse wheel events to the canvas and its children
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind(
            "<Enter>",
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel),
        )
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        # Create frame for checkboxes inside canvas
        self.checkbox_frame = ttk.Frame(self.canvas)
        self.canvas_frame = self.canvas.create_window(
            (0, 0), window=self.checkbox_frame, anchor="nw", width=self.CONTENT_WIDTH
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
                cap_frame, text=name, variable=var, style="primary.TCheckbutton"
            )
            cb.pack(anchor="w")

            # Create description label
            if desc:
                desc_label = ttk.Label(
                    cap_frame,
                    text=desc,
                    wraplength=self.CONTENT_WIDTH,
                    justify="left",
                    font=("TkDefaultFont", 9),
                    foreground="gray",
                )
                desc_label.pack(anchor="w")

            cap_frame.pack(fill="x", padx=5, pady=2)

        # Buttons
        self.btn_frame = ttk.Frame(self, padding=10)
        self.ok_btn = ttk.Button(
            self.btn_frame,
            text="OK",
            command=self._on_ok,
            style="primary.TButton",
            width=10,
        )
        self.cancel_btn = ttk.Button(
            self.btn_frame,
            text="Cancel",
            command=self.destroy,
            style="secondary.TButton",
            width=10,
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
                    widget.configure(wraplength=new_width)

    def _on_mousewheel(self, event):
        # Scroll 2 units for every mouse wheel click
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

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
    ok_only: bool = False,
) -> bool:
    """Create a generic dialog."""
    dialog = ttk.Toplevel(parent)
    dialog.withdraw()  # Hide the window initially
    dialog.title(title)
    
    # Make dialog modal
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

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
        wraplength=400,  # Set wrap length to accommodate text
    )
    msg_label.pack(expand=True)

    dialog.result = default_result

    if ok_only:
        ttk.Button(
            frame,
            text="OK",
            command=lambda: [setattr(dialog, "result", True), dialog.destroy()],
            style="primary.TButton",
            width=10,
        ).pack(pady=(0, 10))
    else:
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(0, 10))

        ttk.Button(
            btn_frame,
            text="Yes",
            command=lambda: [setattr(dialog, "result", True), dialog.destroy()],
            style="primary.TButton",
            width=10,
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="No",
            command=lambda: [setattr(dialog, "result", False), dialog.destroy()],
            style="secondary.TButton",
            width=10,
        ).pack(side="left", padx=5)

    # Show the window and adjust size to content
    dialog.deiconify()
    
    # Grab focus for the dialog
    dialog.focus_force()

    # Bind escape key to close dialog
    dialog.winfo_toplevel().bind("<Escape>", lambda event: dialog.destroy())

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
    def __init__(
        self, parent, db_ops: DatabaseOperations, capability=None, parent_id=None
    ):
        super().__init__(parent)
        self.iconbitmap(os.path.join(os.path.dirname(__file__), "business_capability_model.ico"))
        self.db_ops = db_ops
        self.capability = capability
        self.parent_id = parent_id
        self.result = None

        self.title("Edit Capability" if capability else "New Capability")
        self.geometry("600x450")
        self.minsize(400, 450)
        self.position_center()
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._create_layout()

        if capability:
            self.name_var.set(capability.name)
            self.desc_text.insert("1.0", capability.description or "")

    def _create_widgets(self):
        # Main content frame with padding
        self.content_frame = ttk.Frame(self, padding=15)

        # Labels
        self.name_label = ttk.Label(self.content_frame, text="Name:")
        self.desc_label = ttk.Label(self.content_frame, text="Description:")

        # Entry field for name
        self.name_var = ttk.StringVar()
        self.name_entry = ttk.Entry(self.content_frame, textvariable=self.name_var)

        # Frame for Text widget and scrollbar
        self.desc_frame = ttk.Frame(self.content_frame)

        # Text widget for description
        self.desc_text = ttk.Text(
            self.desc_frame,
            width=40,
            height=10,  # Increased height
            wrap="word",
            font=("TkDefaultFont", 10),
        )

        # Scrollbar for description
        self.desc_scrollbar = ttk.Scrollbar(
            self.desc_frame, orient="vertical", command=self.desc_text.yview
        )
        self.desc_text.configure(yscrollcommand=self.desc_scrollbar.set)

        # Button frame
        self.button_frame = ttk.Frame(self.content_frame)

        # Buttons
        self.ok_btn = ttk.Button(
            self.button_frame,
            text="OK",
            command=self._on_ok,
            style="primary.TButton",
            width=10,
        )
        self.cancel_btn = ttk.Button(
            self.button_frame,
            text="Cancel",
            command=self.destroy,
            style="secondary.TButton",
            width=10,
        )

    def _create_layout(self):
        # Layout main content frame
        self.content_frame.pack(fill="both", expand=True)

        # Layout name field
        self.name_label.pack(anchor="w", pady=(0, 2))
        self.name_entry.pack(fill="x", pady=(0, 15))

        # Layout description field
        self.desc_label.pack(anchor="w", pady=(0, 2))
        self.desc_frame.pack(fill="both", expand=True, pady=(0, 15))
        self.desc_scrollbar.pack(side="right", fill="y")
        self.desc_text.pack(side="left", fill="both", expand=True)

        # Layout buttons
        self.button_frame.pack(fill="x")
        self.cancel_btn.pack(side="right", padx=(5, 0))
        self.ok_btn.pack(side="right")

    async def _on_ok_async(self):
        """Async version of ok handler."""
        name = self.name_var.get().strip()
        if not name:
            return

        if self.capability:
            self.result = CapabilityUpdate(
                name=name, description=self.desc_text.get("1.0", "end-1c").strip()
            )
        else:
            self.result = CapabilityCreate(
                name=name,
                description=self.desc_text.get("1.0", "end-1c").strip(),
                parent_id=self.parent_id,
            )
        self.destroy()

    def _on_ok(self):
        """Sync wrapper for async ok handler."""
        asyncio.run_coroutine_threadsafe(self._on_ok_async(), asyncio.get_event_loop())
