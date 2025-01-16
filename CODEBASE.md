# Codebase Knowledge

## Project Structure
- The project follows a modular architecture with separate files for different export formats
- Export functionality is implemented through a common pattern:
  1. Export module (e.g., mermaid_export.py) defines the export logic
  2. App class (_export_capability_model method) handles file saving and error handling
  3. UI class integrates the export option into the File menu

## Export System
- Common export pattern used across all formats:
  1. Uses LayoutModel for hierarchical data representation
  2. Processes layout with settings
  3. Converts model to target format
  4. Saves to file or copies to clipboard

### Export Formats
- HTML: Interactive visualization with CSS positioning
- SVG: Static vector graphics
- PowerPoint: Slide-based presentation
- Archimate: Enterprise architecture format
- Markdown: Text-based hierarchical format
- Word: Document format
- PlantUML: Mindmap visualization with DOT export
  - Uses PlantUML mindmap syntax
  - Smart color coding based on hierarchy level:
    - Root (level 0): Light Red (#FFCCCC)
    - Level 1: Light Blue (#CCE5FF)
    - Level 2: Light Green (#D5F5E3)
    - Level 3: Light Yellow (#FCF3CF)
    - Level 4+: Light Purple (#E8DAEF)
  - Even distribution of nodes using side markers:
    - First level nodes alternate between left/right
    - Child nodes follow parent's side
  - Word wrapping with \n for line breaks
  - Uses +/- syntax for node distribution:
    - + for right side nodes (repeated for depth: ++, +++)
    - - for left side nodes (repeated for depth: --, ---)
    - First half of children on right, second half on left
  - MaximumWidth parameter controls layout width

- Mermaid: Interactive mindmap visualization
  - Uses Mermaid.js for rendering
  - Hierarchical structure through indentation
  - Node shapes vary by depth level:
    - Root (level 0): Cloud shape using )node(
    - Level 1: Hexagon shape using {{node}}
    - Level 2: Rounded square using (node)
    - Level 3+: Square shape using [node]
  - Long labels are automatically split with <br/> tags
  - Label formatting handled by format_long_label function with 30-char default length

## UI Components
- Uses ttkbootstrap for modern UI elements
- Menu system for export options
- Tree view for capability hierarchy
- Split panel layout with description viewer

## Data Flow
1. User selects a capability node
2. System retrieves node and its children
3. Data is converted to LayoutModel format
4. LayoutModel is processed with user settings
5. Processed model is exported to chosen format
