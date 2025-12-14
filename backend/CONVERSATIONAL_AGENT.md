# HaloAgent - Conversational AI Implementation

## Overview
HaloAgent is a **truly conversational AI**, not a rule-based bot. It understands natural language, infers intent, and responds like a helpful human assistant.

## Key Principles

### 1. Natural Consent Handling
**BAD (Robotic):**
```
"May we store your phone number and send order updates? Reply YES to confirm."
```

**GOOD (Conversational):**
```
"I'll save your number so I can send updates - sound good?"
```

**Consent Inference:**
- "sure" → consent ✅
- "ok" → consent ✅
- "sounds good" → consent ✅
- "go ahead" → consent ✅
- "yes" → consent ✅

### 2. Hidden Backend Processing
Users should **NEVER** see:
- ❌ "I will classify your intent..."
- ❌ "Processing tool_call..."
- ❌ JSON responses
- ❌ Technical language

All tool calls happen **silently** in the backend.

### 3. Natural Order Flow

**User:** "I want jollof rice"
**Agent:** "Nice choice! How many plates would you like, and should I deliver or is it for pickup?"

**User:** "2 plates, deliver to Ikeja"
**Agent:** "Got it! 2 plates of jollof rice coming to Ikeja. That's ₦3,000. I'll send you tracking updates!"

### 4. Context Awareness
The agent remembers:
- Previous messages in conversation
- Customer name (if known)
- Order history
- Loyalty points

### 5. Error Handling
**BAD:**
```
"Error: Tool execution failed. Please try again."
```

**GOOD:**
```
"I'm having a bit of trouble right now. Mind trying again in a sec?"
```

## Implementation Details

### Agent Architecture
```
User Message
    ↓
Orchestrator (orchestrator.py)
    ↓
Agent Core (agent/core.py)
    ↓
[Silently executes tools]
    ↓
Natural Response → User
```

### Tool Execution (Silent)
When user says "sure":
1. Agent detects consent (backend)
2. Calls `award_loyalty_points` tool (backend)
3. Saves contact to database (backend)
4. Returns: "Perfect! I've saved your number. I'll keep you posted on your orders. 😊"

User only sees the final friendly message.

### Consent Service
`consent.py` handles natural language consent:
- **Strong consent** (confidence 0.9): "sure", "ok", "yes"
- **Weak consent** (confidence 0.6): "maybe", "i guess"
- **Rejection** (confidence 0.95): "no", "don't", "stop"

### Response Sanitization
`orchestrator.py` filters out any leaked technical language:
- Removes: "intent_classifier", "tool_call", "parameters"
- Replaces with: "Got it! Let me help you with that."

## Testing

Run conversation test:
```bash
cd backend
python test_conversation.py
```

Expected output: Natural, friendly responses with no technical language.

## Configuration

### Agent Personality (prompts.py)
- Warm and friendly
- Concise (< 2 SMS lengths)
- Empathetic
- Uses natural language
- Builds rapport

### Tools Available
1. `award_loyalty_points` - Give points
2. `check_loyalty_points` - Check balance
3. `create_order` - Place order
4. `get_products` - Fetch inventory
5. `log_complaint` - Handle issues
6. `handle_data_deletion` - NDPA compliance

## Best Practices

### DO:
✅ Respond naturally and conversationally
✅ Infer intent from context
✅ Build rapport with customers
✅ Handle errors gracefully
✅ Keep messages concise

### DON'T:
❌ Show JSON or technical terms to users
❌ Ask for structured input ("Reply YES")
❌ Expose backend processing
❌ Use robotic language
❌ Break conversations into multiple messages

## Examples

### Good Conversation Flow
```
User: hi
Agent: Hey there! 👋 How can I help you today?

User: what do you have?
Agent: We've got jollof rice, fried rice, and chicken. What sounds good?

User: jollof rice
Agent: Great choice! How many plates?

User: 2
Agent: Perfect! Delivery or pickup?

User: delivery to Ikeja
Agent: Got it! 2 plates of jollof rice to Ikeja. That's ₦3,000. Confirm?

User: yes
Agent: Awesome! Your order is confirmed. I'll send you updates as we prepare it! 🎉
```

### Bad Conversation Flow (What to Avoid)
```
User: hi
Agent: I will classify your intent using intent_classifier tool...

User: jollof rice
Agent: {"action": "tool_call", "tool_name": "extract_order_details"...}

User: yes
Agent: Reply YES to confirm your consent.
```

## Monitoring

Check logs for:
- Tool execution (should be silent to user)
- Response sanitization (technical language filtered)
- Consent inference (confidence scores)
- Error handling (graceful fallbacks)

## Next Steps

1. Test with real WhatsApp messages
2. Monitor conversation quality
3. Tune agent personality based on feedback
4. Add more natural language patterns
5. Improve context awareness
