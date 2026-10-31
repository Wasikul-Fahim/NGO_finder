from app.models import NGO, AuditLog, Notification, Role, User, VerificationStatus
from app.tests.conftest import PASSWORD, login
from app.tests.test_workflow import apply, post_opp, review

API = "/api/v1"
NGO_SIGNUP = {
    "name": "Rina Akter", "email": "  Rina@GreenHands.org ", "password": PASSWORD, "confirm_password": PASSWORD,
    "ngo_name": "Green Hands", "description": "Tree planting", "address": "Mirpur, Dhaka", "contact": "hello@greenhands.org",
}


def signup(client, **kw):
    return client.post(f"{API}/auth/register-ngo", json={**NGO_SIGNUP, **kw})


def inbox(client, headers, **p):
    return client.get(f"{API}/notifications", params=p, headers=headers).json()


# --------------------------------------------------------------------- signup

def test_ngo_can_register_and_starts_unverified(client, db):
    r = signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "NGO_ADMIN" and body["email"] == "rina@greenhands.org"
    assert body["ngo"]["ngo_name"] == "Green Hands" and body["ngo"]["verification_status"] == "PENDING"
    assert "password" not in str(body)
    ngo = db.query(NGO).one()
    assert ngo.verification_status == VerificationStatus.PENDING and ngo.address == "Mirpur, Dhaka"
    assert db.query(AuditLog).filter_by(action_type="REGISTER_NGO").count() == 1


def test_new_ngo_can_log_in_and_see_dashboard_but_not_publish(client):
    signup(client)
    h = login(client, "rina@greenhands.org")
    dash = client.get(f"{API}/ngos/me/dashboard", headers=h).json()
    assert dash["verification_status"] == "PENDING"
    me = client.get(f"{API}/auth/me", headers=h).json()
    assert me["role"] == "NGO_ADMIN" and me["ngo"]["verification_status"] == "PENDING"
    publish = {
        "campaigns": {"title": "T", "start_date": "2026-01-01", "end_date": "2026-02-01"},
        "opportunities": {"title": "Role"},
        "announcements": {"title": "A", "message": "B"},
    }
    for path, body in publish.items():
        assert client.post(f"{API}/{path}", json=body, headers=h).status_code == 403, path
    # but it may complete its profile
    assert client.patch(f"{API}/ngos/me", json={"description": "Updated"}, headers=h).status_code == 200


def test_unverified_ngo_is_not_publicly_listed(client, volunteer_headers):
    signup(client)
    assert client.get(f"{API}/ngos", headers=volunteer_headers).json()["total"] == 0


def test_register_endpoint_still_refuses_admin_roles(client, db):
    for role in ("NGO_ADMIN", "PLATFORM_ADMIN"):
        r = client.post(f"{API}/auth/register", json={
            "name": "X", "email": "x@example.com", "password": PASSWORD, "confirm_password": PASSWORD, "role": role})
        assert r.status_code == 422
    assert db.query(User).count() == 0


def test_ngo_signup_validation(client, db):
    assert signup(client, ngo_name="  ").status_code == 422
    assert signup(client, email="nope").status_code == 422
    assert signup(client, password="weak", confirm_password="weak").status_code == 422
    r = signup(client, confirm_password="Different1")
    assert r.status_code == 422 and "Passwords do not match" in str(r.json()["error"]["fields"])
    assert signup(client, role="PLATFORM_ADMIN").status_code == 201  # unknown fields are ignored, role stays NGO_ADMIN
    assert db.query(User).one().role == Role.NGO_ADMIN
    assert signup(client).status_code == 409  # duplicate email
    assert db.query(NGO).count() == 1


def test_duplicate_email_across_account_types(client, volunteer_headers):
    assert signup(client, email="vol@example.com").status_code == 409


# ------------------------------------------------ verification closes the loop

def test_platform_admins_are_told_and_ngo_is_told_back(client, db, platform_headers):
    signup(client)
    queue = inbox(client, platform_headers)
    assert queue["total"] == 1 and queue["items"][0]["link"] == "/platform/ngos"
    assert "Green Hands" in queue["items"][0]["message"]

    ngo = login(client, "rina@greenhands.org")
    nid = db.query(NGO).one().id
    r = client.patch(f"{API}/ngos/{nid}/verify", json={"status": "VERIFIED"}, headers=platform_headers)
    assert r.status_code == 200
    told = inbox(client, ngo)["items"][0]
    assert told["title"] == "Your NGO was verified" and told["priority"] == "HIGH"
    # ...and now it can publish
    body = {"title": "Plant a tree", "start_date": "2026-01-01", "end_date": "2026-02-01"}
    assert client.post(f"{API}/campaigns", json=body, headers=ngo).status_code == 201
    assert client.get(f"{API}/ngos", headers=platform_headers).json()["total"] == 1


