# Product Images Feature - HaloAgent

## Overview
AI Agent can now send product images with descriptions and prices via WhatsApp!

## How It Works

### **Customer Asks for Menu:**
```
Customer: "What do you have?"

AI Agent:
1. Calls send_all_products(phone, business_id)
2. Sends 3 separate WhatsApp messages:

Message 1:
[IMAGE: Chocolate Cake]
*Chocolate Cake*

Rich chocolate cake

Price: ₦5,000

Message 2:
[IMAGE: Vanilla Cake]
*Vanilla Cake*

Classic vanilla

Price: ₦4,500

Message 3:
[IMAGE: Red Velvet Cake]
*Red Velvet Cake*

Smooth red velvet

Price: ₦5,500
```

### **Customer Asks for Specific Product:**
```
Customer: "Show me the chocolate cake"

AI Agent:
1. Calls send_product_with_image(phone, "Chocolate Cake", business_id)
2. Sends 1 WhatsApp message:

[IMAGE: Chocolate Cake]
*Chocolate Cake*

Rich chocolate cake

Price: ₦5,000
```

## Product Schema

### **In Supabase (businesses.inventory):**
```json
{
  "name": "Chocolate Cake",
  "price": 5000,
  "available": true,
  "description": "Rich chocolate cake",
  "image_url": "https://your-cdn.com/chocolate-cake.jpg"
}
```

### **Required Fields:**
- `name` - Product name
- `price` - Price in Naira
- `description` - Product description
- `image_url` - Public URL to product image

## Adding Products from Dashboard

### **API Endpoint:**
```
POST /business/{business_id}/products
```

**Request:**
```json
{
  "name": "Strawberry Cake",
  "price": 6000,
  "description": "Fresh strawberry delight",
  "image_url": "https://cdn.example.com/strawberry.jpg",
  "available": true
}
```

### **Update Inventory in Supabase:**
```sql
UPDATE businesses 
SET inventory = inventory || '[
  {
    "name": "Strawberry Cake",
    "price": 6000,
    "description": "Fresh strawberry delight",
    "image_url": "https://cdn.example.com/strawberry.jpg",
    "available": true
  }
]'::jsonb
WHERE business_id = 'sweetcrumbs_001';
```

## Image Hosting Options

### **1. Supabase Storage (Recommended)**
```javascript
// Upload image to Supabase Storage
const { data, error } = await supabase.storage
  .from('product-images')
  .upload('chocolate-cake.jpg', file)

// Get public URL
const { publicURL } = supabase.storage
  .from('product-images')
  .getPublicUrl('chocolate-cake.jpg')
```

### **2. Cloudinary**
- Free tier: 25GB storage
- Automatic image optimization
- CDN delivery

### **3. AWS S3**
- Scalable storage
- CloudFront CDN

### **4. Direct URLs**
- Any publicly accessible image URL works

## WhatsApp Image Requirements

- **Format:** JPG, PNG
- **Max Size:** 5MB
- **Recommended:** 800x800px
- **Must be:** Publicly accessible URL (no authentication)

## AI Agent Behavior

### **When Customer Says:**
- "What do you have?" → Sends ALL products
- "Show me the menu" → Sends ALL products
- "What cakes do you have?" → Sends ALL products
- "Show me chocolate cake" → Sends ONLY chocolate cake
- "I want vanilla" → Sends vanilla cake image + confirms order

### **Smart Detection:**
AI automatically:
1. Detects if customer wants menu or specific product
2. Fetches from Supabase inventory
3. Sends images via WhatsApp
4. Continues conversation naturally

## Example Conversation Flow

```
Customer: "Hi"
Agent: "Hey! Welcome to SweetCrumbs Cakes 🍰 What can I get you today?"

Customer: "What do you have?"
Agent: [Sends 3 product images with details]
Agent: "Which one would you like to order?"

Customer: "The chocolate one"
Agent: "Great choice! Chocolate Cake for ₦5,000. Pickup or delivery?"

Customer: "Delivery"
Agent: "Perfect! Where should we deliver it?"

Customer: "123 Main St, Ikeja"
Agent: [Creates order in database]
Agent: "Order confirmed! 🎉 We'll deliver to 123 Main St, Ikeja. You earned 50 loyalty points!"
```

## Testing

### **1. Add Product with Image:**
```sql
UPDATE businesses 
SET inventory = '[
  {
    "name": "Test Cake",
    "price": 1000,
    "description": "Test product",
    "image_url": "https://picsum.photos/800",
    "available": true
  }
]'::jsonb
WHERE business_id = 'sweetcrumbs_001';
```

### **2. Send WhatsApp Message:**
```
"Show me the menu"
```

### **3. Verify:**
- ✅ Receives image message
- ✅ Image loads correctly
- ✅ Caption shows name, description, price
- ✅ Can order after seeing image

## Dashboard Integration

### **Product Management UI:**
```typescript
// Add product with image upload
const addProduct = async (product: Product, imageFile: File) => {
  // 1. Upload image to Supabase Storage
  const { data: uploadData } = await supabase.storage
    .from('product-images')
    .upload(`${businessId}/${imageFile.name}`, imageFile)
  
  // 2. Get public URL
  const { publicURL } = supabase.storage
    .from('product-images')
    .getPublicUrl(uploadData.path)
  
  // 3. Add product to inventory
  const productData = {
    ...product,
    image_url: publicURL
  }
  
  // 4. Update business inventory
  await supabase
    .from('businesses')
    .update({ 
      inventory: [...currentInventory, productData] 
    })
    .eq('business_id', businessId)
}
```

## Benefits

✅ **Visual Shopping** - Customers see what they're ordering
✅ **Higher Conversion** - Images increase order rates
✅ **Professional** - Looks like a real e-commerce experience
✅ **Automated** - AI handles everything
✅ **Scalable** - Works for any number of products

## Next Steps

1. ✅ Add image URLs to existing products in Supabase
2. ✅ Test with "Show me the menu"
3. ✅ Build dashboard product upload UI
4. ✅ Set up Supabase Storage bucket
5. ✅ Deploy and test with real customers
