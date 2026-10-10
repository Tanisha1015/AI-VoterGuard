# Methodology

How VoterGuard India turns a draft roll, a final roll and a removal list (ASDD) into booth-level flags and a
risk score. Everything here is deterministic code in `backend/app/engine/` and `backend/app/detectors/`.
All thresholds live in one file, `backend/app/detectors/config.py`, and are exported with every report
(`methodology.thresholds` in `GET /api/audits/{id}/export`).

**What a flag means.** A flag says that a booth-level pattern is *unusual compared with the rest of the
constituency* and *worth verifying*. It does not say why it happened, who is responsible, or whether any
entry is correct. No flag, score or detector decides anything about a voter. Only gender and age bands are
analysed; names are used only to match entries (citizen lookup, repeated-entry check), never to infer
religion, caste or citizenship.

## 1. Inputs and definitions

| Term | Meaning |
| --- | --- |
| Draft / final roll | CSVs with `epic_no, ac_no, part_no, serial_no, name, relative_name, relation_type, house_no, age, gender` |
| ASDD | `epic_no, part_no, reason, remark`: the recorded reason for a removal (ABSENT, SHIFTED, DEAD, DUPLICATE) |
| Added | In the final roll, `epic_no` not in the draft roll (counted in the final booth) |
| Removed | In the draft roll, `epic_no` not in the final roll (counted in the draft booth). Its reason comes from the ASDD; none if the ASDD has no row |
| Modified | Same `epic_no` in both rolls with a different name, relative name, house, age, gender or booth |
| Deletion rate | `removed / draft_count` for the booth |
| Reason mix, gender, age band | Shares of the booth's removals. Age bands: 18-25, 26-35, 36-45, 46-60, 61-80, 80+ |
| Constituency baseline | `deletion_rate` = median of the booth deletion rates; `deletion_rate_mad` = median absolute deviation (MAD) of the same rates, unscaled |

Small booths are protected from noise: every detector that works on shares has a minimum number of removals
(`min_removed`) before it can fire.

## 2. Detectors and default thresholds

Detector names match the `detector` enum in `contracts/CONTRACT.md`. Severity is MEDIUM unless a HIGH
threshold is reached (or LOW where stated).

### DELETION_RATE

Removal rate far above the constituency median, using a robust z-score so a few extreme booths do not
distort the yardstick: `z = (booth_rate - median) / (mad_scale * MAD)`.

| Setting | Default | Effect |
| --- | --- | --- |
| `mad_scale` | 1.4826 | Makes the MAD comparable to a standard deviation |
| `z_min` | 3.5 | Fires at or above this |
| `z_high` | 6.0 | Severity HIGH at or above this |
| `min_removed` | 15 | The booth needs at least this many removals |

If the MAD is 0 there is no spread to compare with, so the detector stays quiet. Metric: `deletion_rate`
against the constituency median.

*Example (synthetic audit):* median 4.86%, scaled MAD 0.97 percentage points, so z = 3.5 starts at a rate of
8.3% and z = 6 at 10.7%. Booth 17 (22.0%) has z of about 17.6 and booth 42 (14.0%) about 9.4.

### REASON_DOMINANCE

One recorded reason accounts for almost all removals in a booth.

| Setting | Default | Effect |
| --- | --- | --- |
| `share_min` | 0.80 | Largest reason share at or above this fires |
| `share_high` | 0.90 | Severity HIGH at or above this |
| `min_removed` | 20 | Minimum removals |

Metric: `reason_share`, against the same reason's share across the whole constituency.

### GENDER_SKEW

A gender is over-represented among removals compared with its share of the booth's own draft roll:
`gap = share of gender g among removed - share of g in the booth's draft roll`. Only F and M are tested.

| Setting | Default | Effect |
| --- | --- | --- |
| `gap_min` | 0.15 | Fires at or above this gap |
| `gap_high` | 0.25 | Severity HIGH at or above this |
| `min_removed` | 30 | Minimum removals |

Metric: `f_removed_share` or `m_removed_share`, against that gender's draft share.

### AGE_SKEW

Two kinds of flag (`details.kind`):

- **DEAD_UNDER_40**: removals recorded as DEAD for voters under 40. Fires at `dead_under_40_min = 10`, HIGH at
  `dead_under_40_high = 25`. Baseline: the median count across booths.
- **YOUNG_REMOVED**: the 18-25 share among removed minus the 18-25 share of the draft roll. Fires at
  `young_gap_min = 0.15`, HIGH at `young_gap_high = 0.30`, with `min_removed = 30`.

### HOUSE_CLUSTER

At most one flag per booth.

- **HOUSE_ADDITIONS** (checked first): many *added* entries at one house number. Fires at `additions_min = 10`,
  HIGH at `additions_high = 30`. Baseline: the median across booths.
- **HOUSE_CROWDED** (only when the rule above did not fire): the most crowded house in the final roll has at
  least `max(voters_floor, 99th percentile across booths)` entries, with `voters_floor = 15` and
  `voters_percentile = 99`. Severity LOW (`voters_only_severity`).

House numbers are not personal data and are the only address detail used.

### DUPLICATE_ENTRY

