# PyBCM - Python Business Capability Modeler

A modern, interactive business capability modeling tool built with Python. This application helps organizations map and manage their business capabilities in a hierarchical structure.

## Features

- Hierarchical capability tree visualization
- Drag-and-drop capability reordering
- CRUD operations for managing capabilities
- Modern Bootstrap-styled interface
- SQLite database for persistent storage
- Form validation using Pydantic

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
   - Click "Update"

3. **Deleting a Capability**
   - Select a capability in the tree
   - Click "Delete"
   - Confirm deletion

4. **Reordering Capabilities**
   - Drag and drop capabilities in the tree
   - The order is automatically saved

## Project Structure

```
pybcm/
├── bcm/
│   ├── __init__.py      # Package initialization
│   ├── app.py           # Main application and UI
│   ├── database.py      # Database operations
│   └── models.py        # Data models and schemas
├── pyproject.toml       # Project configuration
└── README.md           # Documentation
```

## Development

The project uses:
- `ttkbootstrap` for the modern UI components
- `SQLAlchemy` for database operations
- `Pydantic` for data validation
- `uv` for dependency management

## License

MIT License
