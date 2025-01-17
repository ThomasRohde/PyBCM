# Changelog

## [Unreleased]

### Added
- Added PlantUML mindmap export functionality
  - New export option in File menu
  - Exports capability model as PlantUML mindmap
  - Smart word wrapping with MaximumWidth parameter
  - Even distribution of concepts using +/- syntax
  - Color-coded nodes based on hierarchy level
  - Added Ctrl+D shortcut to copy PlantUML diagram to clipboard
  - Proper indentation with repeated +/- markers

- Added Mermaid mindmap export functionality
  - New export option in File menu
  - Exports capability model as an interactive Mermaid mindmap
  - Generates HTML file with embedded Mermaid.js for visualization
  - Added Ctrl+M shortcut to copy Mermaid diagram to clipboard
  - Enhanced node visualization with depth-based shapes:
    - Root nodes use cloud shape
    - Level 1 nodes use hexagon shape
    - Level 2 nodes use rounded square shape
    - Level 3+ nodes use square shape
  - Automatic line breaks for long node labels to improve readability