Near-identical entries in different booths of the final roll. To avoid comparing every pair, entries are
first grouped by gender, age bucket (`age_bucket_width = 3` years) and the first `name_prefix_len = 3`
letters of the normalised name. Two entries form a pair when they are in different booths, have different EPIC
numbers, differ in age by at most `max_age_diff = 1`, and both the name and the relative's name score at least
`name_score_min = 92` (RapidFuzz token-set ratio, 0 to 100).

A booth fires when it has at least `pairs_min = 5` pairs (each pair counts for both of its booths), HIGH at
`pairs_high = 15`. Metric: `duplicate_pairs`, against the median across booths. A pair is a pattern worth
verifying, not a conclusion about either person.

### DATA_QUALITY

Counts data issues recorded for the booth: `REMOVED_WITHOUT_ASDD` (removed, but no ASDD row),
`ASDD_NOT_IN_DRAFT`, `AGE_OUT_OF_RANGE` (age under 18 or over 110) and `DUPLICATE_EPIC` (an EPIC repeated
inside one roll). Fires at `count_min = 3`, HIGH at `count_high = 8`. The count per issue type is kept in the
flag details. These flags often point at the data feed rather than at the booth.

## 3. Booth risk score

The risk score (0 to 100) ranks booths so reviewers know where to look first. It is a priority order for
human verification, not a finding about any booth.

`risk_score = round(100 * (0.6 * isolation + 0.4 * severity))`

- **isolation (0 to 1)**: how unusual the booth looks across ten numeric features, from an IsolationForest
  (`n_estimators = 200`, `random_state = 42`, so results repeat), min-max scaled across the booths.
  Features: deletion rate; shares of SHIFTED, ABSENT and DEAD among removals; female removed-share minus
  female draft-share; 18-25 removed-share minus 18-25 draft-share; addition rate; largest number of additions
  at one house number; duplicate pairs; data-quality issue count.
- **severity (0 to 1)**: `min(1, sum of flag points / severity_cap)` with `severity_cap = 2.0` and points
  LOW = 0.3, MEDIUM = 0.6, HIGH = 1.0 per flag. One HIGH flag gives 0.5; the cap of 1 is reached at 2 points,
  for example two HIGH flags, or HIGH + MEDIUM + MEDIUM (booth 17 in the synthetic audit: 2.2 points).
- A booth is `flagged` when it has at least one flag.

Because isolation is min-max scaled, the most unusual booth always gets the full 60 points from isolation,
and the least unusual gets 0. The score is relative to the audit it was computed in; do not compare scores
between audits.

## 4. Known causes of false positives

Each of these can produce flags when nothing is wrong with the process. A reviewer should rule them out
before deciding on a field check.

| Pattern flagged | Ordinary explanations to rule out |
| --- | --- |
| High deletion rate; REASON_DOMINANCE on SHIFTED | A factory or construction site closing, a new housing project elsewhere, a hostel or barracks emptying, slum resettlement, a booth boundary that was redrawn |
| REASON_DOMINANCE on DEAD | An epidemic or heat wave, an old-age home in the booth, a clean-up of long-outdated entries |
| REASON_DOMINANCE on ABSENT | A house-to-house visit during harvest, a festival or wedding season, a flood or cyclone that displaced residents, a single visit at the wrong time of day |
| GENDER_SKEW (female) | Marriage-related moves, which mostly affect women, depending on which records were used |
| GENDER_SKEW (male) | Seasonal or long-term labour migration to cities, army or seasonal work |
| AGE_SKEW: YOUNG_REMOVED | Students and young workers who moved for study or jobs |
| AGE_SKEW: DEAD_UNDER_40 | Data-entry errors (wrong age or wrong EPIC in the ASDD), an accident or disease cluster |
| HOUSE_CLUSTER | A new apartment block, a hostel, a care home, a camp or a newly regularised colony |
| DUPLICATE_ENTRY | Common names plus a spelling variant (for example Sunita and Sunitha), relatives with similar names, people registered at both a native and a work address |
| DATA_QUALITY | Typing errors, a faulty export, an incomplete ASDD file, files produced by different processes |
| Any detector in a small booth | Few entries move a share a lot. `min_removed` reduces this but does not remove it |

The baseline is the constituency's own median. If many booths changed in the same way (for example after a
large flood), a single affected booth looks *less* unusual; in a calm constituency, ordinary local events
look *more* unusual.

## 5. Reading a flag

1. Read the metric and its baseline, not just the score.
2. Check the table in section 4 against what is known locally.
3. Use the recommended checks: a sample field check, a comparison with Booth Level Officer visit records, a
   household re-verification of a sample.
4. Record the decision (accepted for a field check, or not taken forward) with a note. A report records the
   decision, not a finding.

## 6. Tuning and limits

- Thresholds are defaults chosen for the synthetic data, not calibrated on real rolls. Change them only in
  `backend/app/detectors/config.py`; the new values appear in the next export.
- The synthetic data has six planted patterns (booths 17, 42, 33, 8 with 51, 25, and 3 with 9). The detectors
  recover them. That tests the code; it is not evidence about any real roll.
- Explanation text may be phrased by an LLM, but it can only restate these numbers. A deterministic guard
  rejects text with loaded words or with numbers that are not in the data.
