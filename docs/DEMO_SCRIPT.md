# Five-minute demo script

A walkthrough of the whole system with exact inputs and the outputs to expect. It uses the synthetic audit
`aud_001` ("Demo Nagar (Synthetic)", seed 42), so the numbers below are the same on every fresh start.

**Message to keep repeating:** the tool shows *unusual patterns worth verifying*. It never decides anyone's
eligibility, never declares wrongdoing, and a matching hash proves a file is unchanged, not that it is correct.

## Before you start (not part of the five minutes)

1. Start the six processes from the root README quick start (chain, deploy, trust, core with `AUTO_SEED=true`,
   agent, frontend). Source the root `.env` first so `CLAIMS_DEADLINE` and `SUBMITTER_PRIVATE_KEY` are set.
2. In `frontend/.env.local` set `VITE_USE_MOCKS=false`. With mocks on, the screens show the contract's example
   numbers (for example 48,210 draft voters), not the figures in this script.
3. Start from a clean state, or the numbers below will differ. Stop all six processes, then:
   ```bash
   rm -rf backend/data/voterguard.db backend/data/audits trust-service/data   # keeps backend/data/synthetic
   ```
   and start them again in the quick-start order. A fresh chain plus an empty `trust-service/data` makes the
   first report `VG-2026-0001`; a fresh database makes all 15 flags pending.
4. Optional dry run: `make smoke`. It accepts one flag and records two reports, so **repeat step 3
   afterwards**, before the real demo.
5. Open `http://localhost:5173` in a window about 1000 px wide, English selected, zoom 100%.

Expected on the first screen: the page title tab reads "Check your entry in the roll · VoterGuard India", and
a blue banner says "Demo using synthetic data. This tool does not decide anyone's eligibility."

## Timeline

| Time | Part |
| --- | --- |
| 0:00 to 0:30 | Framing |
| 0:30 to 1:30 | Citizen lookup |
| 1:30 to 2:00 | Hindi and small screens |
| 2:00 to 3:15 | Reviewer dashboard and booth 17 |
| 3:15 to 3:45 | Human review and finalising a report |
| 3:45 to 4:45 | Verify, tamper, correct |
| 4:45 to 5:00 | Close |

## 0:00 to 0:30  Framing

Say: "After a roll revision, two questions are hard to answer: did something change in a way worth a closer
look, and is the report I am reading the one that was published? VoterGuard India helps with both, using
synthetic data only."

Show the banner. Do not click anything yet.

## 0:30 to 1:30  Citizen lookup (page `/`)

**Type** (use the real keyboard, one field at a time):

| Field | Input |
| --- | --- |
| Your name | `Sunita Devi` |
| Father's, mother's or husband's name | `Ramesh Kumar` |
| Part (booth) number | `17` |

Press **Check my entry**.

**Expect** a result card titled **"Your entry is not in the final roll"** with:

| Row | Value |
| --- | --- |
| Name in roll | `Sunita D.` |
| EPIC (masked) | `VGX****051` |
| Part number | `17` |
| Age group | `26-35` |
| Recorded reason | "Recorded as having moved to a different address" |

and a "What you can do" box: "If this is incorrect, you can ask for your name to be restored", step 1
"Contact your Booth Level Officer or visit the official ECI portal", step 2 "Keep a proof of your current
address ready", then "Last date to apply: 2026-10-31" and the official-website disclaimer.

Say: "Only a masked EPIC and 'first name plus last initial' are shown. The page says what the roll records
and what the person can do; it does not say why."

**Spelling variant.** Change the first field to `Sunitha Devi` and press the button again. **Expect** the same
card (status REMOVED, same masked EPIC). Say: "Spelling variants still match."

**Not found.** Change the first field to `Rekha Verma`, relative `Mohan Lal`, part `17`. **Expect** "We could
not find a matching entry" and a button "Search with EPIC number".

## 1:30 to 2:00  Hindi and small screens

Click **हिन्दी** at the top right. **Expect** the heading "मतदाता सूची में अपनी प्रविष्टि देखें", the
banner in Hindi, and the browser tab title in Hindi. Re-run `Sunita Devi` / `Ramesh Kumar` / `17`: the result
title is "आपकी प्रविष्टि अंतिम सूची में नहीं है" and the reason reads "किसी दूसरे पते पर स्थानांतरित दर्ज".

Optional: press F12, choose the device toolbar and set the width to 360. Nothing scrolls sideways.
Switch back to **EN** before moving on.

## 2:00 to 3:15  Reviewer dashboard and booth 17 (page `/reviewer`)

Click **Reviewer** in the navigation.

**Expect** the heading "Reviewer dashboard" with the subtitle "Demo Nagar (Synthetic) · audit aud_001", and six
figures:

| Draft voters | Final voters | Removed | Added | Flagged booths | Pending reviews |
| --- | --- | --- | --- | --- | --- |
| 47,670 | 46,239 | 2,469 | 1,038 | 11 | 15 |

Below them, a heatmap of 60 booth tiles. The 11 flagged booths have a bold border and a flag mark, and the two
darkest tiles are **booth 17 (score 100)** and **booth 42 (score 97)**. The "All booths" table is sorted by
risk score, highest first: 17, 42, 25, 33, 51.

Say: "The score only says which booths to look at first. It is not a finding."

Click **17** (tile or table row).

**Expect** "Booth 17" with these figures:

| Draft voters | Final voters | Removed | Added | Removal rate | Risk score |
| --- | --- | --- | --- | --- | --- |
| 790 | 628 | 174 | 12 | 22.0% | 100 |

