from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import hashlib
import json
from bcm.models import LayoutModel
from bcm.settings import Settings
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

@dataclass
class CacheKey:
    """Represents a unique key for caching layout calculations"""
    node_id: int
    settings_hash: str

    def __hash__(self):
        return hash((self.node_id, self.settings_hash))


class LayoutCache:
    def __init__(self):
        self._size_cache: Dict[CacheKey, NodeSize] = {}
        self._layout_cache: Dict[Tuple[int, ...], LayoutResult] = {}
    
    def get_node_size(self, key: CacheKey) -> Optional[NodeSize]:
        return self._size_cache.get(key)
    
    def set_node_size(self, key: CacheKey, size: NodeSize):
        self._size_cache[key] = size
    
    def get_layout(self, child_ids: Tuple[int, ...], settings_hash: str) -> Optional[LayoutResult]:
        return self._layout_cache.get((child_ids, settings_hash))
    
    def set_layout(self, child_ids: Tuple[int, ...], settings_hash: str, result: LayoutResult):
        self._layout_cache[(child_ids, settings_hash)] = result


def hash_settings(settings: Settings) -> str:
    """Create a stable hash of settings that affect layout"""
    relevant_settings = {
        'box_min_width': settings.get('box_min_width'),
        'box_min_height': settings.get('box_min_height'),
        'horizontal_gap': settings.get('horizontal_gap'),
        'vertical_gap': settings.get('vertical_gap'),
        'padding': settings.get('padding'),
        'top_padding': settings.get('top_padding'),
        'target_aspect_ratio': settings.get('target_aspect_ratio'),
    }
    settings_str = json.dumps(relevant_settings, sort_keys=True)
    return hashlib.sha256(settings_str.encode()).hexdigest()


def calculate_node_size(
    node: LayoutModel,
    settings: Settings,
    cache: LayoutCache,
    settings_hash: str
) -> NodeSize:
    """Calculate the minimum bounding size needed for a node and its children, with caching."""
    # Check cache first
    cache_key = CacheKey(node.id, settings_hash)
    cached_size = cache.get_node_size(cache_key)
    if cached_size is not None:
        return cached_size

    if not node.children:
        size = NodeSize(settings.get("box_min_width"), settings.get("box_min_height"))
    else:
        # Calculate sizes for all children (using cache)
        child_sizes = [
            calculate_node_size(child, settings, cache, settings_hash)
            for child in node.children
        ]
        
        # Create tuple of child IDs for layout cache key
        child_ids = tuple(child.id for child in node.children)
        
        # Try to get cached layout result
        layout_result = cache.get_layout(child_ids, settings_hash)
        if layout_result is None:
            layout_result = find_best_layout(child_sizes, len(child_sizes), settings)
            cache.set_layout(child_ids, settings_hash, layout_result)
        
        size = NodeSize(layout_result.layout.width, layout_result.layout.height)

    # Cache the result
    cache.set_node_size(cache_key, size)
    return size


