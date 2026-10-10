# agent-service

Phrases each flagged booth pattern in English and Hindi using the [Cline SDK](https://docs.cline.bot/sdk)
(`@cline/sdk`). It only writes text. Every number comes from the request payload, and a deterministic
guard checks the result before it is returned. It never decides eligibility and never declares wrongdoing.

Contract: `contracts/CONTRACT.md` section 6.4. Port `8001`. Node 22+, TypeScript strict, Fastify, zod, vitest.

## Run

```bash
cd agent-service
npm install
MOCK_AGENT=true npm run dev          # offline, deterministic text, no API key needed
ANTHROPIC_API_KEY=sk-ant-... npm run dev   # real agents
npm test                             # no network; the SDK Agent is mocked
```

Check it:

```bash
curl localhost:8001/health
curl -X POST localhost:8001/explain -H 'content-type: application/json' -d '{
  "audit_id": "aud_001",
  "booth": {"part_no": 17, "draft_count": 812, "final_count": 640, "removed": 182, "added": 10,
            "deletion_rate": 0.224, "reason_mix": {"ABSENT": 0.1, "SHIFTED": 0.82, "DEAD": 0.05, "DUPLICATE": 0.03},
            "female_removed_share": 0.71, "risk_score": 87, "flagged": true, "flag_count": 3},
  "flag": {"detector": "DELETION_RATE", "severity": "HIGH",
           "metric": {"name": "deletion_rate", "value": 0.224, "baseline": 0.048}},
  "baseline": {"deletion_rate": 0.048, "deletion_rate_mad": 0.012}
}'
```

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8001` | HTTP port |
| `ANTHROPIC_API_KEY` | empty | Provider key. If empty, the service runs in mock mode |
| `AGENT_PROVIDER_ID` | `anthropic` | SDK provider id |
| `AGENT_MODEL_ID` | `claude-sonnet-5-5` | SDK model id (present in the SDK's anthropic catalog) |
| `MOCK_AGENT` | `false` | `true` forces mock mode even when a key is set |
| `AGENT_RUN_TIMEOUT_MS` | `20000` | Per agent run timeout (milliseconds) |
| `AGENT_CACHE_SIZE` | `500` | Maximum cached explanations |

`GET /health` returns `{"status":"ok","mode":"agent"}` or `{"status":"ok","mode":"mock"}`.

## How `/explain` works

1. The body is validated with zod. A malformed body gets `422 VALIDATION_ERROR`.
2. **Mock mode:** `mock.ts` builds neutral bilingual text from the payload. `neutrality.method` is `"mock"`.
3. **Agent mode:** the explainer `Agent` calls three custom tools (`get_booth_stats`, `get_baseline`,
   `get_flag_metric`) that return data from the request held in a per-request closure (no network, no core API call),
   then answers with a JSON object.
4. `guard.ts` checks the text: a blocklist (English and Hindi, case-insensitive, whole-word for English) and a number
   check (each number or percentage must match a payload value; rounding to 0 to 1 decimals, ratios such as
   "4.7 times", and percent or fraction forms are accepted).
5. On violations a second `Agent` (the reviewer) rewrites only the listed problems. The guard runs again.
   At most 2 rewrites, then `422 NEUTRALITY_FAILED`.
6. Results are cached in an LRU keyed by the sha256 of the canonical request body. At most 3 agent runs are in
   flight; a run that exceeds the timeout is aborted and answered with `503 AGENT_UNAVAILABLE`.

The core API falls back to its own templates on either error.

## Files

| File | Purpose |
| --- | --- |
| `src/index.ts` | Fastify server, `/health`, `/explain` |
| `src/explain.ts` | Orchestration: explainer, guard, reviewer, cache, concurrency |
| `src/agents/explainer.ts`, `src/agents/reviewer.ts` | SDK `Agent` instances and system prompts |
| `src/tools.ts` | Custom tools made with the SDK's `createTool` |
| `src/guard.ts`, `src/blocklist.ts`, `src/numbers.ts` | Neutrality guard |
| `src/mock.ts`, `src/mock-checks.ts` | Deterministic mock text |
| `src/cache.ts` | LRU cache, concurrency limit, run timeout |
| `src/config.ts`, `src/types.ts`, `src/facts.ts` | Config, schemas and errors, derived facts |

## Notes on the Cline SDK

- Agent: `new Agent({ providerId, modelId, apiKey, systemPrompt, tools, maxIterations })`, then `await agent.run(prompt)`;
  the final text is `result.outputText`.
- Tools: `createTool({ name, description, inputSchema: z.object(...), execute })`, passed as `tools: [...]`.
- Sub-agents are documented only as a ClineCore session feature (`enableSpawnAgent`), not for the standalone `Agent`,
  so the reviewer is a separate `Agent` instance.
