from typing import List, Dict
from pydantic_ai import Agent
from jinja2 import Environment, FileSystemLoader
import os
from bcm.settings import Settings
from bcm.models import CapabilityExpansion, FirstLevelCapabilities

def init_user_templates():
    """Initialize user template directory and copy application templates if needed."""
    # Get application and user template directories
    app_template_dir = os.path.join(os.path.dirname(__file__), "templates")
    user_dir = os.path.expanduser("~")
    user_template_dir = os.path.join(user_dir, ".pybcm", "templates")
    
    # Create user template directory if it doesn't exist
    os.makedirs(user_template_dir, exist_ok=True)
    
    # Copy application templates to user directory if they don't exist
    for template in os.listdir(app_template_dir):
        src = os.path.join(app_template_dir, template)
        dst = os.path.join(user_template_dir, template)
        if not os.path.exists(dst) and os.path.isfile(src):
            with open(src, 'r') as f_src, open(dst, 'w') as f_dst:
                f_dst.write(f_src.read())
    return app_template_dir, user_template_dir

def get_jinja_env() -> Environment:
    """Get the shared Jinja2 environment that checks user templates first, then falls back to application templates."""
    app_template_dir, user_template_dir = init_user_templates()
    return Environment(loader=FileSystemLoader([user_template_dir, app_template_dir]))

# Initialize the shared Jinja environment
jinja_env = get_jinja_env()


async def generate_first_level_capabilities(
    organisation_name: str, organisation_description: str
) -> Dict[str, str]:
    """
    Generate first-level capabilities for an organization using AI.
    Returns a dictionary of capability names and their descriptions.
    """
    first_level_template = jinja_env.get_template("first_level_prompt.j2")
    settings = Settings()
    model = settings.get("model")

    agent = Agent(
        model,
        system_prompt="You are a business capability modeling expert. Generate clear, strategic first-level capabilities.",
        result_type=FirstLevelCapabilities,
    )

    prompt = first_level_template.render(
        organisation_name=organisation_name,
        organisation_description=organisation_description,
        first_level=settings.get("first_level_range"),
    )

    result = await agent.run(prompt)
    return {cap.name: cap.description for cap in result.data.capabilities}


async def expand_capability_ai(
    context: str, capability_name: str, max_capabilities: int = 5
) -> Dict[str, str]:
    """
    Use PydanticAI to expand a capability into sub-capabilities with descriptions,
    following best practices for business capability modeling.
    """
    # Load and render templates
    system_template = jinja_env.get_template("system_prompt.j2")
    expansion_template = jinja_env.get_template("expansion_prompt.j2")
    settings = Settings()
    model = settings.get("model")

    agent = Agent(
        model, system_prompt=system_template.render(), result_type=CapabilityExpansion
    )

    prompt = expansion_template.render(
        capability_name=capability_name,
        context=context,
        max_capabilities=max_capabilities,
    )

    result = await agent.run(prompt)
    return {cap.name: cap.description for cap in result.data.subcapabilities}


async def get_capability_context(db_ops, capability_id: int) -> str:
    """Get context information for AI expansion, including full parent hierarchy."""
    capability = await db_ops.get_capability(capability_id)
    if not capability:
        return ""

    context_parts = []

    # Section 1: First-level capabilities
    context_parts.append("<first_level_capabilities>")
    first_level_caps = await db_ops.get_capabilities(parent_id=None)
    if first_level_caps:
        for cap in first_level_caps:
            context_parts.append(f"- {cap.name}")
            if cap.description:
                context_parts.append(f"  Description: {cap.description}")
    context_parts.append("</first_level_capabilities>")

    # Section 2: Capability Tree
    context_parts.append("<capability_tree>")

    async def build_capability_tree(
        root_caps, current_cap_id: int, level: int = 0, prefix: str = ""
    ) -> List[str]:
        tree_lines = []
        last_index = len(root_caps) - 1

        for i, cap in enumerate(root_caps):
            is_last = i == last_index
            current_prefix = prefix + ("└── " if is_last else "├── ")
            marker = " *" if cap.id == current_cap_id else ""
            tree_lines.append(f"{prefix}{current_prefix}{cap.name}{marker}")

            # Get children
            children = await db_ops.get_capabilities(cap.id)
            if children:
                next_prefix = prefix + ("    " if is_last else "│   ")
                child_lines = await build_capability_tree(
                    children, current_cap_id, level + 1, next_prefix
                )
                tree_lines.extend(child_lines)

        return tree_lines

    tree_lines = await build_capability_tree(first_level_caps, capability_id)
    context_parts.extend(tree_lines)
    context_parts.append("</capability_tree>")

    # Section 3: Parent Hierarchy
    context_parts.append("<parent_hierarchy>")

    async def add_parent_hierarchy(cap_id: int, level: int = 0) -> None:
        parent = await db_ops.get_capability(cap_id)
        if parent:
            if parent.parent_id:
                await add_parent_hierarchy(parent.parent_id, level + 1)
            context_parts.append(f"Level {level+1}: {parent.name}")
            if parent.description:
                # truncate long descriptions
                context_parts.append(f"Description: {parent.description[:200]}")

    if capability.parent_id:
        await add_parent_hierarchy(capability.parent_id)
    context_parts.append("</parent_hierarchy>")

    # Section 4: Sibling Context
    context_parts.append("<sibling_context>")
    siblings = await db_ops.get_capabilities(capability.parent_id)
    if siblings:
        for sibling in siblings:
            if sibling.id != capability_id:
                context_parts.append(f"- {sibling.name}")
                if sibling.description:
                    context_parts.append(f"  Description: {sibling.description}")
    context_parts.append("</sibling_context>")

    # Section 5: Current Capability
    context_parts.append("<current_capability>")
    context_parts.append(f"Name: {capability.name}")
    if capability.description:
        context_parts.append(f"Description: {capability.description[:200]}")
    context_parts.append("</current_capability>")

    # Section 6: Sub-Capabilities
    context_parts.append("<sub_capabilities>")
    sub_capabilities = await db_ops.get_capabilities(capability_id)
    if sub_capabilities:
        for sub_cap in sub_capabilities:
            context_parts.append(f"- {sub_cap.name}")
            if sub_cap.description:
                context_parts.append(f"  Description: {sub_cap.description}")
    context_parts.append("</sub_capabilities>")

    return "\n".join(context_parts)
