from app.services.loyalty import loyalty_service
from app.services.compliance import compliance_service
from app.services.analytics import analytics_service
from app.services.language import language_service
from typing import Dict, Any, List
import json

class AgentTools:
    async def award_loyalty_points(self, phone: str, amount: float, reason: str = "order") -> str:
        """Award loyalty points to a customer."""
        points = await loyalty_service.award_points(phone, amount, reason)
        return json.dumps({"status": "success", "points_awarded": points, "message": f"Awarded {points} points to {phone}"})

    async def check_loyalty_points(self, phone: str) -> str:
        """Check the loyalty points balance for a customer."""
        balance = await loyalty_service.get_points_balance(phone)
        return json.dumps({"points_balance": balance})

    async def get_privacy_policy(self) -> str:
        """Get the privacy policy content."""
        return "Our privacy policy ensures your data is safe. You can request deletion by saying 'delete my data'."

    async def handle_data_deletion(self, phone: str) -> str:
        """Handle a request to delete user data."""
        response = await compliance_service.handle_data_deletion_request(phone)
        return json.dumps({"status": "processing", "message": response})
    
    async def log_complaint(self, phone: str, description: str) -> str:
        """Log a customer complaint."""
        # Resolve contact_id
        contact = await loyalty_service._get_or_create_contact(phone)
        contact_id = contact['id'] if contact else None
        
        if contact_id:
            await analytics_service.track_interaction(contact_id, "complaint", {"description": description})
            return json.dumps({"status": "logged", "message": "Complaint has been logged and will be reviewed."})
        return json.dumps({"status": "error", "message": "Could not identify customer."})
    
    async def get_products(self, category: str = None) -> str:
        """Fetch available products from Airtable inventory."""
        # This assumes there is an Airtable table named 'Products'
        from app.services.airtable import airtable_service
        formula = f"{{Category}} = '{category}'" if category else None
        records = await airtable_service.get_records("Products", formula)
        
        # Simplify output for LLM
        products = [{"name": r["fields"].get("Name"), "price": r["fields"].get("Price"), "stock": r["fields"].get("Stock")} for r in records]
        return json.dumps({"products": products})

    async def create_order(self, phone: str, items: List[str], total_amount: float) -> str:
        """Create a new order for the customer."""
        # For now, this is a placeholder as per existing code
        await loyalty_service.award_points(phone, total_amount, "purchase")
        return json.dumps({"status": "created", "order_id": "ORD-12345", "message": "Order created successfully. Points awarded."})

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return the JSON schema definitions for the tools."""
        return [
            {
                "name": "award_loyalty_points",
                "description": "Award loyalty points to a customer for a specific amount spent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "amount": {"type": "number", "description": "Amount spent in Naira"},
                        "reason": {"type": "string", "description": "Reason for points (e.g., 'order')"}
                    },
                    "required": ["phone", "amount"]
                }
            },
            {
                "name": "check_loyalty_points",
                "description": "Check the current loyalty points balance of a customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"}
                    },
                    "required": ["phone"]
                }
            },
            {
                "name": "get_products",
                "description": "Get a list of available products, optionally filtered by category.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Optional category to filter by"}
                    }
                }
            },
            {
                "name": "handle_data_deletion",
                "description": "Process a request to delete a customer's data (NDPA compliance).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"}
                    },
                    "required": ["phone"]
                }
            },
            {
                "name": "log_complaint",
                "description": "Log a customer complaint or issue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "description": {"type": "string", "description": "Details of the complaint"}
                    },
                    "required": ["phone", "description"]
                }
            },
            {
                "name": "create_order",
                "description": "Create a new order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "items": {"type": "array", "items": {"type": "string"}, "description": "List of items ordered"},
                        "total_amount": {"type": "number", "description": "Total cost of the order"}
                    },
                    "required": ["phone", "items", "total_amount"]
                }
            }
        ]

agent_tools = AgentTools()
