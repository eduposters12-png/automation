# ListifyAI

ListifyAI is a SaaS scaffold for Etsy sellers. The frontend is a Next.js 14 React app, and the backend is a Python FastAPI service that owns auth, Etsy OAuth, Stripe billing, encrypted credentials, and AI job orchestration boundaries.

## Stack

- Frontend: Next.js 14, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- Auth: FastAPI JWT in HTTP-only cookies
- Payments: Stripe Checkout and webhooks
- Etsy: OAuth 2.0 Authorization Code with PKCE

## Setup

1. Install frontend dependencies:

```bash
npm install
```

2. Create and activate a Python environment, then install backend dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

3. Copy env values:

```bash
copy .env.example .env
```

Generate `ENCRYPTION_KEY` with:

```bash
openssl rand -hex 32
```

For split production domains such as `app.example.com` and `api.example.com`, set `COOKIE_DOMAIN=.example.com` and `COOKIE_SECURE=true`.

4. Create a PostgreSQL database and set `DATABASE_URL`.

5. Run migrations:

```bash
alembic -c backend/alembic.ini upgrade head
```

6. Start the backend:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

7. Start the frontend:

```bash
npm run dev
```

Frontend runs at `http://localhost:3000`; backend runs at `http://localhost:8000`.

## Server Requirements

ffmpeg must be installed on the server for video generation:

Ubuntu/Debian:

```bash
apt-get install ffmpeg
```

macOS:

```bash
brew install ffmpeg
```

## Etsy OAuth

Create an Etsy developer app and set:

- `ETSY_CLIENT_ID` to the Etsy keystring.
- `ETSY_REDIRECT_URI` to `http://localhost:8000/etsy/callback` locally.
- The same redirect URI in the Etsy developer console.

The user clicks `Connect Etsy`, logs in on Etsy, grants access, and the backend stores encrypted access and refresh tokens. Sellers never paste Etsy API keys.

## Stripe

Set these env vars with your Stripe test values:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_BASIC_PRICE_ID`
- `STRIPE_PRO_PRICE_ID`
- `STRIPE_AGENCY_PRICE_ID`

For local webhooks:

```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```

## Shop Intelligence

Set `SERPER_API_KEY` for market trend search. The Etsy OAuth scope list must include `transactions_r` so the backend can read recent sales data for top-seller analysis. Shops connected before this scope was added need to reconnect Etsy.

## Image Generation

Set `OPENAI_API_KEY` for platform-owned GPT Image generation and `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` for signed image uploads. These keys stay in the FastAPI environment and are never exposed to Next.js.

## Backend Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /etsy/connect`
- `GET /etsy/callback`
- `GET /onboarding/status`
- `POST /onboarding/claude-key`
- `GET /dashboard/stats`
- `GET /settings`
- `PATCH /settings`
- `GET /shop/analysis`
- `POST /shop/analyze`
- `POST /stripe/checkout`
- `POST /stripe/webhook`
- `GET /listings`
- `POST /listings/bulk-queue`
- `POST /listings/generate-image`
- `POST /listings/{listing_id}/regenerate-image`
- `POST /listings/{listing_id}/set-high-res`
- `GET /listings/{listing_id}/images`
- `PATCH /listings/{listing_id}/approve-image`
- `POST /listings/{listing_id}/generate-video`
- `POST /listings/{listing_id}/generate-copy`
- `PATCH /listings/{listing_id}/copy`
- `GET /listings/{listing_id}/package`
- `PATCH /listings/{listing_id}/bundle`
- `POST /listings/{listing_id}/upload`
- `GET /listings/{listing_id}/status`
- `GET /listings/{listing_id}/download`
- `DELETE /listings/{listing_id}`
- `GET /jobs`
- `POST /jobs/analyze-shop`
- `POST /jobs/generate-listing`
- `POST /jobs/upload-listing`

## Security Notes

- Etsy OAuth tokens and Claude API keys are encrypted with AES-256-CBC before storage.
- Raw API keys and OAuth tokens are never returned to the frontend.
- Dashboard APIs require a valid HTTP-only auth cookie.
- Stripe webhooks verify the `stripe-signature` header.
- Etsy access tokens refresh server-side before upload jobs.

## Current AI Pipeline Boundary

The job endpoints create durable queue records for shop analysis, listing generation, and uploads. Provider-specific Claude, GPT-4o, Gemini, and Etsy upload workers can be added behind `backend/app/workers/pipeline.py` without changing the frontend contract.
