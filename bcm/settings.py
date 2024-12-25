import json
import ttkbootstrap as ttk
from pathlib import Path

# Default settings
DEFAULT_SETTINGS = {
    "theme": "litera",  # Default ttkbootstrap theme
    "max_ai_capabilities": 10,  # Default max number of AI-generated capabilities
    "font_size": 10  # Default font size for main text content
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
        self.geometry("400x450")
        self.position_center()
        self.resizable(False, False)

        self._create_widgets()
        self._create_layout()

        # Load current settings
        self.theme_var.set(settings.get("theme"))
        self.max_cap_var.set(str(settings.get("max_ai_capabilities")))
        self.font_size_var.set(str(settings.get("font_size")))

    def _create_widgets(self):
        # Font size
        self.font_frame = ttk.LabelFrame(self, text="Text Settings", padding=10)
        self.font_size_var = ttk.StringVar()
        self.font_size_label = ttk.Label(
            self.font_frame,
            text="Font size:"
        )
        self.font_size_entry = ttk.Entry(
            self.font_frame,
            textvariable=self.font_size_var,
            width=5
        )

        # Theme selection
        self.theme_frame = ttk.LabelFrame(self, text="Visual Theme", padding=10)
        self.theme_var = ttk.StringVar()
        self.theme_combo = ttk.Combobox(
            self.theme_frame,
            textvariable=self.theme_var,
            values=AVAILABLE_THEMES,
            state="readonly"
        )

        # Max capabilities
        self.cap_frame = ttk.LabelFrame(
            self,
            text="AI Generation Settings",
            padding=10
        )
        self.max_cap_var = ttk.StringVar()
        self.max_cap_label = ttk.Label(
            self.cap_frame,
            text="Maximum capabilities to generate:"
        )
        self.max_cap_entry = ttk.Entry(
            self.cap_frame,
            textvariable=self.max_cap_var,
            width=5
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
        # Font size section
        self.font_frame.pack(fill="x", padx=10, pady=(10, 5))
        self.font_size_label.pack(side="left", padx=(0, 5))
        self.font_size_entry.pack(side="left")

        # Theme section
        self.theme_frame.pack(fill="x", padx=10, pady=5)
        self.theme_combo.pack(fill="x")

        # Max capabilities section
        self.cap_frame.pack(fill="x", padx=10, pady=5)
        self.max_cap_label.pack(anchor="w")
        self.max_cap_entry.pack(anchor="w")

        # Note
        self.note_label.pack(pady=10)

        # Buttons
        self.btn_frame.pack(fill="x", padx=10, pady=10)
        self.cancel_btn.pack(side="right", padx=5)
        self.ok_btn.pack(side="right", padx=5)

    def _validate_settings(self):
        """Validate settings before saving."""
        try:
            max_cap = int(self.max_cap_var.get())
            if max_cap < 1:
                raise ValueError("Maximum capabilities must be at least 1")
            if max_cap > 10:
                raise ValueError("Maximum capabilities cannot exceed 10")
            
            font_size = int(self.font_size_var.get())
            if font_size < 8:
                raise ValueError("Font size must be at least 8")
            if font_size > 24:
                raise ValueError("Font size cannot exceed 24")
            
            return True
        except ValueError as e:
            from .dialogs import create_dialog
            create_dialog(
                self,
                "Invalid Settings",
                str(e),
                ok_only=True
            )
            return False

    def _on_ok(self):
        """Save settings and close dialog."""
        if not self._validate_settings():
            return

        # Update settings
        self.settings.set("theme", self.theme_var.get())
        self.settings.set("max_ai_capabilities", int(self.max_cap_var.get()))
        self.settings.set("font_size", int(self.font_size_var.get()))
        
        self.result = True
        self.destroy()
