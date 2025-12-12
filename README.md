# HaloAgent - WhatsApp-first CRM for Nigerian MSMEs

Meta-AI-powered conversational CRM agent for small businesses. Automates orders, loyalty, feedback, and insights via WhatsApp, Instagram, Facebook Messenger.

## Project Structure

```
HaloAgent/
├── backend/          # FastAPI server, webhooks, LLM integration
├── frontend/         # React admin dashboard
├── shared/           # Shared types, constants, utilities
├── docs/             # Documentation, API specs, demo scripts
└── README.md
```

## Tech Stack

- **Backend**: FastAPI (Python 3.11+), Postgres, Celery
- **LLM**: Llama 3 via Meta AI Studio
- **Channels**: WhatsApp Business Cloud API, SMS, USSD
- **Frontend**: React, Airtable integration
- **Hosting**: Vercel/Heroku

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure your API keys
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Environment Variables

See `backend/.env.example` for required API keys:
- WhatsApp Business Cloud API
- Meta AI Studio (Llama 3)
- SMS Provider (Twilio)
- Database credentials

## Development

- **API Docs**: http://localhost:8000/docs (FastAPI auto-generated)
- **Admin UI**: http://localhost:3000

## MVP Features

✅ WhatsApp order intake & tracking  
✅ Multilingual support (EN, YO, HA, IG)  
✅ Loyalty & rewards automation  
✅ Feedback remediation  
✅ Weekly trend insights  
✅ NDPA-compliant consent & deletion  

## License

MIT
