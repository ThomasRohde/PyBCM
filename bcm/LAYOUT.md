## Layout Algorithm for Hierarchical Tree Structures

### 1. Introduction

When visualizing hierarchical structures (e.g., organizational charts, business capability models, or taxonomies), it is common to place child nodes within a bounding rectangle under their parent. A naïve layout (e.g., single row or column) can become excessively wide or tall, reducing readability. This algorithm attempts all possible row and column combinations for the children and selects the combination that best matches a target aspect ratio (e.g., close to a square) while minimizing the total area.

**Input:**
- A hierarchical node structure with each node containing a list of children.
- Settings specifying padding, gaps, minimum box dimensions, and target aspect ratio.

**Output:**
- (x, y) positions and width/height dimensions for each node, starting from the root and recursing downward.

### 2. Overview of the Algorithm

#### 2.1 Recursive Size Calculation
For each node, compute the minimal bounding box of its children. If a node has no children (a leaf), its size defaults to a minimum width/height as specified in the settings. Otherwise, the algorithm tries different grid layouts to find the “best fit” bounding box for its children.

#### 2.2 Grid Layout Search
Given a set of child nodes, the algorithm enumerates potential grid layouts by varying the number of rows and deriving the corresponding columns (either as an exact or ceiling division). For each candidate grid:
- Compute row-wise and column-wise maximum widths and heights.
- Sum them to obtain the total required width and height.
- Compare the layout’s aspect ratio to the target ratio, and track how much it deviates.
- If the deviation is less than the current best layout, or if equal but with a smaller total area, update the best layout.
- Distribute extra horizontal/vertical space across columns/rows for balance.

#### 2.3 Positioning and Recursion
Once the best layout for a node’s children is found, each child is assigned an (x, y) coordinate and sized according to the computed row and column dimensions. The algorithm then recurses into each child to lay out its own children similarly.

### 3. Detailed Steps

#### 3.1 Calculating Node Size

**Input:** A node with potential children, plus global layout settings.  
**Process:**  
- If no children, return the minimum box size.  
- Otherwise, gather child sizes by recursing downward.  
- Run `find_best_layout` to determine the minimal bounding box for the children.  
**Output:** A (width, height) bounding box.

#### 3.2 Finding the Best Layout

**Input:** A list of child sizes, the number of child nodes, and layout settings.  
**Process:**  
1. Iterate over possible number of rows, 1 ≤ rows_tentative ≤ child_count.  
2. Compute two possible column counts: the exact float division (child_count/rows_tentative) and its ceiling.  
3. For each (rows, cols) combination, calculate:
   - Row and column dimensions (maximum width/height in each row/column).  
   - Total width/height including gaps and padding.  
   - Aspect ratio deviation from the target.  
   - If deviation is smaller, or if equal but total area is smaller, update the best layout.  
4. Compute final positions for each child within the best layout, distributing extra width/height evenly.  
**Output:** A `GridLayout` object containing the best arrangement’s row/column counts, total width/height, deviation, and child positions.

#### 3.3 Recursively Assigning Positions

**Input:** Root node, layout settings, and an initial (x, y) position offset.  
**Process:**  
- Compute node’s bounding box through `find_best_layout`.  
- Assign the node’s (x, y) coordinates and size.  
- For each child, apply the computed position/size offsets, then recurse.  
**Output:** The entire tree is laid out with consistent coordinates and dimensions.

### 4. Pseudo Code

```text
Algorithm LAYOUT_TREE(node, settings, x=0, y=0):
    if node has no children:
        node.width  ← settings.box_min_width
        node.height ← settings.box_min_height
        node.x ← x
        node.y ← y
        return node

    child_sizes ← []
    for each child in node.children:
        child_size ← CALCULATE_NODE_SIZE(child, settings)
        child_sizes.append(child_size)

    best_layout ← FIND_BEST_LAYOUT(child_sizes, settings)

    node.width  ← best_layout.width
    node.height ← best_layout.height
    node.x ← x
    node.y ← y

    for i from 0 to len(node.children)-1:
        child_position ← best_layout.positions[i]
        child_node ← node.children[i]

        LAYOUT_TREE(child_node, settings,
                    x + child_position.x,
                    y + child_position.y)

        child_node.width  ← child_position.width
        child_node.height ← child_position.height

    return node

Function CALCULATE_NODE_SIZE(node, settings) returns NodeSize:
    if node has no children:
        return NodeSize(settings.box_min_width, settings.box_min_height)
    else:
        child_sizes ← []
        for each child in node.children:
            child_sizes.append(CALCULATE_NODE_SIZE(child, settings))

        best_layout ← FIND_BEST_LAYOUT(child_sizes, settings)
        return NodeSize(best_layout.width, best_layout.height)

Function FIND_BEST_LAYOUT(child_sizes, settings) returns GridLayout:
    best_layout ← new GridLayout(infinite width/height, infinite deviation)
    child_count ← length of child_sizes

    for rows_tentative in [1 .. child_count]:
        possible_cols ← [
            float_division ← child_count / rows_tentative,
            ceiling_division ← ceil(child_count / rows_tentative)
        ]

        for cols in possible_cols:
            if cols == 0:
                continue
            rows ← ceil(child_count / cols)

            row_heights ← array of length rows initialized to 0
            col_widths  ← array of length cols initialized to 0

            for i from 0 to child_count-1:
                row ← i // cols
                col ← i % cols
                size ← child_sizes[i]

                row_heights[row] ← max(row_heights[row], size.height)
                col_widths[col]  ← max(col_widths[col],  size.width)

            grid_width  ← sum(col_widths) + (cols - 1) * settings.horizontal_gap
            grid_height ← sum(row_heights) + (rows - 1) * settings.vertical_gap

            total_width  ← grid_width  + 2*settings.padding
            total_height ← grid_height + 2*settings.padding

            aspect_ratio ← total_width / total_height
            deviation    ← abs(aspect_ratio - settings.target_aspect_ratio)

            if (deviation < best_layout.deviation) or
               (deviation == best_layout.deviation and total_width*total_height < best_layout.width*best_layout.height):
                best_layout.rows      ← rows
                best_layout.cols      ← cols
                best_layout.width     ← total_width
                best_layout.height    ← total_height
                best_layout.deviation ← deviation

    return best_layout
```

### 5. Conclusion

This algorithm systematically explores all plausible grid configurations to place child nodes under a parent, achieving a balance between the **target aspect ratio** and **minimum area**. By distributing extra space proportionally among rows and columns, it avoids excessive whitespace and produces a compact, visually coherent diagram suitable for a wide range of hierarchical structures, from organizational charts to business capability maps.

