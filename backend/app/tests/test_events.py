from app.models import AuditLog, Event

API = "/api/v1"
CAMPAIGN = {"title": "Flood Relief", "start_date": "2026-11-01", "end_date": "2026-12-01"}
EVENT = {"event_name": "Packing day", "event_date": "2026-11-10", "event_time": "09:30:00", "location": "Dhaka"}


def make_campaign(client, headers, activate=True):
    cid = client.post(f"{API}/campaigns", json=CAMPAIGN, headers=headers).json()["id"]
    if activate:
        client.post(f"{API}/campaigns/{cid}/status", json={"status": "ACTIVE"}, headers=headers)
    return cid


def make_event(client, headers, cid, **overrides):
    r = client.post(f"{API}/events", json={**EVENT, "campaign_id": cid, **overrides}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_event(client, db, ngo_headers):
    cid = make_campaign(client, ngo_headers)
    e = make_event(client, ngo_headers, cid)
    assert e["campaign_title"] == "Flood Relief" and e["event_time"] == "09:30:00"
    assert db.query(AuditLog).filter_by(action_type="CREATE_EVENT").one().entity_id == e["id"]


def test_event_date_must_be_inside_campaign(client, ngo_headers):
    cid = make_campaign(client, ngo_headers)
    for d in ("2026-10-31", "2026-12-02"):
        r = client.post(f"{API}/events", json={**EVENT, "campaign_id": cid, "event_date": d},
                        headers=ngo_headers)
        assert r.status_code == 422 and "event_date" in r.json()["error"]["fields"]


def test_cannot_create_event_on_other_ngos_campaign(client, ngo_headers, other_ngo_headers):
    cid = make_campaign(client, ngo_headers)
    r = client.post(f"{API}/events", json={**EVENT, "campaign_id": cid}, headers=other_ngo_headers)
    assert r.status_code == 403


def test_volunteer_cannot_create_event(client, ngo_headers, volunteer_headers):
    cid = make_campaign(client, ngo_headers)
    r = client.post(f"{API}/events", json={**EVENT, "campaign_id": cid}, headers=volunteer_headers)
    assert r.status_code == 403


def test_unknown_campaign(client, ngo_headers):
    r = client.post(f"{API}/events", json={**EVENT, "campaign_id": 999}, headers=ngo_headers)
    assert r.status_code == 404


def test_locked_campaign_blocks_event_changes(client, ngo_headers):
    cid = make_campaign(client, ngo_headers)
    e = make_event(client, ngo_headers, cid)
    client.post(f"{API}/campaigns/{cid}/status", json={"status": "COMPLETED"}, headers=ngo_headers)
    assert client.post(f"{API}/events", json={**EVENT, "campaign_id": cid}, headers=ngo_headers).status_code == 409
    assert client.patch(f"{API}/events/{e['id']}", json={"location": "x"}, headers=ngo_headers).status_code == 409
    assert client.delete(f"{API}/events/{e['id']}", headers=ngo_headers).status_code == 409


def test_list_visibility_and_filters(client, ngo_headers):
    active = make_campaign(client, ngo_headers)
    draft = make_campaign(client, ngo_headers, activate=False)
    make_event(client, ngo_headers, active, event_name="Public one", event_date="2026-11-05")
    make_event(client, ngo_headers, active, event_name="Public two", event_date="2026-11-20")
    make_event(client, ngo_headers, draft, event_name="Hidden")

    public = client.get(f"{API}/events").json()
    assert [e["event_name"] for e in public["items"]] == ["Public one", "Public two"]  # date ordered
    assert client.get(f"{API}/events", headers=ngo_headers).json()["total"] == 3
    assert client.get(f"{API}/events?campaign_id={draft}").json()["total"] == 0
    assert client.get(f"{API}/events?from_date=2026-11-10").json()["total"] == 1
    assert client.get(f"{API}/events?q=two").json()["total"] == 1


def test_get_event_visibility(client, ngo_headers):
    draft = make_campaign(client, ngo_headers, activate=False)
    e = make_event(client, ngo_headers, draft)
    assert client.get(f"{API}/events/{e['id']}").status_code == 404
    assert client.get(f"{API}/events/{e['id']}", headers=ngo_headers).status_code == 200


def test_update_and_delete(client, db, ngo_headers, other_ngo_headers):
    cid = make_campaign(client, ngo_headers)
    e = make_event(client, ngo_headers, cid)
    url = f"{API}/events/{e['id']}"
    assert client.patch(url, json={"location": "Chattogram"}, headers=other_ngo_headers).status_code == 403
    r = client.patch(url, json={"location": "Chattogram"}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["location"] == "Chattogram"
    assert client.patch(url, json={"event_date": "2027-01-01"}, headers=ngo_headers).status_code == 422
    assert client.patch(url, json={"campaign_id": 5}, headers=ngo_headers).status_code == 422
    assert client.delete(url, headers=other_ngo_headers).status_code == 403
    assert client.delete(url, headers=ngo_headers).status_code == 204
    assert db.query(Event).count() == 0
    assert client.delete(url, headers=ngo_headers).status_code == 404
    actions = {a.action_type for a in db.query(AuditLog)}
    assert {"CREATE_EVENT", "UPDATE_EVENT", "DELETE_EVENT"} <= actions
