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

## Deployment risks to handle next

- The frontend and backend need separate deployments or a platform that supports both Node and Python services.
- The backend host must include the processed CSV files and allow outbound HTTPS to Featherless.
- `NEXT_PUBLIC_API_BASE_URL` is embedded when the frontend is built, so it must be correct for the deployed environment.
- `FRONTEND_ORIGIN` must match the deployed frontend for browser CORS requests.
- The configured Featherless model must be available on the account's plan and not blocked by a provider gate.
- Before a public launch, `/explain` should receive basic rate limiting to control abuse and inference cost.
