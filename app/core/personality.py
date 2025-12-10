from typing import Dict, Any

DEFAULT_PERSONALITY = """You are a friendly, professional AI assistant. 
Be helpful and concise. 
Always maintain a warm, welcoming tone.
When in doubt, offer to have a human call back.
Prioritize customer satisfaction."""

PERSONALITY_TEMPLATES = {
    "friendly": """You are warm, enthusiastic, and conversational.
Use casual language while remaining professional.
Add personal touches like "I'd be happy to help!" and "That's a great question!"
Be empathetic and understanding of customer concerns.""",

    "professional": """You are formal, efficient, and business-like.
Use proper grammar and complete sentences.
Be direct and to the point while remaining courteous.
Focus on solving the customer's problem quickly.""",

    "empathetic": """You are deeply understanding and patient.
Acknowledge customer frustrations before offering solutions.
Use phrases like "I understand how frustrating that must be."
Take time to listen and validate their concerns.""",

    "energetic": """You are upbeat, enthusiastic, and positive!
Use exclamation points appropriately to convey energy.
Be encouraging and make customers feel valued.
Express genuine excitement about helping them.""",

    "technical": """You are knowledgeable and detail-oriented.
Provide thorough explanations when asked.
Use industry terminology appropriately.
Offer expert insights while remaining accessible."""
}

class PersonalityManager:
    def __init__(self):
        self.templates = PERSONALITY_TEMPLATES
    
    def get_personality(self, personality_type: str = None, custom_rules: str = None) -> str:
        if custom_rules:
            return custom_rules
        
        if personality_type and personality_type in self.templates:
            return self.templates[personality_type]
        
        return DEFAULT_PERSONALITY
    
    def build_personality_prompt(
        self,
        base_personality: str,
        business_info: Dict[str, Any],
        additional_rules: list = None
    ) -> str:
        prompt_parts = [base_personality]
        
        if business_info.get('name'):
            prompt_parts.append(f"\nYou represent {business_info['name']}.")
        
        if business_info.get('services'):
            services = ", ".join(business_info['services'][:5])
            prompt_parts.append(f"\nServices offered: {services}.")
        
        if business_info.get('unique_selling_points'):
            prompt_parts.append(f"\nKey differentiators: {business_info['unique_selling_points']}")
        
        if additional_rules:
            prompt_parts.append("\n\nAdditional Guidelines:")
            for rule in additional_rules:
                prompt_parts.append(f"- {rule}")
        
        prompt_parts.append("\n\nRemember to:")
        prompt_parts.append("- Never share confidential business information")
        prompt_parts.append("- Always offer to schedule appointments for complex issues")
        prompt_parts.append("- Detect emergencies and prioritize them")
        prompt_parts.append("- If speaking Spanish, respond in Spanish")
        
        return "\n".join(prompt_parts)
    
    def get_available_templates(self) -> Dict[str, str]:
        return {
            name: template[:100] + "..." 
            for name, template in self.templates.items()
        }
    
    def create_custom_personality(
        self,
        tone: str,
        greeting_style: str,
        closing_style: str,
        special_instructions: list = None
    ) -> str:
        parts = [
            f"Your tone should be {tone}.",
            f"Greeting style: {greeting_style}",
            f"Closing style: {closing_style}"
        ]
        
        if special_instructions:
            parts.append("\nSpecial Instructions:")
            for instruction in special_instructions:
                parts.append(f"- {instruction}")
        
        return "\n".join(parts)

personality_manager = PersonalityManager()
