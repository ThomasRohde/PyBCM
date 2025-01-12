import uuid
import xml.etree.ElementTree as ET
from typing import Dict

from bcm.models import LayoutModel
from bcm.layout_manager import process_layout
from bcm.settings import Settings


def generate_id() -> str:
    """Generate a unique identifier for Archimate elements."""
    return f"id-{str(uuid.uuid4()).replace('-', '')}"


def create_archimate_element(root: ET.Element, name: str, documentation: str) -> str:
    """Create an Archimate element and return its identifier."""
    identifier = generate_id()
    element = ET.SubElement(
        root.find("elements"),
        "element",
        {"identifier": identifier, "xsi:type": "Capability"},
    )
    name_elem = ET.SubElement(element, "name", {"xml:lang": "en"})
    name_elem.text = name

    documentatio_elem = ET.SubElement(element, "documentation", {"xml:lang": "en"})
    documentatio_elem.text = documentation

    return identifier


def create_relationship(
    root: ET.Element, source_id: str, target_id: str, rel_type: str = "Composition"
) -> str:
    """Create a relationship between two elements."""
    identifier = generate_id()
    ET.SubElement(
        root.find("relationships"),
        "relationship",
        {
            "identifier": identifier,
            "source": source_id,
            "target": target_id,
            "xsi:type": rel_type,
        },
    )
    return identifier


def create_node(
    view: ET.Element,
    element_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
) -> str:
    """Create a view node for an element."""
    identifier = generate_id()
    node = ET.SubElement(
        view,
        "node",
        {
            "identifier": identifier,
            "elementRef": element_id,
            "xsi:type": "Element",
            "x": str(int(x)),
            "y": str(int(y)),
            "w": str(int(width)),
            "h": str(int(height)),
        },
    )

    # Add style
    style = ET.SubElement(node, "style")

    # Parse color components (assuming hex color)
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)

    ET.SubElement(
        style, "fillColor", {"r": str(r), "g": str(g), "b": str(b), "a": "100"}
    )

    ET.SubElement(style, "lineColor", {"r": "92", "g": "92", "b": "92", "a": "100"})

    font = ET.SubElement(style, "font", {"name": "Segoe UI", "size": "9"})

    ET.SubElement(font, "color", {"r": "0", "g": "0", "b": "0"})

    return identifier, node


def process_node(
    root: ET.Element,
    view: ET.Element,
    node: LayoutModel,
    settings: Settings,
    level: int = 0,
) -> Dict[str, str]:
    """Process a node and its children recursively."""
    # Create element
    element_id = create_archimate_element(root, node.name, node.description)

    # Determine node color based on level
    if not node.children:
        color = settings.get("color_leaf")
    else:
        color = settings.get(f"color_{min(level, 6)}")

    # Create view node
    node_id, view_node = create_node(
        view, element_id, node.x, node.y, node.width, node.height, color
    )

    # Process children
    if node.children:
        for child in node.children:
            child_ids = process_node(root, view_node, child, settings, level + 1)
            # Create relationship
            create_relationship(root, element_id, child_ids["element"])

    return {"element": element_id, "node": node_id}


def export_to_archimate(model: LayoutModel, settings: Settings) -> str:
    """Export the capability model to Archimate Open Exchange format."""
    # Process layout
    processed_model = process_layout(model, settings)

    # Create root element
    root = ET.Element(
        "model",
        {
            "xmlns": "http://www.opengroup.org/xsd/archimate/3.0/",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.opengroup.org/xsd/archimate/3.0/ http://www.opengroup.org/xsd/archimate/3.1/archimate3_Diagram.xsd",
            "identifier": generate_id(),
        },
    )

    # Add model name
    name = ET.SubElement(root, "name", {"xml:lang": "en"})
    name.text = model.name

    # Create sections
    ET.SubElement(root, "elements")
    ET.SubElement(root, "relationships")
    views = ET.SubElement(root, "views")
    diagrams = ET.SubElement(views, "diagrams")

    # Create view
    view = ET.SubElement(
        diagrams, "view", {"identifier": generate_id(), "xsi:type": "Diagram"}
    )
    view_name = ET.SubElement(view, "name", {"xml:lang": "en"})
    view_name.text = model.name

    # Process nodes recursively
    process_node(root, view, processed_model, settings)

    # Convert to string with proper XML declaration
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        root, encoding="unicode", method="xml"
    )
