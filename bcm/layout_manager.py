from bcm.models import LayoutModel
from bcm.settings import Settings
from bcm import layout
from bcm import hq_layout
from bcm import alt_layout


def process_layout(model: LayoutModel, settings: Settings) -> LayoutModel:
    """
    Process the layout using the selected algorithm from settings.

    Args:
        model: The model to layout
        settings: Settings instance containing layout preferences

    Returns:
        The processed model with layout information
    """
    algorithm = settings.get("layout_algorithm", "Simple - fast")

    if algorithm == "Advanced - slow":
        return hq_layout.process_layout(model, settings)
    if algorithm == "Experimental":
        return alt_layout.process_layout(model, settings)
    else:  # standard or fallback
        return layout.process_layout(model, settings)
