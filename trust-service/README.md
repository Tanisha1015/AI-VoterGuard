# VoterGuard trust service (:8002)

Builds the audit report from the core API's export, hashes it, records the hash on the local
`ReportRegistry` contract, and serves the saved JSON and PDF files. It never judges any voter or
roll; it only proves which report bytes were published, when, and by whom.
Follows `contracts/CONTRACT.md` sections 6.5, 6.6 and 6.7.

## Setup (Python 3.11)

```powershell
cd trust-service
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

(macOS/Linux: `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`.)

## Run

1. In `chain/`: `npm run node`, then in a second terminal `npm run deploy:local`. The node resets
   on restart, so redeploy each time.
2. Set the environment (see `.env.example`). `SUBMITTER_PRIVATE_KEY` is the private key of
   **Hardhat account #1**, which `npm run node` prints. It is a public development key for the local
   node only. Never use it anywhere else, and never commit keys.
3. Start the service:

```powershell
$env:SUBMITTER_PRIVATE_KEY = "<account #1 key printed by npm run node>"
.venv\Scripts\python -m uvicorn app.main:app --port 8002
```

| Variable | Default | Purpose |
|---|---|---|
| `CORE_URL` | `http://localhost:8000` | Core API (export source) |
| `CHAIN_RPC_URL` | `http://127.0.0.1:8545` | Hardhat JSON-RPC |
| `SUBMITTER_PRIVATE_KEY` | (empty) | Signs `recordReport` transactions |
| `REPORT_DIR` | `./data/reports` | Saved `VG-*.json` and `VG-*.pdf` |
| `TRUST_DB_PATH` | `<REPORT_DIR>/../trust.sqlite3` | SQLite store |
| `DEPLOYMENTS_DIR` | `../chain/deployments` | `local.json` + `ReportRegistry.abi.json` |
| `ASSETS_DIR` | `./assets` | Optional `NotoSansDevanagari-Regular.ttf` |

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` |
| POST | `/api/reports` | `{audit_id, reviewer_name, supersedes?}` returns 201 (contract shape) |
| GET | `/api/reports` | Newest first, with `superseded_by` |
| GET | `/api/reports/{id}` | POST shape plus `superseded_by` (read from the chain) |
| POST | `/api/reports/verify` | Multipart `file` (+ optional `report_id`): MATCH / MISMATCH / NOT_FOUND |
| GET | `/api/chain/status` | Always 200; `connected:false` when the node or contract is down |
| GET | `/files/{VG-YYYY-NNNN}.json\|.pdf` | Saved files only; other names return 404 |

Errors use `{"error": {"code", "message"}}`:

| Situation | Status |
|---|---|
| Core API unreachable or 5xx | 502 `CORE_UNAVAILABLE` / `CORE_ERROR` |
| Unknown audit | 404 `AUDIT_NOT_FOUND` |
| `supersedes` not in the store | 404 `SUPERSEDED_REPORT_NOT_FOUND` |
| Report already superseded on chain | 409 `ALREADY_SUPERSEDED` |
| Node, contract or key unavailable | 502 `CHAIN_UNAVAILABLE` |
| Verify file has no readable `report_id` and none was given | 422 `REPORT_ID_REQUIRED` |

## How a report is recorded

1. Fetch `GET {CORE_URL}/api/audits/{audit_id}/export`.
2. Allocate `VG-{year}-{seq:04d}`; build the document (`schema_version`, `report_id`,
   `generated_at`, `reviewer`, `audit`, `supersedes`).
3. Canonical bytes: `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, UTF-8.
   `report_hash` = SHA-256 of exactly these bytes. Render the PDF.
4. Call `recordReport` on the chain. If the chain already has that id (for example, the local data
   was wiped), the next free id is used.
5. **Only after the transaction succeeds**: write `{id}.json` (the exact canonical bytes) and `{id}.pdf`
   (each via temp file + rename), then insert the store row. If the chain call fails, nothing is
   written and the response is 502.

Verification hashes the uploaded bytes exactly as received, so any edit (even one space) gives MISMATCH.

## PDF and Hindi

The PDF includes the summary, snapshot hashes, flagged booths, each flag's English explanation with
the reviewer decision and note, the disclaimer and the report hash. If
`assets/NotoSansDevanagari-Regular.ttf` exists, the Hindi explanation and disclaimer are added;
otherwise a warning is logged and the PDF is English-only. The font is not bundled. ReportLab does
not shape complex scripts, so Devanagari conjuncts may render imperfectly even with the font.

## Tests

```powershell
.venv\Scripts\python -m pytest -q          # unit tests (chain mocked); the chain test is deselected
$env:SUBMITTER_PRIVATE_KEY = "<account #1 key>"
.venv\Scripts\python -m pytest -m chain    # needs the node running and the contract deployed
```

The chain test records a report, verifies MATCH, flips one character for MISMATCH, records a
corrected version with `supersedes`, and checks `superseded_by`. It skips if the node is not reachable.

For a manual end-to-end check without the real core API:
`python -m uvicorn tests.stub_core:app --port 8000` serves the export fixture.
