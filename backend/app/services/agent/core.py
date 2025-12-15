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
        Run the agent loop - handles tool calls silently and returns natural responses.
        """
        
        # Get conversation history from database
        from app.db.supabase_client import supabase
        history = supabase.table("message_logs").select("direction, content").eq("contact_id", phone).order("created_at", desc=True).limit(10).execute()
        
        # Build conversation context
        conversation_history = ""
        if history.data:
            for msg in reversed(history.data[-6:]):  # Last 3 exchanges
                role = "Customer" if msg["direction"] == "IN" else "You"
                conversation_history += f"{role}: {msg['content']}\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{context}\n\nRecent conversation:\n{conversation_history}\nCustomer now says: {message}"}
        ]

        for i in range(self.max_iterations):
            response_text = await meta_ai_service.chat_completion(messages, temperature=0.7)
            
            if not response_text:
                return "I'm having a bit of trouble right now. Mind trying again in a sec?"
            
            cleaned_response = self._clean_json_response(response_text)
            
            try:
                response_data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # LLM returned plain text - use it directly
                logger.info(f"Agent returned natural text: {response_text[:100]}")
                return response_text

            action = response_data.get("action")
            
            if action == "final_answer":
                return response_data.get("message", "Got it!")
            
            elif action == "tool_call":
                tool_name = response_data.get("tool_name")
                parameters = response_data.get("parameters", {})
                
                # Auto-inject phone
                if "phone" not in parameters:
                    parameters["phone"] = phone
                
                # Execute tool silently
                tool_result = await self._execute_tool(tool_name, parameters)
                logger.info(f"Tool {tool_name} executed: {tool_result[:100]}")
                
                # Continue conversation with tool result
                messages.append({"role": "assistant", "content": cleaned_response})
                messages.append({"role": "user", "content": f"Tool result: {tool_result}"})
                
            else:
                return "Let me know how I can help!"
                
        return "This is taking a bit longer than expected. Can you try asking in a simpler way?"

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
