"""Pydantic schemas for Executive Fraud Analytics & Risk Command Center."""
from pydantic import BaseModel, Field


class ScannedDocumentsMetric(BaseModel):
    month_to_date: int = Field(..., description="Month-to-date document volume processed")
    monthly_limit: int = Field(..., description="Monthly document quota limit")
    quota_usage_percentage: float = Field(..., description="Percentage of monthly quota utilized")
    remaining_capacity: int = Field(..., description="Remaining document scans in active billing period")
    total_lifetime: int = Field(..., description="Total lifetime documents ingested across organization")
    days_until_renewal: int = Field(..., description="Days remaining until next billing cycle rollover")
    tier: str = Field(..., description="Active institutional subscription tier")


class TamperingDetectionMetric(BaseModel):
    rate_percentage: float = Field(..., description="Percentage of evaluated documents flagged as CRITICAL or HIGH")
    critical_count: int = Field(..., description="Total cases flagged as CRITICAL risk")
    high_count: int = Field(..., description="Total cases flagged as HIGH risk")
    elevated_count: int = Field(..., description="Total cases flagged as ELEVATED risk")
    moderate_count: int = Field(..., description="Total cases flagged as MODERATE risk")
    low_count: int = Field(..., description="Total cases flagged as LOW risk / clean")
    total_evaluated: int = Field(..., description="Total evaluated forensic dockets")
    risk_status: str = Field(..., description="Descriptive institutional risk posture label")


class FinancialExposureMetric(BaseModel):
    total_prevented_pkr: float = Field(..., description="Total rupee value of fraudulent balance inflations blocked")
    total_prevented_formatted: str = Field(..., description="Formatted rupee string with thousands separators")
    total_prevented_short: str = Field(..., description="Formatted Pakistani Lakh / Crore notation (e.g. PKR 4.825 Crore)")
    flagged_cases_count: int = Field(..., description="Number of cases with detected balance manipulation")
    average_inflation_pkr: float = Field(..., description="Average blocked inflation per flagged case")
    largest_single_inflation_pkr: float = Field(..., description="Highest single balance inflation intercepted")


class VerificationLatencyMetric(BaseModel):
    p50_ms: float = Field(..., description="Median processing latency in milliseconds")
    p95_ms: float = Field(..., description="95th percentile processing latency in milliseconds")
    p50_formatted: str = Field(..., description="Formatted p50 latency string (e.g. 580 ms)")
    p95_formatted: str = Field(..., description="Formatted p95 latency string (e.g. 2.1 s)")
    deterministic_p50_ms: float = Field(..., description="Median latency for deterministic zero-tolerance stages")
    deterministic_formatted: str = Field(..., description="Formatted deterministic latency string")
    multi_page_ocr_p95_ms: float = Field(..., description="95th percentile latency for OCR & computer vision stages")
    multi_page_ocr_formatted: str = Field(..., description="Formatted OCR/Vision latency string")
    stage_latencies: dict[str, float] = Field(default_factory=dict, description="Median latency per forensic pipeline stage in ms")


class CriticalAlertItem(BaseModel):
    id: str = Field(..., description="Investigation ID")
    case_number: str = Field(..., description="Human-readable case identifier")
    title: str = Field(..., description="Investigation title")
    document_type: str = Field(default="BANK_STATEMENT", description="Classified document type")
    risk_score: int | None = Field(default=None, description="Calibrated risk score (0-100)")
    risk_tier: str = Field(..., description="Risk tier classification")
    action_directive: str = Field(..., description="Recommended enforcement directive")
    prevented_rupees: float | None = Field(default=None, description="Blocked discrepancy amount in PKR if applicable")
    prevented_rupees_formatted: str | None = Field(default=None, description="Formatted rupee amount")
    client_reference: str | None = Field(default=None, description="Client or loan application reference")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")


class DashboardStatsResponse(BaseModel):
    organization_id: str
    organization_name: str
    tenant_slug: str
    total_scanned: ScannedDocumentsMetric
    tampering_detection: TamperingDetectionMetric
    financial_exposure: FinancialExposureMetric
    verification_latency: VerificationLatencyMetric
    recent_critical_alerts: list[CriticalAlertItem]
    document_type_distribution: dict[str, int]
    generated_at: str
