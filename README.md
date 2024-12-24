# PyBCM - Python Business Capability Modeler

A modern, interactive business capability modeling tool built with Python. This application helps organizations map and manage their business capabilities in a hierarchical structure.

## Features

- Hierarchical capability tree visualization
- Drag-and-drop capability reordering
- CRUD operations for managing capabilities
- Modern Bootstrap-styled interface
- SQLite database for persistent storage
- Form validation using Pydantic
- AI-powered capability expansion
- Search functionality for capabilities
- Import/Export capabilities to JSON
- Rich text descriptions with auto-save
- Expand/Collapse all tree nodes

## Requirements

- Python 3.11 or higher
- Dependencies:
  - ttkbootstrap>=1.10.1
  - sqlalchemy>=2.0.0
  - pydantic>=2.0.0

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pybcm.git
cd pybcm
```

2. Install dependencies using uv:
```bash
uv pip install -e .
```

## Usage

Run the application:
```bash
bcm
```

### Managing Capabilities

1. **Adding a Capability**
   - Enter the capability name and optional description
   - Select a parent capability in the tree (optional)
   - Click "Add New"

2. **Updating a Capability**
   - Select a capability in the tree
   - Modify the name or description
   - Click "Update" or "Save Description"

3. **Deleting a Capability**
   - Select a capability in the tree
   - Click "Delete"
   - Confirm deletion

4. **Reordering Capabilities**
   - Drag and drop capabilities in the tree
   - The order is automatically saved

### Advanced Features

1. **AI Capability Expansion**
   - Select a capability in the tree
   - Click the "✨" button in the toolbar
   - Review and select suggested sub-capabilities
   - Click OK to add selected capabilities

2. **Search**
   - Use the search bar in the toolbar
   - Results update in real-time
   - Clear search with the "✕" button

3. **Import/Export**
   - File menu > Import: Load capabilities from JSON
   - File menu > Export: Save capabilities to JSON

4. **Tree Navigation**
   - Use "⬇" to expand all nodes
   - Use "⬆" to collapse all nodes

## Project Structure

```
pybcm/
├── bcm/
│   ├── __init__.py      # Package initialization
│   ├── app.py           # Main application and UI
│   ├── database.py      # Database operations
│   ├── dialogs.py       # Custom dialog windows
│   ├── models.py        # Data models and schemas
│   ├── pb.py           # Progress bar implementation
│   ├── treeview.py     # Custom tree view widget
│   └── utils.py        # Utility functions
├── pyproject.toml       # Project configuration
└── README.md           # Documentation
```

## Development

The project uses:
- `ttkbootstrap` for the modern UI components
- `SQLAlchemy` for database operations
- `Pydantic` for data validation
- `PydanticAI` for LLM generation
- `uv` for dependency management

## License

MIT License
