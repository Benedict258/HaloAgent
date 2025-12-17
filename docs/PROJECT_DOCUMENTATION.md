# HaloAgent Core Documentation

## 1. Project Overview

- **Project Name:** HaloAgent, WhatsApp CRM AI AGENT
- **Summary:** HaloAgent combines a FastAPI backend, Meta AI-powered agent brain, and a React admin dashboard to automate CRM workflows (orders, payments, support) for Nigerian MSMEs via WhatsApp and Web FallBack.
- **Problem Statement:** Several Nigerian MSMEs rely on WhatsApp chats or in-person attention to receive inquiries but lack a single, reliable CRM channel that captures leads, guides orders, confirms payments, and notifies owners without 24/7 human effort. Key CRM steps—catalog sharing, structured order capture, payment confirmation, and delivery updates—are often manual or scattered, causing lost revenue, missed follow-ups, and mixed customer experiences. Founders have no consolidated visibility; orders, receipts, and intents live separately so important tasks slip through the cracks.
- **Motivation:** When chats time out or payment proofs are mismatched, vendors lose sales and customers. Customers expect instant, personalized replies while founders need assurance every chat, payment, and follow-up is tracked. Automating end-to-end CRM flows reduces manual overhead, protects MSME margins, and lets lean teams scale service without night-shift staffing.
- **Proposed Solution:** HaloAgent is a Llama 3–powered WhatsApp CRM AI agent (with web-chat fallback) plus dashboard. Operating in-channel via Twilio/Meta, it captures intents, presents inventory, takes orders, generates unique payment references, tracks receipts/order statuses, and preserves brand voice. The FastAPI backend orchestrates routing, queries Supabase for context, and leverages Meta AI Studio for intent extraction + tool-calling. A DINOV3-styled vision layer handles receipts/product photos, AssemblyAI transcribes voice notes, and owners manage chats/payment reviews via the React dashboard.
- **Target Stakeholders:** Small/medium business owners, sales/ops teams, support agents, and their customers on WhatsApp/voice.
- **Goals:**
  - Automate chat-based order capture, payment instructions, and status updates.
  - Provide owners with real-time dashboards, payment review queues, and DINOV3 insights.
  - Maintain NDPA-compliant contact records and escalation logs.
- **Non-goals:** Replacing full ERP/back-office systems, handling fulfillment logistics or payments settlement.

### Materials & Technologies

- **Meta AI / Llama 3:** conversational understanding, tool-calling, multilingual replies, system orchestration.
- **Meta/Twilio WhatsApp + Meta Cloud:** customer messaging transport.
- **DINOV3 vision stub:** receipt & product image analysis.
- **AssemblyAI + Deepgram:** voice-note transcription and TTS responses.
- **FastAPI + Supabase/Postgres (with pgvector):** backend orchestration, CRM datastore, realtime feeds.
- **React + Vite + Tailwind (shadcn):** admin dashboard and public showcase.
- **Supporting libs:** httpx, asyncio, Alembic migrations, Airtable ingest scripts.

## 2. Requirements

- **Functional:**
  1. Receive WhatsApp/voice messages via Twilio + Meta webhooks.
  2. Extract intents, menu requests, orders, and payment confirmations through Meta AI agent loops.
  3. Persist contacts, orders, receipts, escalations in Supabase/Postgres.
  4. Render public business showcase + admin dashboard (React).
  5. Provide payment-review queue with DINOV3 receipt insights.
  6. Support owner-triggered status changes and automated customer notifications.
- **Non-functional:**
  - Target <1s response latency for AI replies after LLM call.
  - 99% uptime for webhook endpoints (Render/Fly.io deployment).
  - Encrypt secrets at rest; HTTPS for all external calls; NDPA compliance.
  - Scale to thousands of concurrent chats (async FastAPI, Supabase connection pooling).
- **Constraints:**
  - Budget: hackathon-tier (Render free tier + Supabase). No heavy GPU inference on-prem.
  - Timeline: 4-week sprint.
  - Platforms: WhatsApp Business API, web dashboard, Postgres/Supabase; compliance with Meta/Twilio policies.

## 3. Architecture & Design

- **System Overview:**
  - WhatsApp/Twilio webhook → FastAPI `app/api/webhooks.py` → HaloAgent core (LLM loop) → Supabase.
  - Dashboard (React/Vite) consumes FastAPI `/api/*` endpoints for orders, contacts, vision analyses.
