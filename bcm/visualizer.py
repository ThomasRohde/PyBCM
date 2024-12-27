import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, YES, VERTICAL, HORIZONTAL, LEFT, RIGHT, Y, X, BOTTOM
import tkinter as tk
from .layout import process_layout
from .models import LayoutModel

class CapabilityVisualizer(ttk.Toplevel):
    def __init__(self, parent, model: LayoutModel):
        super().__init__(parent)
        self.title("Capability Model Visualizer")
        self.geometry("1200x800")

        # Process layout
        self.model = process_layout(model)
        
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create frame with grid weights
        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.frame,
            background='white'
        )
        
        # Add scrollbars with grid
        self.v_scrollbar = ttk.Scrollbar(self.frame, orient=VERTICAL)
        self.h_scrollbar = ttk.Scrollbar(self.frame, orient=HORIZONTAL)
        
        # Configure grid layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure frame grid weights
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)

        # Configure scrolling
        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)
        self.canvas.config(
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set
        )

        # Bind resize event
        self.bind('<Configure>', self._on_resize)

        # Enable zooming with mouse wheel
        self.canvas.bind('<Control-MouseWheel>', self._on_mousewheel)
        self.scale = 1.0

        # Draw the model
        self.draw_model()

    def _on_resize(self, event):
        """Handle window resize events."""
        # Update canvas size
        self.canvas.config(width=event.width, height=event.height)
        self.draw_model()

    def _on_mousewheel(self, event):
        """Handle zooming with mouse wheel."""
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale *= 0.9
        self.draw_model()

    def draw_box(self, x, y, width, height, text, description=None, has_children=False):
        """Draw a single capability box with text."""
        # Apply scaling and convert to integers
        sx = int(x * self.scale)
        sy = int(y * self.scale)
        sw = int(width * self.scale)
        sh = int(height * self.scale)

        # Create box
        self.canvas.create_rectangle(
            sx, sy, sx + sw, sy + sh,
            fill='white',
            outline='black',
            width=2
        )

        # Calculate adaptive font size based on box dimensions
        # and scale factor
        font_size = min(
            int(10 * self.scale),  # Scale-based size
            int(sw / (len(text) + 2) * 1.5),  # Width-based size
            int(sh / 3)  # Height-based size
        )
        font_size = max(8, font_size)  # Minimum font size

        # Calculate text position - adjust y coordinate if has children
        text_x = int(sx + sw/2)
        padding = max(font_size + 2, 15)  # Add padding based on font size
        text_y = int(sy + (padding if has_children else sh/2))  # Place text just below top line if has children

        self.canvas.create_text(
            text_x,
            text_y,
            text=text,
            width=max(10, sw - 10),
            font=('TkDefaultFont', font_size),
            anchor='center'
        )

    def draw_model(self):
        """Draw the entire capability model."""
        self.canvas.delete('all')  # Clear canvas

        def draw_node(node: LayoutModel):
            # Draw current node
            self.draw_box(
                node.x, node.y,
                node.width, node.height,
                node.name,
                node.description,
                bool(node.children)  # Pass whether node has children
            )

            # Draw children and connections
            if node.children:
                for child in node.children:
                    draw_node(child)

        # Draw the model starting from root
        draw_node(self.model)

        # Update canvas scroll region
        self.canvas.config(
            scrollregion=self.canvas.bbox('all')
        )
