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


class ApplicationStatus(enum.StrEnum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TaskStatus(enum.StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"


class DonationType(enum.StrEnum):
    MONEY = "MONEY"
    FOOD = "FOOD"
    CLOTHES = "CLOTHES"
    MEDICINE = "MEDICINE"
    EDUCATIONAL = "EDUCATIONAL"
    OTHER = "OTHER"


class DonationStatus(enum.StrEnum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    REJECTED = "REJECTED"


class SupportStatus(enum.StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