- **Components:**
  1. **Agent Core:** `backend/app/services/agent/core.py` (conversation state, tool calls, Meta AI prompts).
  2. **Supabase Tools:** `app/services/agent/supabase_tools.py` (contacts/orders CRUD).
  3. **Vision Service:** `app/services/vision.py` (DINOV3 stub for receipts/images).
  4. **REST APIs:** `app/api/*.py` for orders, contacts, businesses, auth.
  5. **Frontend:** React dashboards + public showcase.
- **Data Flow:**
  1. Incoming message stored in Supabase `message_logs`.
  2. Agent fetches business context, inventory, outstanding orders.
  3. Agent decides: respond naturally or call tools (create order, send products, log escalation).
  4. Order/payment updates push back to Supabase; frontend polls `/api/orders`, `/api/orders/payment-reviews`.
  5. Vision analysis triggered when receipts uploaded; results stored in `vision_analysis_results`.
- **Tech Stack:** FastAPI, Python 3.11, Supabase/Postgres, React + Vite + Tailwind, Meta AI (Llama-based), Twilio, AssemblyAI, Deepgram.
- **Integrations:** Meta/Twilio WhatsApp, Supabase, AssemblyAI (voice transcription), Deepgram (TTS), DINOV3 (vision stub), Twilio media download.

## 4. Data & Models

- **Database:** Supabase/Postgres tables (simplified).
  - `contacts(id, business_id, phone_number, name, loyalty_points, order_count, opt_in, language)`
  - `orders(id, contact_id, business_id, order_number, items JSONB, total_amount, status, fulfillment_type, delivery_address, payment_reference, payment_instructions_sent, payment_receipt_url, timestamps...)`
  - `vision_analysis_results(id, order_id, analysis_type, media_url, analysis JSONB)`
  - `escalations(id, business_id, contact_id, issue_type, description, status)`
  - `message_logs(id, contact_id, direction, content, created_at)`
- **Relationships:** contacts:orders = 1:N; orders:vision_analysis_results = 1:N.
- **Constraints:** Unique `(phone_number,business_id)` for contacts; `orders.contact_id` FK; NDPA fields for consent.
- **Migrations:** Alembic scripts in `backend/alembic/versions`. Run `alembic upgrade head` before deploy.

## 5. APIs & Interfaces

- **REST Endpoints (samples):**
  - `GET /api/public/businesses?limit=12` – showcase listings.
  - `GET /api/orders`, `GET /api/orders/payment-reviews`, `POST /api/orders/{id}/update-status`.
  - `POST /api/orders/{id}/approve-payment`, `POST /api/orders/{id}/upload-receipt`.
  - `GET /api/contacts`, `GET /api/contacts/orders`, `POST /api/contacts/identify`.
- **Requests/Responses:** JSON; orders endpoints return arrays of normalized order dicts (items parsed from JSON strings).
- **Auth:** `require_business_user` dependency uses Supabase auth/session tokens.
- **Errors:** Standard FastAPI `HTTPException` with `detail`. Webhooks return 200 even on downstream failure (logged to Sentry).
- **Webhooks:** `/webhooks/whatsapp` (Twilio), `/webhooks/meta` (future). Voice uploads processed via `voice.py`.

## 6. Business Logic & Workflows

- **Order Creation Flow:** greeting → agent collects product/fulfillment/address → tool `db_create_order` → order saved; payment instructions sent with order ID + reference.
- **Payment Confirmation:** customer says “I paid” → agent finds pending orders, moves to `awaiting_confirmation`, notifies owner dashboard.
- **Receipt Review:** owner uploads receipt → vision analysis stored → `/api/orders/payment-reviews` surfaces results.
- **Status Updates:** owner sets `preparing`, `ready_for_pickup`, `completed`; FastAPI notifies customer via Twilio.
- **Edge Cases:** missing contact -> auto-upsert; multiple pending orders -> agent lists choices; missing payment reference -> instructs manual confirmation.
- **Idempotency:** tool throttling avoids repeated menu sends; Supabase updates scoped by contact/order IDs.

## 7. Setup & Environment

- **Env Vars:** `backend/.env` (Supabase URL/keys, Meta/Twilio creds, AssemblyAI, Deepgram). `frontend/.env` for Vite env (API base URL).
- **Configs:** `backend/app/core/config.py`; `frontend/vite.config.ts`.
- **Secrets:** store in .env (never commit). Deploy via Render/Fly secrets manager.
- **Environments:**
  - Local: `uvicorn app.main:app --reload`, `npm run dev`.
  - Staging: Supabase project + Render service.
  - Production: Render or Fly with HTTPS + Twilio verified webhook URLs.

