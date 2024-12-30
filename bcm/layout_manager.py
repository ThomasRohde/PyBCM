from .models import LayoutModel
from .settings import Settings
from . import layout
from . import hq_layout

def process_layout(model: LayoutModel, settings: Settings) -> LayoutModel:
    """
    Process the layout using the selected algorithm from settings.
    
    Args:
        model: The model to layout
        settings: Settings instance containing layout preferences
        
    Returns:
        The processed model with layout information
    """
    algorithm = settings.get("layout_algorithm", "standard")
    
    if algorithm == "hq":
        return hq_layout.process_layout(model, settings)
    else:  # standard or fallback
        return layout.process_layout(model, settings)
