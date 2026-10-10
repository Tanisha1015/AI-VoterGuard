# VoterGuard India: frontend

React + Vite + TypeScript (strict) + Tailwind CSS v4 web app for the VoterGuard India demo.
It uses **synthetic data only** and never decides anyone's eligibility.

## Requirements

- Node 22 or newer, npm 10 or newer

## Run

```bash
cd frontend
npm install
cp .env.example .env.local   # PowerShell: Copy-Item .env.example .env.local
npm run dev                  # http://localhost:5173
```

| Command             | What it does                                  |
| ------------------- | --------------------------------------------- |
| `npm run dev`       | Dev server on port 5173                       |
| `npm test`          | Vitest + Testing Library (jsdom), single run  |
| `npm run typecheck` | `tsc -b` in strict mode                       |
| `npm run build`     | Type check, then production build to `dist/`  |
| `npm run preview`   | Serve the production build                    |

## Environment

| Variable         | Default                 | Purpose                                         |
| ---------------- | ----------------------- | ----------------------------------------------- |
| `VITE_CORE_URL`  | `http://localhost:8000` | Core API (Member A)                             |
| `VITE_TRUST_URL` | `http://localhost:8002` | Trust service                                   |
| `VITE_AUDIT_ID`  | `aud_001`               | Audit used by reviewer pages                    |
| `VITE_USE_MOCKS` | `true`                  | Serve responses from `src/mocks` after 300 ms   |

## Mock mode

With `VITE_USE_MOCKS=true` every request is answered from `src/mocks/*.json`. These files were
copied once from `contracts/fixtures/`; `citizen_added.json` is a frontend-only synthetic addition
because the contract has no ADDED fixture. Unknown routes fail with `MOCK_ROUTE_NOT_FOUND`.

Citizen lookup rules (by the name typed in the form):

| Name contains | Result      |
| ------------- | ----------- |
| `sunita`      | REMOVED     |
| `ambig`       | AMBIGUOUS   |
| `none`        | NOT_FOUND   |
| `added`       | ADDED       |
| anything else | PRESENT     |

Verify mocks (trust service):

- Reports start from `report_list.json` (VG-2026-0001 superseded by 0002) and are kept in memory.
  Recording a corrected version adds the next id on top and marks the old one superseded; correcting
  an already superseded report returns 409, as the real service does.
- `GET /files/{id}.json` returns a synthetic report file (canonical JSON built from `export.json`).
- Verify compares content: the file from "Load original" returns MATCH; any other content
  (a tampered copy or an edited upload) returns MISMATCH; an unknown report id returns NOT_FOUND.

Reviewer mocks:

- `GET /api/audits` is derived from `audit_summary.json` (one audit, `aud_001`).
- Review decisions (`PUT …/flags/{id}/review`) are kept in memory for the session, so booth pages,
  the flag list and the pending-review count reflect them. Reloading the page resets them.
- Booth 17 uses `booth_17.json`. Other booths are built from `booths.json` and `flags.json`; their
  gender counts are estimated from `female_removed_share` and their age shares reuse booth 17's
  (synthetic approximation for the demo only). Unknown part numbers return 404.
- `POST /api/reports` returns `report_created.json`.

## Reviewer flow

1. `/reviewer`: KPI cards, booth heatmap (darker = higher risk score, bold border + ⚑ = has flags),
   sortable/filterable booth table, and the finalize panel.
2. Select a booth to open `/reviewer/booth/:part`: stats, three charts (each with a data table),
   and flag cards with Accept / Not taken forward controls.
3. Back on the dashboard, enter a reviewer name and choose **Finalize and record report** to get
   the report card with hashes, downloads and a link to `/verify?report_id=…`.

## Structure

```
src/
  api/          types.ts (contract types), client.ts, mockRouter.ts, core.ts, trust.ts
  hooks/        useCurrentAudit.ts (first item of GET /api/audits)
  lib/          format.ts (numbers, %, dates, hashes, risk scale), booths.ts (sort/filter)
  i18n/         index.ts, en.json, hi.json   (all user-facing strings)
  components/   Layout, LanguageToggle, Disclaimer, StatusCard, FormField, CitizenResult,
                KpiCards, Heatmap, BoothTable, SeverityChip, FlagCard, ReviewControls,
                FinalizePanel, ReportCard, QueryState, charts/*
  pages/        Citizen, ReviewerDashboard, BoothDetail, Verify (Verify: coming soon)
  mocks/        synthetic fixtures
```

Routes: `/` (citizen), `/reviewer`, `/reviewer/booth/:part`, `/verify`.

The API contract is `contracts/CONTRACT.md`. Field names in `src/api/types.ts` mirror it exactly.
