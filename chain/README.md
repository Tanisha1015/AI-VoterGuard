# VoterGuard chain: ReportRegistry

A Hardhat 3 project (TypeScript, viem, `node:test`) with the `ReportRegistry` smart contract.
It records the SHA-256 hashes of VoterGuard audit reports so anyone can check that a published
report file has not been changed. It stores hashes only and makes no judgement about any voter.
The interface follows `contracts/CONTRACT.md` sections 6.6 and 6.7.

Requires Node.js 22.10 or later. Install once:

```bash
npm install
```

## Commands

```bash
npm run node          # start a local chain at http://127.0.0.1:8545 (chain id 31337)
npm run deploy:local  # in a second terminal: deploy the contract and add account #1 as a submitter
npm test              # compile and run the contract tests
```

`npm run compile` compiles the contract only.

## Deployment output

`npm run deploy:local` writes:

- `deployments/local.json`: `{ "address", "chainId", "deployer", "submitters": [...] }`
- `deployments/ReportRegistry.abi.json`: the contract ABI array

The local node resets every time it restarts, so redeploy after each `npm run node`.

## Contract summary

| Function | Access | Notes |
|---|---|---|
| `recordReport(reportId, reportHash, draftHash, finalHash, asddHash, supersedesId)` | submitters | Reverts with `EmptyReportId`, `ReportExists`, `UnknownSupersededReport`, `AlreadySuperseded` |
| `getReport(reportId)` | view | Reverts with `UnknownReport` if the id has not been recorded |
| `verifyReport(reportId, candidateHash)` | view | `false` if the id is unknown or the hash differs |
| `supersededBy(reportId)` | view | `""` if the report has not been superseded |
| `addSubmitter(address)` / `removeSubmitter(address)` | owner | The owner is a submitter by default |

Event: `ReportRecorded(string indexed reportId, string reportIdPlain, bytes32 reportHash, address submitter, uint64 timestamp)`.
An indexed string is stored as its keccak256 hash in the log topic, so `reportIdPlain` carries
the readable id. Decode events with `deployments/ReportRegistry.abi.json`.
