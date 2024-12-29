from typing import List, Dict
from dataclasses import dataclass
from .models import LayoutModel
from .settings import Settings


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


def calculate_node_size(node: LayoutModel, settings: Settings) -> NodeSize:
    """Calculate the minimum size needed for a node and its children."""
    if not node.children:
        return NodeSize(settings.get("box_min_width"), settings.get("box_min_height"))

    child_sizes = [calculate_node_size(child, settings) for child in node.children]
    best_layout = find_best_layout(child_sizes, len(node.children), settings)

    return NodeSize(best_layout.width, best_layout.height)


def find_best_layout(child_sizes: List[NodeSize], child_count: int, settings: Settings) -> GridLayout:
    """
    Find the optimal grid layout for a set of child nodes.

    Improves packing by:
    1. Allowing non-integer rows/cols for intermediate calculations.
    2. Considering layouts where not all cells in the last row are filled.
    3. Prioritizing aspect ratio, then total area when deviations are equal.
    4. Minimizing gaps by distributing extra space among rows/cols.
    """
    best_layout = GridLayout(
        rows=1,
        cols=child_count,
        width=float('inf'),
        height=float('inf'),
        deviation=float('inf'),
        positions=[]
    )

    horizontal_gap = settings.get("horizontal_gap")
    vertical_gap = settings.get("vertical_gap")
    padding = settings.get("padding")
    target_aspect_ratio = settings.get("target_aspect_ratio")

    for rows_tentative in range(1, child_count + 1):
        for cols_float in [child_count / rows_tentative, (child_count + rows_tentative - 1) // rows_tentative]:  # Test both even and ceiling divisions
            cols = int(round(cols_float))
            if cols == 0:
                continue
            rows = (child_count + cols -1 ) // cols

            row_heights = [0.0] * rows
            col_widths = [0.0] * cols

            # Calculate maximum heights and widths for each row and column
            for i in range(child_count):
                row = i // cols
                col = i % cols
                size = child_sizes[i]

                row_heights[row] = max(row_heights[row], size.height)
                col_widths[col] = max(col_widths[col], size.width)

            grid_width = sum(col_widths) + (cols - 1) * horizontal_gap
            grid_height = sum(row_heights) + (rows - 1) * vertical_gap

            # Calculate total dimensions including padding
            total_width = grid_width + 2 * padding
            total_height = grid_height + 2 * padding

            # Ensure the layout height accounts for both top and bottom padding
            available_height = total_height - (settings.get("top_padding", padding) + padding)
            if grid_height > available_height:
                total_height = grid_height + settings.get("top_padding", padding) + padding

            aspect_ratio = total_width / total_height
            deviation = abs(aspect_ratio - target_aspect_ratio)

            # Calculate positions for each child, ensuring they fit within padding bounds
            positions = []
            y_offset = settings.get("top_padding", padding)  # Use top_padding for initial vertical offset
            max_y = total_height - padding  # Maximum allowed y position
            
            # Calculate extra space for distributing among rows and columns
            extra_width = max(0, total_width - (sum(col_widths) + (cols-1) * horizontal_gap + 2 * padding))
            extra_height = max(0, total_height - (sum(row_heights) + (rows-1) * vertical_gap + 2 * padding))
            
            extra_width_per_col = extra_width / cols if cols > 0 else 0
            extra_height_per_row = extra_height / rows if rows > 0 else 0

            for row in range(rows):
                x_offset = padding
                for col in range(cols):
                    idx = row * cols + col
                    if idx < child_count:
                        # Calculate the position and dimensions for this child
                        child_position = {
                            'x': x_offset,
                            'y': y_offset,
                            'width': col_widths[col] + extra_width_per_col, # Distribute extra width
                            'height': row_heights[row] + extra_height_per_row # Distribute extra height
                        }

                        # Check if this child would extend beyond the bottom padding
                        child_bottom = y_offset + row_heights[row] + extra_height_per_row
                        if child_bottom > max_y:
                            # Adjust total height to accommodate this child with proper padding
                            total_height = child_bottom + padding

                        positions.append(child_position)
                        x_offset += col_widths[col] + extra_width_per_col + horizontal_gap
                y_offset += row_heights[row] + extra_height_per_row + vertical_gap

            # Ensure final height includes proper bottom padding
            final_height = max(total_height, y_offset + padding)

            current_layout = GridLayout(
                rows=rows,
                cols=cols,
                width=total_width,
                height=final_height,
                deviation=deviation,
                positions=positions
            )

            if current_layout.deviation < best_layout.deviation or (
                current_layout.deviation == best_layout.deviation and 
                current_layout.width * current_layout.height < best_layout.width * best_layout.height
            ):
                best_layout = current_layout

    return best_layout


def layout_tree(node: LayoutModel, settings: Settings, x: float = 0, y: float = 0) -> LayoutModel:
    """Recursively layout the tree starting from the given node."""
    if not node.children:
        node.width = settings.get("box_min_width")
        node.height = settings.get("box_min_height")
        node.x = x
        node.y = y
        return node

    layout = find_best_layout(
        [calculate_node_size(child, settings) for child in node.children],
        len(node.children),
        settings
    )

    node.width = layout.width
    node.height = layout.height
    node.x = x
    node.y = y

    for child, pos in zip(node.children, layout.positions):
        layout_tree(
            child,
            settings,
            x + pos['x'],
            y + pos['y']
        )
        child.width = pos['width']
        child.height = pos['height']

    return node


def process_layout(model: LayoutModel, settings: Settings) -> LayoutModel:
    """Process the layout for the entire tree."""
    return layout_tree(model, settings)