Three charts: recorded reasons (the "Shifted" bar is about 82%), removals by gender (women 124, men 50), and
removals by age group. Each chart has "Show data as a table".

**Expect** three flag cards, each labelled "AI-assisted" and "Pending":

| Card | Severity | Metric line | Explanation (starts with) |
| --- | --- | --- | --- |
| Removal rate compared with constituency | High | Removal rate: 22.0% (constituency baseline 4.9%) | "Booth 17 shows a deletion rate of 22.0%, compared with a constituency baseline of 4.9%, about 4.5 times that baseline. This is unusual and worth verifying." |
| One removal reason dominates | Medium | Share of the most common recorded reason: 82.2% (constituency baseline 40.6%) | "In booth 17, removals recorded as "shifted" make up 82.2% of all removals, compared with 40.6% across the constituency. This is unusual and worth verifying." |
| Gender balance of removals | Medium | Share of women among removals: 71.3% (constituency baseline 47.7%) | "Female voters make up 71.3% of removed entries in booth 17, compared with 47.7% of the booth's draft roll. This is unusual and worth verifying." |

Say: "Every number is computed by code. The wording can come from an AI model, but a guard checks that it only
repeats those numbers and uses no accusatory words. The note under the flags says these are prompts for field
verification; they do not establish wrongdoing or eligibility. Common innocent causes, such as a factory
closing, are listed in docs/METHODOLOGY.md."

Optional, if time allows: open booth 33 (45 additions at one house number: "Most additions at one house
number: 45 (constituency baseline 1)") to show that a count is shown as a count, not as a percentage.

## 3:15 to 3:45  Human review and finalising

On the first card (Removal rate), type `Field check scheduled` in "Reviewer note (optional)" and press
**Accept**. **Expect** the status line "Status: ✓ Accepted for field check" and "Saved <date and time> UTC".
Click **Back to dashboard**: Pending reviews now shows **14**.

Scroll to "Finalize and record report". Type `R. Sharma` as the reviewer name and press **Finalize and record
report**. A gentle note says some flags are still pending; that is fine.

**Expect** a green "Report recorded" card with:

| Row | Value |
| --- | --- |
| Report ID | `VG-2026-0001` |
| Report hash | shortened `0x…` with a **Copy hash** button |
| Transaction hash | shortened `0x…` and a block number |
| Recorded at | the current time, UTC |

and buttons **Download JSON**, **Download PDF**, **Verify this report**.

Say: "The report records the human decisions, not a verdict. Its SHA-256 fingerprint is now on the chain."

## 3:45 to 4:45  Verify, tamper, correct (page `/verify`)

Press **Verify this report** (or click **Verify** in the navigation and select `VG-2026-0001`).

**Expect** the blue box "What this check means": "What this proves: the file has not changed since it was
recorded. What it does not prove: that the findings are correct or that any removal was or was not
appropriate." Read both sentences aloud.

1. Press **Load original**, then **Verify**. **Expect** "Identical to the recorded report", with "Hash of this
   file" equal to "Recorded hash".
2. Press **Simulate tampering**. **Expect** "Simulation: changed character 56 from “9” to “0”." (the last digit
   of `ac_no` 999 in the saved file) and the result "Different from the recorded report", marked as a
   simulation, with two different hashes. Say: "One character, completely different fingerprint. Nothing was
   saved."
3. Press **Load original** and **Verify** again to return to Identical.
4. In "Record a corrected version" type `R. Sharma` and press **Record corrected version**. **Expect** the
   notice "Recorded VG-2026-0002. It now supersedes VG-2026-0001." In the list, `VG-2026-0002` shows
   "Latest version" and `VG-2026-0001` shows "Superseded by VG-2026-0002".
5. Select `VG-2026-0001`, press **Load original** and **Verify**. **Expect** it is still identical, with "A
   corrected version exists: View report VG-2026-0002". Say: "Reports are never overwritten. The old one stays
   on the chain, marked as replaced."

Optional proof outside the browser (terminal):

```bash
curl -s localhost:8002/files/VG-2026-0001.json | shasum -a 256
curl -s localhost:8002/api/reports/VG-2026-0001      # report_hash is the same digest with a 0x prefix
```

## 4:45 to 5:00  Close

Say: "Three things: patterns are made visible and ranked, people verify them in the field, and the published
report is tamper-evident. It works offline with no API key, uses synthetic data only, and it never decides who
may vote or who did what."

## If something goes wrong

| Symptom | Cause and fix |
| --- | --- |
| Numbers such as 48,210 draft voters, or the Verify list already shows VG-2026-0002 | The frontend is in mock mode. Set `VITE_USE_MOCKS=false` in `frontend/.env.local` and restart `npm run dev` |
| Reviewer page says "No audit is available yet." | The core has no audit. Start it with `AUTO_SEED=true`, or run `curl -X POST localhost:8000/api/audits -H 'content-type: application/json' -d '{"use_synthetic": true}'`, then reload |
| Finalize shows "The report ledger could not be reached right now" (and a notice at the bottom) | The trust service has no `SUBMITTER_PRIVATE_KEY`, or the chain was restarted without redeploying. Check `GET :8002/api/chain/status`, redeploy, restart the trust service |
| First report is not `VG-2026-0001` | Old state remained. Repeat step 3 of "Before you start". What you say still works; only the id differs |
| Citizen lookup says "Many searches were made in a short time" | The lookup is limited to 20 per minute per client. Wait one minute |
| Flags say "Template" instead of "AI-assisted" | The agent service was down when the audit was created, so the core used its own templates. This is the offline fallback working as designed |
