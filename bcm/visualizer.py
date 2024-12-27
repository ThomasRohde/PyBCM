import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from .layout import process_layout, BOX_MIN_WIDTH, BOX_MIN_HEIGHT
from .models import LayoutModel

class CapabilityVisualizer(ttk.Toplevel):
    def __init__(self, parent, model: LayoutModel):
        super().__init__(parent)
        self.title("Capability Model Visualizer")
        self.geometry("800x600")

        # Process layout
        self.model = process_layout(model)
        
        # Create canvas with scrollbars
        self.frame = ttk.Frame(self)
        self.frame.pack(fill=BOTH, expand=YES)

        self.canvas = tk.Canvas(
            self.frame,
            background='white',
            width=800,
            height=600
        )
        
        # Add scrollbars
        self.v_scrollbar = ttk.Scrollbar(self.frame, orient=VERTICAL)
        self.h_scrollbar = ttk.Scrollbar(self.frame, orient=HORIZONTAL)
        self.v_scrollbar.pack(side=RIGHT, fill=Y)
        self.h_scrollbar.pack(side=BOTTOM, fill=X)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=YES)

        # Configure scrolling
        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)
        self.canvas.config(
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set
        )

        # Enable zooming with mouse wheel
        self.canvas.bind('<Control-MouseWheel>', self._on_mousewheel)
        self.scale = 1.0

        # Draw the model
        self.draw_model()

    def _on_mousewheel(self, event):
        """Handle zooming with mouse wheel."""
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale *= 0.9
        self.draw_model()

    def draw_box(self, x, y, width, height, text, description=None):
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

        # Add text
        font_size = int(10 * self.scale)
        self.canvas.create_text(
            sx + sw//2,  # Integer division
            sy + sh//2,  # Integer division
            text=text,
            width=max(10, sw - 10),  # Ensure minimum width
            font=('TkDefaultFont', font_size),
            anchor='center'
        )

    def draw_connection(self, parent_x, parent_y, parent_w, parent_h, 
                       child_x, child_y, child_w, child_h):
        """Draw a connection line between parent and child boxes."""
        # Calculate connection points and convert to integers
        start_x = int((parent_x + parent_w/2) * self.scale)
        start_y = int((parent_y + parent_h) * self.scale)
        end_x = int((child_x + child_w/2) * self.scale)
        end_y = int(child_y * self.scale)
        mid_y = start_y + (end_y - start_y)//2  # Integer division

        # Draw line
        self.canvas.create_line(
            start_x, start_y,
            start_x, mid_y,
            end_x, mid_y,
            end_x, end_y,
            smooth=True,
            width=2
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
                node.description
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
