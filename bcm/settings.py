import json
import ttkbootstrap as ttk
from pathlib import Path
from pydantic_ai import models
from typing import get_args
from tkinter import colorchooser  # For color selection

BOX_MIN_WIDTH_DEFAULT = 120
BOX_MIN_HEIGHT_DEFAULT = 80
HORIZONTAL_GAP_DEFAULT = 20
VERTICAL_GAP_DEFAULT = 20
PADDING_DEFAULT = 30
TOP_PADDING_DEFAULT = 40  # Slightly larger than standard padding by default
DEFAULT_TARGET_ASPECT_RATIO_DEFAULT = 1.0

DEFAULT_SETTINGS = {
    "theme": "litera",           # Default ttkbootstrap theme
    "max_ai_capabilities": 10,   # Default max number of AI-generated capabilities
    "font_size": 10,             # Default font size for main text content
    "model": "openai:gpt-4o",    # Default model
    # Layout
    "root_font_size": 20,        # Default root font size for layout
    "box_min_width": BOX_MIN_WIDTH_DEFAULT,
    "box_min_height": BOX_MIN_HEIGHT_DEFAULT,
    "horizontal_gap": HORIZONTAL_GAP_DEFAULT,
    "vertical_gap": VERTICAL_GAP_DEFAULT,
    "padding": PADDING_DEFAULT,
    "top_padding": TOP_PADDING_DEFAULT,  # New setting for vertical padding between parent and first child
    "target_aspect_ratio": DEFAULT_TARGET_ASPECT_RATIO_DEFAULT,
    "max_level": 6,  # Add default max level
    # Color settings for hierarchy levels + leaf nodes
    "color_0": "#5B8C85",   # Muted teal
    "color_1": "#6B5B95",   # Muted purple
    "color_2": "#806D5B",   # Muted brown
    "color_3": "#5B7065",   # Muted sage
    "color_4": "#8B635C",   # Muted rust
    "color_5": "#707C8C",   # Muted steel blue
    "color_6": "#7C6D78",   # Muted mauve
    "color_leaf": "#E0E0E0" # Light grey
}

# Available themes in ttkbootstrap
AVAILABLE_THEMES = [
    "cosmo",
    "flatly",
    "litera",
    "minty",
    "lumen",
    "sandstone",
    "yeti",
    "pulse",
    "united",
    "morph",
    "journal",
    "darkly",
    "superhero",
    "solar",
    "cyborg",
    "vapor",
]

class Settings:
    def __init__(self):
        self.settings_dir = Path.home() / ".pybcm"
        self.settings_file = self.settings_dir / "settings.json"
        self.settings = self._load_settings()

    def _load_settings(self):
        """Load settings from file or create with defaults if not exists."""
        try:
            self.settings_dir.mkdir(exist_ok=True)
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    # Merge loaded settings with DEFAULT_SETTINGS
                    return {**DEFAULT_SETTINGS, **json.load(f)}
            return DEFAULT_SETTINGS.copy()
        except Exception as e:
            print(f"Error loading settings: {e}")
            return DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """Save current settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        """Get a setting value."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a setting value and save."""
        self.settings[key] = value
        self.save_settings()

