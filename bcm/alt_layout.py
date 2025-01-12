from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from bcm.models import LayoutModel
from bcm.settings import Settings

@dataclass
class NodeSize:
    width: float
    height: float

@dataclass
class DiagonalLayout:
    width: float
    height: float
    positions: List[Dict[str, float]]
    deviation: float

def calculate_node_size(node: LayoutModel, settings: Settings) -> NodeSize:
    """Calculate the minimum size needed for a node and its children."""
    if not node.children:
        return NodeSize(settings.get("box_min_width"), settings.get("box_min_height"))
    
    child_sizes = [calculate_node_size(child, settings) for child in node.children]
    layout = compute_diagonal_layout(child_sizes, settings)
    
    return NodeSize(layout.width, layout.height)

def find_non_overlapping_position(
    x: float,
    y: float,
    width: float,
    height: float,
    existing_positions: List[Dict[str, float]],
    gap: float
) -> Tuple[float, float]:
    """Find the nearest position where the new element won't overlap with existing ones."""
    if not existing_positions:
        return x, y
        
    while any(
        rectangles_overlap(
            x, y, width, height,
            pos["x"], pos["y"], pos["width"], pos["height"],
            gap
        )
        for pos in existing_positions
    ):
        # Move diagonally until we find a non-overlapping position
        x += gap
        y += gap
    
    return x, y

def rectangles_overlap(
    x1: float, y1: float, w1: float, h1: float,
    x2: float, y2: float, w2: float, h2: float,
    gap: float
) -> bool:
    """Check if two rectangles overlap, including the minimum gap between them."""
    return not (
        x1 + w1 + gap <= x2 or
        x2 + w2 + gap <= x1 or
        y1 + h1 + gap <= y2 or
        y2 + h2 + gap <= y1
    )

def compute_diagonal_layout(child_sizes: List[NodeSize], settings: Settings) -> DiagonalLayout:
    """
    Compute a diagonal cascade layout where elements flow diagonally from top-left
    to bottom-right without overlapping while maintaining approximate aspect ratio.
    """
    padding = settings.get("padding", 20.0)
    top_padding = settings.get("top_padding", padding)
    gap = settings.get("horizontal_gap", 20.0)
    target_ratio = settings.get("target_aspect_ratio", 1.6)  # 16:9 ≈ 1.6
    
    best_layout = None
    best_deviation = float('inf')
    
    # Try different diagonal spacings to find optimal aspect ratio
    for spacing_factor in range(1, 6):  # Try 5 different spacing patterns
        base_spacing = gap * spacing_factor
        positions = []
        max_width = padding  # Start with padding
        max_height = top_padding  # Start with top padding
        
        # Start position for first element
        x = padding
        y = top_padding
        
        for size in child_sizes:
            # Find non-overlapping position for this element
            x, y = find_non_overlapping_position(
                x, y, size.width, size.height, positions, gap
            )
            
            # If we're too far right, reset x and increment y
            if x + size.width > max_width * 2:  # Allow some horizontal expansion
                x = padding
                y = max_height + gap
                # Recheck for overlaps at new position
                x, y = find_non_overlapping_position(
                    x, y, size.width, size.height, positions, gap
                )
            
            positions.append({
                "x": x,
                "y": y,
                "width": size.width,
                "height": size.height
            })
            
            # Update maximum dimensions
            max_width = max(max_width, x + size.width + padding)
            max_height = max(max_height, y + size.height + padding)
            
            # Move diagonally for next element
            x += base_spacing
            y += base_spacing
        
        # Calculate aspect ratio deviation
        current_ratio = max_width / max_height
        deviation = abs(current_ratio - target_ratio)
        
        # Update best layout if this one is better
        if deviation < best_deviation:
            best_deviation = deviation
            best_layout = DiagonalLayout(
                width=max_width,
                height=max_height,
                positions=positions,
                deviation=deviation
            )
    
    return best_layout

def layout_tree(node: LayoutModel, settings: Settings, x: float = 0.0, y: float = 0.0) -> LayoutModel:
    """Recursively layout the tree starting from the given node."""
    if not node.children:
        node.width = settings.get("box_min_width")
        node.height = settings.get("box_min_height")
        node.x = x
        node.y = y
        return node
    
    child_sizes = [calculate_node_size(child, settings) for child in node.children]
    layout = compute_diagonal_layout(child_sizes, settings)
    
    # Assign dimensions to parent node
    node.width = layout.width
    node.height = layout.height
    node.x = x
    node.y = y
    
    # Layout children
    for child, pos in zip(node.children, layout.positions):
        layout_tree(child, settings, x + pos["x"], y + pos["y"])
        child.width = pos["width"]
        child.height = pos["height"]
    
    return node

def process_layout(model: LayoutModel, settings: Settings) -> LayoutModel:
    """Process the layout for the entire tree."""
    return layout_tree(model, settings)