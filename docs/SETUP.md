# HaloAgent - Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis (for Celery workers)
- Git

## Step 1: Clone & Setup

```bash
cd HaloAgent
```

## Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys
```

## Step 3: Database Setup

```bash
# Create database
createdb haloagent

# Run migrations (after Phase 1)
alembic upgrade head
```

## Step 4: Run Backend

```bash
# Development server
python -m uvicorn app.main:app --reload --port 8000

# API docs available at: http://localhost:8000/docs
```

## Step 5: Frontend Setup (Phase 5)

```bash
cd frontend
npm install
npm start
```

## Step 6: Workers (Phase 8+)

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

## API Keys Required

### WhatsApp Business Cloud API
1. Go to https://developers.facebook.com
2. Create app → Add WhatsApp product
3. Get Phone Number ID, Business Account ID, and Access Token
4. Setup webhook with verify token

### Meta AI Studio (Llama 3)
1. Visit https://ai.meta.com/llama/
2. Request API access
3. Get API key

### Twilio (SMS)
1. Sign up at https://www.twilio.com
2. Get Account SID, Auth Token, and Phone Number

### Airtable
1. Create base at https://airtable.com
2. Get API key from account settings
3. Copy Base ID from URL

## Troubleshooting

**Database connection error:**
- Check PostgreSQL is running
- Verify DATABASE_URL in .env

**Import errors:**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again

**Port already in use:**
- Change port: `uvicorn app.main:app --port 8001`

## Next Steps

After setup, proceed to Phase 1: Data Models
