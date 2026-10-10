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

When you upload a file for verification, a file name containing `mismatch` or `tamper` returns MISMATCH; any other name returns MATCH.

## Structure

```
src/
  api/          types.ts (contract types), client.ts, mockRouter.ts, core.ts, trust.ts
  i18n/         index.ts, en.json, hi.json   (all user-facing strings)
  components/   Layout, LanguageToggle, Disclaimer, StatusCard, FormField, CitizenResult
  pages/        Citizen, ReviewerDashboard, BoothDetail, Verify (last three: coming soon)
  mocks/        synthetic fixtures
```

Routes: `/` (citizen), `/reviewer`, `/reviewer/booth/:part`, `/verify`.

The API contract is `contracts/CONTRACT.md`. Field names in `src/api/types.ts` mirror it exactly.
