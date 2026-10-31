import pytest

from app.models import NGO, AuditLog, RefreshToken, User, VerificationStatus
from app.tests.conftest import PASSWORD, login, make_ngo_admin, make_user
from app.tests.test_workflow import accept, post_opp

API = "/api/v1"
NEW_ADMIN = {"name": "New Admin", "email": "Newngo@Example.com", "password": "Strong123",
             "ngo_name": "Fresh NGO"}


# ---------------------------------------------------------------- access control

ADMIN_GETS = ["/admin/audit-logs", "/admin/audit-logs/actions", "/admin/users", "/admin/users/1", "/admin/stats"]


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_admin_area_is_platform_admin_only(client, path, ngo_headers, volunteer_headers, platform_headers):
    assert client.get(API + path).status_code == 401
    assert client.get(API + path, headers=volunteer_headers).status_code == 403
    assert client.get(API + path, headers=ngo_headers).status_code == 403
    assert client.get(API + path, headers=platform_headers).status_code in (200, 404)


def test_admin_mutations_need_platform_admin(client, ngo_headers, volunteer_headers):
    for h in (ngo_headers, volunteer_headers):
        assert client.post(f"{API}/admin/ngo-admins", json=NEW_ADMIN, headers=h).status_code == 403
        assert client.patch(f"{API}/admin/users/1", json={"is_active": False}, headers=h).status_code == 403


# ------------------------------------------------------------------- audit log

def test_audit_log_lists_actions_newest_first_with_actor(client, ngo_headers, platform_headers):
    post_opp(client, ngo_headers)
    post_opp(client, ngo_headers, title="Second")
    body = client.get(f"{API}/admin/audit-logs", headers=platform_headers).json()
    assert body["total"] == 2 and set(body) == {"items", "page", "page_size", "total", "pages"}
    first = body["items"][0]
    assert first["action_type"] == "CREATE_OPPORTUNITY" and first["actor_name"] == "NGO Admin"
    assert first["details"]["title"] == "Second" and first["id"] > body["items"][1]["id"]


def test_audit_log_filters(client, db, ngo_headers, platform_headers):
    post_opp(client, ngo_headers)
    client.post(f"{API}/campaigns", headers=ngo_headers,
                json={"title": "C", "start_date": "2026-01-01", "end_date": "2026-02-01"})
    ngo_user = db.query(User).filter_by(email="ngo@example.com").one()
    get = lambda q: client.get(f"{API}/admin/audit-logs{q}", headers=platform_headers).json()
    assert get("?action_type=CREATE_CAMPAIGN")["total"] == 1
    assert get("?entity_type=Opportunity")["total"] == 1
    assert get(f"?actor_user_id={ngo_user.id}")["total"] == 2
    assert get("?actor_user_id=9999")["total"] == 0
    assert get("?q=campaign")["total"] == 1
    assert get("?date_from=2000-01-01&date_to=2999-01-01")["total"] == 2
    assert get("?date_from=2999-01-01")["total"] == 0
    assert get("?date_to=2000-01-01")["total"] == 0
    assert client.get(f"{API}/admin/audit-logs?date_from=nope", headers=platform_headers).status_code == 422
    assert sorted(client.get(f"{API}/admin/audit-logs/actions", headers=platform_headers).json()) == [
        "CREATE_CAMPAIGN", "CREATE_OPPORTUNITY"]


def test_audit_log_pagination(client, ngo_headers, platform_headers):
    for i in range(5):
        post_opp(client, ngo_headers, title=f"O{i}")
    page = client.get(f"{API}/admin/audit-logs?page=2&page_size=2", headers=platform_headers).json()
    assert page["total"] == 5 and page["pages"] == 3 and len(page["items"]) == 2


def test_audit_log_is_read_only_over_http(client, platform_headers):
    for method in ("post", "put", "patch", "delete"):
        r = getattr(client, method)(f"{API}/admin/audit-logs", headers=platform_headers)
        assert r.status_code == 405, method
        r = getattr(client, method)(f"{API}/admin/audit-logs/1", headers=platform_headers)
        assert r.status_code in (404, 405), method


def test_audit_rows_cannot_be_changed_or_deleted_even_in_code(db, platform_admin):
    entry = AuditLog(actor_user_id=platform_admin.id, action_type="X", entity_type="Y", details={})
    db.add(entry)
    db.commit()
    entry.action_type = "TAMPERED"
    with pytest.raises(RuntimeError, match="append-only"):
        db.commit()
    db.rollback()
    db.delete(db.get(AuditLog, entry.id))
    with pytest.raises(RuntimeError, match="append-only"):
        db.commit()
    db.rollback()
    assert db.get(AuditLog, entry.id).action_type == "X"


def test_every_admin_action_is_audited(client, db, ngo_headers, volunteer_headers, platform_headers):
    """The spec's list: approve/reject application, edit donation/resource, assign task, verify NGO."""
    from app.tests.test_finance import active_campaign, add_resource
    from app.tests.test_workflow import apply, make_task, review, vol_id

    cid = active_campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    review(client, ngo_headers, aid, "ACCEPTED")
    t = make_task(client, ngo_headers, cid).json()
    client.post(f"{API}/tasks/{t['id']}/assign", json={"volunteer_id": vol_id(client, volunteer_headers)},
                headers=ngo_headers)
    add_resource(client, ngo_headers, cid)
    ngo_id = db.query(NGO).one().id
    client.patch(f"{API}/ngos/{ngo_id}/verify", json={"status": "REJECTED"}, headers=platform_headers)
    seen = {a.action_type for a in db.query(AuditLog)}
    assert {"APPLICATION_UNDER_REVIEW", "APPLICATION_ACCEPTED", "ASSIGN_TASK", "CREATE_RESOURCE",
            "REJECT_NGO", "CREATE_TASK"} <= seen