def _try_layout_for_permutation(
    perm_sizes: List[NodeSize],
    permutation: List[int],
    child_count: int,
    settings: Settings,
) -> GridLayout:
    """
    For a given list of child sizes in the exact order `perm_sizes`,
    try all row/col combinations. Return the **best** GridLayout found.
    This does NOT store a global best; it only returns the best for this single permutation.
    """
    # Grab relevant settings
    horizontal_gap = settings.get("horizontal_gap", 20.0)
    vertical_gap = settings.get("vertical_gap", 20.0)
    padding = settings.get("padding", 20.0)
    top_padding = settings.get("top_padding", padding)
    target_aspect_ratio = settings.get("target_aspect_ratio", 1.6)

    # Start with a "worst" possible layout
    local_best_layout = GridLayout(
        rows=1,
        cols=child_count,
        width=float("inf"),
        height=float("inf"),
        deviation=float("inf"),
        positions=[],
    )

    for rows_tentative in range(1, child_count + 1):
        # We try two ways for columns:
        #  - float division
        #  - integer-based "ceil" approach
        for cols_float in [
            child_count / rows_tentative,
            (child_count + rows_tentative - 1) // rows_tentative,
        ]:
            cols = int(round(cols_float))
            if cols <= 0:
                continue

            # Figure out how many rows are needed if we have 'cols' columns
            rows = (child_count + cols - 1) // cols

            row_heights = [0.0] * rows
            col_widths = [0.0] * cols

            # Compute bounding box for each row & column
            for i, size in enumerate(perm_sizes):
                r = i // cols
                c = i % cols
                row_heights[r] = max(row_heights[r], size.height)
                col_widths[c] = max(col_widths[c], size.width)

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
            extra_width_per_col = (
                max(0, total_width - (grid_width + 2 * padding)) / cols
                if cols > 0
                else 0
            )

            extra_height_per_row = (
                max(0, total_height - (grid_height + top_padding + padding)) / rows
                if rows > 0
                else 0
            )

            for r in range(rows):
                x_offset = padding
                for c in range(cols):
                    idx = r * cols + c
                    if idx < child_count:
                        child_size = perm_sizes[idx]
                        pos = {
                            "x": x_offset,
                            "y": y_offset,
                            "width": child_size.width + extra_width_per_col,
                            "height": child_size.height + extra_height_per_row,
                        }
                        positions.append(pos)
                        x_offset += (
                            child_size.width + extra_width_per_col + horizontal_gap
                        )
                y_offset += row_heights[r] + extra_height_per_row + vertical_gap

            # Recompute the actual needed height from the bottom-most child
            max_child_bottom = max(pos["y"] + pos["height"] for pos in positions)
            actual_height = max_child_bottom + padding

            current_layout = GridLayout(
                rows=rows,
                cols=cols,
                width=total_width,
                height=actual_height,
                deviation=deviation,
                positions=positions,
            )

            # Compare with local_best_layout
            if (current_layout.deviation < local_best_layout.deviation) or (
                abs(current_layout.deviation - local_best_layout.deviation) < 1e-9
                and (
                    current_layout.width * current_layout.height
                    < local_best_layout.width * local_best_layout.height
                )
            ):
                local_best_layout = current_layout

    return local_best_layout


def find_best_layout(
    child_sizes: List[NodeSize], child_count: int, settings: Settings
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
        width=float("inf"),
        height=float("inf"),
        deviation=float("inf"),
        positions=[],
    )
    best_perm = list(range(child_count))

    # Decide if we brute-force permutations
    do_permutations = child_count <= MAX_PERMUTATION_CHILDREN

    # Helper to test a given permutation
    def check_permutation(
        perm: List[int], best_layout: GridLayout, best_perm: List[int]
    ):
        # Build the permuted child_sizes
        perm_sizes = [child_sizes[i] for i in perm]
        candidate_layout = _try_layout_for_permutation(
            perm_sizes, perm, child_count, settings
        )

        # Compare with best_layout
        if (candidate_layout.deviation < best_layout.deviation) or (
            abs(candidate_layout.deviation - best_layout.deviation) < 1e-9
            and (
                candidate_layout.width * candidate_layout.height
                < best_layout.width * best_layout.height
            )
        ):
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
        best_layout, best_perm = check_permutation(
            identity_perm, best_layout, best_perm
        )

    # Return both
    return LayoutResult(layout=best_layout, permutation=best_perm)


def layout_tree(
    node: LayoutModel,
    settings: Settings,
    cache: LayoutCache,
    settings_hash: str,
    x: float = 0.0,
    y: float = 0.0
) -> LayoutModel:
    """Recursively layout the tree starting from the given node, using cache."""
    if not node.children:
        node.width = settings.get("box_min_width")
        node.height = settings.get("box_min_height")
        node.x = x
        node.y = y
        return node

    # Calculate child sizes (using cache)
    child_sizes = [
        calculate_node_size(child, settings, cache, settings_hash)
        for child in node.children
    ]

    # Get layout result from cache or compute it
    child_ids = tuple(child.id for child in node.children)
    layout_result = cache.get_layout(child_ids, settings_hash)
    if layout_result is None:
        layout_result = find_best_layout(child_sizes, len(child_sizes), settings)
        cache.set_layout(child_ids, settings_hash, layout_result)

    # Reorder children according to best permutation
    node.children = [node.children[i] for i in layout_result.permutation]
    child_sizes = [child_sizes[i] for i in layout_result.permutation]

    # Assign bounding box for parent node
    node.x = x
    node.y = y
    node.width = layout_result.layout.width
    node.height = layout_result.layout.height

    # Place each child
    for child, pos in zip(node.children, layout_result.layout.positions):
        layout_tree(child, settings, cache, settings_hash, x + pos["x"], y + pos["y"])
        child.width = pos["width"]
        child.height = pos["height"]

    return node

def process_layout(model: LayoutModel, settings: Settings) -> LayoutModel:
    """Process the layout for the entire tree with caching."""
    # Create cache and hash settings
    cache = LayoutCache()
    settings_hash = hash_settings(settings)
    
    return layout_tree(model, settings, cache, settings_hash)
