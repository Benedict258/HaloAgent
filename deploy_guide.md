# Deploy HaloAgent to Render

## Step 1: Deploy to Render

1. **Push to GitHub**:

   ```bash
   git init
   git add .
   git commit -m "Initial HaloAgent setup"
   git branch -M main
   git remote add origin https://github.com/yourusername/haloagent.git
   git push -u origin main
   ```

2. **Deploy on Render**:

   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Use these settings:
     - **Build Command**: `pip install -r backend/requirements.txt`
     - **Start Command**: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - **Environment**: Python 3.11

3. **Your webhook URL will be**: `https://your-app-name.onrender.com`

## Step 2: Configure WhatsApp Webhook

1. Go to **Facebook Developers Console**
2. Navigate to **WhatsApp → Configuration**
3. Set webhook URL: `https://your-app-name.onrender.com/webhook/whatsapp`
4. Set verify token: `haloagent_verify_2024`
5. Subscribe to: `messages`, `message_deliveries`, `message_reads`

## Step 3: Test

Send a WhatsApp message to your business number. HaloAgent should respond automatically!

## Step 4: Keep Supabase Schema In Sync

1. **Apply the latest SQL migrations**
   ```bash
   psql "$SUPABASE_DB_URL" -f backend/migrations/20251217_add_vision_analysis_results.sql
   psql "$SUPABASE_DB_URL" -f backend/migrations/20251217_add_pickup_and_settlement_fields.sql
   ```
   The scripts ensure `vision_analysis_results` exists (required for `/api/vision/analyses`) and add new pickup/payment columns on `businesses`.
2. **Refresh the Supabase schema cache** so PostgREST picks up new tables:
   ```bash
   curl -X POST \
     -H "apikey: $SUPABASE_SERVICE_KEY" \
     -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
     "$SUPABASE_URL/rest/v1/rpc/pg_reload_conf"
   ```
   You can also run this from the Supabase SQL editor: `select pg_reload_conf();`
3. **Re-deploy/Restart** the Render service after schema changes so the refreshed catalog is used everywhere.

## Webhook Endpoints

- **WhatsApp**: `/webhook/whatsapp`
- **SMS**: `/webhook/sms`
- **Health Check**: `/health`
- **API Docs**: `/docs`
