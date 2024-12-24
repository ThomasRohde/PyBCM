from typing import List, Dict
from pydantic_ai import Agent
from pydantic import BaseModel, Field

class SubCapability(BaseModel):
    name: str = Field(description="Name of the sub-capability")
    description: str = Field(description="Clear description of the sub-capability's purpose and scope")

class CapabilityExpansion(BaseModel):
    subcapabilities: List[SubCapability] = Field(
        description="List of sub-capabilities that would logically extend the given capability"
    )

async def expand_capability_ai(context: str, capability_name: str) -> Dict[str, str]:
    """
    Use PydanticAI to expand a capability into sub-capabilities with descriptions,
    following best practices for business capability modeling.
    """
    agent = Agent(
        # Your model name here
        'openai:gpt-4o-mini',
        system_prompt=(
            "You are a business capability modeling expert specializing in established frameworks "
            "such as BIZBOK. Your role is to analyze a business capability in its context and propose "
            "logical sub-capabilities that are stable, distinct, measurable, and outcome-focused. "
            "Each sub-capability should have a name and a concise description that clearly defines "
            "its scope, purpose, and value. Keep in mind: "
            "• Align sub-capabilities with business strategy and stakeholder needs. "
            "• Ensure each sub-capability is re-usable, well-defined, and non-overlapping. "
            "• Present them so that an organization could readily assign ownership and measure performance. "
            "• Do NOT use language in the description like 'this sub-capability'; instead, "
            "explicitly use the capability name in the description if needed."
        ),
        result_type=CapabilityExpansion
    )

    prompt = (
        f"Based on the following context, suggest sub-capabilities for '{capability_name}':"
        f"\n\n{context}\n\n"
        "Please list and describe a set of sub-capabilities that logically extend or detail the above capability. "
        "For each sub-capability: "
        "• Provide a clear name. "
        "• Include a concise, business-oriented description of its scope, purpose, and any critical processes. "
        "• Ensure it is distinct, stable, and aligned with best practices for capability modeling."
    )

    result = await agent.run(prompt)
    # Convert the validated SubCapability objects to a dictionary
    return {cap.name: cap.description for cap in result.data.subcapabilities}

def get_capability_context(db_ops, capability_id: int) -> str:
    """Get context information for AI expansion, including full parent hierarchy."""
    capability = db_ops.get_capability(capability_id)
    if not capability:
        return ""

    context_parts = []

    # Add full parent hierarchy context
    def add_parent_hierarchy(cap_id: int, level: int = 0) -> None:
        parent = db_ops.get_capability(cap_id)
        if parent:
            if parent.parent_id:
                add_parent_hierarchy(parent.parent_id, level + 1)
            context_parts.append(f"Parent capability: {parent.name}")
            if parent.description:
                context_parts.append(f"Parent description: {parent.description}\n")

    if capability.parent_id:
        add_parent_hierarchy(capability.parent_id)

    # Add sibling context
    siblings = db_ops.get_capabilities(capability.parent_id)
    if siblings:
        context_parts.append("Related capabilities:")
        for sibling in siblings:
            if sibling.id != capability_id:  # Exclude the current capability
                context_parts.append(f"- {sibling.name}")
                if sibling.description:
                    context_parts.append(f"  Description: {sibling.description}")

    # Add current capability
    context_parts.append(f"\nCurrent capability: {capability.name}")
    if capability.description:
        context_parts.append(f"Current description: {capability.description}")

    return "\n".join(context_parts)
