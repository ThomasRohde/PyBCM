import json
import ttkbootstrap as ttk
from pathlib import Path
from pydantic_ai import models
from typing import get_args

BOX_MIN_WIDTH_DEFAULT = 120
BOX_MIN_HEIGHT_DEFAULT = 80
HORIZONTAL_GAP_DEFAULT = 20
VERTICAL_GAP_DEFAULT = 20
PADDING_DEFAULT = 30
DEFAULT_TARGET_ASPECT_RATIO_DEFAULT = 1.0

DEFAULT_SETTINGS = {
    "theme": "litera",           # Default ttkbootstrap theme
    "max_ai_capabilities": 10,   # Default max number of AI-generated capabilities
    "font_size": 10,             # Default font size for main text content
    "model": "openai:gpt-4o",    # Default model
    # Layout
    "box_min_width": BOX_MIN_WIDTH_DEFAULT,
    "box_min_height": BOX_MIN_HEIGHT_DEFAULT,
    "horizontal_gap": HORIZONTAL_GAP_DEFAULT,
    "vertical_gap": VERTICAL_GAP_DEFAULT,
    "padding": PADDING_DEFAULT,
    "target_aspect_ratio": DEFAULT_TARGET_ASPECT_RATIO_DEFAULT,
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
        self.geometry("600x550")
        self.position_center()
        self.resizable(False, False)

        # Create all variables that will be used in the UI
        # Look & Feel
        self.theme_var = ttk.StringVar()
        self.max_cap_var = ttk.StringVar()
        self.font_size_var = ttk.StringVar()
        self.model_var = ttk.StringVar()

        # Layout
        self.box_min_width_var = ttk.StringVar()
        self.box_min_height_var = ttk.StringVar()
        self.horizontal_gap_var = ttk.StringVar()
        self.vertical_gap_var = ttk.StringVar()
        self.padding_var = ttk.StringVar()
        self.target_aspect_ratio_var = ttk.StringVar()

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
        self.box_min_width_var.set(str(self.settings.get("box_min_width")))
        self.box_min_height_var.set(str(self.settings.get("box_min_height")))
        self.horizontal_gap_var.set(str(self.settings.get("horizontal_gap")))
        self.vertical_gap_var.set(str(self.settings.get("vertical_gap")))
        self.padding_var.set(str(self.settings.get("padding")))
        self.target_aspect_ratio_var.set(str(self.settings.get("target_aspect_ratio")))

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

        self.aspect_ratio_label.grid(row=2, column=2, padx=(10, 5), pady=(5, 5), sticky="w")
        self.aspect_ratio_entry.grid(row=2, column=3, padx=(0, 10), pady=(5, 5), sticky="w")

        # Add tabs to Notebook
        self.notebook.add(self.look_frame, text="Look & Feel")
        self.notebook.add(self.ai_frame, text="AI Generation")
        self.notebook.add(self.layout_frame, text="Layout")

        # Notebook in main window
        self.notebook.pack(expand=True, fill="both", padx=10, pady=(10, 0))

        # Note label (below the notebook)
        self.note_label.pack(pady=10)

        # Buttons
        self.btn_frame.pack(fill="x", padx=10, pady=10)
        self.cancel_btn.pack(side="right", padx=5)
        self.ok_btn.pack(side="right", padx=5)

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

            # Float check
            aspect_ratio = float(self.target_aspect_ratio_var.get())
            if aspect_ratio <= 0.0:
                raise ValueError("Target Aspect Ratio must be greater than 0")

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
        self.settings.set("theme", self.theme_var.get())
        self.settings.set("max_ai_capabilities", int(self.max_cap_var.get()))
        self.settings.set("font_size", int(self.font_size_var.get()))
        self.settings.set("model", self.model_var.get())

        self.settings.set("box_min_width", int(self.box_min_width_var.get()))
        self.settings.set("box_min_height", int(self.box_min_height_var.get()))
        self.settings.set("horizontal_gap", int(self.horizontal_gap_var.get()))
        self.settings.set("vertical_gap", int(self.vertical_gap_var.get()))
        self.settings.set("padding", int(self.padding_var.get()))
        self.settings.set("target_aspect_ratio", float(self.target_aspect_ratio_var.get()))

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
