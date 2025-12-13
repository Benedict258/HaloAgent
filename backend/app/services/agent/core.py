import json
import logging
from typing import Dict, Any, List, Optional
from app.services.meta_ai import meta_ai_service
from app.services.agent.tools import agent_tools
from app.services.agent.prompts import agent_prompts

logger = logging.getLogger(__name__)

class HaloAgent:
    def __init__(self):
        self.tools = agent_tools
        self.tool_definitions = self.tools.get_tool_definitions()
        self.system_prompt = agent_prompts.get_system_prompt(json.dumps(self.tool_definitions, indent=2))
        self.max_iterations = 5

    async def run(self, message: str, phone: str, context: Optional[str] = None) -> str:
        """
        Run the agent loop for a given user message.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"User Phone: {phone}\nContext: {context}\nMessage: {message}"}
        ]

        for i in range(self.max_iterations):
            response_text = await meta_ai_service.chat_completion(messages)
            
            if not response_text:
                return "I apologize, but I'm having trouble connecting to my brain right now. Please try again later."
            
            # Clean up potential markdown code blocks if the LLM wraps JSON in ```json ... ```
            cleaned_response = self._clean_json_response(response_text)
            
            try:
                response_data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If valid JSON wasn't returned, treat it as a raw text response (fallback)
                logger.warning(f"Agent returned non-JSON response: {response_text}")
                return response_text

            action = response_data.get("action")
            
            if action == "final_answer":
                return response_data.get("message", "I have processed your request.")
            
            elif action == "tool_call":
                tool_name = response_data.get("tool_name")
                parameters = response_data.get("parameters", {})
                
                # Automatically inject phone if missing and needed
                if "phone" not in parameters:
                    parameters["phone"] = phone
                
                tool_result = await self._execute_tool(tool_name, parameters)
                
                # Append the interaction to history so the agent knows what happened
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Tool Output ({tool_name}): {tool_result}"})
                
            else:
                return "I'm not sure how to proceed. Please try rephrasing."
                
        return "I'm taking too long to think. Please try a simpler request."

    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        try:
            if hasattr(self.tools, tool_name):
                method = getattr(self.tools, tool_name)
                # Call the method with unpacked parameters
                # Note: This assumes parameters match the method signature
                # In a robust system, we'd inspect signature or use **kwargs
                return await method(**parameters)
            else:
                return json.dumps({"error": f"Tool '{tool_name}' not found"})
        except Exception as e:
            return json.dumps({"error": f"Error executing tool '{tool_name}': {str(e)}"})

    def _clean_json_response(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

agent = HaloAgent()
