from typing import List, Tuple
from bcm.models import LayoutModel
from bcm.layout_manager import process_layout
from bcm.settings import Settings
import random

# Define color schemes for different levels
COLOR_SCHEMES = {
    0: "#FFCCCC",  # Root - Light Red
    1: "#CCE5FF",  # Level 1 - Light Blue
    2: "#D5F5E3",  # Level 2 - Light Green
    3: "#FCF3CF",  # Level 3 - Light Yellow
    4: "#E8DAEF"   # Level 4+ - Light Purple
}

def format_long_label(text: str, max_width: int = 25) -> str:
    """Format long labels by adding line breaks."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_width:  # +1 for space
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(" ".join(current_line))
    
    return "\\n".join(lines)

def create_plantuml_node(node: LayoutModel, level: int = 0, is_right: bool = True) -> str:
    """Create PlantUML mindmap syntax for a node and its children."""
    # Format the node name with line breaks
    formatted_name = format_long_label(node.name)
    
    # Get color for current level (remove extra # from color code)
    bgcolor = COLOR_SCHEMES.get(level, COLOR_SCHEMES[4]).lstrip('#')
    
    # Determine side marker (+ for right, - for left)
    side = '+' if is_right else '-'
    if level == 0:
        # Root node always has single marker
        side = side
    else:
        # Child nodes have markers based on depth + 1 to ensure connection
        side = side * (level + 1)
    
    # Create node line with styling
    node_line = f"{side}[#{bgcolor}] {formatted_name}"
    
    # Start with current node
    plantuml_content = [node_line]
    
    # Recursively add child nodes with alternating sides for better distribution
    if node.children:
        for i, child in enumerate(node.children):
            # Alternate sides for first level children
            if level == 0:
                child_is_right = (i < len(node.children) // 2)  # First half right, second half left
            else:
                child_is_right = is_right
                
            child_content = create_plantuml_node(child, level + 1, child_is_right)
            plantuml_content.append(child_content)
    
    return "\n".join(plantuml_content)

def export_to_plantuml(model: LayoutModel, settings: Settings) -> str:
    """Export the capability model to PlantUML mindmap format."""
    # Process layout
    processed_model = process_layout(model, settings)
    
    # Create PlantUML content
    plantuml_content = create_plantuml_node(processed_model)
    
    # Create the complete PlantUML diagram
    diagram = f'''@startmindmap
skinparam MaximumWidth 200
skinparam BackgroundColor transparent
skinparam ArrowColor #2C3E50
skinparam NodeFontSize 14
skinparam NodeFontName Arial
skinparam NodeBorderColor #2C3E50

{plantuml_content}

@endmindmap'''
    
    return diagram
