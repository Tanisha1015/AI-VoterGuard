.PHONY: backend agent test-backend smoke

# Run the core API on :8000
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

# Run the agent service on :8001
agent:
	cd agent-service && npm run dev

# Run backend unit tests
test-backend:
	cd backend && python -m pytest -q

# End-to-end smoke test against running services (core, agent, trust, chain). Add --seed via SMOKE_ARGS=--seed
smoke:
	python3 scripts/e2e_smoke.py $(SMOKE_ARGS)
