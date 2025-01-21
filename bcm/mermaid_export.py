from typing import List
from bcm.models import LayoutModel
from bcm.layout_manager import process_layout
from bcm.settings import Settings

def format_long_label(text: str, max_length: int = 30) -> str:
    """Format long labels by adding line breaks."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_length:  # +1 for space
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(" ".join(current_line))
    
    return "<br/>".join(lines)

def create_mermaid_node(node: LayoutModel, level: int = 0) -> str:
    """Create Mermaid mindmap syntax for a node and its children."""
    # Create indentation based on level
    indent = "    " * level
    
    # Format the node name with line breaks if needed
    formatted_name = format_long_label(node.name)
    
    # Apply different shapes based on level
    if level == 0:
        # Root node - cloud shape
        node_line = f"{indent}{formatted_name}){formatted_name}("
    elif level == 1:
        # First level - hexagon
        node_line = f"{indent}{{{{{formatted_name}}}}}"
    elif level == 2:
        # Second level - rounded square
        node_line = f"{indent}({formatted_name})"
    else:
        # Third level and deeper - square
        node_line = f"{indent}[{formatted_name}]"
    
    # Start with current node
    mermaid_content = [node_line]
    
    # Recursively add child nodes
    if node.children:
        for child in node.children:
            mermaid_content.append(create_mermaid_node(child, level + 1))
    
    return "\n".join(mermaid_content)

def export_to_mermaid(model: LayoutModel, settings: Settings) -> str:
    """Export the capability model to Mermaid mindmap format."""
    # Process layout
    processed_model = process_layout(model, settings) # TODO: Why do we process the layout here? It's not needed for Mermaid export.
    
    # Create the HTML content with Mermaid
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Capability Model - Mermaid Mind Map</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            mindmap: {
                padding: 20,
                useMaxWidth: true
            }
        });
    </script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
        }
        .mermaid {
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="mermaid">
mindmap
''' + create_mermaid_node(processed_model) + '''
    </div>
</body>
</html>'''

    return html_content
