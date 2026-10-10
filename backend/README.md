# VoterGuard core API (:8000)

FastAPI service that compares a draft roll, a final roll and the removal list (ASDD), runs seven detectors
over the booths, scores them, stores the audit in SQLite, and serves it. It also answers citizen lookups.
All numbers, flags and scores come from deterministic code; the agent service may only phrase the
explanation text, and the core falls back to its own templates when it cannot. It never decides eligibility
and never declares wrongdoing. Synthetic data only.

Contract: [`contracts/CONTRACT.md`](../contracts/CONTRACT.md) section 6.3. Detectors and thresholds:
[`docs/METHODOLOGY.md`](../docs/METHODOLOGY.md).

## Run

```bash
pip install -r requirements.txt
AUTO_SEED=true python -m uvicorn app.main:app --port 8000   # from backend/
python -m pytest -q                                          # tests (each uses its own temporary DATA_DIR)
```

`AUTO_SEED=true` creates `aud_001` from the synthetic data on first start when no audit exists. You can also
create it later with `curl -X POST localhost:8000/api/audits -H 'content-type: application/json' -d '{"use_synthetic": true}'`,
or upload your own three CSV files as multipart fields `draft`, `final` and `asdd`.
Check it: `curl localhost:8000/api/health` returns `{"status":"ok","audit_ready":true}`.

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `AUTO_SEED` | `false` | `true` builds the synthetic audit at startup when none exists |
| `DATA_DIR` | `backend/data` | SQLite database (`voterguard.db`), `synthetic/` CSVs and `audits/{audit_id}/` snapshots |
| `AGENT_URL` | `http://localhost:8001` | Agent service used to phrase flag explanations |
| `AGENT_TIMEOUT_SECONDS` | `8` | After this the core uses its templates (`explanation_source: "template"`) |
| `CLAIMS_DEADLINE` | empty | Date shown in the citizen "what you can do" box |

## Endpoints

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/health` | `audit_ready` is true once an audit exists |
| POST / GET | `/api/audits` | Create (synthetic or upload) and list audits |
| GET | `/api/audits/{id}/summary` | Totals, snapshot hashes, constituency baseline, reason mix |
| GET | `/api/audits/{id}/booths`, `/booths/{part_no}` | Booths by risk score; detail with charts data and flags |
| GET | `/api/audits/{id}/flags` | Optional filters `part_no`, `severity`, `detector` |
| PUT | `/api/audits/{id}/flags/{flag_id}/review` | `PENDING`, `ACCEPTED` or `REJECTED`, with an optional note |
| GET | `/api/audits/{id}/export` | Everything the trust service needs to build a report |
| POST | `/api/citizen/lookup` | Masked result; 20 requests per minute per client IP; nothing typed is logged |

Errors use `{"error": {"code", "message"}}`.

## Layout

| Folder | Purpose |
| --- | --- |
| `app/engine/` | Compare rolls, aggregate per booth, constituency baseline, file hashing (pure Pandas) |
| `app/detectors/` | Seven detectors, `config.py` (all thresholds), IsolationForest risk score |
| `app/services/` | Pipeline, store, export, citizen lookup, agent client, bilingual templates |
| `app/routers/` | HTTP routes |
| `app/synth/` | Seeded synthetic roll generator with planted patterns (`python -m app.synth.generate --out data/synthetic --seed 42`) |
| `tests/` | Engine, detectors, synthetic data, API and fixtures |
