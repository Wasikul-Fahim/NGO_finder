from app.models import AuditLog
from app.tests.conftest import login, make_ngo_admin

API = "/api/v1"
OPP = {
    "title": "Teaching assistant",
    "description": "Help kids with maths",
    "location": "Dhaka, Dhaka",
    "required_skills": ["Teaching", " teaching ", "Maths"],
    "interests": ["Education"],
    "availability": ["sat", "SUN"],
}


def create(client, headers, **kw):
    r = client.post(f"{API}/opportunities", json={**OPP, **kw}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_normalises_and_audits(client, db, ngo_headers):
    o = create(client, ngo_headers)
    assert o["required_skills"] == ["Teaching", "Maths"]  # deduped, trimmed
    assert o["availability"] == ["SAT", "SUN"]
    assert o["is_active"] and o["ngo_name"] == "Helping Hands"
    assert db.query(AuditLog).filter_by(action_type="CREATE_OPPORTUNITY").count() == 1


def test_bad_day_rejected(client, ngo_headers):
    r = client.post(f"{API}/opportunities", json={**OPP, "availability": ["FUNDAY"]}, headers=ngo_headers)
    assert r.status_code == 422


def test_roles_enforced(client, volunteer_headers, db):
    assert client.post(f"{API}/opportunities", json=OPP, headers=volunteer_headers).status_code == 403
    assert client.post(f"{API}/opportunities", json=OPP).status_code == 401
    make_ngo_admin(db, "pending@example.com", verified=False)
    pending = login(client, "pending@example.com")
    assert client.post(f"{API}/opportunities", json=OPP, headers=pending).status_code == 403


def test_campaign_must_be_own(client, ngo_headers, other_ngo_headers):
    cid = client.post(f"{API}/campaigns", json={"title": "C", "start_date": "2026-01-01",
                                                "end_date": "2026-02-01"}, headers=ngo_headers).json()["id"]
    r = client.post(f"{API}/opportunities", json={**OPP, "campaign_id": cid}, headers=other_ngo_headers)
    assert r.status_code == 422 and "campaign_id" in r.json()["error"]["fields"]
    o = create(client, ngo_headers, campaign_id=cid)
    assert o["campaign_title"] == "C"


def test_browse_search_filter_sort(client, ngo_headers):
    create(client, ngo_headers, title="Zebra helper", location="Sylhet", required_skills=["Cooking"])
    create(client, ngo_headers, title="Alpha teacher", location="Dhaka")
    assert client.get(f"{API}/opportunities").json()["total"] == 2
    assert client.get(f"{API}/opportunities?q=zebra").json()["total"] == 1
    assert client.get(f"{API}/opportunities?location=sylhet").json()["total"] == 1
    assert client.get(f"{API}/opportunities?skill=cooking").json()["total"] == 1
    assert client.get(f"{API}/opportunities?skill=nothing").json()["total"] == 0
    titles = [o["title"] for o in client.get(f"{API}/opportunities?sort=title").json()["items"]]
    assert titles == ["Alpha teacher", "Zebra helper"]
    assert client.get(f"{API}/opportunities?sort=bogus").status_code == 422


def test_inactive_and_unverified_hidden_from_public(client, db, ngo_headers, other_ngo_headers):
    o = create(client, ngo_headers)
    assert client.delete(f"{API}/opportunities/{o['id']}", headers=ngo_headers).status_code == 200
    assert client.get(f"{API}/opportunities").json()["total"] == 0
    assert client.get(f"{API}/opportunities/{o['id']}").status_code == 404
    assert client.get(f"{API}/opportunities/{o['id']}", headers=other_ngo_headers).status_code == 404
    assert client.get(f"{API}/opportunities/{o['id']}", headers=ngo_headers).status_code == 200
    assert client.get(f"{API}/opportunities?mine=true", headers=ngo_headers).json()["total"] == 1
    assert client.delete(f"{API}/opportunities/{o['id']}", headers=ngo_headers).status_code == 409
    # Unverified NGO's postings are invisible to the public.
    make_ngo_admin(db, "pending@example.com", verified=False, ngo_name="Pending")
    from app.models import NGO, Opportunity, VerificationStatus
    pend = db.query(NGO).filter_by(ngo_name="Pending").one()
    db.add(Opportunity(ngo_id=pend.id, title="Hidden", required_skills=[], interests=[], availability=[]))
    db.commit()
    assert client.get(f"{API}/opportunities?q=Hidden").json()["total"] == 0
    assert pend.verification_status == VerificationStatus.PENDING


def test_cannot_edit_other_ngos(client, ngo_headers, other_ngo_headers):
    o = create(client, ngo_headers)
    url = f"{API}/opportunities/{o['id']}"
    assert client.patch(url, json={"title": "x"}, headers=other_ngo_headers).status_code == 403
    assert client.delete(url, headers=other_ngo_headers).status_code == 403
    r = client.patch(url, json={"title": "Renamed", "is_active": False}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["title"] == "Renamed" and not r.json()["is_active"]
    assert client.patch(url, json={"ngo_id": 3}, headers=ngo_headers).status_code == 422
    assert client.patch(url, json={"title": None}, headers=ngo_headers).status_code == 422


def test_volunteer_profile_roundtrip(client, volunteer_headers):
    r = client.get(f"{API}/volunteers/me", headers=volunteer_headers)
    assert r.status_code == 200 and r.json()["skills"] == []
    r = client.patch(f"{API}/volunteers/me", headers=volunteer_headers, json={
        "skills": ["Teaching", "teaching"], "interests": ["Education"], "availability": ["sat"],
        "experience": "2 years", "location": "Dhaka, Dhaka"})
    body = r.json()
    assert r.status_code == 200 and body["skills"] == ["Teaching"] and body["availability"] == ["SAT"]
    assert body["location"] == "Dhaka, Dhaka" and body["experience"] == "2 years"
    assert client.patch(f"{API}/volunteers/me", json={"role": "x"}, headers=volunteer_headers).status_code == 422


def test_volunteer_profile_volunteers_only(client, ngo_headers):
    assert client.get(f"{API}/volunteers/me", headers=ngo_headers).status_code == 403


def test_recommended_ranks_and_explains(client, ngo_headers, volunteer_headers):
    client.patch(f"{API}/volunteers/me", headers=volunteer_headers, json={
        "skills": ["Teaching"], "interests": ["Education"], "availability": ["SAT"], "location": "Dhaka, Dhaka"})
    create(client, ngo_headers, title="Weak", required_skills=["Driving"], interests=[],
           location="Sylhet", availability=["MON"])
    best = create(client, ngo_headers, title="Best", required_skills=["Teaching"], interests=["Education"],
                  location="Dhaka, Dhaka", availability=["SAT"])
    r = client.get(f"{API}/opportunities/recommended", headers=volunteer_headers)
    assert r.status_code == 200
    items = r.json()
    assert [i["opportunity"]["title"] for i in items] == ["Best", "Weak"]
    assert items[0]["match"]["percentage"] == 100 and items[0]["match"]["reasons"]
    assert items[1]["match"]["percentage"] == 0
    assert items[0]["has_applied"] is False
    client.post(f"{API}/opportunities/{best['id']}/applications", headers=volunteer_headers)
    assert client.get(f"{API}/opportunities/recommended", headers=volunteer_headers).json()[0]["has_applied"]
    assert client.get(f"{API}/opportunities/recommended?limit=1", headers=volunteer_headers).json().__len__() == 1


def test_recommended_excludes_inactive(client, ngo_headers, volunteer_headers):
    o = create(client, ngo_headers)
    client.delete(f"{API}/opportunities/{o['id']}", headers=ngo_headers)
    assert client.get(f"{API}/opportunities/recommended", headers=volunteer_headers).json() == []


def test_recommended_volunteers_only(client, ngo_headers):
    assert client.get(f"{API}/opportunities/recommended", headers=ngo_headers).status_code == 403
    assert client.get(f"{API}/opportunities/recommended").status_code == 401
