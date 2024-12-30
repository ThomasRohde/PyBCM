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


@dataclass
class LayoutResult:
    """
    A container to return both the best layout
    and the best child ordering (permutation) that produced it.
    """
    layout: GridLayout
    permutation: List[int]  # Indices of child_sizes in the best order


def calculate_node_size(node: LayoutModel, settings: Settings) -> NodeSize:
    """Calculate the minimum bounding size needed for a node and its children."""
    if not node.children:
        return NodeSize(
            settings.get("box_min_width"), 
            settings.get("box_min_height")
        )

    child_sizes = [calculate_node_size(child, settings) for child in node.children]
    best_result = find_best_layout(child_sizes, len(child_sizes), settings)
    return NodeSize(best_result.layout.width, best_result.layout.height)


def _try_layout_for_permutation(
    perm_sizes: List[NodeSize],
    permutation: List[int],
    child_count: int,
    settings: Settings
) -> GridLayout:
    """
    For a given list of child sizes in the exact order `perm_sizes`,
    try all row/col combinations. Return the **best** GridLayout found.
    This does NOT store a global best; it only returns the best for this single permutation.
    """
    # Grab relevant settings
    horizontal_gap = settings.get("horizontal_gap", 20.0)
    vertical_gap   = settings.get("vertical_gap", 20.0)
    padding        = settings.get("padding", 20.0)
    top_padding    = settings.get("top_padding", padding)
    target_aspect_ratio = settings.get("target_aspect_ratio", 1.6)

    # Start with a "worst" possible layout
    local_best_layout = GridLayout(
        rows=1,
        cols=child_count,
        width=float('inf'),
        height=float('inf'),
        deviation=float('inf'),
        positions=[]
    )

    for rows_tentative in range(1, child_count + 1):
        # We try two ways for columns:
        #  - float division
        #  - integer-based "ceil" approach
        for cols_float in [
            child_count / rows_tentative,
            (child_count + rows_tentative - 1) // rows_tentative
        ]:
            cols = int(round(cols_float))
            if cols <= 0:
                continue

            # Figure out how many rows are needed if we have 'cols' columns
            rows = (child_count + cols - 1) // cols

            row_heights = [0.0] * rows
            col_widths  = [0.0] * cols

            # Compute bounding box for each row & column
            for i, size in enumerate(perm_sizes):
                r = i // cols
                c = i % cols
                row_heights[r] = max(row_heights[r], size.height)
                col_widths[c]  = max(col_widths[c], size.width)

            grid_width = sum(col_widths) + (cols - 1) * horizontal_gap
            grid_height = sum(row_heights) + (rows - 1) * vertical_gap

            # Adjust for padding
            total_width = grid_width + 2 * padding
            total_height = grid_height + top_padding + padding

            # Compute squared difference from target aspect ratio
            aspect_ratio = total_width / total_height
            deviation = (aspect_ratio - target_aspect_ratio) ** 2

            # Build child positions
            positions = []
            y_offset = top_padding

            # Possibly leftover space
            extra_width_per_col = max(
                0,
                total_width - (grid_width + 2 * padding)
            ) / cols if cols > 0 else 0

            extra_height_per_row = max(
                0,
                total_height - (grid_height + top_padding + padding)
            ) / rows if rows > 0 else 0

            for r in range(rows):
                x_offset = padding
                for c in range(cols):
                    idx = r * cols + c
                    if idx < child_count:
                        child_size = perm_sizes[idx]
                        pos = {
                            'x': x_offset,
                            'y': y_offset,
                            'width':  child_size.width  + extra_width_per_col,
                            'height': child_size.height + extra_height_per_row
                        }
                        positions.append(pos)
                        x_offset += (
                            child_size.width +
                            extra_width_per_col +
                            horizontal_gap
                        )
                y_offset += (
                    row_heights[r] +
                    extra_height_per_row +
                    vertical_gap
                )

            # Recompute the actual needed height from the bottom-most child
            max_child_bottom = max(pos['y'] + pos['height'] for pos in positions)
            actual_height = max_child_bottom + padding

            current_layout = GridLayout(
                rows=rows,
                cols=cols,
                width=total_width,
                height=actual_height,
                deviation=deviation,
                positions=positions
            )

            # Compare with local_best_layout
            if (current_layout.deviation < local_best_layout.deviation) or \
               (abs(current_layout.deviation - local_best_layout.deviation) < 1e-9 and
                (current_layout.width * current_layout.height <
                 local_best_layout.width * local_best_layout.height)):
                local_best_layout = current_layout

    return local_best_layout


