from typing import List
from bcm.models import LayoutModel
from bcm.layout_manager import process_layout
from bcm.settings import Settings

def _format_description(description: str) -> str:
    """Format description text for markdown, handling newlines and quotes."""
    if not description:
        return "_No description provided_"
    
    # Replace newlines with markdown line breaks
    description = description.replace('\n', '  \n')
        
    return description

def _process_node(node: LayoutModel, level: int = 0) -> List[str]:
    """Process a node and its children recursively to generate markdown lines."""
    lines = []
    
    # Add header with proper indentation level
    indent = "  " * level
    lines.append(f"{indent}* **{node.name}**\n")
    
    # Add description if present
    if node.description:
        desc_lines = _format_description(node.description).split('\n')
        for desc_line in desc_lines:
            lines.append(f"{indent}  {desc_line}")
        lines.append('\n')
    
    # Process children if present
    if node.children:
        lines.append(f"{indent}  *Sub-capabilities:*\n")
        for child in node.children:
            lines.extend(_process_node(child, level + 1))
    
    return lines

def export_to_markdown(model: LayoutModel, settings: Settings) -> str:
    """Export the capability model to Markdown format.
    
    Args:
        model: The capability model to export
        settings: Application settings
        
    Returns:
        A string containing the markdown representation of the model
    """
    # Process layout first
    processed_model = process_layout(model, settings)
    
    # Start with title
    lines = [
        f"# {processed_model.name}",
        "",
    ]
    
    # Process all nodes recursively
    lines.extend(_process_node(processed_model))
    
    # Join all lines with newlines
    return '\n'.join(lines)
