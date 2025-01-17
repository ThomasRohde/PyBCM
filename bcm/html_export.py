import math
from typing import List
from bcm.models import LayoutModel
from bcm.layout_manager import process_layout
from bcm.settings import Settings

def create_html_node(node: LayoutModel, level: int = 0) -> str:
    """Create HTML for a node and its children."""
    # Determine node color based on level and whether it has children
    color = "var(--leaf-color)" if not node.children else f"var(--level-{min(level, 6)}-color)"
    
    # Create node HTML with data attributes for hover and position class
    position_class = "has-children" if node.children else "leaf-node"
    node_html = f'''
    <div class="node level-{level} {position_class}" 
         style="left: {node.x}px; top: {node.y}px; width: {node.width}px; height: {node.height}px; background-color: {color};"
         data-description="{node.description or ''}"
         data-name="{node.name}">
        <div class="node-content">{node.name}</div>
    </div>'''

    # Recursively add child nodes
    if node.children:
        for child in node.children:
            node_html += create_html_node(child, level + 1)

    return node_html

def export_to_html(model: LayoutModel, settings: Settings) -> str:
    """Export the capability model to HTML format."""
    # Process layout
    processed_model = process_layout(model, settings)

    # Calculate dimensions with padding
    padding = settings.get("padding", 20)
    width = math.ceil(processed_model.width + 2 * padding)
    height = math.ceil(processed_model.height + 2 * padding)

    # Create CSS variables for colors
    color_vars = ""
    for i in range(7):  # 0-6 levels
        color_vars += f"--level-{i}-color: {settings.get(f'color_{i}', '#ffffff')};\n"
    color_vars += f"--leaf-color: {settings.get('color_leaf', '#ffffff')};\n"

    # Create the HTML content with embedded CSS and JS
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Capability Model</title>
    <style>
        :root {{
            {color_vars}
        }}
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
        }}
        #model-container {{
            position: relative;
            width: {width}px;
            height: {height}px;
        }}
        .node {{
            position: absolute;
            border: 1px solid #333333;
            border-radius: 5px;
            overflow: hidden;
            transition: box-shadow 0.3s ease;
        }}
        .node:hover {{
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
        }}
        .node-content {{
            padding: 8px;
            font-size: {settings.get("root_font_size", 14)}px;
            text-align: center;
            word-wrap: break-word;
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            width: calc(100% - 16px); /* Account for padding */
        }}
        .leaf-node .node-content {{
            top: 50%;
            transform: translate(-50%, -50%);
        }}
        .has-children .node-content {{
            top: 8px;
            transform: translateX(-50%);
        }}
        #tooltip {{
            position: fixed;
            display: none;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px;
            border-radius: 4px;
            max-width: 300px;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div id="model-container">
        {create_html_node(processed_model)}
    </div>
    <div id="tooltip"></div>

    <script>
        const tooltip = document.getElementById('tooltip');
        
        document.querySelectorAll('.node').forEach(node => {{
            node.addEventListener('mousemove', (e) => {{
                const description = node.dataset.description;
                if (description) {{
                    tooltip.textContent = `${{node.dataset.name}}: ${{description}}`;
                    tooltip.style.display = 'block';
                    tooltip.style.left = e.pageX + 10 + 'px';
                    tooltip.style.top = e.pageY + 10 + 'px';
                }}
            }});

            node.addEventListener('mouseleave', () => {{
                tooltip.style.display = 'none';
            }});
        }});
    </script>
</body>
</html>'''

    return html_content
