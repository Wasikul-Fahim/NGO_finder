import enum


class Role(enum.StrEnum):
    NGO_ADMIN = "NGO_ADMIN"
    VOLUNTEER = "VOLUNTEER"
    DONOR = "DONOR"
    BENEFICIARY = "BENEFICIARY"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"


PUBLIC_ROLES = (Role.VOLUNTEER, Role.DONOR, Role.BENEFICIARY)


class VerificationStatus(enum.StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class CampaignStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class BeneficiaryStatus(enum.StrEnum):
    PENDING = "PENDING"
    ASSISTED = "ASSISTED"
    CLOSED = "CLOSED"