def test_rejection_includes_reason(client, db, platform_headers):
    signup(client)
    ngo = login(client, "rina@greenhands.org")
    nid = db.query(NGO).one().id
    client.patch(f"{API}/ngos/{nid}/verify", json={"status": "REJECTED", "reason": "Incomplete details"},
                 headers=platform_headers)
    n = inbox(client, ngo)["items"][0]
    assert n["title"] == "Your NGO was not verified" and "Incomplete details" in n["message"]
    assert client.post(f"{API}/campaigns", headers=ngo, json={
        "title": "T", "start_date": "2026-01-01", "end_date": "2026-02-01"}).status_code == 403


def test_signup_notification_failure_does_not_block_signup(client, db, monkeypatch):
    from app.services import notifications as svc

    monkeypatch.setattr(svc, "Notification", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert signup(client).status_code == 201
    assert db.query(Notification).count() == 0


# ------------------------------------------------- contacting applicants

def test_ngo_sees_applicant_contact_details(client, db, ngo_headers, volunteer_headers, other_ngo_headers):
    db.query(User).filter_by(email="vol@example.com").one().phone = "01711112222"
    db.commit()
    oid = post_opp(client, ngo_headers)
    apply(client, volunteer_headers, oid)
    row = client.get(f"{API}/applications", headers=ngo_headers).json()["items"][0]
    assert row["volunteer_email"] == "vol@example.com" and row["volunteer_phone"] == "01711112222"
    assert client.get(f"{API}/applications", headers=other_ngo_headers).json()["total"] == 0
    # review responses keep the contact details for the owning NGO
    r = review(client, ngo_headers, row["id"], "UNDER_REVIEW")
    assert r.json()["volunteer_email"] == "vol@example.com"
    # a volunteer's own list never carries contact fields
    mine = client.get(f"{API}/applications/me", headers=volunteer_headers).json()["items"][0]
    assert mine["volunteer_email"] is None and mine["volunteer_phone"] is None


def message(client, headers, aid, text="Can you start Saturday?"):
    return client.post(f"{API}/applications/{aid}/messages", json={"message": text}, headers=headers)


def test_ngo_can_message_an_applicant(client, db, ngo_headers, volunteer_headers):
    aid = apply(client, volunteer_headers, post_opp(client, ngo_headers)).json()["id"]
    r = message(client, ngo_headers, aid)
    assert r.status_code == 201 and r.json() == {"sent": 1}
    n = inbox(client, volunteer_headers, notification_type="DIRECT_MESSAGE")["items"][0]
    assert n["title"] == "Message from Helping Hands" and "Can you start Saturday?" in n["message"]
    assert 'About "Helper"' in n["message"] and "Reply to: ngo@example.com" in n["message"]
    assert n["link"] == "/applications"
    log = db.query(AuditLog).filter_by(action_type="MESSAGE_APPLICANT").one()
    assert "Saturday" not in str(log.details)  # the audit log records that it happened, not the content


def test_message_uses_ngo_contact_for_replies(client, ngo_headers, volunteer_headers):
    client.patch(f"{API}/ngos/me", json={"contact": "volunteers@helpinghands.org"}, headers=ngo_headers)
    aid = apply(client, volunteer_headers, post_opp(client, ngo_headers)).json()["id"]
    message(client, ngo_headers, aid)
    n = inbox(client, volunteer_headers)["items"][0]
    assert "Reply to: volunteers@helpinghands.org" in n["message"]


def test_message_works_for_any_application_status(client, ngo_headers, volunteer_headers):
    aid = apply(client, volunteer_headers, post_opp(client, ngo_headers)).json()["id"]
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    review(client, ngo_headers, aid, "REJECTED")
    assert message(client, ngo_headers, aid, "Thanks for applying, we'll keep you in mind.").status_code == 201


def test_message_permissions_and_validation(client, db, ngo_headers, other_ngo_headers, volunteer_headers,
                                            volunteer2_headers):
    from app.tests.conftest import make_ngo_admin

    aid = apply(client, volunteer_headers, post_opp(client, ngo_headers)).json()["id"]
    assert message(client, other_ngo_headers, aid).status_code == 403
    assert message(client, volunteer_headers, aid).status_code == 403
    assert message(client, volunteer2_headers, aid).status_code == 403
    assert client.post(f"{API}/applications/{aid}/messages", json={"message": "x"}).status_code == 401
    assert message(client, ngo_headers, 999).status_code == 404
    for bad in ("", "   ", "x" * 1001):
        assert message(client, ngo_headers, aid, bad).status_code == 422
    make_ngo_admin(db, "pending@example.com", verified=False, ngo_name="Pending")
    assert message(client, login(client, "pending@example.com"), aid).status_code == 403
    assert inbox(client, volunteer2_headers)["total"] == 0


def test_repeating_the_same_message_is_not_spammed(client, ngo_headers, volunteer_headers):
    aid = apply(client, volunteer_headers, post_opp(client, ngo_headers)).json()["id"]
    assert message(client, ngo_headers, aid).json() == {"sent": 1}
    assert message(client, ngo_headers, aid).json() == {"sent": 0}  # identical and still unread
    assert message(client, ngo_headers, aid, "A different message").json() == {"sent": 1}
