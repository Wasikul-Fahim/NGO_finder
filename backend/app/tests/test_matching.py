import pytest

from app.services.matching import (
    OpportunityProfile,
    VolunteerProfile,
    Weights,
    availability_overlap,
    jaccard,
    location_match,
    rank_opportunities,
    score_opportunity,
)

W = Weights(0.45, 0.20, 0.20, 0.15)

VOL = VolunteerProfile(
    skills=["Teaching", "First Aid"], interests=["Education"], availability=["SAT", "SUN"],
    location="Dhaka, Dhaka",
)


def opp(id, **kw):
    return OpportunityProfile(id=id, **kw)


def test_jaccard_basics():
    assert jaccard(["a", "b"], ["B", "c"]) == pytest.approx(1 / 3)  # case-insensitive
    assert jaccard(["a"], ["a"]) == 1.0
    assert jaccard(["a"], ["b"]) == 0.0
    assert jaccard([], ["a"]) == 0.0 and jaccard([], []) == 0.0


def test_location_exact_partial_none():
    assert location_match("Dhaka", "dhaka") == 1.0
    assert location_match("Dhaka, Dhaka", "Dhaka, Dhaka") == 1.0
    assert location_match("Savar, Dhaka", "Gazipur, Dhaka") == 0.5  # same region
    assert location_match("Sylhet, Sylhet", "Dhaka, Dhaka") == 0.0
    assert location_match("Dhaka", "Gazipur, Dhaka") == 0.0  # no region info on one side
    assert location_match(None, "Dhaka") == 0.0 and location_match("Dhaka", "") == 0.0


def test_availability_overlap():
    assert availability_overlap(["SAT", "SUN"], ["SAT"]) == 1.0
    assert availability_overlap(["SAT"], ["SAT", "SUN"]) == 0.5
    assert availability_overlap(["MON"], ["SAT"]) == 0.0
    assert availability_overlap(["SAT"], []) == 0.0


def test_perfect_match_scores_one():
    o = opp(1, required_skills=["teaching", "first aid"], interests=["education"],
            availability=["SAT", "SUN"], location="Dhaka, Dhaka")
    r = score_opportunity(VOL, o, W)
    assert r.score == 1.0 and r.percentage == 100
    assert r.breakdown == {"skills": 1.0, "interests": 1.0, "location": 1.0, "availability": 1.0}


def test_no_overlap_scores_zero_with_reason():
    r = score_opportunity(VOL, opp(1, required_skills=["driving"], location="Sylhet, Sylhet",
                                   availability=["MON"]), W)
    assert r.score == 0.0 and r.reasons == ["No overlap with your profile yet"]


def test_weights_applied():
    only_skills = opp(1, required_skills=["Teaching", "First Aid"])
    assert score_opportunity(VOL, only_skills, W).score == 0.45
    only_loc = opp(2, location="Dhaka, Dhaka")
    assert score_opportunity(VOL, only_loc, W).score == 0.2
    half_loc = opp(3, location="Savar, Dhaka")
    assert score_opportunity(VOL, half_loc, W).score == 0.1
    only_avail = opp(4, availability=["SAT", "SUN"])
    assert score_opportunity(VOL, only_avail, W).score == 0.15


def test_empty_profile_scores_zero():
    r = score_opportunity(VolunteerProfile(), opp(1, required_skills=["x"], location="Dhaka"), W)
    assert r.score == 0.0


def test_ranking_descending_and_explained():
    strong = opp(1, required_skills=["Teaching"], interests=["Education"], location="Dhaka, Dhaka")
    medium = opp(2, required_skills=["Teaching", "Cooking"])
    weak = opp(3, required_skills=["Driving"])
    ranked = rank_opportunities(VOL, [weak, medium, strong], W)
    assert [r.opportunity_id for r in ranked] == [1, 2, 3]
    assert ranked[0].score > ranked[1].score > ranked[2].score
    assert any("Teaching".lower() in reason.lower() for reason in ranked[0].reasons)


def test_ties_break_by_id():
    a, b, c = opp(7, location="Dhaka, Dhaka"), opp(3, location="Dhaka, Dhaka"), opp(5, location="Dhaka, Dhaka")
    assert [r.opportunity_id for r in rank_opportunities(VOL, [a, b, c], W)] == [3, 5, 7]


def test_ranking_is_deterministic():
    opps = [opp(i, required_skills=["Teaching"] if i % 2 else []) for i in range(1, 8)]
    first = rank_opportunities(VOL, opps, W)
    assert first == rank_opportunities(VOL, list(reversed(opps)), W)
