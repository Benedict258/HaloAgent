# HaloAgent - Business Onboarding Guide

## 🧱 Core Principle

**Phone Number = Contact ID**

- No customer accounts
- No passwords
- No OTP
- Phone number is the single source of truth

## Step-by-Step Onboarding

### STEP 1: Create Demo Business

**API Endpoint:** `POST /onboarding/onboard-business`

**Example Request:**
```json
{
  "business_id": "sweetcrumbs_001",
  "business_name": "SweetCrumbs Cakes",
  "whatsapp_number": "+14155238886",
  "default_language": "en",
  "supported_languages": ["en", "yo"],
  "inventory": [
    {
      "name": "Chocolate Cake",
      "price": 5000,
      "available": true,
      "description": "Rich chocolate cake"
    },
    {
      "name": "Vanilla Cake",
      "price": 4500,
      "available": true,
      "description": "Classic vanilla"
    }
  ]
}
```

**What Happens:**
- Business record created
- WhatsApp number mapped to business
- Inventory loaded
- Ready to receive messages

### STEP 2: WhatsApp Webhook Configuration

**Incoming Message Flow:**
```
Customer sends WhatsApp → Twilio/Meta → Your Webhook
                                            ↓
                                    Resolve Business
                                            ↓
                                    Auto-create Contact
                                            ↓
                                        AI Agent
```

**Webhook receives:**
- `From`: Customer phone (+2348012345678)
- `To`: Business WhatsApp number (+14155238886)
- `Body`: Message text

**Backend resolves:**
1. `To` number → Business ID
2. `From` number → Contact (auto-created if new)
3. Routes to AI with business context

### STEP 3: Contact Auto-Creation

**First Message from Customer:**
```
Customer: "Hi"
```

**Backend automatically:**
```python
contact = {
    "phone_number": "+2348012345678",  # Contact ID
    "business_id": "sweetcrumbs_001",
    "opt_in": False,                    # Unconsented
    "status": "unconsented",
    "language": "unknown",
    "order_count": 0,
    "loyalty_points": 0
}
```

**AI Response:**
```
"Hi! I'm SweetCrumbs Cakes 🍰
Can I save your number to send order updates?
Reply YES to continue."
```

### STEP 4: Consent Flow

**Customer:** "yes"

**Backend updates:**
```python
contact.opt_in = True
contact.status = "active"
contact.consent_timestamp = now()
```

**AI Response:**
```
"Perfect! I've saved your number. 
What can I help you with today?"
```

### STEP 5: Order Flow

**Customer:** "I want a chocolate cake"

**AI checks inventory:**
- Chocolate Cake → ₦5,000 ✅

**AI Response:**
```
"Great choice! Chocolate cake for ₦5,000.
Pickup or delivery?"
```

**Customer:** "Delivery"

**Backend creates order:**
```python
order = {
    "order_id": "ORD-001",
    "contact_id": "+2348012345678",
    "business_id": "sweetcrumbs_001",
    "items": [{"name": "Chocolate Cake", "price": 5000}],
    "status": "CONFIRMED",
    "delivery_type": "delivery"
}
```

**AI Response:**
```
"Your order is confirmed! 🎉
We'll notify you when it's ready."
```

### STEP 6: Dashboard Interaction

**Business Owner Dashboard Shows:**
- New order: ORD-001
- Customer: +2348012345678
- Status buttons: [Preparing] [Ready] [Delivered]

**Owner clicks "Ready":**

**API Call:** `PATCH /orders/ORD-001/status`
```json
{"status": "READY"}
```

**AI automatically sends:**
```
"Your chocolate cake is ready for pickup! 🍰"
```

### STEP 7: Feedback Flow

**Order marked "Delivered"**

**AI sends:**
```
"How was your experience?
Reply 1 (bad) to 5 (excellent)"
```

**Customer:** "5"

**Backend:**
- Logs feedback
- Updates loyalty: order_count++
- Checks loyalty threshold

**AI Response:**
```
"Thank you! 🎉
You've completed 5 orders - here's 10% off your next one!"
```

## Testing Checklist

### As Customer:
- [ ] Send first message
- [ ] Receive consent request
- [ ] Reply "yes"
- [ ] Place order
- [ ] Receive confirmation
- [ ] Get status updates
- [ ] Give feedback

### As Business:
- [ ] View new contact in dashboard
- [ ] See order appear
- [ ] Update order status
- [ ] View contact history
- [ ] Check loyalty points

### Edge Cases:
- [ ] Ambiguous order: "I want cake" → AI asks which one
- [ ] Out of stock: AI suggests alternatives
- [ ] Angry customer: AI apologizes, flags owner
- [ ] Opt-out: "STOP" → Contact marked inactive

## API Endpoints

### Onboarding
- `POST /onboarding/onboard-business` - Create business
- `GET /onboarding/business/{business_id}` - Get business
- `GET /onboarding/business/{business_id}/inventory` - Get products

### Webhooks
- `POST /webhook/whatsapp` - Receive messages
- `GET /webhook/whatsapp` - Verify webhook

### Orders
- `GET /orders` - List orders
- `PATCH /orders/{id}/status` - Update status
- `GET /orders/{id}` - Get order details

### Contacts
- `GET /contacts` - List contacts
- `GET /contacts/{phone}` - Get contact details

## Database Schema

### businesses
```sql
- id (PK)
- business_id (unique)
- business_name
- whatsapp_number (unique, indexed)
- inventory (JSON)
- default_language
- supported_languages (JSON)
```

### contacts
```sql
- id (PK)
- phone_number (indexed) -- Contact ID
- business_id (FK)
- opt_in (boolean)
- status (unconsented/active/opted_out)
- language
- order_count
- loyalty_points
```

### orders
```sql
- id (PK)
- order_id (unique)
- contact_id (phone_number)
- business_id (FK)
- items (JSON)
- status (CONFIRMED/PREPARING/READY/DELIVERED)
- total
```

## Multi-Business Support

**How it works:**
1. Each business has unique WhatsApp number
2. Incoming message `To` field resolves business
3. Contacts are scoped to business
4. One customer can have multiple contacts (one per business)

**Example:**
```
Customer +2348012345678 orders from:
- SweetCrumbs (+14155238886) → Contact 1
- PizzaPlace (+14155238887) → Contact 2

Same phone, different businesses, separate contacts.
```

## Next Steps

1. ✅ Create demo business via API
2. ✅ Configure WhatsApp webhook
3. ✅ Test customer flow
4. ✅ Test dashboard updates
5. ✅ Deploy to production
