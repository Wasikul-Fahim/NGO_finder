from app.models import AuditLog, Campaign, CampaignStatus

API = "/api/v1"
CAMPAIGN = {
    "title": "Flood Relief",
    "description": "Emergency aid",
    "location": "Sylhet",
    "start_date": "2026-11-01",
    "end_date": "2026-12-01",
    "required_volunteers": 20,
    "required_resources": [{"name": "Rice", "quantity": 500, "unit": "kg"}],
}


def create(client, headers, **overrides):
    r = client.post(f"{API}/campaigns", json={**CAMPAIGN, **overrides}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def set_status(client, headers, cid, status):
    return client.post(f"{API}/campaigns/{cid}/status", json={"status": status}, headers=headers)


def test_create_campaign_starts_as_draft_and_is_audited(client, db, ngo_headers):
    body = create(client, ngo_headers)
    assert body["status"] == "DRAFT" and body["ngo_name"] == "Helping Hands"
    assert body["required_resources"][0]["name"] == "Rice"
    log = db.query(AuditLog).filter_by(action_type="CREATE_CAMPAIGN").one()
    assert log.entity_id == body["id"] and log.actor_user_id


def test_only_verified_ngo_admin_can_create(client, volunteer_headers):
    r = client.post(f"{API}/campaigns", json=CAMPAIGN, headers=volunteer_headers)
    assert r.status_code == 403
    assert client.post(f"{API}/campaigns", json=CAMPAIGN).status_code == 401


def test_date_validation(client, ngo_headers):
    r = client.post(
        f"{API}/campaigns",
        json={**CAMPAIGN, "start_date": "2026-12-02", "end_date": "2026-12-01"},
        headers=ngo_headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["fields"]


def test_visibility_rules(client, ngo_headers, other_ngo_headers, volunteer_headers):
    draft = create(client, ngo_headers, title="Draft one")
    active = create(client, ngo_headers, title="Active one")
    set_status(client, ngo_headers, active["id"], "ACTIVE")

    public = client.get(f"{API}/campaigns").json()
    assert [c["title"] for c in public["items"]] == ["Active one"]
    assert client.get(f"{API}/campaigns/{draft['id']}").status_code == 404
    assert client.get(f"{API}/campaigns/{draft['id']}", headers=volunteer_headers).status_code == 404
    assert client.get(f"{API}/campaigns/{draft['id']}", headers=other_ngo_headers).status_code == 404
    assert client.get(f"{API}/campaigns/{draft['id']}", headers=ngo_headers).status_code == 200

    mine = client.get(f"{API}/campaigns?mine=true", headers=ngo_headers).json()
    assert mine["total"] == 2
    assert client.get(f"{API}/campaigns?mine=true", headers=volunteer_headers).status_code == 403


def test_platform_admin_sees_everything(client, ngo_headers, platform_headers):
    create(client, ngo_headers)
    assert client.get(f"{API}/campaigns", headers=platform_headers).json()["total"] == 1


def test_pagination_search_and_filters(client, ngo_headers):
    for i in range(5):
        c = create(client, ngo_headers, title=f"Campaign {i}", location="Dhaka" if i % 2 else "Sylhet")
        set_status(client, ngo_headers, c["id"], "ACTIVE")
    page = client.get(f"{API}/campaigns?page=2&page_size=2").json()
    assert set(page) == {"items", "page", "page_size", "total", "pages"}
    assert page["total"] == 5 and page["pages"] == 3 and len(page["items"]) == 2
    assert client.get(f"{API}/campaigns?q=Campaign 3").json()["total"] == 1
    assert client.get(f"{API}/campaigns?location=dhaka").json()["total"] == 2
    assert client.get(f"{API}/campaigns?page_size=1000").status_code == 422


def test_empty_list_envelope(client):
    body = client.get(f"{API}/campaigns").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0, "pages": 0}


def test_update_campaign(client, db, ngo_headers):
    c = create(client, ngo_headers)
    r = client.patch(f"{API}/campaigns/{c['id']}", json={"title": "Renamed", "required_volunteers": 5},
                     headers=ngo_headers)
    assert r.status_code == 200 and r.json()["title"] == "Renamed"
    assert db.query(AuditLog).filter_by(action_type="UPDATE_CAMPAIGN").count() == 1


def test_update_validates_merged_dates(client, ngo_headers):
    c = create(client, ngo_headers)
    r = client.patch(f"{API}/campaigns/{c['id']}", json={"end_date": "2026-10-01"}, headers=ngo_headers)
    assert r.status_code == 422


def test_update_cannot_change_status_or_owner(client, ngo_headers):
    c = create(client, ngo_headers)
    for body in ({"status": "ACTIVE"}, {"ngo_id": 99}):
        assert client.patch(f"{API}/campaigns/{c['id']}", json=body, headers=ngo_headers).status_code == 422


def test_cannot_touch_other_ngos_campaign(client, ngo_headers, other_ngo_headers):
    c = create(client, ngo_headers)
    set_status(client, ngo_headers, c["id"], "ACTIVE")
    assert client.patch(f"{API}/campaigns/{c['id']}", json={"title": "Hijack"},
                        headers=other_ngo_headers).status_code == 403
    assert set_status(client, other_ngo_headers, c["id"], "COMPLETED").status_code == 403
    assert client.delete(f"{API}/campaigns/{c['id']}", headers=other_ngo_headers).status_code == 403


def test_status_transitions(client, db, ngo_headers):
    c = create(client, ngo_headers)
    cid = c["id"]
    assert set_status(client, ngo_headers, cid, "COMPLETED").status_code == 409  # DRAFT -> COMPLETED
    assert set_status(client, ngo_headers, cid, "DRAFT").status_code == 409
    assert set_status(client, ngo_headers, cid, "ACTIVE").status_code == 200
    assert set_status(client, ngo_headers, cid, "DRAFT").status_code == 409  # no going back
    assert set_status(client, ngo_headers, cid, "COMPLETED").status_code == 200
    r = set_status(client, ngo_headers, cid, "ACTIVE")
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"
    assert db.query(AuditLog).filter_by(action_type="CHANGE_CAMPAIGN_STATUS").count() == 2


def test_completed_campaign_cannot_be_edited(client, ngo_headers):
    c = create(client, ngo_headers)
    set_status(client, ngo_headers, c["id"], "ACTIVE")
    set_status(client, ngo_headers, c["id"], "COMPLETED")
    r = client.patch(f"{API}/campaigns/{c['id']}", json={"title": "Late edit"}, headers=ngo_headers)
    assert r.status_code == 409


def test_delete_archives(client, db, ngo_headers):
    c = create(client, ngo_headers)
    r = client.delete(f"{API}/campaigns/{c['id']}", headers=ngo_headers)
    assert r.status_code == 200 and r.json()["status"] == "ARCHIVED"
    assert db.get(Campaign, c["id"]).status == CampaignStatus.ARCHIVED
    assert client.delete(f"{API}/campaigns/{c['id']}", headers=ngo_headers).status_code == 409
    assert db.query(AuditLog).filter_by(action_type="ARCHIVE_CAMPAIGN").count() == 1
    assert client.get(f"{API}/campaigns").json()["total"] == 0


def test_missing_campaign(client, ngo_headers):
    assert client.get(f"{API}/campaigns/9999").status_code == 404
    assert client.patch(f"{API}/campaigns/9999", json={"title": "x"}, headers=ngo_headers).status_code == 404
