# PyBCM User Manual

## Introduction
PyBCM (Python Business Capability Modeler) is a graphical application for creating, visualizing, and managing hierarchical business capability models. It provides an intuitive interface with features like drag-and-drop reordering, rich text descriptions, and multiple export options. This manual will guide you through the essential aspects of installing and using PyBCM effectively.

## Installation

### Using Git Clone and Pip Install

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pybcm.git
cd pybcm
```

2. Install dependencies using `uv` (recommended):
```bash
uv pip install -e .
```

Alternatively, you can use standard pip:
```bash
pip install -e .
```

### Creating an Executable File

#### Command-line Tool
PyBCM is installed as a command-line tool. After installation, you can run it by simply typing:
```bash
bcm
```

You can also install it directly as a uv tool:
```bash
uv tool install pybcm
```

#### Standalone Executable
You can create a standalone executable using PyInstaller:

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Create the executable:
```bash
pyinstaller --name pybcm --onefile --windowed --icon bcm/business_capability_model.ico bcm/app.py
```

This will:
- Create a single executable file named `pybcm.exe` (Windows) or `pybcm` (Linux/Mac)
- Include all necessary dependencies
- Add the BCM icon to the executable
- Create a windowed application (no console window)

The executable will be created in the `dist` directory. You can distribute this single file to users who don't have Python installed.

## Understanding the .pybcm Directory

PyBCM creates a `.pybcm` directory in your home folder to store user-specific data and customizations:

```
~/.pybcm/
├── settings.json     # User settings  
└── templates/        # Customizable templates for AI integration
    ├── expansion_prompt_gpt.j2  # Template for capability expansion
    └── first_level_prompt_gpt.j2 # Template for first-level capabilities
```

- `settings.json`: Stores your personal preferences including visual theme, layout settings, and color schemes
- `templates/`: Contains customizable templates for AI integration features

## Creating, Editing, and Rearranging Capabilities

### Creating Capabilities
1. Right-click on a desired parent in the tree view
2. Select "New Child"
3. Enter the capability name and optional description
4. Click "OK"

### Editing Capabilities
1. Select a capability in the tree view
2. Click "Edit" in the toolbar
3. Modify the name or description in the right panel
4. Click "View" to preview or "Save" to save changes

### Rearranging Capabilities
- Use drag-and-drop in the tree view to:
  - Reorder capabilities within the same level
  - Move capabilities to different parent nodes
  - Restructure your capability hierarchy

## Importing, Exporting, and Visualizing Models

### Importing/Exporting
- **Import**: Use File > Import to load a JSON format capability model
- **Export Options**:
  - JSON: Export entire model for backup or sharing
  - SVG: Generate vector graphics for documentation
  - PowerPoint: Create presentations with your model
  - Archimate: Export in Open Exchange format for enterprise architecture tools

### Visualizing Models
1. Click the "🗺️" button in toolbar
2. Navigate the visualization:
   - Zoom: Ctrl + Mouse Wheel
   - Pan: Click and drag
3. Customize visualization through File > Settings:
   - Layout algorithm selection
   - Color schemes
   - Font sizes
   - Box dimensions
   - Spacing parameters

## Using Copy/Paste to Expand the Model

PyBCM provides smart copy/paste functionality for AI integration:

### Copying Capabilities
1. Select a capability in the tree view
2. Press Ctrl+C to copy its context
3. The copied format is optimized for AI tools like ChatGPT

### Pasting AI-Generated Capabilities
1. Select a parent capability
2. Press Ctrl+V to paste a JSON array of sub-capabilities
3. Each capability in the array must have:
   - `name` field
   - `description` field

### Template Customization
You can customize how capabilities are formatted for AI tools by modifying templates in `~/.pybcm/templates/`:
- `expansion_prompt_gpt.j2`: Template for expanding sub-capabilities
- `first_level_prompt_gpt.j2`: Template for generating first-level capabilities

This allows you to:
- Tailor capability formats for specific AI tools
- Customize the structure of AI-generated responses
- Maintain your customizations across application updates
