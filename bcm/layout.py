from typing import List, Dict, Any
from dataclasses import dataclass
from .models import LayoutModel

# Layout constants
BOX_MIN_WIDTH = 120
BOX_MIN_HEIGHT = 80
HORIZONTAL_GAP = 20
VERTICAL_GAP = 20
PADDING = 30
DEFAULT_TARGET_ASPECT_RATIO = 1.0

@dataclass
class NodeSize:
    width: float
    height: float

@dataclass
class GridLayout:
    rows: int
    cols: int
    width: float
    height: float
    deviation: float
    positions: List[Dict[str, float]]

def calculate_node_size(node: LayoutModel) -> NodeSize:
    """Calculate the minimum size needed for a node and its children."""
    if not node.children:
        return NodeSize(BOX_MIN_WIDTH, BOX_MIN_HEIGHT)

    child_sizes = [calculate_node_size(child) for child in node.children]
    best_layout = find_best_layout(child_sizes, len(node.children))
    
    return NodeSize(best_layout.width, best_layout.height)

def find_best_layout(child_sizes: List[NodeSize], child_count: int) -> GridLayout:
    """Find the optimal grid layout for a set of child nodes."""
    best_layout = GridLayout(
        rows=1,
        cols=child_count,
        width=float('inf'),
        height=float('inf'),
        deviation=float('inf'),
        positions=[]
    )

    for rows in range(1, child_count + 1):
        cols = (child_count + rows - 1) // rows  # Ceiling division
        
        row_heights = [0.0] * rows
        col_widths = [0.0] * cols
        
        # Calculate maximum heights and widths for each row and column
        for i in range(child_count):
            row = i // cols
            col = i % cols
            size = child_sizes[i]
            
            row_heights[row] = max(row_heights[row], size.height)
            col_widths[col] = max(col_widths[col], size.width)
        
        grid_width = sum(col_widths) + (cols - 1) * HORIZONTAL_GAP
        grid_height = sum(row_heights) + (rows - 1) * VERTICAL_GAP
        
        total_width = grid_width + 2 * PADDING
        total_height = grid_height + 2 * PADDING
        aspect_ratio = total_width / total_height
        deviation = abs(aspect_ratio - DEFAULT_TARGET_ASPECT_RATIO)

        # Calculate positions for each child
        positions = []
        y_offset = PADDING
        for row in range(rows):
            x_offset = PADDING
            for col in range(cols):
                idx = row * cols + col
                if idx < child_count:
                    positions.append({
                        'x': x_offset,
                        'y': y_offset,
                        'width': col_widths[col],
                        'height': row_heights[row]
                    })
                x_offset += col_widths[col] + HORIZONTAL_GAP
            y_offset += row_heights[row] + VERTICAL_GAP

        current_layout = GridLayout(
            rows=rows,
            cols=cols,
            width=total_width,
            height=total_height,
            deviation=deviation,
            positions=positions
        )

        if current_layout.deviation < best_layout.deviation:
            best_layout = current_layout

    return best_layout

def layout_tree(node: LayoutModel, x: float = 0, y: float = 0) -> LayoutModel:
    """Recursively layout the tree starting from the given node."""
    if not node.children:
        node.width = BOX_MIN_WIDTH
        node.height = BOX_MIN_HEIGHT
        node.x = x
        node.y = y
        return node

    layout = find_best_layout(
        [calculate_node_size(child) for child in node.children],
        len(node.children)
    )

    node.width = layout.width
    node.height = layout.height
    node.x = x
    node.y = y

    for child, pos in zip(node.children, layout.positions):
        layout_tree(
            child,
            x + pos['x'],
            y + pos['y']
        )
        child.width = pos['width']
        child.height = pos['height']

    return node

def process_layout(model: LayoutModel) -> LayoutModel:
    """Process the layout for the entire tree."""
    return layout_tree(model)
