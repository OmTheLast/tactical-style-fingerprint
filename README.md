# Tactical Style Fingerprint

An event-data football analytics MVP that represents Premier League 2015/16 teams using five transparent tactical dimensions, finds their nearest tactical neighbours, and optionally generates a data-grounded explanation through Featherless AI.

## Frozen MVP model

The application consumes validated offline outputs. It does **not** recalculate 380 event files when a user opens the page.

1. Attacking Territory — Attacking Territory Share
2. Pass Verticality — Pass Verticality
3. Pressing Intensity — High-Zone Pressures per 100 Opposition Passes
4. Attacking Width — Mean Final-Third Destination Width
5. Counterattacking Tendency — From-Counter Possession Rate

The similarity model uses population z-score standardization across the 20 teams, equal feature weights, and Euclidean distance. Smaller distance means closer in this five-dimensional representation. It is not a probability or percentage of tactical identity.

The UI uses a separate visualization-only scale:

```text
100 × (team raw value − league minimum) / (league maximum − league minimum)
```

On this scale, 0 and 100 mean the lowest and highest observed values in this league-season. They do not mean absent, perfect, or better. This display transformation never enters the similarity calculation.

## Architecture

```text
StatsBomb event data
        ↓ offline analysis
validated processed CSVs
        ↓ loaded once and cached
FastAPI backend (:8000)
        ↓ JSON over HTTP
Next.js frontend (:3000)
        ↓ POST /explain only
Featherless chat-completions API
```

- `analysis/` — offline metric and similarity calculations
- `data/processed/` — validated runtime-ready outputs
- `backend/app/` — FastAPI data service and Featherless integration
- `backend/tests/` — API and graceful-failure tests
- `frontend/` — Next.js App Router interface

The Featherless API key is read only by Python. The browser receives the generated explanation, never the key.

## Local setup

Requirements: Python 3.10+ and Node.js 20.9+.

### 1. Environment

```bash
cp .env.example .env
```

Fill these values if you want live AI explanations:

```dotenv
FEATHERLESS_API_KEY=your_key
FEATHERLESS_MODEL=your_available_model_id
```

The backend defaults to Featherless's official `https://api.featherless.ai/v1/chat/completions` endpoint. For a deployed frontend, also configure `FRONTEND_ORIGIN`, `APP_PUBLIC_URL`, and build the frontend with `NEXT_PUBLIC_API_BASE_URL` pointing to the deployed backend.

Never commit `.env` or `frontend/.env.local`.

### 2. Backend terminal

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Useful URLs:

- API health: `http://localhost:8000/health`
- Interactive API documentation: `http://localhost:8000/docs`

### 3. Frontend terminal

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend defaults to `http://localhost:8000`, so no frontend environment file is required for local development.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Verify that the API and 20-team dataset loaded |
| `GET` | `/teams` | List teams, season, model, and disclosed limitations |
| `GET` | `/teams/{team}/fingerprint` | Return raw, z-score, and display values for five features |
| `GET` | `/teams/{team}/neighbours` | Return the five nearest teams and feature gaps |
| `GET` | `/compare?team_a=...&team_b=...` | Return both fingerprints, distance, and signed differences |
| `POST` | `/explain` | Ask Featherless to interpret a structured comparison |

The explanation request includes both teams' raw and standardized values, signed differences, Euclidean distance, metric definitions, and model limitations. Its system prompt prohibits invented club facts, quality claims, and probability language.

If Featherless is missing, unavailable, times out, or rejects the configured model, `/explain` returns a useful error. The other endpoints and the frontend comparison remain operational.

`POST /explain` is limited by default to five attempts per client in a rolling ten-minute window. This small in-memory control is suitable for a single-instance hackathon deployment: it prevents accidental request spam, but resets when the backend restarts and is not a substitute for distributed production rate limiting.

## Production deployment

The public hackathon MVP is deployed at:

- Frontend: <https://tactical-style-fingerprint.vercel.app>
- Backend API: <https://tactical-style-fingerprint-api.onrender.com>
- API health: <https://tactical-style-fingerprint-api.onrender.com/health>

The included `render.yaml` defines the FastAPI service for Render. Connect the GitHub repository, create the Blueprint, and set the secret/configuration values in Render rather than in Git:

```dotenv
FEATHERLESS_API_KEY=<secret>
FEATHERLESS_MODEL=<available Featherless model ID>
FRONTEND_ORIGIN=https://<deployed-frontend-origin>
APP_PUBLIC_URL=https://<deployed-frontend-origin>
```

Deploy the backend first and verify its `/health` endpoint. Then deploy `frontend/` on Vercel with this build-time variable:

```dotenv
NEXT_PUBLIC_API_BASE_URL=https://<deployed-backend-origin>
```

When the frontend URL is known, update `FRONTEND_ORIGIN` and `APP_PUBLIC_URL` on the backend to that exact HTTPS origin. Changing `NEXT_PUBLIC_API_BASE_URL` requires rebuilding the frontend because Next.js embeds public environment variables in the browser bundle at build time.

## Verification

```bash
.venv/bin/python -m pytest -q
cd frontend
npm run lint
npm run build
```

## Known modelling limitations

- Attacking Territory and Pass Verticality correlate at `-0.839`, potentially partly double-weighting a control/directness axis.
- Attacking Width has a narrow raw range, and the Width-ablation diagnostic materially changed several neighbour rankings.
- Five event-data-derived dimensions cannot describe the whole tactical behaviour of a football team.
- “Nearest” means least distant among the available teams; it does not guarantee a close match.

## Production limitations

- The backend host must include the processed CSV files and allow outbound HTTPS to Featherless.
- `NEXT_PUBLIC_API_BASE_URL` is embedded when the frontend is built, so it must be correct for the deployed environment.
- `FRONTEND_ORIGIN` must match the deployed frontend for browser CORS requests.
- The configured Featherless model must be available on the account's plan and not blocked by a provider gate.
- The in-memory explanation limiter resets on backend restart and does not coordinate across multiple backend instances.
- The backend currently uses Render's free service tier, so it may spin down while idle. The first request after an idle period can take substantially longer than a warm request.
