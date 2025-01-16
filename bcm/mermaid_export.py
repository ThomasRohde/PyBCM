from typing import List
from bcm.models import LayoutModel
from bcm.layout_manager import process_layout
from bcm.settings import Settings

def create_mermaid_node(node: LayoutModel, level: int = 0) -> str:
    """Create Mermaid mindmap syntax for a node and its children."""
    # Create indentation based on level
    indent = "    " * level
    
    # Create node line (without description to avoid Mermaid syntax errors)
    node_line = f"{indent}{node.name}"
    
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
    processed_model = process_layout(model, settings)
    
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