class SettingsDialog(ttk.Toplevel):
    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        self.settings = settings
        self.result = None
        self.iconbitmap("./bcm/business_capability_model.ico")
        self.title("Settings")
        self.geometry("600x700")
        self.position_center()
        self.resizable(False, False)

        # Create all variables that will be used in the UI
        # Look & Feel
        self.theme_var = ttk.StringVar()
        self.max_cap_var = ttk.StringVar()
        self.font_size_var = ttk.StringVar()
        self.model_var = ttk.StringVar()

        # Layout
        self.root_font_size_var = ttk.StringVar()
        self.box_min_width_var = ttk.StringVar()
        self.box_min_height_var = ttk.StringVar()
        self.horizontal_gap_var = ttk.StringVar()
        self.vertical_gap_var = ttk.StringVar()
        self.padding_var = ttk.StringVar()
        self.top_padding_var = ttk.StringVar()  # New variable for top padding
        self.target_aspect_ratio_var = ttk.StringVar()
        self.max_level_var = ttk.StringVar()

        # Colors
        self.color_0_var = ttk.StringVar()
        self.color_1_var = ttk.StringVar()
        self.color_2_var = ttk.StringVar()
        self.color_3_var = ttk.StringVar()
        self.color_4_var = ttk.StringVar()
        self.color_5_var = ttk.StringVar()
        self.color_6_var = ttk.StringVar()
        self.color_leaf_var = ttk.StringVar()

        # Build the UI
        self._create_widgets()
        self._create_layout()

        # Load current settings into UI
        # Look & Feel
        self.theme_var.set(self.settings.get("theme"))
        self.max_cap_var.set(str(self.settings.get("max_ai_capabilities")))
        self.font_size_var.set(str(self.settings.get("font_size")))
        self.model_var.set(self.settings.get("model"))

        # Layout
        self.root_font_size_var.set(str(self.settings.get("root_font_size")))
        self.box_min_width_var.set(str(self.settings.get("box_min_width")))
        self.box_min_height_var.set(str(self.settings.get("box_min_height")))
        self.horizontal_gap_var.set(str(self.settings.get("horizontal_gap")))
        self.vertical_gap_var.set(str(self.settings.get("vertical_gap")))
        self.padding_var.set(str(self.settings.get("padding")))
        self.top_padding_var.set(str(self.settings.get("top_padding")))  # Load top padding setting
        self.target_aspect_ratio_var.set(str(self.settings.get("target_aspect_ratio")))
        self.max_level_var.set(str(self.settings.get("max_level")))

        # Colors
        self.color_0_var.set(self.settings.get("color_0"))
        self.color_1_var.set(self.settings.get("color_1"))
        self.color_2_var.set(self.settings.get("color_2"))
        self.color_3_var.set(self.settings.get("color_3"))
        self.color_4_var.set(self.settings.get("color_4"))
        self.color_5_var.set(self.settings.get("color_5"))
        self.color_6_var.set(self.settings.get("color_6"))
        self.color_leaf_var.set(self.settings.get("color_leaf"))

    def _create_widgets(self):
        """Create and initialize all the widgets."""

        # Create a Notebook for tabbed settings
        self.notebook = ttk.Notebook(self)

        # --------------------
        # 1) LOOK & FEEL TAB
        # --------------------
        self.look_frame = ttk.Frame(self.notebook)

        # Font size
        self.font_frame = ttk.LabelFrame(self.look_frame, text="Text Settings", padding=10)
        self.font_size_label = ttk.Label(self.font_frame, text="Font size:")
        self.font_size_entry = ttk.Entry(self.font_frame, textvariable=self.font_size_var, width=5)

        # Theme selection
        self.theme_frame = ttk.LabelFrame(self.look_frame, text="Visual Theme", padding=10)
        self.theme_combo = ttk.Combobox(
            self.theme_frame,
            textvariable=self.theme_var,
            values=AVAILABLE_THEMES,
            state="readonly"
        )

        # ----------------------
        # 2) AI GENERATION TAB
        # ----------------------
        self.ai_frame = ttk.Frame(self.notebook)

        # Max capabilities
        self.cap_frame = ttk.LabelFrame(self.ai_frame, text="AI Generation Settings", padding=10)
        self.max_cap_label = ttk.Label(self.cap_frame, text="Maximum capabilities to generate:")
        self.max_cap_entry = ttk.Entry(self.cap_frame, textvariable=self.max_cap_var, width=5)

        # Model selection
        self.model_frame = ttk.LabelFrame(self.ai_frame, text="Model Selection", padding=10)
        self.model_combo = ttk.Combobox(
            self.model_frame,
            textvariable=self.model_var,
            values=[
                model for model in get_args(models.KnownModelName)
                if not model.startswith(("groq:", "mistral:", "vertexai:"))
            ],
            state="readonly"
        )

        # ---------------
        # 3) LAYOUT TAB
        # ---------------
        self.layout_frame = ttk.Frame(self.notebook)

        self.layout_settings_frame = ttk.LabelFrame(
            self.layout_frame,
            text="Layout Settings",
            padding=10
        )

        # box_min_width
        self.box_min_width_label = ttk.Label(self.layout_settings_frame, text="Box Min Width:")
        self.box_min_width_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.box_min_width_var,
            width=6
        )

        # box_min_height
        self.box_min_height_label = ttk.Label(self.layout_settings_frame, text="Box Min Height:")
        self.box_min_height_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.box_min_height_var,
            width=6
        )

        # horizontal_gap
        self.horizontal_gap_label = ttk.Label(self.layout_settings_frame, text="Horizontal Gap:")
        self.horizontal_gap_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.horizontal_gap_var,
            width=6
        )

        # vertical_gap
        self.vertical_gap_label = ttk.Label(self.layout_settings_frame, text="Vertical Gap:")
        self.vertical_gap_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.vertical_gap_var,
            width=6
        )

        # padding
        self.padding_label = ttk.Label(self.layout_settings_frame, text="Padding:")
        self.padding_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.padding_var,
            width=6
        )

        # top_padding
        self.top_padding_label = ttk.Label(self.layout_settings_frame, text="Top Padding:")
        self.top_padding_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.top_padding_var,
            width=6
        )

        # target_aspect_ratio
        self.aspect_ratio_label = ttk.Label(
            self.layout_settings_frame,
            text="Target Aspect Ratio:"
        )
        self.aspect_ratio_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.target_aspect_ratio_var,
            width=6
        )

        # max_level
        self.max_level_label = ttk.Label(self.layout_settings_frame, text="Max Level:")
        self.max_level_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.max_level_var,
            width=6
        )

        # --------------
        # 4) COLOR TAB
        # --------------
        self.color_frame = ttk.Frame(self.notebook)
        self.color_settings_frame = ttk.LabelFrame(
            self.color_frame,
            text="Color Settings for Hierarchy",
            padding=10
        )

        # We'll create one row per level (0–6) plus leaf
        self.color_labels = []
        self.color_buttons = []
        self.color_previews = []
        self.color_vars = [
            ("Level 0", self.color_0_var),
            ("Level 1", self.color_1_var),
            ("Level 2", self.color_2_var),
            ("Level 3", self.color_3_var),
            ("Level 4", self.color_4_var),
            ("Level 5", self.color_5_var),
            ("Level 6", self.color_6_var),
            ("Leaf", self.color_leaf_var)
        ]

        # We'll store references so we can grid them properly.
        for i, (label_text, var) in enumerate(self.color_vars):
            lbl = ttk.Label(self.color_settings_frame, text=f"{label_text} Color:")
            btn = ttk.Button(
                self.color_settings_frame,
                textvariable=var,
                command=lambda v=var, i=i: self._choose_color(v),
                width=15
            )
            style_name = f'Preview{i}.TFrame'  # Create unique style name
            preview = ttk.Frame(
                self.color_settings_frame,
                width=20,
                height=20,
                style=style_name
            )
            # Ensure the frame stays at requested size
            preview.pack_propagate(False)
            
            self.color_labels.append(lbl)
            self.color_buttons.append(btn)
            self.color_previews.append((preview, style_name))  # Store style name with preview
            
            # Update preview when variable changes
            var.trace_add('write', lambda *args, p=preview, v=var, s=style_name: self._update_preview(p, v.get(), s))
            # Initialize the preview color
            self._update_preview(preview, var.get(), style_name)

        # Note about theme
        self.note_label = ttk.Label(
            self,
            text="Some changes will take effect after restart",
            font=("TkDefaultFont", 9),
            foreground="gray"
        )

        # Buttons
        self.btn_frame = ttk.Frame(self)
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

    def _create_layout(self):
        """Lay out all the widgets in the dialog."""

        # --------------------
        # 1) LOOK & FEEL TAB
        # --------------------
        self.look_frame.pack(fill="both", expand=True)

        # Font frame layout
        self.font_frame.pack(fill="x", padx=10, pady=(10, 5))
        self.font_size_label.pack(side="left", padx=(0, 5))
        self.font_size_entry.pack(side="left")

        # Theme frame layout
        self.theme_frame.pack(fill="x", padx=10, pady=5)
        self.theme_combo.pack(fill="x")

        # ----------------------
        # 2) AI GENERATION TAB
        # ----------------------
        self.ai_frame.pack(fill="both", expand=True)

        self.cap_frame.pack(fill="x", padx=10, pady=(10, 5))
        self.max_cap_label.pack(anchor="w")
        self.max_cap_entry.pack(anchor="w")

        self.model_frame.pack(fill="x", padx=10, pady=5)
        self.model_combo.pack(fill="x")

        # ---------------
        # 3) LAYOUT TAB
        # ---------------
        self.layout_frame.pack(fill="both", expand=True)
        self.layout_settings_frame.pack(fill="x", padx=10, pady=10)

        # Row 1
        self.box_min_width_label.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky="w")
        self.box_min_width_entry.grid(row=0, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        self.box_min_height_label.grid(row=0, column=2, padx=(10, 5), pady=(0, 5), sticky="w")
        self.box_min_height_entry.grid(row=0, column=3, padx=(0, 10), pady=(0, 5), sticky="w")

        # Row 2
        self.horizontal_gap_label.grid(row=1, column=0, padx=(0, 5), pady=(5, 5), sticky="w")
        self.horizontal_gap_entry.grid(row=1, column=1, padx=(0, 10), pady=(5, 5), sticky="w")

        self.vertical_gap_label.grid(row=1, column=2, padx=(10, 5), pady=(5, 5), sticky="w")
        self.vertical_gap_entry.grid(row=1, column=3, padx=(0, 10), pady=(5, 5), sticky="w")

        # Row 3
        self.padding_label.grid(row=2, column=0, padx=(0, 5), pady=(5, 5), sticky="w")
        self.padding_entry.grid(row=2, column=1, padx=(0, 10), pady=(5, 5), sticky="w")

        self.top_padding_label.grid(row=2, column=2, padx=(10, 5), pady=(5, 5), sticky="w")
        self.top_padding_entry.grid(row=2, column=3, padx=(0, 10), pady=(5, 5), sticky="w")

        # Row 4
        self.aspect_ratio_label.grid(row=3, column=0, padx=(0, 5), pady=(5, 5), sticky="w")
        self.aspect_ratio_entry.grid(row=3, column=1, padx=(0, 10), pady=(5, 5), sticky="w")

        # Root font size
        self.root_font_size_label = ttk.Label(self.layout_settings_frame, text="Root Font Size:")
        self.root_font_size_entry = ttk.Entry(
            self.layout_settings_frame,
            textvariable=self.root_font_size_var,
            width=6
        )

        # Row 5
        self.root_font_size_label.grid(row=4, column=0, padx=(0, 5), pady=(5, 5), sticky="w")
        self.root_font_size_entry.grid(row=4, column=1, padx=(0, 10), pady=(5, 5), sticky="w")

        # Row 6
        self.max_level_label.grid(row=5, column=0, padx=(0, 5), pady=(5, 5), sticky="w")
        self.max_level_entry.grid(row=5, column=1, padx=(0, 10), pady=(5, 5), sticky="w")

        # --------------
        # 4) COLOR TAB
        # --------------
        self.color_frame.pack(fill="both", expand=True)
        self.color_settings_frame.pack(fill="x", padx=10, pady=10)

        for i, (lbl, btn, preview) in enumerate(zip(self.color_labels, self.color_buttons, self.color_previews)):
            lbl.grid(row=i, column=0, sticky="w", padx=(0, 5), pady=5)
            btn.grid(row=i, column=1, sticky="w", padx=(0, 10), pady=5)
            preview[0].grid(row=i, column=2, sticky="w", padx=5, pady=5)
            # Initialize preview color with the current variable value
            var = self.color_vars[i][1]  # Get the StringVar from color_vars
            self._update_preview(preview[0], var.get(), preview[1])

        # Add tabs to Notebook
        self.notebook.add(self.look_frame, text="Look & Feel")
        self.notebook.add(self.ai_frame, text="AI Generation")
        self.notebook.add(self.layout_frame, text="Layout")
        self.notebook.add(self.color_frame, text="Coloring")

        # Notebook in main window
        self.notebook.pack(expand=True, fill="both", padx=10, pady=(10, 0))

        # Note label (below the notebook)
        self.note_label.pack(pady=10)

        # Buttons
        self.btn_frame.pack(fill="x", padx=10, pady=10)
        self.cancel_btn.pack(side="right", padx=5)
        self.ok_btn.pack(side="right", padx=5)

    def _update_preview(self, preview_frame, color, style_name):
        """Update the color preview frame using a unique style name."""
        style = ttk.Style()
        style.configure(style_name, background=color, relief="solid", borderwidth=1)
        preview_frame.configure(style=style_name)

    def _choose_color(self, color_var: ttk.StringVar):
        """Open a color chooser dialog and set the variable."""
        initial_color = color_var.get()
        chosen_color = colorchooser.askcolor(
            initialcolor=initial_color,
            parent=self,
            title="Choose Color"
        )
        if chosen_color[1]:  # If user did not cancel
            color_var.set(chosen_color[1])

    def _validate_settings(self):
        """Validate settings before saving."""
        from .dialogs import create_dialog  # import inside the method to avoid circular import issues
        try:
            # AI
            max_cap = int(self.max_cap_var.get())
            if max_cap < 1:
                raise ValueError("Maximum capabilities must be at least 1")
            if max_cap > 10:
                raise ValueError("Maximum capabilities cannot exceed 10")

            # Font
            font_size = int(self.font_size_var.get())
            if font_size < 8:
                raise ValueError("Font size must be at least 8")
            if font_size > 24:
                raise ValueError("Font size cannot exceed 24")

            # Layout
            box_min_width = int(self.box_min_width_var.get())
            if box_min_width < 10:
                raise ValueError("Box Min Width must be at least 10")

            box_min_height = int(self.box_min_height_var.get())
            if box_min_height < 10:
                raise ValueError("Box Min Height must be at least 10")

            horizontal_gap = int(self.horizontal_gap_var.get())
            if horizontal_gap < 0:
                raise ValueError("Horizontal Gap cannot be negative")

            vertical_gap = int(self.vertical_gap_var.get())
            if vertical_gap < 0:
                raise ValueError("Vertical Gap cannot be negative")

            padding = int(self.padding_var.get())
            if padding < 0:
                raise ValueError("Padding cannot be negative")

            top_padding = int(self.top_padding_var.get())
            if top_padding < 0:
                raise ValueError("Top Padding cannot be negative")

            aspect_ratio = float(self.target_aspect_ratio_var.get())
            if aspect_ratio <= 0.0:
                raise ValueError("Target Aspect Ratio must be greater than 0")

            # Root font size validation
            root_font_size = int(self.root_font_size_var.get())
            if root_font_size < 8:
                raise ValueError("Root font size must be at least 8")
            if root_font_size > 48:
                raise ValueError("Root font size cannot exceed 48")

            # Add max_level validation
            max_level = int(self.max_level_var.get())
            if max_level < 1:
                raise ValueError("Max Level must be at least 1")
            if max_level > 10:
                raise ValueError("Max Level cannot exceed 10")

            # Color settings: basic check that they are non-empty strings
            # (You could add more robust color validation if desired.)
            for i, var in enumerate([
                self.color_0_var,
                self.color_1_var,
                self.color_2_var,
                self.color_3_var,
                self.color_4_var,
                self.color_5_var,
                self.color_6_var,
                self.color_leaf_var
            ]):
                color_val = var.get()
                if not color_val or not color_val.startswith('#'):
                    raise ValueError(f"Invalid color for Level {i} or leaf if i == 7")

            # All good
            return True

        except ValueError as e:
            create_dialog(self, "Invalid Settings", str(e), ok_only=True)
            return False

    def _on_ok(self):
        """Save settings and close dialog."""
        if not self._validate_settings():
            return

        # Save each setting
        # Look & Feel
        self.settings.set("theme", self.theme_var.get())
        self.settings.set("max_ai_capabilities", int(self.max_cap_var.get()))
        self.settings.set("font_size", int(self.font_size_var.get()))
        self.settings.set("model", self.model_var.get())

        # Layout
        self.settings.set("box_min_width", int(self.box_min_width_var.get()))
        self.settings.set("box_min_height", int(self.box_min_height_var.get()))
        self.settings.set("horizontal_gap", int(self.horizontal_gap_var.get()))
        self.settings.set("vertical_gap", int(self.vertical_gap_var.get()))
        self.settings.set("padding", int(self.padding_var.get()))
        self.settings.set("top_padding", int(self.top_padding_var.get()))  # Save top padding setting
        self.settings.set("target_aspect_ratio", float(self.target_aspect_ratio_var.get()))
        self.settings.set("root_font_size", int(self.root_font_size_var.get()))
        self.settings.set("max_level", int(self.max_level_var.get()))

        # Colors
        self.settings.set("color_0", self.color_0_var.get())
        self.settings.set("color_1", self.color_1_var.get())
        self.settings.set("color_2", self.color_2_var.get())
        self.settings.set("color_3", self.color_3_var.get())
        self.settings.set("color_4", self.color_4_var.get())
        self.settings.set("color_5", self.color_5_var.get())
        self.settings.set("color_6", self.color_6_var.get())
        self.settings.set("color_leaf", self.color_leaf_var.get())

        self.result = True
        self.destroy()

    def position_center(self):
        """Helper method to center the dialog on the parent."""
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
