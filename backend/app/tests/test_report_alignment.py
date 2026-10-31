"""Endpoints and rules taken from the project report (docs/CSE314_Report_Overleaf.pdf), chapter 6."""
import io
from datetime import date, timedelta

import pytest

from app.models import NGO, AuditLog, Campaign, Resource
from app.tests.conftest import PASSWORD, login, make_ngo_admin, make_user
from app.tests.test_finance import active_campaign, add_resource, donate, enroll, set_status
from app.tests.test_workflow import accept, apply, make_task, post_opp, vol_id

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32


def inbox(client, headers, **p):
    return client.get(f"{API}/notifications", params=p, headers=headers).json()


def mk_campaign(client, headers, activate=True, **kw):
    body = {"title": "Drive", "start_date": str(date.today() - timedelta(days=30)),
            "end_date": str(date.today() + timedelta(days=60)), **kw}
    cid = client.post(f"{API}/campaigns", json=body, headers=headers).json()["id"]
    if activate:
        client.post(f"{API}/campaigns/{cid}/status", json={"status": "ACTIVE"}, headers=headers)
    return cid


def mk_event(client, headers, cid, days=10, name="Event"):
    r = client.post(f"{API}/events", headers=headers, json={
        "campaign_id": cid, "event_name": name, "event_date": str(date.today() + timedelta(days=days))})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ===================================================== mobile number (report 6.2.1, 5.1.2)

def test_register_stores_a_normalised_mobile_number(client, db):
    body = {"name": "A", "email": "a@example.com", "password": PASSWORD, "confirm_password": PASSWORD,
            "role": "VOLUNTEER", "phone": " +880 1712-345678 "}
    r = client.post(f"{API}/auth/register", json=body)
    assert r.status_code == 201 and r.json()["phone"] == "+8801712345678"


@pytest.mark.parametrize("bad", ["abc", "12", "0171-xyz", "+" + "1" * 20])
def test_invalid_mobile_numbers_are_rejected_everywhere(client, volunteer_headers, bad):
    reg = {"name": "A", "email": "b@example.com", "password": PASSWORD, "confirm_password": PASSWORD,
           "role": "DONOR", "phone": bad}
    assert client.post(f"{API}/auth/register", json=reg).status_code == 422
    assert client.patch(f"{API}/auth/me", json={"phone": bad}, headers=volunteer_headers).status_code == 422
    r = client.patch(f"{API}/volunteers/me", json={"phone": bad}, headers=volunteer_headers)
    assert r.status_code == 422 and "phone" in r.json()["error"]["fields"]


def test_volunteer_adds_mobile_number_to_profile_and_completeness_follows(client, db):
    make_user(db, "new@example.com", phone=None)
    h = login(client, "new@example.com")
    p = client.get(f"{API}/volunteers/me", headers=h).json()
    assert p["phone"] is None and p["profile_complete"] is False
    r = client.patch(f"{API}/volunteers/me", headers=h, json={"phone": "01712345678", "location": "Dhaka, Dhaka"})
    assert r.json()["phone"] == "01712345678" and r.json()["profile_complete"] is False  # no skills yet
    r = client.put(f"{API}/volunteers/me", headers=h, json={"skills": ["Teaching"]})
    assert r.json()["profile_complete"] is True
    assert client.get(f"{API}/auth/me", headers=h).json()["phone"] == "01712345678"


def test_applying_requires_a_mobile_number(client, db, ngo_headers):
    make_user(db, "nophone@example.com", phone=None)
    h = login(client, "nophone@example.com")
    oid = post_opp(client, ngo_headers)
    r = apply(client, h, oid)
    assert r.status_code == 409 and r.json()["error"]["code"] == "PROFILE_INCOMPLETE"
    assert "mobile number" in r.json()["error"]["message"]
    client.patch(f"{API}/volunteers/me", json={"phone": "01800000000"}, headers=h)
    assert apply(client, h, oid).status_code == 201


# ====================================================== report-style paths and methods

