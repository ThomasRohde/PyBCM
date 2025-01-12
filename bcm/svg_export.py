import math
from typing import List
import xml.etree.ElementTree as ET
import textwrap

from bcm.models import LayoutModel
from bcm.layout_manager import process_layout
from bcm.settings import Settings

def create_svg_element(width: int, height: int) -> ET.Element:
    """Create the root SVG element with given dimensions."""
    svg = ET.Element(
        "svg",
        {
            "width": str(width),
            "height": str(height),
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
        },
    )
    return svg


def calculate_font_size(root_size: int, level: int, is_leaf: bool) -> int:
    """Calculate font size based on level and node type."""
    # Calculate base size for this level - decrease by 4 points per level
    base_size = root_size - (level * 4)

    if is_leaf:
        # Leaf nodes get a slightly smaller size than their parent level
        return max(base_size - 2, 8)
    else:
        # Non-leaf nodes use the level's base size
        return max(base_size, 10)


def wrap_text(text: str, width: float, font_size: int) -> List[str]:
    """Wrap text to fit within a given width."""
    # Approximate characters that fit in width (assuming average char width is 0.6 * font_size)
    chars_per_line = int(width / (font_size * 0.6))
    # Wrap text into lines
    return textwrap.wrap(text, width=max(1, chars_per_line))


def add_wrapped_text(
    g: ET.Element,
    text: str,
    x: float,
    y: float,
    height: float,
    width: float,
    root_font_size: int,
    level: int,
    has_children: bool = False,
):
    """Add wrapped text to SVG with proper positioning."""
    # Calculate appropriate font size for this level
    font_size = calculate_font_size(root_font_size, level, not has_children)

    lines = wrap_text(text, width - 10, font_size)  # Subtract padding for text
    line_height = font_size * 1.2  # Add some line spacing
    total_text_height = line_height * len(lines)

    # For nodes with children, position text near top
    if has_children:
        start_y = y + font_size - 4  # Add small padding from top
    else:
        # For leaf nodes, center text vertically
        # Adjust the calculation to ensure perfect centering
        start_y = y + (height - total_text_height) / 2 + (font_size * 0.8)

    # Create text element for each line
    for i, line in enumerate(lines):
        text_elem = ET.SubElement(
            g,
            "text",
            {
                "x": str(x),
                "y": str(start_y + (i * line_height)),
                "font-family": "Arial",
                "text-anchor": "middle",
                "dominant-baseline": "middle",
                "font-size": str(font_size),
                "fill": "#000000",
            },
        )
        text_elem.text = line


def add_node_to_svg(
    svg: ET.Element, node: LayoutModel, settings: Settings, level: int = 0
):
    """Add a node and its children to the SVG."""
    # Create group for this node
    g = ET.SubElement(svg, "g")

    # Determine node color based on level and whether it has children
    if not node.children:
        color = settings.get("color_leaf")
    else:
        color = settings.get(f"color_{min(level, 6)}")

    # Add rectangle for node
    ET.SubElement(
        g,
        "rect",
        {
            "x": str(node.x),
            "y": str(node.y),
            "width": str(node.width),
            "height": str(node.height),
            "fill": color,
            "rx": "5",
            "ry": "5",
            "stroke": "#333333",
            "stroke-width": "1",
        },
    )

    # Add wrapped text with appropriate positioning
    add_wrapped_text(
        g,
        node.name,
        node.x + node.width / 2,  # Center horizontally
        node.y,  # Start from top
        node.height,  # Pass height for vertical centering
        node.width,
        settings.get("root_font_size"),  # Pass base font size
        level,  # Pass level for font size calculation
        has_children=bool(node.children),
    )

    # Recursively add child nodes without connections
    if node.children:
        for child in node.children:
            add_node_to_svg(svg, child, settings, level + 1)


def export_to_svg(model: LayoutModel, settings: Settings) -> str:
    """Export the capability model to SVG format."""
    # Process layout
    processed_model = process_layout(model, settings)

    # Create SVG with padding
    padding = settings.get("padding", 20)
    width = math.ceil(processed_model.width + 2 * padding)
    height = math.ceil(processed_model.height + 2 * padding)

    # Create SVG element
    svg = create_svg_element(width, height)

    # Add nodes recursively
    add_node_to_svg(svg, processed_model, settings)

    # Convert to string
    return ET.tostring(svg, encoding="unicode", method="xml")
