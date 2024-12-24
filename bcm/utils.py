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
    """Use PydanticAI to expand a capability into sub-capabilities with descriptions."""
    agent = Agent(
        'openai:gpt-4o-mini',
        system_prompt=(
            "You are a business capability modeling expert. "
            "Analyze the context and suggest logical sub-capabilities "
            "that would extend and detail the current capability. "
            "For each sub-capability, provide a clear, concise description "
            "that explains its purpose and scope. "
            "Be specific and business-oriented."
        ),
        result_type=CapabilityExpansion
    )

    prompt = (
        f"Based on the following context, suggest sub-capabilities for '{capability_name}':"
        f"\n\n{context}"
        "\n\nProvide specific, business-oriented sub-capabilities that would "
        "logically extend this capability. Include a clear description for each "
        "sub-capability explaining its purpose and scope."
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
