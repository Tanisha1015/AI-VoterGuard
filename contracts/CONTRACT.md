Both members build to this. It is frozen after Joint 0.

6.1 Conventions
JSON keys are snake_case. Timestamps are ISO-8601 UTC strings. part_no is an integer.
Hashes are lowercase 0x + 64 hex characters (a SHA-256, compatible with Solidity bytes32).
Errors use {"error": {"code": "SOME_CODE", "message": "Human readable"}} with a proper HTTP status.
CORS allows http://localhost:5173 on every service.
Bilingual text is always {"en": "...", "hi": "..."}.
Ports: core 8000, agent 8001, trust 8002, frontend 5173, chain 8545.
Enums

Name	Values
reason	ABSENT, SHIFTED, DEAD, DUPLICATE
detector	DELETION_RATE, REASON_DOMINANCE, GENDER_SKEW, AGE_SKEW, HOUSE_CLUSTER, DUPLICATE_ENTRY, DATA_QUALITY
severity	LOW, MEDIUM, HIGH
review.status	PENDING, ACCEPTED, REJECTED
citizen.status	PRESENT, REMOVED, ADDED, NOT_FOUND, AMBIGUOUS
verify.status	MATCH, MISMATCH, NOT_FOUND
gender	M, F, O
relation_type	FATHER, HUSBAND, MOTHER, OTHER
age bands	18-25, 26-35, 36-45, 46-60, 61-80, 80+
6.2 CSV schemas (synthetic rolls)
draft_roll.csv and final_roll.csv: epic_no, ac_no, part_no, serial_no, name, relative_name, relation_type, house_no, age, gender
asdd.csv: epic_no, part_no, reason, remark (remark may be empty)
Synthetic EPIC numbers always start with VGX (for example VGX1234567) so nobody mistakes them for real IDs.
6.3 Core API (Member A, :8000)
GET /api/health returns {"status": "ok", "audit_ready": true}

POST /api/audits (body {"use_synthetic": true} or multipart with draft, final, asdd files) returns 201 {"audit_id": "aud_001", "status": "READY"}

GET /api/audits returns {"items": [{"audit_id": "aud_001", "ac_name": "Demo Nagar (Synthetic)", "created_at": "..."}]}

GET /api/audits/{audit_id}/summary

{
  "audit_id": "aud_001",
  "ac_no": 999,
  "ac_name": "Demo Nagar (Synthetic)",
  "created_at": "2026-10-10T09:00:00Z",
  "snapshot_hashes": {"draft": "0x…64hex", "final": "0x…64hex", "asdd": "0x…64hex"},
  "totals": {"draft_count": 48210, "final_count": 46102, "removed": 2301, "added": 193,
             "modified": 57, "booths": 60, "flagged_booths": 6, "flags": 9, "pending_reviews": 9},
  "constituency_baseline": {"deletion_rate": 0.048, "deletion_rate_mad": 0.012},
  "reason_mix": {"ABSENT": 0.2, "SHIFTED": 0.4, "DEAD": 0.35, "DUPLICATE": 0.05}
}
GET /api/audits/{audit_id}/booths returns {"items": [BoothSummary…]} sorted by risk_score descending.

{
  "part_no": 17, "draft_count": 812, "final_count": 640, "removed": 182, "added": 10,
  "deletion_rate": 0.224,
  "reason_mix": {"ABSENT": 0.1, "SHIFTED": 0.82, "DEAD": 0.05, "DUPLICATE": 0.03},
  "female_removed_share": 0.71, "risk_score": 87, "flagged": true, "flag_count": 3
}
GET /api/audits/{audit_id}/booths/{part_no} returns a BoothSummary plus gender_removed ({"F": 129, "M": 53, "O": 0}), age_band_removed_share (age band to share), and flags: [Flag…].

GET /api/audits/{audit_id}/flags returns {"items": [Flag…]} (optional query: part_no, severity, detector).

Flag

{
  "flag_id": "f_17_1", "part_no": 17, "detector": "DELETION_RATE", "severity": "HIGH",
  "metric": {"name": "deletion_rate", "value": 0.224, "baseline": 0.048},
  "explanation": {"en": "…", "hi": "…"},
  "recommended_checks": [{"en": "…", "hi": "…"}],
  "explanation_source": "agent",
  "review": {"status": "PENDING", "note": null, "reviewed_at": null}
}
explanation_source is "agent" or "template".

PUT /api/audits/{audit_id}/flags/{flag_id}/review: body {"status": "ACCEPTED", "note": "Field check scheduled"} returns the updated Flag.

GET /api/audits/{audit_id}/export (used by the trust service to build the report)

{
  "audit_id": "aud_001", "ac_no": 999, "ac_name": "Demo Nagar (Synthetic)",
  "generated_at": "2026-10-10T10:00:00Z",
  "snapshot_hashes": {"draft": "0x…", "final": "0x…", "asdd": "0x…"},
  "summary": {"…": "same as summary.totals and constituency_baseline"},
  "flagged_booths": [{"booth": {"…BoothSummary…"}, "flags": ["…Flag…"]}],
  "methodology": {"version": "0.1", "detectors": ["DELETION_RATE", "…"], "thresholds": {"…": "…"}},
  "disclaimer": {"en": "Flags are prompts for field verification. They do not establish wrongdoing or eligibility.",
                 "hi": "…"}
}
POST /api/citizen/lookup