def test_api_prefix_without_version_serves_the_documented_paths(client, db):
    body = {"name": "A", "email": "c@example.com", "password": PASSWORD, "confirm_password": PASSWORD,
            "role": "VOLUNTEER"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    r = client.post("/api/auth/login", json={"email": "c@example.com", "password": PASSWORD})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post("/api/auth/refresh").status_code == 200  # the cookie is sent to /api/auth/*
    assert client.get("/api/users/profile", headers=h).json()["email"] == "c@example.com"
    assert client.get("/api/matching/opportunities", headers=h).status_code == 200
    assert client.get("/api/campaigns").status_code == 200


def test_users_profile_get_and_update(client, volunteer_headers):
    assert client.get(f"{API}/users/profile", headers=volunteer_headers).json()["email"] == "vol@example.com"
    for method in (client.put, client.patch):
        r = method(f"{API}/users/profile/update", json={"name": "Renamed"}, headers=volunteer_headers)
        assert r.status_code == 200 and r.json()["name"] == "Renamed"
    assert client.get(f"{API}/users/profile").status_code == 401


def test_matching_endpoint_matches_recommended(client, ngo_headers, volunteer_headers):
    post_opp(client, ngo_headers)
    a = client.get(f"{API}/matching/opportunities", headers=volunteer_headers).json()
    b = client.get(f"{API}/opportunities/recommended", headers=volunteer_headers).json()
    assert a == b and len(a) == 1


def test_submit_application_and_status_aliases(client, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    r = client.post(f"{API}/applications", json={"opportunity_id": oid}, headers=volunteer_headers)
    assert r.status_code == 201 and r.json()["status"] == "SUBMITTED"
    assert client.post(f"{API}/applications", json={"opportunity_id": oid}, headers=volunteer_headers).status_code == 409
    assert client.post(f"{API}/applications", json={}, headers=volunteer_headers).status_code == 422
    aid = r.json()["id"]
    r = client.patch(f"{API}/applications/{aid}/status", json={"status": "UNDER_REVIEW"}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["status"] == "UNDER_REVIEW"


def test_participations_alias(client, ngo_headers, volunteer_headers):
    from app.tests.test_impact import make_event, record  # noqa: F401

    cid = mk_campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    past = client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": cid, "event_name": "Done", "event_date": str(date.today() - timedelta(days=2))}).json()["id"]
    r = client.post(f"{API}/participations", headers=ngo_headers, json={
        "event_id": past, "volunteer_id": vol_id(client, volunteer_headers), "hours": 2})
    assert r.status_code == 201
    assert client.get(f"{API}/participations", headers=ngo_headers).json()["total"] == 1
    pid = r.json()["id"]
    assert client.patch(f"{API}/participations/{pid}", json={"hours": 3}, headers=ngo_headers).json()["hours"] == 3


def test_tasks_list_is_role_aware(client, ngo_headers, volunteer_headers, volunteer2_headers, platform_headers,
                                  donor_headers):
    cid = mk_campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    make_task(client, ngo_headers, cid, volunteer_id=vol_id(client, volunteer_headers), task_name="Mine")
    make_task(client, ngo_headers, cid, task_name="Unassigned")
    names = lambda h: sorted(t["task_name"] for t in client.get(f"{API}/tasks", headers=h).json()["items"])
    assert names(volunteer_headers) == ["Mine"]
    assert names(volunteer2_headers) == []
    assert names(ngo_headers) == ["Mine", "Unassigned"]
    assert names(platform_headers) == ["Mine", "Unassigned"]
    assert client.get(f"{API}/tasks", headers=donor_headers).status_code == 403


def test_notifications_post_creates_an_announcement(client, ngo_headers, volunteer_headers):
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    r = client.post(f"{API}/notifications", headers=ngo_headers,
                    json={"title": "Hello", "message": "Meeting Friday", "audience": "VOLUNTEERS"})
    assert r.status_code == 201 and r.json()["recipients"] == 1
    assert inbox(client, volunteer_headers, notification_type="ANNOUNCEMENT")["total"] == 1
    assert client.post(f"{API}/notifications", headers=volunteer_headers,
                       json={"title": "x", "message": "y"}).status_code == 403


# ============================================== volunteer API (report 6.3)

def test_create_profile_conflicts_when_one_exists(client, volunteer_headers):
    assert client.post(f"{API}/volunteers", json={"skills": ["x"]}, headers=volunteer_headers).status_code == 409


def test_delete_then_recreate_profile(client, db, volunteer_headers):
    vid = vol_id(client, volunteer_headers)
    assert client.delete(f"{API}/volunteers/{vid}", headers=volunteer_headers).json() == {"deleted": True}
    assert client.get(f"{API}/volunteers/me", headers=volunteer_headers).status_code == 403  # no profile now
    r = client.post(f"{API}/volunteers", headers=volunteer_headers,
                    json={"skills": ["Cooking"], "location": "Sylhet, Sylhet", "phone": "01711111111"})
    assert r.status_code == 201 and r.json()["skills"] == ["Cooking"] and r.json()["profile_complete"] is True
    assert db.query(AuditLog).filter_by(action_type="DELETE_VOLUNTEER").count() == 1


def test_profile_with_history_cannot_be_deleted(client, ngo_headers, volunteer_headers):
    apply(client, volunteer_headers, post_opp(client, ngo_headers))
    r = client.delete(f"{API}/volunteers/{vol_id(client, volunteer_headers)}", headers=volunteer_headers)
    assert r.status_code == 409 and "1 applications" in r.json()["error"]["message"]


def test_volunteer_directory_and_detail_access(client, ngo_headers, other_ngo_headers, volunteer_headers,
                                               volunteer2_headers, platform_headers, donor_headers):
    apply(client, volunteer_headers, post_opp(client, ngo_headers))
    v1, v2 = vol_id(client, volunteer_headers), vol_id(client, volunteer2_headers)
    listing = client.get(f"{API}/volunteers", headers=ngo_headers).json()
    assert [v["id"] for v in listing["items"]] == [v1]  # only people who applied to this NGO
    assert listing["items"][0]["email"] == "vol@example.com"
    assert client.get(f"{API}/volunteers", headers=other_ngo_headers).json()["total"] == 0
    assert client.get(f"{API}/volunteers", headers=platform_headers).json()["total"] == 2
    for h in (volunteer_headers, donor_headers):
        assert client.get(f"{API}/volunteers", headers=h).status_code == 403
    assert client.get(f"{API}/volunteers/{v1}", headers=ngo_headers).status_code == 200
    assert client.get(f"{API}/volunteers/{v1}", headers=volunteer_headers).status_code == 200
    assert client.get(f"{API}/volunteers/{v1}", headers=other_ngo_headers).status_code == 403
    assert client.get(f"{API}/volunteers/{v1}", headers=volunteer2_headers).status_code == 403
    assert client.get(f"{API}/volunteers/{v2}", headers=ngo_headers).status_code == 403  # never applied here
    assert client.get(f"{API}/volunteers/999", headers=ngo_headers).status_code == 404
    assert client.get(f"{API}/volunteers?q=vol@example", headers=ngo_headers).json()["total"] == 1


def test_update_volunteer_by_id_is_owner_or_platform_only(client, ngo_headers, volunteer_headers, volunteer2_headers,
                                                          platform_headers):
    apply(client, volunteer_headers, post_opp(client, ngo_headers))
    v1 = vol_id(client, volunteer_headers)
    url = f"{API}/volunteers/{v1}"
    assert client.put(url, json={"skills": ["A"]}, headers=volunteer_headers).json()["skills"] == ["A"]
    assert client.put(url, json={"skills": ["B"]}, headers=volunteer2_headers).status_code == 403
    assert client.put(url, json={"skills": ["B"]}, headers=ngo_headers).status_code == 403  # NGOs read, not edit
    assert client.patch(url, json={"skills": ["C"]}, headers=platform_headers).json()["skills"] == ["C"]
    assert client.delete(url, headers=ngo_headers).status_code == 403


def test_ngo_reviews_a_volunteers_contributions_within_its_own_ngo(client, ngo_headers, other_ngo_headers,
                                                                   volunteer_headers):
    cid = mk_campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    vid = vol_id(client, volunteer_headers)
    past = client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": cid, "event_name": "Done", "event_date": str(date.today() - timedelta(days=1))}).json()["id"]
    client.post(f"{API}/participation", headers=ngo_headers, json={"event_id": past, "volunteer_id": vid, "hours": 4})
    c = client.get(f"{API}/volunteers/{vid}/contributions", headers=ngo_headers).json()
    assert c["total_hours"] == 4 and c["events_attended"] == 1
    assert client.get(f"{API}/volunteers/{vid}/contributions", headers=other_ngo_headers).status_code == 403
    assert client.get(f"{API}/volunteers/{vid}/contributions", headers=volunteer_headers).json()["total_hours"] == 4


def test_contributions_include_ngos_supported_and_people_reached(client, ngo_headers, other_ngo_headers,
                                                                volunteer_headers):
    cid = active_campaign(client, ngo_headers)
    enroll(client, ngo_headers, cid)
    enroll(client, ngo_headers, cid, name="Second")
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    vid = vol_id(client, volunteer_headers)
    past = client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": cid, "event_name": "Done", "event_date": "2026-02-01"}).json()["id"]
    client.post(f"{API}/participation", headers=ngo_headers, json={"event_id": past, "volunteer_id": vid, "hours": 2})
    c = client.get(f"{API}/contributions/me", headers=volunteer_headers).json()
    assert c["ngos_supported"] == 1 and c["people_reached"] == 2


# ============================================== NGO API (report 6.4)

def test_ngo_registration_details_logo_and_contact_number(client, db):
    r = client.post(f"{API}/ngos", json={
        "name": "Rina", "email": "rina@ngo.org", "password": PASSWORD, "confirm_password": PASSWORD,
        "ngo_name": "Green Hands", "contact": "hello@ngo.org", "contact_number": "01712 345 678",
        "registration_info": "Reg. no. 123/2020, Dept. of Social Services", "address": "Dhaka"})
    assert r.status_code == 201 and r.json()["ngo"]["verification_status"] == "PENDING"
    ngo = db.query(NGO).one()
    assert ngo.contact_number == "01712345678" and ngo.registration_info.startswith("Reg. no.")
    h = login(client, "rina@ngo.org")
    me = client.get(f"{API}/ngos/me", headers=h).json()
    assert me["contact_number"] == "01712345678" and me["logo_url"] is None
    bad = client.post(f"{API}/ngos", json={"name": "x", "email": "x@y.org", "password": PASSWORD,
                                           "confirm_password": PASSWORD, "ngo_name": "N", "contact_number": "nope"})
    assert bad.status_code == 422


def upload(client, headers, content, name="logo.png", ctype="image/png"):
    return client.post(f"{API}/ngos/me/logo", headers=headers, files={"file": (name, io.BytesIO(content), ctype)})


@pytest.mark.parametrize(("content", "ext"), [(PNG, "png"), (JPG, "jpg"), (WEBP, "webp")])
def test_logo_upload_accepts_real_images_and_serves_them(client, ngo_headers, content, ext):
    r = upload(client, ngo_headers, content, f"logo.{ext}")
    assert r.status_code == 200
    url = r.json()["logo_url"]
    assert url.startswith("/uploads/logos/") and url.endswith(f".{ext}")
    served = client.get(url)
    assert served.status_code == 200 and served.content == content


def test_logo_upload_validates_type_by_content_and_size(client, ngo_headers):
    cases = [
        (b"<script>alert(1)</script>", "evil.png", "image/png"),         # wrong bytes, image name
        (b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "x.svg", "image/svg+xml"),
        (b"%PDF-1.4 fake", "doc.pdf", "application/pdf"),
        (b"", "empty.png", "image/png"),
        (PNG + b"\x00" * (2 * 1024 * 1024), "big.png", "image/png"),     # over 2 MB
    ]
    for content, name, ctype in cases:
        r = upload(client, ngo_headers, content, name, ctype)
        assert r.status_code == 422, name
        assert "file" in r.json()["error"]["fields"]
    assert client.get(f"{API}/ngos/me", headers=ngo_headers).json()["logo_url"] is None


def test_logo_replace_and_remove_cleans_up_files(client, ngo_headers):
    from app.core.config import get_settings

    folder = get_settings().upload_path / "logos"
    first = upload(client, ngo_headers, PNG).json()["logo_url"].rsplit("/", 1)[1]
    assert (folder / first).exists()
    second = upload(client, ngo_headers, JPG, "b.jpg", "image/jpeg").json()["logo_url"].rsplit("/", 1)[1]
    assert not (folder / first).exists() and (folder / second).exists()
    assert client.delete(f"{API}/ngos/me/logo", headers=ngo_headers).json()["logo_url"] is None
    assert not (folder / second).exists()


def test_logo_upload_permissions(client, volunteer_headers, db):
    assert upload(client, volunteer_headers, PNG).status_code == 403
    make_ngo_admin(db, "p@example.com", verified=False, ngo_name="Pending")
    assert upload(client, login(client, "p@example.com"), PNG).status_code == 200  # may brand its profile
    assert client.post(f"{API}/ngos/me/logo", files={"file": ("a.png", io.BytesIO(PNG), "image/png")}).status_code == 401


def test_ngo_update_by_id_put_and_ownership(client, db, ngo_headers, other_ngo_headers, platform_headers,
                                            volunteer_headers):
    nid = db.query(NGO).filter_by(ngo_name="Helping Hands").one().id
    url = f"{API}/ngos/{nid}"
    r = client.put(url, json={"description": "New text", "contact_number": "01999999999"}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["description"] == "New text"
    assert client.put(url, json={"description": "x"}, headers=other_ngo_headers).status_code == 403
    assert client.put(url, json={"description": "x"}, headers=volunteer_headers).status_code == 403
    assert client.patch(url, json={"address": "By admin"}, headers=platform_headers).json()["address"] == "By admin"
    assert client.put(f"{API}/ngos/999", json={"description": "x"}, headers=platform_headers).status_code == 404
    assert db.query(AuditLog).filter_by(action_type="UPDATE_NGO").count() == 2


def test_ngo_detail_visibility(client, db, ngo_headers, volunteer_headers, platform_headers):
    make_ngo_admin(db, "p@example.com", verified=False, ngo_name="Pending")
    pending = db.query(NGO).filter_by(ngo_name="Pending").one().id
    verified = db.query(NGO).filter_by(ngo_name="Helping Hands").one().id
    assert client.get(f"{API}/ngos/{verified}", headers=volunteer_headers).status_code == 200
    assert client.get(f"{API}/ngos/{pending}", headers=volunteer_headers).status_code == 404
    assert client.get(f"{API}/ngos/{pending}", headers=platform_headers).status_code == 200
    assert client.get(f"{API}/ngos/{pending}", headers=login(client, "p@example.com")).status_code == 200


def test_ngo_delete_is_restricted_when_it_has_records(client, db, ngo_headers, other_ngo_headers, platform_headers):
    nid = db.query(NGO).filter_by(ngo_name="Helping Hands").one().id
    mk_campaign(client, ngo_headers)
    r = client.delete(f"{API}/ngos/{nid}", headers=ngo_headers)
    assert r.status_code == 409 and "1 campaigns" in r.json()["error"]["message"]
    other = db.query(NGO).filter_by(ngo_name="Other NGO").one().id
    assert client.delete(f"{API}/ngos/{other}", headers=ngo_headers).status_code == 403  # not yours
    assert client.delete(f"{API}/ngos/{other}", headers=platform_headers).json() == {"deleted": True}
    assert db.get(NGO, other) is None
    assert db.query(AuditLog).filter_by(action_type="DELETE_NGO").count() == 1


def test_verification_path_stores_admin_remarks(client, db, platform_headers, ngo_headers):
    make_ngo_admin(db, "p@example.com", verified=False, ngo_name="Pending")
    nid = db.query(NGO).filter_by(ngo_name="Pending").one().id
    r = client.patch(f"{API}/ngos/{nid}/verification", headers=platform_headers,
                     json={"status": "REJECTED", "remarks": "Registration number missing"})
    assert r.status_code == 200 and r.json()["verification_remarks"] == "Registration number missing"
    me = client.get(f"{API}/ngos/me", headers=login(client, "p@example.com")).json()
    assert me["verification_status"] == "REJECTED" and me["verification_remarks"] == "Registration number missing"
    assert "Registration number missing" in inbox(client, login(client, "p@example.com"))["items"][0]["message"]
    assert client.patch(f"{API}/ngos/{nid}/verify", headers=platform_headers,
                        json={"status": "VERIFIED", "reason": "Docs received"}).json()["verification_remarks"] == "Docs received"


# ============================================== campaigns (report 6.5, 5.4.3)

def test_campaign_create_with_status_goal_and_emergency_flag(client, db, ngo_headers, donor_headers):
    body = {"title": "Flood", "start_date": "2026-01-01", "end_date": "2026-12-31", "status": "ACTIVE",
            "donation_goal": 1000, "is_emergency": True}
    c = client.post(f"{API}/campaigns", json=body, headers=ngo_headers).json()
    assert c["status"] == "ACTIVE" and c["is_emergency"] is True and c["donation_goal"] == 1000
    assert c["donations_received"] == 0 and c["donation_progress"] == 0
    assert client.post(f"{API}/campaigns", json={**body, "status": "COMPLETED"}, headers=ngo_headers).status_code == 422
    assert client.post(f"{API}/campaigns", json={**body, "donation_goal": -1}, headers=ngo_headers).status_code == 422
    for amount in (250, 300):
        set_status(client, ngo_headers, donate(client, donor_headers, c["id"], amount=amount).json()["id"], "RECEIVED")
    donate(client, donor_headers, c["id"], amount=900)  # pending money does not count toward progress
    got = client.get(f"{API}/campaigns/{c['id']}").json()
    assert got["donations_received"] == 550 and got["donation_progress"] == 55
    listed = client.get(f"{API}/campaigns").json()["items"][0]
    assert listed["donations_received"] == 550 and listed["donation_progress"] == 55


def test_progress_is_capped_and_absent_without_a_goal(client, ngo_headers, donor_headers):
    capped = client.post(f"{API}/campaigns", headers=ngo_headers, json={
        "title": "Small goal", "start_date": "2026-01-01", "end_date": "2026-12-31", "status": "ACTIVE",
        "donation_goal": 100}).json()
    set_status(client, ngo_headers, donate(client, donor_headers, capped["id"], amount=500).json()["id"], "RECEIVED")
    assert client.get(f"{API}/campaigns/{capped['id']}").json()["donation_progress"] == 100
    nogoal = mk_campaign(client, ngo_headers)
    assert client.get(f"{API}/campaigns/{nogoal}").json()["donation_progress"] is None


def test_emergency_campaigns_sort_first_and_filter(client, ngo_headers):
    mk_campaign(client, ngo_headers, title="Normal")
    mk_campaign(client, ngo_headers, title="Urgent", is_emergency=True)
    assert [c["title"] for c in client.get(f"{API}/campaigns").json()["items"]] == ["Urgent", "Normal"]
    assert client.get(f"{API}/campaigns?emergency=true").json()["total"] == 1
    assert client.get(f"{API}/campaigns?emergency=false").json()["items"][0]["title"] == "Normal"


def test_campaign_put_updates_goal_and_flag(client, ngo_headers):
    cid = mk_campaign(client, ngo_headers)
    r = client.put(f"{API}/campaigns/{cid}", json={"donation_goal": 5000, "is_emergency": True}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["donation_goal"] == 5000 and r.json()["is_emergency"] is True
    assert client.put(f"{API}/campaigns/{cid}", json={"is_emergency": None}, headers=ngo_headers).status_code == 422
    cleared = client.put(f"{API}/campaigns/{cid}", json={"donation_goal": None}, headers=ngo_headers)
    assert cleared.json()["donation_goal"] is None


# ============================================== donations & resources (report 6.8)

def test_donation_list_is_role_aware(client, ngo_headers, other_ngo_headers, donor_headers, donor2_headers,
                                     volunteer_headers, platform_headers):
    cid = active_campaign(client, ngo_headers)
    donate(client, donor_headers, cid)
    count = lambda h: client.get(f"{API}/donations", headers=h).json()["total"]
    assert (count(donor_headers), count(donor2_headers), count(ngo_headers), count(other_ngo_headers),
            count(platform_headers)) == (1, 0, 1, 0, 1)
    assert client.get(f"{API}/donations", headers=volunteer_headers).status_code == 403


def test_ngo_can_correct_a_donation_and_the_change_is_audited(client, db, ngo_headers, other_ngo_headers,
                                                              donor_headers):
    cid = active_campaign(client, ngo_headers)
    did = donate(client, donor_headers, cid, amount=500).json()["id"]
    url = f"{API}/donations/{did}"
    r = client.put(url, json={"amount": 750, "note": "Corrected amount"}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["amount"] == 750 and r.json()["note"] == "Corrected amount"
    log = db.query(AuditLog).filter_by(action_type="UPDATE_DONATION").one()
    assert log.details == {"before": {"amount": 500.0, "note": None}, "after": {"amount": 750.0, "note": "Corrected amount"}}
    assert "corrected" in inbox(client, donor_headers)["items"][0]["message"]
    assert client.put(url, json={"amount": 1}, headers=other_ngo_headers).status_code == 403
    assert client.put(url, json={"amount": 1}, headers=donor_headers).status_code == 403
    assert client.put(url, json={"amount": 0}, headers=ngo_headers).status_code == 422  # money needs an amount
    assert client.put(url, json={"amount": None}, headers=ngo_headers).status_code == 422
    assert client.put(url, json={"status": "RECEIVED"}, headers=ngo_headers).status_code == 422
    assert client.put(url, json={"card_number": "4242"}, headers=ngo_headers).status_code == 422
    set_status(client, ngo_headers, did, "REJECTED")
    assert client.put(url, json={"amount": 5}, headers=ngo_headers).status_code == 409
    assert client.put(f"{API}/donations/999", json={"amount": 5}, headers=ngo_headers).status_code == 404


def test_top_level_resources_crud(client, db, ngo_headers, other_ngo_headers, volunteer_headers):
    cid = active_campaign(client, ngo_headers)
    r = client.post(f"{API}/resources", json={"campaign_id": cid, "name": "Rice", "quantity_total": 100, "unit": "kg"},
                    headers=ngo_headers)
    assert r.status_code == 201 and r.json()["quantity_remaining"] == 100
    rid = r.json()["id"]
    assert client.post(f"{API}/resources", json={"campaign_id": cid, "name": "x", "quantity_total": 1},
                       headers=other_ngo_headers).status_code == 403
    assert client.post(f"{API}/resources", json={"campaign_id": cid, "name": "x", "quantity_total": 1},
                       headers=volunteer_headers).status_code == 403
    assert client.post(f"{API}/resources", json={"name": "x", "quantity_total": 1}, headers=ngo_headers).status_code == 422
    listing = client.get(f"{API}/resources", headers=ngo_headers).json()
    assert listing["total"] == 1 and client.get(f"{API}/resources", headers=other_ngo_headers).json()["total"] == 0
    assert client.get(f"{API}/resources?campaign_id=999", headers=ngo_headers).json()["total"] == 0
    assert client.put(f"{API}/resources/{rid}", json={"quantity_total": 200}, headers=ngo_headers).json()["quantity_total"] == 200
    assert client.delete(f"{API}/resources/{rid}", headers=other_ngo_headers).status_code == 403
    assert client.delete(f"{API}/resources/{rid}", headers=ngo_headers).json() == {"deleted": True}
    assert db.query(Resource).count() == 0 and db.query(AuditLog).filter_by(action_type="DELETE_RESOURCE").count() == 1


def test_resource_with_distributions_cannot_be_deleted(client, ngo_headers):
    cid = active_campaign(client, ngo_headers)
    rid = add_resource(client, ngo_headers, cid).json()["id"]
    bid = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    client.post(f"{API}/resources/{rid}/distributions", json={"beneficiary_id": bid, "quantity": 5}, headers=ngo_headers)
    r = client.delete(f"{API}/resources/{rid}", headers=ngo_headers)
    assert r.status_code == 409 and "already distributed" in r.json()["error"]["message"]


# ============================================== beneficiaries (report 6.9)

def test_top_level_beneficiary_register_list_update(client, ngo_headers, other_ngo_headers, volunteer_headers,
                                                    donor_headers, beneficiary_headers):
    cid = active_campaign(client, ngo_headers)
    r = client.post(f"{API}/beneficiaries", headers=ngo_headers, json={
        "campaign_id": cid, "name": "Rahim", "contact": "01711111111", "location": "Sylhet",
        "required_assistance": "Food and water", "support_status": "ACTIVE"})
    assert r.status_code == 201
    body = r.json()
    assert body["campaign_id"] == cid and body["support_status"] == "ACTIVE" and body["required_assistance"] == "Food and water"
    bid = body["beneficiary_id"]
    listing = client.get(f"{API}/beneficiaries", headers=ngo_headers).json()
    assert listing["total"] == 1 and client.get(f"{API}/beneficiaries?support_status=PENDING", headers=ngo_headers).json()["total"] == 0
    for h in (volunteer_headers, donor_headers, beneficiary_headers):
        assert client.get(f"{API}/beneficiaries", headers=h).status_code == 403
    assert client.get(f"{API}/beneficiaries", headers=other_ngo_headers).json()["total"] == 0
    assert client.post(f"{API}/beneficiaries", headers=other_ngo_headers, json={"campaign_id": cid, "name": "X"}).status_code == 403
    url = f"{API}/beneficiaries/{bid}"
    r = client.put(url, headers=ngo_headers, json={"campaign_id": cid, "location": "Dhaka", "support_status": "COMPLETED"})
    assert r.status_code == 200 and r.json()["location"] == "Dhaka" and r.json()["support_status"] == "COMPLETED"
    assert client.put(url, headers=other_ngo_headers, json={"campaign_id": cid, "location": "x"}).status_code == 403
    assert client.put(url, headers=ngo_headers, json={"campaign_id": cid, "bogus": 1}).status_code == 422
    assert client.put(f"{API}/beneficiaries/999", headers=ngo_headers, json={"campaign_id": cid}).status_code == 404


def test_registered_beneficiary_details_are_not_editable_by_the_ngo(client, ngo_headers, beneficiary_headers):
    cid = active_campaign(client, ngo_headers)
    link = client.post(f"{API}/beneficiaries", headers=ngo_headers,
                       json={"campaign_id": cid, "email": "ben@example.com"}).json()
    url = f"{API}/beneficiaries/{link['beneficiary_id']}"
    assert client.put(url, headers=ngo_headers, json={"campaign_id": cid, "location": "Elsewhere"}).status_code == 409
    ok = client.put(url, headers=ngo_headers, json={"campaign_id": cid, "support_status": "ACTIVE"})
    assert ok.status_code == 200 and ok.json()["support_status"] == "ACTIVE"


# ============================================== notification settings (report 5.4.7, 3.1.3)

def test_muting_a_type_stops_it_but_urgent_alerts_still_arrive(client, ngo_headers, volunteer_headers):
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    assert client.get(f"{API}/notifications/settings", headers=volunteer_headers).json() == {"muted_types": []}
    r = client.put(f"{API}/notifications/settings", headers=volunteer_headers,
                   json={"muted_types": ["ANNOUNCEMENT", "ANNOUNCEMENT", "EMERGENCY_ALERT"]})
    assert r.json()["muted_types"] == ["ANNOUNCEMENT", "EMERGENCY_ALERT"]
    base = {"title": "Meet", "message": "Friday", "audience": "VOLUNTEERS"}
    assert client.post(f"{API}/announcements", json=base, headers=ngo_headers).json()["recipients"] == 0
    assert inbox(client, volunteer_headers, notification_type="ANNOUNCEMENT")["total"] == 0
    # emergency alerts and HIGH-priority notices cannot be muted
    sent = client.post(f"{API}/announcements", json={**base, "title": "FLOOD", "priority": "HIGH"}, headers=ngo_headers)
    assert sent.json()["recipients"] == 1
    assert inbox(client, volunteer_headers, notification_type="EMERGENCY_ALERT")["total"] == 1
    assert client.put(f"{API}/notifications/settings", headers=volunteer_headers,
                      json={"muted_types": ["NOT_A_TYPE"]}).status_code == 422
    client.put(f"{API}/notifications/settings", headers=volunteer_headers, json={"muted_types": []})
    again = client.post(f"{API}/announcements", json={**base, "title": "Later"}, headers=ngo_headers)
    assert again.json()["recipients"] == 1
    assert client.get(f"{API}/notifications/settings").status_code == 401


def test_settings_are_per_user(client, ngo_headers, volunteer_headers, volunteer2_headers):
    client.put(f"{API}/notifications/settings", headers=volunteer_headers, json={"muted_types": ["DIRECT_MESSAGE"]})
    assert client.get(f"{API}/notifications/settings", headers=volunteer2_headers).json() == {"muted_types": []}


# ============================================== volunteers volunteer in events (report 3.1.3, 5.1.2)

def test_ngo_assigns_volunteers_to_an_event_roster(client, db, ngo_headers, other_ngo_headers, volunteer_headers,
                                                   volunteer2_headers):
    cid = mk_campaign(client, ngo_headers)
    eid = mk_event(client, ngo_headers, cid)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    v1, v2 = vol_id(client, volunteer_headers), vol_id(client, volunteer2_headers)
    url = f"{API}/events/{eid}/assignments"
    r = client.post(url, json={"volunteer_id": v1}, headers=ngo_headers)
    assert r.status_code == 201 and r.json()["assigned_by"] == "NGO"
    assert "roster" in inbox(client, volunteer_headers, notification_type="EVENT_REMINDER")["items"][0]["message"]
    assert client.post(url, json={"volunteer_id": v1}, headers=ngo_headers).status_code == 409
    assert client.post(url, json={"volunteer_id": v2}, headers=ngo_headers).status_code == 409  # not accepted
    assert client.post(url, json={"volunteer_id": v1}, headers=other_ngo_headers).status_code == 403
    assert client.post(url, json={"volunteer_id": v1}, headers=volunteer_headers).status_code == 403
    roster = client.get(url, headers=ngo_headers).json()
    assert [(x["volunteer_id"], x["assigned_by"]) for x in roster] == [(v1, "NGO")]
    assert client.get(url, headers=other_ngo_headers).status_code == 403
    assert client.delete(f"{url}/{v1}", headers=ngo_headers).json() == {"removed": True}
    assert client.delete(f"{url}/{v1}", headers=ngo_headers).status_code == 404
    assert client.get(url, headers=ngo_headers).json() == []
    assert db.query(AuditLog).filter_by(action_type="ASSIGN_VOLUNTEER_TO_EVENT").count() == 1


def test_roster_is_closed_for_past_events_and_closed_campaigns(client, ngo_headers, volunteer_headers):
    cid = mk_campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    v1 = vol_id(client, volunteer_headers)
    past = client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": cid, "event_name": "Old", "event_date": str(date.today() - timedelta(days=3))}).json()["id"]
    assert client.post(f"{API}/events/{past}/assignments", json={"volunteer_id": v1}, headers=ngo_headers).status_code == 409
    future = mk_event(client, ngo_headers, cid)
    client.post(f"{API}/campaigns/{cid}/status", json={"status": "COMPLETED"}, headers=ngo_headers)
    assert client.post(f"{API}/events/{future}/assignments", json={"volunteer_id": v1}, headers=ngo_headers).status_code == 409


def test_volunteer_joins_and_leaves_an_event_and_sees_it(client, ngo_headers, volunteer_headers, volunteer2_headers):
    cid = mk_campaign(client, ngo_headers)
    eid = mk_event(client, ngo_headers, cid, name="Clean-up")
    # not accepted yet -> cannot join
    r = client.post(f"{API}/events/{eid}/join", headers=volunteer_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_ELIGIBLE"
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    assert client.get(f"{API}/events", headers=volunteer_headers).json()["items"][0]["joined"] is False
    assert client.post(f"{API}/events/{eid}/join", headers=volunteer_headers).status_code == 201
    assert client.post(f"{API}/events/{eid}/join", headers=volunteer_headers).status_code == 409
    assert client.get(f"{API}/events", headers=volunteer_headers).json()["items"][0]["joined"] is True
    assert client.get(f"{API}/events/{eid}", headers=volunteer_headers).json()["joined"] is True
    assert client.get(f"{API}/events/{eid}", headers=volunteer2_headers).json()["joined"] is False
    assert client.get(f"{API}/events/{eid}").json()["joined"] is False
    mine = client.get(f"{API}/events/me", headers=volunteer_headers).json()
    assert [e["event_name"] for e in mine["items"]] == ["Clean-up"]
    assert client.get(f"{API}/events/me", headers=volunteer2_headers).json()["total"] == 0
    assert client.get(f"{API}/events/me", headers=ngo_headers).status_code == 403
    # the NGO sees who joined, and was told
    roster = client.get(f"{API}/events/{eid}/assignments", headers=ngo_headers).json()
    assert roster[0]["assigned_by"] == "SELF"
    assert "joined" in inbox(client, ngo_headers, notification_type="EVENT_REMINDER")["items"][0]["message"]
    assert client.delete(f"{API}/events/{eid}/join", headers=volunteer_headers).json() == {"joined": False}
    assert client.get(f"{API}/events/me", headers=volunteer_headers).json()["total"] == 0
    assert client.delete(f"{API}/events/{eid}/join", headers=volunteer_headers).status_code == 404


def test_cannot_join_draft_or_past_events(client, ngo_headers, volunteer_headers):
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    draft = mk_campaign(client, ngo_headers, activate=False, title="Draft")
    de = mk_event(client, ngo_headers, draft)
    assert client.post(f"{API}/events/{de}/join", headers=volunteer_headers).status_code == 404
    live = mk_campaign(client, ngo_headers, title="Live")
    past = client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": live, "event_name": "Old", "event_date": str(date.today() - timedelta(days=1))}).json()["id"]
    assert client.post(f"{API}/events/{past}/join", headers=volunteer_headers).status_code == 409


# ============================================== admin (report 6.11)

def test_admin_can_delete_only_accounts_without_history(client, db, platform_headers, ngo_headers, volunteer_headers):
    spam = make_user(db, "spam@example.com", name="Spam", phone=None)
    sid = spam.id
    assert client.delete(f"{API}/admin/users/{sid}", headers=platform_headers).json() == {"deleted": True}
    assert client.get(f"{API}/admin/users/{sid}", headers=platform_headers).status_code == 404
    assert db.query(AuditLog).filter_by(action_type="DELETE_USER").count() == 1
    ngo_user = db.query(NGO).first().user_id
    r = client.delete(f"{API}/admin/users/{ngo_user}", headers=platform_headers)
    assert r.status_code == 409 and "Deactivate it instead" in r.json()["error"]["message"]
    apply(client, volunteer_headers, post_opp(client, ngo_headers))
    vid = vol_id(client, volunteer_headers)
    assert client.get(f"{API}/volunteers/{vid}", headers=platform_headers).status_code == 200
    from app.models import User
    uid = db.query(User).filter_by(email="vol@example.com").one().id
    assert client.delete(f"{API}/admin/users/{uid}", headers=platform_headers).status_code == 409
    me = db.query(User).filter_by(email="root@example.com").one().id
    assert client.delete(f"{API}/admin/users/{me}", headers=platform_headers).status_code == 409
    assert client.delete(f"{API}/admin/users/999", headers=platform_headers).status_code == 404
    assert client.delete(f"{API}/admin/users/{sid}", headers=ngo_headers).status_code == 403


def test_campaign_and_resource_reports(client, ngo_headers, other_ngo_headers, volunteer_headers, donor_headers,
                                       platform_headers):
    cid = client.post(f"{API}/campaigns", headers=ngo_headers, json={
        "title": "Flood", "start_date": "2026-01-01", "end_date": "2026-12-31", "status": "ACTIVE",
        "donation_goal": 1000, "is_emergency": True, "required_volunteers": 5}).json()["id"]
    oid = client.post(f"{API}/opportunities", headers=ngo_headers,
                      json={"title": "Helper", "campaign_id": cid}).json()["id"]
    accept(client, ngo_headers, volunteer_headers, oid)
    past = client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": cid, "event_name": "Pack", "event_date": "2026-02-01"}).json()["id"]
    client.post(f"{API}/participation", headers=ngo_headers,
                json={"event_id": past, "volunteer_id": vol_id(client, volunteer_headers), "hours": 3})
    set_status(client, ngo_headers, donate(client, donor_headers, cid, amount=400).json()["id"], "RECEIVED")
    rid = add_resource(client, ngo_headers, cid, quantity_total=200).json()["id"]
    bid = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    client.post(f"{API}/resources/{rid}/distributions", json={"beneficiary_id": bid, "quantity": 50}, headers=ngo_headers)

    row = client.get(f"{API}/reports/campaigns", headers=ngo_headers).json()["items"][0]
    assert (row["accepted_volunteers"], row["events"], row["volunteer_hours"]) == (1, 1, 3.0)
    assert (row["money_received"], row["donation_progress"], row["is_emergency"]) == (400.0, 40.0, True)
    assert (row["resources_total"], row["resources_distributed"]) == (200, 50)
    util = client.get(f"{API}/reports/resource-utilization", headers=ngo_headers).json()["items"][0]
    assert util["utilization_percent"] == 25.0 and util["quantity_remaining"] == 150
    assert "Rahim" not in str(util)
    assert client.get(f"{API}/reports/campaigns", headers=other_ngo_headers).json()["total"] == 0
    assert client.get(f"{API}/reports/campaigns", headers=platform_headers).json()["total"] == 1
    for path in ("campaigns", "resource-utilization"):
        assert client.get(f"{API}/reports/{path}", headers=volunteer_headers).status_code == 403


def test_admin_reports_bundle(client, ngo_headers, volunteer_headers, donor_headers, platform_headers):
    cid = active_campaign(client, ngo_headers)
    add_resource(client, ngo_headers, cid)
    set_status(client, ngo_headers, donate(client, donor_headers, cid, amount=100).json()["id"], "RECEIVED")
    r = client.get(f"{API}/admin/reports", headers=platform_headers)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"generated_at", "volunteers", "campaigns", "donations", "resources"}
    assert len(body["campaigns"]) == 1 and body["donations"][0]["money_received"] == 100
    assert body["resources"][0]["name"] == "Rice"
    for h in (ngo_headers, volunteer_headers):
        assert client.get(f"{API}/admin/reports", headers=h).status_code == 403
    assert Campaign  # model import used for type clarity
