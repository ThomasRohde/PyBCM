# Business Capability Model Layout Algorithms

This repository contains two different approaches to laying out hierarchical business capability models in a grid format. Both algorithms optimize for aspect ratio while maintaining a clean, organized visual structure.

## Overview

The repository contains two main layout implementations:
- `hq_layout.py`: Advanced layout with permutation optimization
- `layout.py`: Streamlined layout with predictable ordering

## Key Features

### Common Functionality
- Recursive tree-based layout approach
- Grid-based child node arrangement
- Aspect ratio optimization
- Configurable padding and gaps
- Minimum box size constraints
- Support for hierarchical node structures

### HQ Layout (`hq_layout.py`)
- Permutation testing for optimal arrangements (≤8 nodes)
- Tracks both layout and node ordering
- Uses squared difference for aspect ratio deviation
- Can reorder children for optimal layout
- Includes dedicated `LayoutResult` class

### Standard Layout (`layout.py`)
- Maintains original child order
- Uses absolute difference for aspect ratio deviation
- Streamlined implementation
- Predictable output
- Memory efficient

## Usage

```python
from hq_layout import process_layout
# or
from layout import process_layout

# Create your model and settings
model = LayoutModel(...)
settings = Settings({
    "box_min_width": 100,
    "box_min_height": 50,
    "horizontal_gap": 20,
    "vertical_gap": 20,
    "padding": 20,
    "target_aspect_ratio": 1.6
})

# Process the layout
processed_model = process_layout(model, settings)
```

## When to Use Which

### Use HQ Layout When:
- Layout quality is the top priority
- You have small sets of children (≤8 nodes)
- Child ordering isn't critical
- Processing time isn't a major concern

### Use Standard Layout When:
- Performance is critical
- You have large sets of children
- Child order must be preserved
- Predictable output is required

## Performance Considerations

### HQ Layout
- Time Complexity: O(n!) for small sets (n ≤ 8), O(n) for larger sets
- Memory Usage: Higher due to permutation storage
- Best for small to medium hierarchies with emphasis on layout quality

### Standard Layout
- Time Complexity: O(n)
- Memory Usage: Minimal
- Best for large hierarchies or performance-critical applications

## Implementation Details

### Deviation Calculation
```python
# HQ Layout
deviation = (aspect_ratio - target_aspect_ratio) ** 2

# Standard Layout
deviation = abs(aspect_ratio - target_aspect_ratio)
```

### Grid Position Calculation
Both implementations use similar approaches for calculating grid positions:
- Top-down layout calculation
- Recursive size computation
- Gap and padding considerations
- Automatic height/width adjustments

