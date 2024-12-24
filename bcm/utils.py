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
        'openai:gpt-4o',  
        system_prompt=(
            "You are a business capability modeling expert specializing in established frameworks "
            "such as BIZBOK and the Business Architecture Guild's guidance. Your role is to analyze "
            "a business capability in its context and propose logical, MECE (Mutually Exclusive, "
            "Collectively Exhaustive) sub-capabilities. "
            "Focus on creating sub-capabilities that are stable, distinct, measurable, and outcome-focused. "
            "Each sub-capability should have a concise name and a clear description that defines "
            "its scope, purpose, and value, making it understandable to business stakeholders. "
            "Remember these key principles:\n"
            "• **Strategic Alignment:** Ensure each sub-capability directly supports the overarching business strategy and objectives.\n"
            "• **Stakeholder Value:**  Focus on delivering clear value to stakeholders.\n"
            "• **Reusability and Stability:** Design sub-capabilities that are reusable across different business units or initiatives and remain relevant over time.\n"
            "• **Non-Overlapping:** Ensure that sub-capabilities are distinct and do not overlap in scope or responsibility. (MECE)\n"
            "• **Measurability:** Each sub-capability should be measurable through relevant KPIs or metrics.\n"
            "• **Outcome-Focused:** Define sub-capabilities in terms of the outcomes they enable, rather than the activities they perform.\n"
            "• **Clarity and Simplicity:** Use clear, concise, and business-oriented language, avoiding technical jargon.\n"
            "• **Ownership:**  Structure sub-capabilities so that ownership can be clearly assigned within the organization.\n"
            "• **Abstraction:** Model capabilities at the appropriate level of abstraction, neither too detailed nor too high-level. Focus on the 'what' not the 'how'\n"
            "• **Standard Nomenclature:** Use consistent naming conventions aligned with industry best practices and the organization's terminology.\n"
            "• **Do NOT use reflexive language** like 'this sub-capability' in the description; instead, explicitly use the capability name if needed.\n"
        ),
        result_type=CapabilityExpansion
    )

    prompt = (
        f"Analyze the business capability '{capability_name}' within the context provided below. "
        f"Decompose this capability into a set of MECE sub-capabilities that adhere to the principles "
        f"of effective business capability modeling.\n\n"
        f"**Context:**\n{context}\n\n"
        f"**Instructions:**\n"
        f"For each sub-capability identified, provide:\n"
        f"1. **Name:** A concise and descriptive name that clearly communicates the sub-capability's focus.\n"
        f"2. **Description:** A brief, business-oriented explanation that outlines the sub-capability's scope, purpose, intended outcomes, and alignment with the overall business capability. "
        f"Ensure the description is understandable to both business and technical stakeholders.\n\n"
        f"**Consider the following when defining sub-capabilities:**\n"
        f"- **Alignment with Parent Capability:** Each sub-capability should directly contribute to and be a logical extension of '{capability_name}'.\n"
        f"- **Business Value:** Clearly articulate the value each sub-capability provides to the organization.\n"
        f"- **Distinctness:** Ensure there is no overlap in scope or responsibility between sub-capabilities.\n"
        f"- **Completeness:** The set of sub-capabilities should collectively cover the entire scope of '{capability_name}' without any gaps.\n"
        f"- **Consistency:**  Maintain a consistent level of detail and abstraction across all sub-capabilities."
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
            context_parts.append(f"Parent capability (Level {level+1}): {parent.name}")
            if parent.description:
                context_parts.append(f"Parent description: {parent.description}\n")

    if capability.parent_id:
        add_parent_hierarchy(capability.parent_id)

    # Add sibling context
    siblings = db_ops.get_capabilities(capability.parent_id)
    if siblings:
        context_parts.append("Related capabilities (Siblings):")
        for sibling in siblings:
            if sibling.id != capability_id:  # Exclude the current capability
                context_parts.append(f"- {sibling.name}")
                if sibling.description:
                    context_parts.append(f"  Description: {sibling.description}")

    # Add current capability
    context_parts.append(f"\n**Current capability to expand:** {capability.name}") # Added emphasis
    if capability.description:
        context_parts.append(f"Current description: {capability.description}")

    return "\n".join(context_parts)