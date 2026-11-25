.PHONY: install catalog test test-e2e backend frontend

install:            ## install all deps
	cd backend && uv sync
	cd frontend && npm install && npx playwright install chromium

catalog:            ## re-export the shared component catalog + backend fixtures
	cd frontend && npm run export-catalog
	cd backend && uv run python scripts/export_fixtures.py

test:               ## unit + contract tests (no LLM needed)
	cd backend && uv run pytest -q
	cd frontend && npm run typecheck && npm test

test-e2e:           ## Playwright against real backend (fake LLM)
	cd frontend && npm run test:e2e

backend:            ## run the agent (LLM_PROVIDER=ollama|fake, default ollama)
	cd backend && uv run uvicorn travel_agent.server:app --reload --port 8000

frontend:           ## run the UI on http://localhost:5173
	cd frontend && npm run dev
