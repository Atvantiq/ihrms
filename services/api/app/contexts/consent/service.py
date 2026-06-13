"""DPDP consent purposes — the catalogue of what we ask consent for.

Each purpose is specific and separately consentable/withdrawable, as the DPDP
Act requires. `version` lets us re-request consent when a purpose's notice
changes. Pure data; no DB.
"""

from pydantic import BaseModel


class ConsentPurpose(BaseModel):
    key: str
    label: str
    description: str
    version: int
    required: bool  # processing genuinely needed for employment vs optional


# The current consent catalogue (FY25-26). Bump `version` to re-request.
PURPOSES: list[ConsentPurpose] = [
    ConsentPurpose(
        key="data_processing",
        label="HR data processing",
        description="Store and process my personal data to administer my employment.",
        version=1,
        required=True,
    ),
    ConsentPurpose(
        key="payroll_banking",
        label="Payroll & statutory",
        description="Process my bank, PAN and Aadhaar details for salary and statutory filings.",
        version=1,
        required=True,
    ),
    ConsentPurpose(
        key="background_verification",
        label="Background verification",
        description="Conduct background and reference checks where applicable.",
        version=1,
        required=False,
    ),
    ConsentPurpose(
        key="communications",
        label="HR communications",
        description="Send me HR notices, surveys and announcements.",
        version=1,
        required=False,
    ),
]

PURPOSE_KEYS = frozenset(p.key for p in PURPOSES)


def purpose(key: str) -> ConsentPurpose | None:
    return next((p for p in PURPOSES if p.key == key), None)
