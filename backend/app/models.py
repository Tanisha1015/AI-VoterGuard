"""Pydantic response/request models that mirror contracts/CONTRACT.md section 6.3 field for field."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, SerializerFunctionWrapHandler, model_serializer

Severity = Literal["LOW", "MEDIUM", "HIGH"]
DetectorName = Literal[
    "DELETION_RATE", "REASON_DOMINANCE", "GENDER_SKEW", "AGE_SKEW",
    "HOUSE_CLUSTER", "DUPLICATE_ENTRY", "DATA_QUALITY",
]
ReviewStatus = Literal["PENDING", "ACCEPTED", "REJECTED"]
ExplanationSource = Literal["agent", "template"]
CitizenStatus = Literal["PRESENT", "REMOVED", "ADDED", "NOT_FOUND", "AMBIGUOUS"]
Reason = Literal["ABSENT", "SHIFTED", "DEAD", "DUPLICATE"]


class Bilingual(BaseModel):
    """Text in both languages: {"en": ..., "hi": ...}."""

    en: str
    hi: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorBody(BaseModel):
    """Standard error body (documented in OpenAPI for the 404/422 responses)."""

    error: ErrorDetail


class Health(BaseModel):
    status: str
    audit_ready: bool


# ------------------------------------------------------------------ flags and booths


class Metric(BaseModel):
    name: str
    value: float
    baseline: float


class Review(BaseModel):
    status: ReviewStatus
    note: Optional[str] = None
    reviewed_at: Optional[str] = None


class Flag(BaseModel):
    flag_id: str
    part_no: int
    detector: DetectorName
    severity: Severity
    metric: Metric
    explanation: Bilingual
    recommended_checks: list[Bilingual]
    explanation_source: ExplanationSource
    review: Review


class ReviewRequest(BaseModel):
    """Body of PUT /api/audits/{audit_id}/flags/{flag_id}/review."""

    status: ReviewStatus
    note: Optional[str] = Field(default=None, max_length=500)


class BoothSummary(BaseModel):
    part_no: int
    draft_count: int
    final_count: int
    removed: int
    added: int
    deletion_rate: float
    reason_mix: dict[str, float]
    female_removed_share: float
    risk_score: int
    flagged: bool
    flag_count: int


class BoothDetail(BoothSummary):
    gender_removed: dict[str, int]
    age_band_removed_share: dict[str, float]
    flags: list[Flag]


class BoothList(BaseModel):
    items: list[BoothSummary]


class FlagList(BaseModel):
    items: list[Flag]


# ------------------------------------------------------------------ audits


class SnapshotHashes(BaseModel):
    draft: str
    final: str
    asdd: str


class Totals(BaseModel):
    draft_count: int
    final_count: int
    removed: int
    added: int
    modified: int
    booths: int
    flagged_booths: int
    flags: int
    pending_reviews: int


class Baseline(BaseModel):
    deletion_rate: float
    deletion_rate_mad: float


class AuditSummary(BaseModel):
    audit_id: str
    ac_no: int
    ac_name: str
    created_at: str
    snapshot_hashes: SnapshotHashes
    totals: Totals
    constituency_baseline: Baseline
    reason_mix: dict[str, float]


class CreateAuditRequest(BaseModel):
    """JSON body of POST /api/audits (the alternative is a multipart upload of three CSV files)."""

    use_synthetic: bool = True


class AuditCreated(BaseModel):
    audit_id: str
    status: Literal["READY"]


class AuditListItem(BaseModel):
    audit_id: str
    ac_name: str
    created_at: str


class AuditList(BaseModel):
    items: list[AuditListItem]


# ------------------------------------------------------------------ export


class ExportSummary(BaseModel):
    totals: Totals
    constituency_baseline: Baseline


class FlaggedBooth(BaseModel):
    booth: BoothSummary
    flags: list[Flag]


class Methodology(BaseModel):
    version: str
    detectors: list[str]
    thresholds: dict[str, Any]


class AuditExport(BaseModel):
    audit_id: str
    ac_no: int
    ac_name: str
    generated_at: str
    snapshot_hashes: SnapshotHashes
    summary: ExportSummary
    flagged_booths: list[FlaggedBooth]
    methodology: Methodology
    disclaimer: Bilingual


# ------------------------------------------------------------------ citizen lookup


class CitizenRequest(BaseModel):
    """Either epic_no, or name + relative_name + part_no, is required (checked in the service)."""

    name: Optional[str] = Field(default=None, max_length=120)
    relative_name: Optional[str] = Field(default=None, max_length=120)
    part_no: Optional[int] = None
    epic_no: Optional[str] = Field(default=None, max_length=32)
    lang: Literal["en", "hi"] = "en"


class CitizenRecord(BaseModel):
    epic_masked: str
    part_no: int
    name_display: str
    age_band: Optional[str] = None


class NextStep(BaseModel):
    title: Bilingual
    steps: list[Bilingual]
    deadline: Optional[str] = None
    disclaimer: Bilingual


class CitizenResponse(BaseModel):
    status: CitizenStatus
    match_confidence: float
    record: Optional[CitizenRecord] = None
    reason: Optional[Reason] = None
    next_step: Optional[NextStep] = None
    message: Optional[Bilingual] = None  # only for AMBIGUOUS

    @model_serializer(mode="wrap")
    def _omit_empty_message(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """The contract only has ``message`` on AMBIGUOUS responses, so leave it out otherwise."""
        data: dict[str, Any] = handler(self)
        if data.get("message") is None:
            data.pop("message", None)
        return data
