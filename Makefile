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

# End-to-end smoke test (script is added in a later task)
smoke:
	@if [ -f scripts/smoke.sh ]; then bash scripts/smoke.sh; else echo "scripts/smoke.sh not created yet (later task)"; fi