Request: {"name": "Sunita Devi", "relative_name": "Ramesh Kumar", "part_no": 17, "epic_no": null, "lang": "en"}. Either epic_no, or name + relative_name + part_no, is required.

{
  "status": "REMOVED",
  "match_confidence": 0.97,
  "record": {"epic_masked": "VGX****482", "part_no": 17, "name_display": "Sunita D.", "age_band": "26-35"},
  "reason": "SHIFTED",
  "next_step": {
    "title": {"en": "If this is incorrect, you can ask for your name to be restored", "hi": "…"},
    "steps": [{"en": "Contact your Booth Level Officer or visit the official ECI portal", "hi": "…"}],
    "deadline": "2026-10-31",
    "disclaimer": {"en": "Confirm current forms and deadlines on the official ECI website.", "hi": "…"}
  }
}
For NOT_FOUND and AMBIGUOUS, record, reason and next_step are null (AMBIGUOUS returns a message and never lists candidates).

6.4 Agent service (Member A, :8001)
GET /health returns {"status": "ok", "mode": "agent" | "mock"}

POST /explain

{
  "audit_id": "aud_001",
  "booth": {"…BoothSummary…": "…"},
  "flag": {"detector": "DELETION_RATE", "severity": "HIGH", "metric": {"name": "deletion_rate", "value": 0.224, "baseline": 0.048}},
  "baseline": {"deletion_rate": 0.048, "deletion_rate_mad": 0.012}
}
Success 200:

{
  "explanation": {"en": "…", "hi": "…"},
  "recommended_checks": [{"en": "…", "hi": "…"}],
  "neutrality": {"passed": true, "method": "blocklist+number_check+agent", "violations": []},
  "source": "agent"
}
Errors: 422 NEUTRALITY_FAILED (text failed the guard after retries) or 503 AGENT_UNAVAILABLE. The core API then uses its template fallback.

6.5 Trust service (Member B, :8002)
POST /api/reports: body {"audit_id": "aud_001", "reviewer_name": "R. Sharma", "supersedes": null} returns 201:

{
  "report_id": "VG-2026-0001",
  "report_hash": "0x…",
  "snapshot_hashes": {"draft": "0x…", "final": "0x…", "asdd": "0x…"},
  "tx_hash": "0x…", "block_number": 12, "recorded_at": "2026-10-10T10:05:00Z",
  "supersedes": null,
  "files": {"json": "/files/VG-2026-0001.json", "pdf": "/files/VG-2026-0001.pdf"}
}
GET /api/reports returns {"items": [{"report_id": "…", "recorded_at": "…", "report_hash": "0x…", "superseded_by": null}]}

GET /api/reports/{report_id} returns the same shape as the POST response plus superseded_by.

POST /api/reports/verify (multipart: file required, report_id optional; if missing, it is read from the file's JSON)

{
  "report_id": "VG-2026-0001", "status": "MISMATCH",
  "computed_hash": "0x…", "onchain_hash": "0x…",
  "recorded_at": "2026-10-10T10:05:00Z", "submitter": "0x…",
  "superseded_by": null
}
GET /api/chain/status returns {"connected": true, "chain_id": 31337, "contract_address": "0x…", "latest_block": 12}

GET /files/{report_id}.json and GET /files/{report_id}.pdf serve the saved files.

6.6 Smart contract interface (Member B, ReportRegistry)
recordReport(string reportId, bytes32 reportHash, bytes32 draftHash, bytes32 finalHash,
             bytes32 asddHash, string supersedesId)       // allow-listed submitters only
getReport(string reportId) view returns (Report)           // reverts if unknown
verifyReport(string reportId, bytes32 candidateHash) view returns (bool)
supersededBy(string reportId) view returns (string)        // "" if not superseded
addSubmitter(address) / removeSubmitter(address)           // owner only
event ReportRecorded(string indexed reportId, bytes32 reportHash, address submitter, uint64 timestamp)

Report { bytes32 reportHash; bytes32 draftHash; bytes32 finalHash; bytes32 asddHash;
         uint64 timestamp; address submitter; string supersedesId; }
Reports are immutable. Recording an existing reportId reverts. A non-empty supersedesId must reference an existing report, and it sets supersededBy[old] = new.

6.7 Report file and hashing rule
The report JSON has these top-level keys: schema_version, report_id, generated_at, reviewer, audit (the export payload), supersedes.
It is saved as canonical JSON: UTF-8, keys sorted, separators , and : with no spaces, ensure_ascii=false.
The saved file is the canonical form. report_hash is the SHA-256 of the file's exact bytes. Any edit, even a space, changes the hash.
Roll snapshot hashes are the SHA-256 of each CSV file's exact bytes.
The PDF is a human-readable copy. Its hash is stored off-chain only.