## 8. Deployment & Operations

- **Backend Deploy:** build Docker (Render) or `fly deploy`; run Alembic migrations.
- **Frontend Deploy:** Vercel/Netlify `npm run build`.
- **CI/CD:** GitHub Actions (lint/test/build) – configure `python -m pytest` + `npm test`.
- **Monitoring:** Structured logging (UVicorn, Twilio webhooks). Future: Sentry/Datadog.
- **Rollback:** Redeploy previous Docker image / Vercel build; keep migrations reversible.
- **Scaling:** Auto-scale FastAPI replicas; Supabase connection pooling; Twilio rate limits handled via retry/backoff.

## 9. Testing

- **Strategy:**
  - Unit: agent state machine, supabase tools (mocked), vision utilities.
  - Integration: FastAPI endpoints via `pytest` + `httpx.AsyncClient`.
  - E2E: Cypress for frontend, Twilio sandbox for webhook tests.
- **Commands:** `cd backend && pytest`; `cd frontend && npm test`.
- **Fixtures:** Supabase test schema or SQLite fallback; mocked Twilio/Meta responses.
- **Coverage Goal:** ≥80% for agent services + API routes.

## 10. Security

- **Auth:** Supabase JWT for dashboard; webhook secrets validated per provider.
- **Authorization:** `require_business_user` ensures resources scoped to `business_id`.
- **Data Protection:** HTTPS, hashed secrets, NDPA-compliant consent flags.
- **Rate Limiting:** Twilio inbound limited via provider; agent throttles tool reuse.
- **Known Risks:** Stubbed DINOV3 – manual review required; Twilio media download uses basic auth (rotate tokens regularly).

## 11. Maintenance & Ownership

- **Limitations:** Vision module stubbed; no automated invoice generation; single-region deployment.
- **Technical Debt:** Expand tests for payment flows; caching for inventory; add proper webhook signature validation.
- **Owners:** Benedict (product/ops), HaloAgent dev team.

## 12. Implementation Results

- Full catalog + inventory pipeline delivers media-rich product cards (image, price, description) over WhatsApp, and `/api/public/businesses` powers the React showcase so businesses appear instantly online.
- End-to-end order lifecycle: agent captures product/fulfillment/address → confirms → saves → responds with structured summary; owners can trigger status changes that auto-notify customers.
- Idempotent message handling prevents duplicate orders; contact-centric CRM tracks opt-ins, languages, loyalty metrics, and visit-based rewards with automated issuance/expiry.
- Conversations/reports support English, Yoruba, Hausa, and Igbo; Supabase Realtime streams updates to the dashboard with full action/message logs.
- Low-confidence interactions escalate to owners with context; compliance enforced via consent tracking, encrypted PII, retention rules, and delete-on-request flows.
- Receipt ingestion (DINOV3 stub) extracts payment signals and surfaces payment-review rows, supporting the `awaiting_confirmation` state when customers indicate payment.
- Voice notes transcribe end-to-end into natural text, feeding the same agent workflows.
- Stabilized APIs resolved earlier contact/order lookup errors, centralizing owner reviews and eliminating manual spreadsheet tracking.

## 13. Conclusion & Key Learnings

- **Impact:** HaloAgent delivers instant, branded conversational service while giving founders centralized operational visibility. Early pilots reported fewer mismatched payments and faster conversions because the agent enforces unique references and preserves per-contact context.
- **Feedback:** SMEs appreciated having receipts, orders, and chats in one place plus the ability to override or escalate anytime.
- **Learnings:**
  - Tool-callable LLMs must be guarded by deterministic flows (contact lookups, payment hints) to avoid hallucinations.
  - CRM automation must cover real-world edge cases (missing contacts, ambiguous receipts) or trust erodes quickly.
  - Observability (logs, dashboards, audit trails) is essential when agents act autonomously; every action must be explainable.

## 14. Future Improvement Plans

1. Integrate payment gateways (Paystack/Flutterwave) for instant verification and fewer manual reviews.
2. Launch proactive retention features—abandoned-order nudges, loyalty campaigns—and templatized onboarding so newcomers self-serve setup.
3. Build deeper analytics (conversion funnels, SLA alerts) and a mobile owner app for approvals on the go.
4. Expand to more channels (Instagram DMs, Facebook Messenger, USSD) under the same conversation memory, broadening reach.
5. Replace the DINOV3 stub with a production-grade vision pipeline plus anomaly detection for fraud prevention.
