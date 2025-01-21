import tempfile
from fastapi import HTTPException
from fastapi.responses import Response
from bcm.models import LayoutModel
from bcm.settings import Settings
from bcm.archimate_export import export_to_archimate
from bcm.pptx_export import export_to_pptx
from bcm.svg_export import export_to_svg
from bcm.markdown_export import export_to_markdown
from bcm.word_export import export_to_word
from bcm.html_export import export_to_html
from bcm.mermaid_export import export_to_mermaid
from bcm.plantuml_export import export_to_plantuml

def format_capability(node_id: int, format_type: str, layout_model: LayoutModel, settings: Settings) -> Response:
    """Format a capability model in the specified format.
    
    Args:
        node_id: ID of the node being exported
        format_type: Type of format to export to
        layout_model: The layout model to format
        settings: Application settings
        
    Returns:
        FastAPI Response with appropriate content type and headers
        
    Raises:
        HTTPException: If format is invalid or export fails
    """
    try:
        if format_type == "powerpoint":
            presentation = export_to_pptx(layout_model, settings)
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                presentation.save(tmp.name)
                with open(tmp.name, 'rb') as f:
                    content = f.read()
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.pptx"}
            )
        elif format_type == "word":
            document = export_to_word(layout_model, settings)
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
                document.save(tmp.name)
                with open(tmp.name, 'rb') as f:
                    content = f.read()
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.docx"}
            )
        elif format_type == "archimate":
            content = export_to_archimate(layout_model, settings)
            return Response(
                content=content,
                media_type="application/xml",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.xml"}
            )
        elif format_type == "svg":
            content = export_to_svg(layout_model, settings)
            return Response(
                content=content,
                media_type="image/svg+xml",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.svg"}
            )
        elif format_type == "markdown":
            content = export_to_markdown(layout_model, settings)
            return Response(
                content=content,
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.md"}
            )
        elif format_type == "html":
            content = export_to_html(layout_model, settings)
            return Response(
                content=content,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.html"}
            )
        elif format_type == "mermaid":
            content = export_to_mermaid(layout_model, settings)
            return Response(
                content=content,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.html"}
            )
        elif format_type == "plantuml":
            content = export_to_plantuml(layout_model, settings)
            return Response(
                content=content,
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename=capability_{node_id}.puml"}
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
