"""Deterministic volunteer <-> opportunity scoring.

score = w_skills*skills + w_interests*interests + w_location*location + w_availability*availability

* skills / interests: Jaccard similarity of lower-cased sets (|A∩B| / |A∪B|). 0 if either side is empty.
* location: locations are written "City" or "City, Region". Same city -> 1.0, same region -> 0.5, else 0.
* availability: share of the opportunity's required days the volunteer can cover (|A∩B| / |B|).
  0 if the opportunity names no days.
Weights come from settings and must sum to 1.
"""
from dataclasses import dataclass, field

from app.core.config import get_settings


@dataclass(frozen=True)
class Weights:
    skills: float
    interests: float
    location: float
    availability: float

    @classmethod
    def from_settings(cls) -> "Weights":
        s = get_settings()
        return cls(
            s.matching_skills_weight,
            s.matching_interest_weight,
            s.matching_location_weight,
            s.matching_availability_weight,
        )


@dataclass(frozen=True)
class VolunteerProfile:
    skills: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    availability: list[str] = field(default_factory=list)
    location: str | None = None


@dataclass(frozen=True)
class OpportunityProfile:
    id: int
    required_skills: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    availability: list[str] = field(default_factory=list)
    location: str | None = None


@dataclass(frozen=True)
class MatchResult:
    opportunity_id: int
    score: float
    percentage: int
    breakdown: dict[str, float]
    reasons: list[str]


def _norm_set(values) -> set[str]:
    return {str(v).strip().lower() for v in (values or []) if str(v).strip()}


def jaccard(a, b) -> float:
    sa, sb = _norm_set(a), _norm_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def availability_overlap(volunteer_days, required_days) -> float:
    need = _norm_set(required_days)
    if not need:
        return 0.0
    return len(_norm_set(volunteer_days) & need) / len(need)


def _parts(location: str | None) -> list[str]:
    return [p.strip().lower() for p in (location or "").split(",") if p.strip()]


def location_match(volunteer_location: str | None, opportunity_location: str | None) -> float:
    v, o = _parts(volunteer_location), _parts(opportunity_location)
    if not v or not o:
        return 0.0
    if v[0] == o[0]:
        return 1.0
    if len(v) > 1 and len(o) > 1 and v[-1] == o[-1]:
        return 0.5
    return 0.0


def score_opportunity(
    volunteer: VolunteerProfile, opportunity: OpportunityProfile, weights: Weights | None = None
) -> MatchResult:
    w = weights or Weights.from_settings()
    parts = {
        "skills": jaccard(volunteer.skills, opportunity.required_skills),
        "interests": jaccard(volunteer.interests, opportunity.interests),
        "location": location_match(volunteer.location, opportunity.location),
        "availability": availability_overlap(volunteer.availability, opportunity.availability),
    }
    score = (
        w.skills * parts["skills"]
        + w.interests * parts["interests"]
        + w.location * parts["location"]
        + w.availability * parts["availability"]
    )
    score = round(min(max(score, 0.0), 1.0), 4)

    reasons = []
    shared_skills = sorted(_norm_set(volunteer.skills) & _norm_set(opportunity.required_skills))
    if shared_skills:
        reasons.append("Matching skills: " + ", ".join(shared_skills))
    shared_interests = sorted(_norm_set(volunteer.interests) & _norm_set(opportunity.interests))
    if shared_interests:
        reasons.append("Shared interests: " + ", ".join(shared_interests))
    if parts["location"] == 1.0:
        reasons.append("Same city")
    elif parts["location"] == 0.5:
        reasons.append("Same region")
    shared_days = sorted(_norm_set(volunteer.availability) & _norm_set(opportunity.availability))
    if shared_days:
        reasons.append("Available on: " + ", ".join(d.upper() for d in shared_days))
    if not reasons:
        reasons.append("No overlap with your profile yet")

    return MatchResult(
        opportunity_id=opportunity.id,
        score=score,
        percentage=round(score * 100),
        breakdown={k: round(v, 4) for k, v in parts.items()},
        reasons=reasons,
    )


def rank_opportunities(
    volunteer: VolunteerProfile,
    opportunities: list[OpportunityProfile],
    weights: Weights | None = None,
) -> list[MatchResult]:
    """Best first; ties broken by lowest opportunity id so ordering is stable."""
    results = [score_opportunity(volunteer, o, weights) for o in opportunities]
    return sorted(results, key=lambda r: (-r.score, r.opportunity_id))
