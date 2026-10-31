from app.models import NGO, AuditLog, VerificationStatus
from app.tests.conftest import login, make_ngo_admin

API = "/api/v1"


def test_get_and_update_my_ngo(client, db, ngo_headers):
    assert client.get(f"{API}/ngos/me", headers=ngo_headers).json()["ngo_name"] == "Helping Hands"
    r = client.patch(f"{API}/ngos/me", json={"description": "We help", "contact": "01700"}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["description"] == "We help"
    assert db.query(AuditLog).filter_by(action_type="UPDATE_NGO").count() == 1


def test_ngo_cannot_self_verify(client, db):
    make_ngo_admin(db, "p@example.com", verified=False)
    headers = login(client, "p@example.com")
    r = client.patch(f"{API}/ngos/me", json={"verification_status": "VERIFIED"}, headers=headers)
    assert r.status_code == 422
    assert db.query(NGO).one().verification_status == VerificationStatus.PENDING


def test_list_ngos_hides_unverified_from_non_platform(client, db, volunteer_headers, platform_headers):
    make_ngo_admin(db, "v@example.com", ngo_name="Verified NGO")
    make_ngo_admin(db, "p@example.com", verified=False, ngo_name="Pending NGO")
    assert client.get(f"{API}/ngos").status_code == 401
    seen = client.get(f"{API}/ngos", headers=volunteer_headers).json()
    assert [n["ngo_name"] for n in seen["items"]] == ["Verified NGO"]
    all_ = client.get(f"{API}/ngos", headers=platform_headers).json()
    assert all_["total"] == 2
    pending = client.get(f"{API}/ngos?status=PENDING", headers=platform_headers).json()
    assert [n["ngo_name"] for n in pending["items"]] == ["Pending NGO"]


def test_verify_ngo(client, db, platform_headers, volunteer_headers):
    make_ngo_admin(db, "p@example.com", verified=False)
    ngo_id = db.query(NGO).one().id
    url = f"{API}/ngos/{ngo_id}/verify"
    assert client.patch(url, json={"status": "VERIFIED"}, headers=volunteer_headers).status_code == 403
    r = client.patch(url, json={"status": "VERIFIED"}, headers=platform_headers)
    assert r.status_code == 200 and r.json()["verification_status"] == "VERIFIED"
    assert client.patch(url, json={"status": "VERIFIED"}, headers=platform_headers).status_code == 409
    assert client.patch(url, json={"status": "PENDING"}, headers=platform_headers).status_code == 422
    log = db.query(AuditLog).filter_by(action_type="VERIFY_NGO").one()
    assert log.details["to"] == "VERIFIED"
    # Now the NGO admin can write.
    headers = login(client, "p@example.com")
    r = client.post(f"{API}/campaigns", json={"title": "T", "start_date": "2026-01-01",
                                              "end_date": "2026-01-02"}, headers=headers)
    assert r.status_code == 201


def test_verify_unknown_ngo(client, platform_headers):
    assert client.patch(f"{API}/ngos/99/verify", json={"status": "VERIFIED"},
                        headers=platform_headers).status_code == 404