# ------------------------------------------------------------------------ users

def test_user_listing_filters(client, db, ngo_headers, volunteer_headers, platform_headers):
    make_user(db, "off@example.com", name="Sleepy Person", active=False)
    get = lambda q: client.get(f"{API}/admin/users{q}", headers=platform_headers).json()
    assert get("")["total"] == 4
    assert get("?role=VOLUNTEER")["total"] == 2
    assert get("?is_active=false")["items"][0]["email"] == "off@example.com"
    assert get("?q=sleepy")["total"] == 1
    ngo = next(u for u in get("?role=NGO_ADMIN")["items"])
    assert ngo["ngo_name"] == "Helping Hands" and ngo["ngo_status"] == "VERIFIED"
    assert "password_hash" not in str(get(""))


def test_deactivate_user_blocks_login_and_kills_sessions(client, db, volunteer_headers, platform_headers):
    vid = db.query(User).filter_by(email="vol@example.com").one().id
    r = client.patch(f"{API}/admin/users/{vid}", json={"is_active": False}, headers=platform_headers)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get(f"{API}/auth/me", headers=volunteer_headers).status_code == 401  # token dies at once
    assert client.post(f"{API}/auth/login", json={"email": "vol@example.com", "password": PASSWORD}).status_code == 401
    assert all(t.revoked_at for t in db.query(RefreshToken).filter_by(user_id=vid))
    assert db.query(AuditLog).filter_by(action_type="DEACTIVATE_USER", entity_id=vid).count() == 1
    r = client.patch(f"{API}/admin/users/{vid}", json={"is_active": True}, headers=platform_headers)
    assert r.json()["is_active"] is True
    assert login(client, "vol@example.com")
    assert db.query(AuditLog).filter_by(action_type="ACTIVATE_USER").count() == 1


def test_user_update_edge_cases(client, db, platform_headers):
    me = db.query(User).filter_by(email="root@example.com").one()
    assert client.patch(f"{API}/admin/users/{me.id}", json={"is_active": False}, headers=platform_headers).status_code == 409
    assert client.patch(f"{API}/admin/users/{me.id}", json={"role": "VOLUNTEER"}, headers=platform_headers).status_code == 422
    assert client.patch(f"{API}/admin/users/{me.id}", json={"is_active": None}, headers=platform_headers).status_code == 422
    assert client.patch(f"{API}/admin/users/999", json={"is_active": False}, headers=platform_headers).status_code == 404
    assert client.get(f"{API}/admin/users/999", headers=platform_headers).status_code == 404
    # no-op change writes no audit row
    before = db.query(AuditLog).count()
    client.patch(f"{API}/admin/users/{me.id}", json={"is_active": True}, headers=platform_headers)
    assert db.query(AuditLog).count() == before


# ------------------------------------------------------------- NGO admin creation

def test_create_ngo_admin(client, db, platform_headers):
    r = client.post(f"{API}/admin/ngo-admins", json=NEW_ADMIN, headers=platform_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "newngo@example.com" and body["role"] == "NGO_ADMIN"
    assert body["ngo_name"] == "Fresh NGO" and body["ngo_status"] == "PENDING"
    assert db.query(NGO).filter_by(ngo_name="Fresh NGO").one().verification_status == VerificationStatus.PENDING
    assert db.query(AuditLog).filter_by(action_type="CREATE_NGO_ADMIN").count() == 1
    assert login(client, "newngo@example.com", "Strong123")  # the new admin can sign in
    ok = client.post(f"{API}/admin/ngo-admins", json={**NEW_ADMIN, "email": "v@example.com", "verified": True},
                     headers=platform_headers)
    assert ok.json()["ngo_status"] == "VERIFIED"


def test_create_ngo_admin_validation(client, db, platform_headers):
    post = lambda **kw: client.post(f"{API}/admin/ngo-admins", json={**NEW_ADMIN, **kw}, headers=platform_headers)
    assert post(password="weak").status_code == 422
    assert post(email="nope").status_code == 422
    assert post(ngo_name="  ").status_code == 422
    post()
    assert post().status_code == 409  # duplicate email
    make_user(db, "taken@example.com")
    assert post(email="taken@example.com").status_code == 409


# ------------------------------------------------------------------------ stats

def test_platform_stats(client, ngo_headers, volunteer_headers, platform_headers):
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    s = client.get(f"{API}/admin/stats", headers=platform_headers).json()
    assert s["users_by_role"] == {"NGO_ADMIN": 1, "VOLUNTEER": 1, "PLATFORM_ADMIN": 1}
    assert s["active_users"] == 3 and s["ngos_by_status"] == {"VERIFIED": 1}
    assert s["opportunities_active"] == 1 and s["applications_by_status"] == {"ACCEPTED": 1}
    assert s["audit_entries"] >= 3 and s["volunteer_hours"] == 0


def test_stats_empty_platform(client, platform_headers):
    s = client.get(f"{API}/admin/stats", headers=platform_headers).json()
    assert s["campaigns_by_status"] == {} and s["donations_received_money"] == 0


def test_ngo_verification_controls_ngo_powers(client, db, platform_headers):
    make_ngo_admin(db, "p@example.com", verified=False)
    h = login(client, "p@example.com")
    body = {"title": "T", "start_date": "2026-01-01", "end_date": "2026-02-01"}
    assert client.post(f"{API}/campaigns", json=body, headers=h).status_code == 403
    nid = db.query(NGO).one().id
    client.patch(f"{API}/ngos/{nid}/verify", json={"status": "VERIFIED"}, headers=platform_headers)
    assert client.post(f"{API}/campaigns", json=body, headers=h).status_code == 201
