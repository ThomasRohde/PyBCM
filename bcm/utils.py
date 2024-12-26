from typing import List, Dict
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader
import os

# Setup Jinja2 environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = Environment(loader=FileSystemLoader(template_dir))

class SubCapability(BaseModel):
    name: str = Field(description="Name of the sub-capability")
    description: str = Field(description="Clear description of the sub-capability's purpose and scope")

class CapabilityExpansion(BaseModel):
    subcapabilities: List[SubCapability] = Field(
        description="List of sub-capabilities that would logically extend the given capability"
    )

class FirstLevelCapability(BaseModel):
    name: str = Field(description="Name of the first-level capability")
    description: str = Field(description="Description of the first-level capability's purpose and scope")

class FirstLevelCapabilities(BaseModel):
    capabilities: List[FirstLevelCapability] = Field(
        description="List of first-level capabilities for the organization"
    )

async def generate_first_level_capabilities(organisation_name: str, organisation_description: str) -> Dict[str, str]:
    """
    Generate first-level capabilities for an organization using AI.
    Returns a dictionary of capability names and their descriptions.
    """
    first_level_template = jinja_env.get_template('first_level_prompt.j2')
    
    agent = Agent(
        'openai:gpt-4o',
        system_prompt="You are a business capability modeling expert. Generate clear, strategic first-level capabilities.",
        result_type=FirstLevelCapabilities
    )

    prompt = first_level_template.render(
        organisation_name=organisation_name,
        organisation_description=organisation_description
    )

    result = await agent.run(prompt)
    return {cap.name: cap.description for cap in result.data.capabilities}

async def expand_capability_ai(context: str, capability_name: str, max_capabilities: int = 5) -> Dict[str, str]:
    """
    Use PydanticAI to expand a capability into sub-capabilities with descriptions,
    following best practices for business capability modeling.
    """
    # Load and render templates
    system_template = jinja_env.get_template('system_prompt.j2')
    expansion_template = jinja_env.get_template('expansion_prompt.j2')

    agent = Agent(
        'openai:gpt-4o',
        system_prompt=system_template.render(),
        result_type=CapabilityExpansion
    )

    prompt = expansion_template.render(
        capability_name=capability_name,
        context=context,
        max_capabilities=max_capabilities
    )

    result = await agent.run(prompt)
    return {cap.name: cap.description for cap in result.data.subcapabilities}

def build_capability_tree(db_ops, root_caps, current_cap_id: int, level: int = 0, prefix: str = "") -> List[str]:
    """Build a tree representation of capabilities with the current capability marked."""
    tree_lines = []
    last_index = len(root_caps) - 1

    for i, cap in enumerate(root_caps):
        is_last = i == last_index
        current_prefix = prefix + ("└── " if is_last else "├── ")
        marker = " *" if cap.id == current_cap_id else ""
        tree_lines.append(f"{prefix}{current_prefix}{cap.name}{marker}")
        
        # Get children
        children = db_ops.get_capabilities(cap.id)
        if children:
            next_prefix = prefix + ("    " if is_last else "│   ")
            tree_lines.extend(build_capability_tree(db_ops, children, current_cap_id, level + 1, next_prefix))
    
    return tree_lines

def get_capability_context(db_ops, capability_id: int) -> str:
    """Get context information for AI expansion, including full parent hierarchy."""
    capability = db_ops.get_capability(capability_id)
    if not capability:
        return ""

    context_parts = []

    # Section 1: First-level capabilities
    context_parts.append("<first_level_capabilities>")
    first_level_caps = db_ops.get_capabilities(parent_id=None)
    if first_level_caps:
        for cap in first_level_caps:
            context_parts.append(f"- {cap.name}")
            if cap.description:
                context_parts.append(f"  Description: {cap.description}")
    context_parts.append("</first_level_capabilities>")

    # Section 2: Capability Tree
    context_parts.append("<capability_tree>")
    tree_lines = build_capability_tree(db_ops, first_level_caps, capability_id)
    context_parts.extend(tree_lines)
    context_parts.append("</capability_tree>")

    # Section 3: Parent Hierarchy
    context_parts.append("<parent_hierarchy>")
    def add_parent_hierarchy(cap_id: int, level: int = 0) -> None:
        parent = db_ops.get_capability(cap_id)
        if parent:
            if parent.parent_id:
                add_parent_hierarchy(parent.parent_id, level + 1)
            context_parts.append(f"Level {level+1}: {parent.name}")
            if parent.description:
                # truncate long descriptions
                context_parts.append(f"Description: {parent.description[:200]}")

    if capability.parent_id:
        add_parent_hierarchy(capability.parent_id)
    context_parts.append("</parent_hierarchy>")

    # Section 4: Sibling Context
    context_parts.append("<sibling_context>")
    siblings = db_ops.get_capabilities(capability.parent_id)
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
        context_parts.append(f"Description: {capability.description}")

    context_parts.append("</current_capability>")
    return "\n".join(context_parts)