def find_best_layout(
    child_sizes: List[NodeSize],
    child_count: int,
    settings: Settings
) -> LayoutResult:
    """
    Find the best grid layout for child_sizes. 
    - If child_count <= MAX_PERMUTATION_CHILDREN, we attempt all permutations.
    - Else, we attempt just one 'identity' ordering (or you can add other heuristics).
    Returns both the best layout and the permutation of indices that got that layout.
    """
    MAX_PERMUTATION_CHILDREN = 8

    # Start with "worst" possible layout
    best_layout = GridLayout(
        rows=1,
        cols=child_count,
        width=float('inf'),
        height=float('inf'),
        deviation=float('inf'),
        positions=[]
    )
    best_perm = list(range(child_count))

    # Decide if we brute-force permutations
    do_permutations = (child_count <= MAX_PERMUTATION_CHILDREN)

    # Helper to test a given permutation
    def check_permutation(perm: List[int], best_layout: GridLayout, best_perm: List[int]):
        # Build the permuted child_sizes
        perm_sizes = [child_sizes[i] for i in perm]
        candidate_layout = _try_layout_for_permutation(
            perm_sizes, perm, child_count, settings
        )

        # Compare with best_layout
        if (candidate_layout.deviation < best_layout.deviation) or \
           (abs(candidate_layout.deviation - best_layout.deviation) < 1e-9 and
            (candidate_layout.width * candidate_layout.height <
             best_layout.width * best_layout.height)):
            return candidate_layout, list(perm)
        else:
            return best_layout, best_perm

    if do_permutations:
        # Attempt all permutations (factorial time!)
        from itertools import permutations
        for perm in permutations(range(child_count)):
            best_layout, best_perm = check_permutation(perm, best_layout, best_perm)
    else:
        # For big sets, just use original order or a simple heuristic
        identity_perm = list(range(child_count))
        best_layout, best_perm = check_permutation(identity_perm, best_layout, best_perm)

    # Return both
    return LayoutResult(layout=best_layout, permutation=best_perm)


def layout_tree(
    node: LayoutModel,
    settings: Settings,
    x: float = 0.0,
    y: float = 0.0
) -> LayoutModel:
    """
    Recursively layout the tree starting from the given node.
    We reorder node.children according to the best permutation found.
    """
    if not node.children:
        node.width = settings.get("box_min_width")
        node.height = settings.get("box_min_height")
        node.x = x
        node.y = y
        return node

    # Compute child sizes (recursively)
    child_sizes = [calculate_node_size(child, settings) for child in node.children]

    # Find best layout (and best ordering) for these children
    result = find_best_layout(child_sizes, len(child_sizes), settings)
    best_layout = result.layout
    best_perm = result.permutation

    # Reorder node.children to match the best permutation
    node.children = [node.children[i] for i in best_perm]

    # Reorder child_sizes similarly
    child_sizes = [child_sizes[i] for i in best_perm]

    # Assign bounding box for this parent node
    node.x = x
    node.y = y
    node.width = best_layout.width
    node.height = best_layout.height

    # Now place each child in the positions that produced the best layout
    for (child, pos) in zip(node.children, best_layout.positions):
        # Recursively layout the child
        layout_tree(child, settings, x + pos['x'], y + pos['y'])
        # Also set the child's bounding box explicitly
        child.width = pos['width']
        child.height = pos['height']

    return node


def process_layout(model: LayoutModel, settings: Settings) -> LayoutModel:
    """
    Entrypoint: Process the layout for the entire tree.
    """
    return layout_tree(model, settings)
