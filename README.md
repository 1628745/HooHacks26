# LLM Pipeline Optimizer

Hackathon demo tool for analyzing and optimizing single-file LangChain-style Python pipelines.

## Project Layout
- `frontend`: React + TypeScript app (Monaco, TanStack Query)
- `backend`: FastAPI service (AST parser, IR extraction, issue analyzer, optimizer)
- `samples`: demo Python files
- `docs`: architecture and API notes

## Run Frontend
```bash
cd frontend
npm install
npm run dev
```

## Run Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### OpenRouter (LLM)

The backend calls [OpenRouter](https://openrouter.ai/)’s OpenAI-compatible **chat completions** API.

1. Create an API key at [openrouter.ai/keys](https://openrouter.ai/keys).
2. Copy `backend/.env.example` to `backend/.env` and set:
   - **`OPENROUTER_API_KEY`** — your key
   - Optionally **`OPENROUTER_MODEL`** (default: **`stepfun/step-3.5-flash`**)
   - Optionally **`OPENROUTER_BASE_URL`** (default: `https://openrouter.ai/api/v1`)
   - Optionally **`OPENROUTER_TIMEOUT_SECONDS`** (default **600**)
   - Optionally **`OPENROUTER_HTTP_REFERER`** and **`OPENROUTER_APP_TITLE`** (recommended by OpenRouter for app identification)

3. Restart the backend. **Preview Optimization** and **Chat** use the same model.

If something fails, check the browser **Network** tab → response JSON **`detail`**, and backend logs prefixed with **`[openrouter]`** or **`[pipeline-optimize]`**.

## Test Backend
```bash
cd backend
pytest
```
