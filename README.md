# HaloAgent WhatsApp CRM AI AGENT

HaloAgent is an AI-powered CRM agent plus dashboard that automates order capture, payment confirmation, and customer follow-up for Nigerian MSMEs across WhatsApp, voice, and web channels.

📚 **Detailed docs:** [PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md)

## Key Features

- Conversational ordering with Meta AI (inventory, quotes, fulfillment details).
- Automated payment instructions + receipt review queue with DINOV3 insights.
- Owner dashboard for contacts, orders, and AI-generated escalations.
- Voice-note transcription via AssemblyAI and TTS playback via Deepgram.
- Public business showcase API + React landing page.

## Problem & Motivation

Nigerian MSMEs rely on WhatsApp chats or physical store visits to receive inquiries but rarely have a single CRM channel that captures leads, guides orders, confirms payments, and notifies owners without round-the-clock staff. Catalog sharing, structured order capture, payment confirmation, and delivery updates end up manual or scattered, so teams miss follow-ups and lose revenue. When chats time out or payment proofs are mismatched, both vendors and customers churn. Automating the entire CRM flow keeps every conversation, payment, and follow-up tracked, letting lean teams scale support without hiring overnight agents.

## Solution Overview

HaloAgent is a Llama 3–powered WhatsApp CRM AI agent (with web-chat fallback) plus dashboard. Running inside WhatsApp/Twilio and the web, it captures intents, presents inventory, takes orders, generates unique payment references, tracks receipts/order statuses, and keeps each brand’s tone. The FastAPI backend orchestrates message routing and tool-calling, Supabase stores CRM context, DINOV3-style vision inspects receipts/product photos, AssemblyAI handles voice notes, and owners monitor everything via the React dashboard with payment reviews and weekly insight cards.

## Implementation Outcomes

- Catalog pipeline shares media-rich product cards (name, image, price) directly in chat and powers the `/api/public/businesses` showcase so new brands appear instantly.
- End-to-end order lifecycle (capture → confirm → save → respond) with idempotent handling prevents duplicates and enforces unique payment references.
- Contact-first CRM tracks opt-ins, language/loyalty data, multilingual conversations (English, Yoruba, Hausa, Igbo), and visit-based rewards.
- DINOV3 receipt ingestion plus `awaiting_confirmation` workflow gives owners a payment-review queue with escalation context.
- Voice notes transcribe seamlessly into the same agent workflow, and Supabase Realtime keeps the dashboard live.
- Compliance features (consent tracking, encrypted PII, delete-on-request) and detailed logs mean every autonomous action is auditable.

## Tech Stack

- **Languages:** Python 3.11, TypeScript/JavaScript.
- **Frameworks:** FastAPI, React + Vite + Tailwind.
- **Database/Infra:** Supabase/Postgres, Alembic migrations.
- **AI/External Services:** Meta AI (Llama-based), Twilio WhatsApp, DINOV3 (vision stub), AssemblyAI, Deepgram, Airtable (inventory import).

## Installation / Setup

### Prerequisites

- Python 3.11+, Node.js 20+, Supabase project, Twilio sandbox, Meta WhatsApp credentials.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # add Supabase, Twilio, Meta, AssemblyAI keys
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Usage

- Backend (Render): https://haloagent.onrender.com (API docs at `/docs`).
- React admin dashboard (local dev): `http://localhost:5173` (Vite) or `http://localhost:3000` (CRA fallback).
- Frontend production URL: _coming soon_.
- WhatsApp webhooks: expose backend via `ngrok http 8000` and register the public URL with Twilio/Meta.

## Configuration

- Backend env vars (`backend/.env.example`): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `META_WHATSAPP_TOKEN`, `ASSEMBLYAI_API_KEY`, `DEEPGRAM_API_KEY`, etc.
- Frontend env vars (`frontend/.env`): `VITE_API_BASE_URL`, `VITE_SUPABASE_URL` (if directly accessing), analytics keys.
- Secrets should be stored in Render/Fly/Vercel secret managers for staging/production.

## Project Structure

```
HaloAgent/
├─ backend/        # FastAPI app, agent services, webhooks, Alembic
├─ frontend/       # React dashboard + public showcase
├─ docs/           # Architecture, API specs, hackathon briefs
├─ shared/         # Cross-cutting helpers (if any)
└─ README.md
```

## Running Tests

- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test`
- Configure Supabase test env or mock clients before running integration suites.

## Deployment

- Backend: containerize with Docker/Render/Fly; run `alembic upgrade head` during deploy.
- Frontend: `npm run build` → deploy to Vercel/Netlify.
- Register webhook URLs with Twilio + Meta and set environment secrets on the hosting platform.

## Future Plans

- Integrate Paystack/Flutterwave for instant payment verification.
- Launch proactive retention features (abandoned-order nudges, loyalty campaigns) and self-serve onboarding kits.
- Build deeper analytics/SLA alerts plus a mobile owner app for approvals on the go.
- Expand channels (Instagram DMs, Facebook Messenger, USSD) under the same conversation memory once WhatsApp traffic matures.

## Contributing

1. Fork + branch from `main`.
2. Follow Conventional Commits and Black/ESLint formatting.
3. Add tests for any new service or endpoint.
4. Submit PR with screenshots/logs of relevant flows.

## License

MIT
