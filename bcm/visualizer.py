import ttkbootstrap as ttk
import tkinter as tk
from .layout_manager import process_layout
from .models import LayoutModel
from .settings import Settings
import os

class CapabilityVisualizer(ttk.Toplevel):
    def __init__(self, parent, model: LayoutModel):
        super().__init__(parent)
        self.title("Capability Model Visualizer")
        self.iconbitmap(os.path.join(os.path.dirname(__file__), "business_capability_model.ico"))
        # Fraction of screen size you want to allow. Adjust as necessary.
        self.max_screen_fraction = 0.8

        # Set a default geometry (optional).
        self.geometry("1200x800")

        # Process layout
        self.settings = Settings()  # Create settings instance
        self.model = process_layout(
            model, self.settings
        )  # Pass settings to process_layout

        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main frame
        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)

        # Canvas setup
        self.canvas = tk.Canvas(self.frame, background="white")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Control-MouseWheel>", self._on_mousewheel)
        self.scale = 1.0

        # Add panning variables
        self._pan_start_x = 0
        self._pan_start_y = 0
        self._panning = False

        # Add mouse bindings for panning
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._pan)
        self.canvas.bind("<ButtonRelease-1>", self._stop_pan)

        # Create a hidden tooltip Toplevel
        self.tooltip = tk.Toplevel(self, bg="yellow", padx=5, pady=5)
        self.tooltip.withdraw()  # Hide by default
        self.tooltip.overrideredirect(True)  # Remove window decorations

        # IMPORTANT: wraplength to set a max width
        self.tooltip_label = ttk.Label(
            self.tooltip,
            padding=5,
            borderwidth=1,
            text="",
            background="white",
            foreground="black",
            wraplength=500,
        )
        self.tooltip_label.pack()

        # List to hold item references so we can bind hover events
        self.item_to_description = {}

        # Draw the model once
        self.draw_model()

        # Optionally, do one automatic resize to content at startup
        self._resize_window_to_content()

        # If you do NOT want further automatic resizing,
        # remove the bind on <Configure> or comment it out.
        # self.bind('<Configure>', self._on_resize)  # <-- remove or comment out

    def _on_mousewheel(self, event):
        """Handle zooming with mouse wheel (Ctrl + Wheel)."""
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale *= 0.9
        self.draw_model()
        
    def draw_box(
        self, x, y, width, height, text, description=None, has_children=False, level=0
    ):
        """Draw a single capability box with text and bind events for tooltip."""
        # Apply scaling
        sx = int(x * self.scale)
        sy = int(y * self.scale)
        sw = int(width * self.scale)
        sh = int(height * self.scale)

        # Determine fill color based on level and whether it's a leaf node
        if not has_children:
            fill_color = self.settings.get("color_leaf")
        else:
            color_key = f"color_{min(level, 6)}"
            fill_color = self.settings.get(color_key)

        # Set corner radius (scaled with the box size)
        radius = min(
            20 * self.scale, sw / 8, sh / 8
        )  # Limit radius to prevent oversized corners

        # Draw rounded rectangle using arcs and lines
        rect_id = self.canvas.create_polygon(
            sx + radius,
            sy,  # Top line start
            sx + sw - radius,
            sy,  # Top line end
            sx + sw,
            sy,  # Top right corner
            sx + sw,
            sy + radius,
            sx + sw,
            sy + sh - radius,  # Right line
            sx + sw,
            sy + sh,  # Bottom right corner
            sx + sw - radius,
            sy + sh,
            sx + radius,
            sy + sh,  # Bottom line
            sx,
            sy + sh,  # Bottom left corner
            sx,
            sy + sh - radius,
            sx,
            sy + radius,  # Left line
            sx,
            sy,  # Top left corner
            sx + radius,
            sy,  # Back to start
            smooth=True,  # This creates the rounded effect
            fill=fill_color,
            outline="black",
            width=2,
        )

        # Calculate a suitable font size
        font_size = min(
            int(10 * self.scale),  # scale-based
            int(sw / (len(text) + 2) * 1.5),  # width-based
            int(sh / 3),  # height-based
        )
        font_size = max(2, font_size)  # minimum

        # Adjust text position if node has children (place near top)
        text_x = sx + sw // 2
        padding = max(font_size + 20, 15)
        text_y = sy + (padding // 2 if has_children else sh // 2)

        text_id = self.canvas.create_text(
            text_x,
            text_y,
            text=text,
            width=max(10, sw - 10),
            font=("TkDefaultFont", font_size),
            anchor="center",
            justify="center",
        )

        # Only bind tooltip if there's a description
        if description:
            self.item_to_description[rect_id] = description
            self.item_to_description[text_id] = description

            # Bind events for enter/leave
            self.canvas.tag_bind(rect_id, "<Enter>", self._show_tooltip)
            self.canvas.tag_bind(rect_id, "<Leave>", self._hide_tooltip)
            self.canvas.tag_bind(text_id, "<Enter>", self._show_tooltip)
            self.canvas.tag_bind(text_id, "<Leave>", self._hide_tooltip)

    def _show_tooltip(self, event):
        """Show the tooltip near the mouse pointer."""
        item = event.widget.find_withtag("current")
        if item:
            item_id = item[0]
            if item_id in self.item_to_description:
                desc = self.item_to_description[item_id]
                # Update tooltip text
                self.tooltip_label.config(text=desc)
                # Position tooltip near the mouse
                x_root = self.winfo_pointerx() + 10
                y_root = self.winfo_pointery() + 10
                self.tooltip.geometry(f"+{x_root}+{y_root}")
                self.tooltip.deiconify()

    def _hide_tooltip(self, event):
        """Hide the tooltip."""
        self.tooltip.withdraw()

    def draw_model(self):
        """Draw the entire capability model."""
        self.canvas.delete("all")  # Clear canvas
        self.item_to_description.clear()

        def draw_node(node: LayoutModel, level=0):
            # Draw current node
            self.draw_box(
                node.x,
                node.y,
                node.width,
                node.height,
                node.name,
                node.description if level > 0 else None,  # Skip tooltip for root
                bool(node.children),
                level,
            )
            # Recursively draw children with incremented level
            for child in node.children or []:
                draw_node(child, level + 1)

        # Draw from the root with level 0
        draw_node(self.model)

        # Update scroll region to fit all elements
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def _resize_window_to_content(self):
        """Resize Toplevel so it fits the drawn content up to a max fraction of screen size (only done once)."""
        bbox = self.canvas.bbox("all")
        if not bbox:
            return

        x1, y1, x2, y2 = bbox
        content_width = x2 - x1
        content_height = y2 - y1

        # Get screen width/height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        max_width = int(screen_width * self.max_screen_fraction)
        max_height = int(screen_height * self.max_screen_fraction)

        # Pick the smaller between content size and max fraction
        new_width = min(content_width, max_width)
        new_height = min(content_height, max_height)

        # Update geometry just once
        self.geometry(f"{new_width}x{new_height}")

    def _start_pan(self, event):
        """Start panning by recording the initial position."""
        self.canvas.configure(cursor="fleur")  # Change cursor to indicate panning
        self.canvas.scan_mark(event.x, event.y)
        self._panning = True

    def _pan(self, event):
        """Pan the canvas based on mouse movement."""
        if not self._panning:
            return
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _stop_pan(self, event):
        """Stop panning."""
        self.canvas.configure(cursor="")  # Reset cursor
        self._panning = False
