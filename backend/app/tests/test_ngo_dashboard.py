from app.tests.conftest import login, make_ngo_admin
from app.tests.test_finance import active_campaign, add_resource, donate, enroll, set_status
from app.tests.test_impact import make_event, record
from app.tests.test_workflow import accept, apply, make_task, post_opp, vol_id

API = "/api/v1"


def dash(client, headers):
    r = client.get(f"{API}/ngos/me/dashboard", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_empty_dashboard(client, ngo_headers):
    d = dash(client, ngo_headers)
    assert d["ngo_name"] == "Helping Hands" and d["verification_status"] == "VERIFIED"
    assert d["campaigns_by_status"] == {} and d["needs_attention"] == [] and d["upcoming_events"] == []
    assert d["money_received"] == 0 and d["volunteer_hours"] == 0 and d["recent_activity"] == []


def test_dashboard_ties_every_module_together(client, ngo_headers, volunteer_headers, volunteer2_headers,
                                              donor_headers):
    cid = active_campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    post_opp(client, ngo_headers, title="Second")
    accept(client, ngo_headers, volunteer_headers, oid)
    apply(client, volunteer2_headers, oid)                      # one application waiting for review
    v1 = vol_id(client, volunteer_headers)
    make_task(client, ngo_headers, cid, volunteer_id=v1)        # assigned
    make_task(client, ngo_headers, cid)                          # unassigned
    past = make_event(client, ngo_headers, cid, "2026-02-01")
    make_event(client, ngo_headers, cid, "2026-02-02", "Another past one")
    client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": cid, "event_name": "Coming up", "event_date": "2026-12-01"})
    record(client, ngo_headers, past, v1, hours=3.5)
    did = donate(client, donor_headers, cid, amount=700).json()["id"]
    set_status(client, ngo_headers, did, "RECEIVED")
    donate(client, donor_headers, cid, amount=50)               # still pending
    rid = add_resource(client, ngo_headers, cid).json()["id"]
    bid = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    client.post(f"{API}/resources/{rid}/distributions", json={"beneficiary_id": bid, "quantity": 30},
                headers=ngo_headers)

    d = dash(client, ngo_headers)
    assert d["campaigns_by_status"] == {"ACTIVE": 1}
    assert d["opportunities_active"] == 2 and d["opportunities_inactive"] == 0
    assert d["applications_by_status"] == {"ACCEPTED": 1, "SUBMITTED": 1}
    assert d["tasks_by_status"] == {"PENDING": 2}
    assert d["accepted_volunteers"] == 1 and d["volunteer_hours"] == 3.5
    assert d["money_received"] == 700 and d["donations_pending"] == 1
    assert d["beneficiaries_enrolled"] == 1
    assert (d["resources_total"], d["resources_distributed"]) == (100, 30)
    attention = {c["key"]: c for c in d["needs_attention"]}
    assert attention["applications_new"]["count"] == 1 and attention["applications_new"]["link"] == "/admin/applications"
    assert attention["donations_pending"]["count"] == 1
    assert attention["tasks_unassigned"]["count"] == 1
    assert attention["events_attendance"]["count"] == 1          # the second past event has no attendance
    assert "applications_in_review" not in attention             # zero-count items are hidden
    assert [e["event_name"] for e in d["upcoming_events"]] == ["Coming up"]
    assert d["recent_activity"][0]["actor_name"] == "NGO Admin" and len(d["recent_activity"]) == 10


def test_dashboard_is_scoped_to_own_ngo(client, ngo_headers, other_ngo_headers, volunteer_headers):
    active_campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    other = dash(client, other_ngo_headers)
    assert other["campaigns_by_status"] == {} and other["accepted_volunteers"] == 0
    assert other["recent_activity"] == [] and other["opportunities_active"] == 0


def test_dashboard_permissions(client, db, volunteer_headers, donor_headers, platform_headers):
    assert client.get(f"{API}/ngos/me/dashboard").status_code == 401
    for h in (volunteer_headers, donor_headers, platform_headers):
        assert client.get(f"{API}/ngos/me/dashboard", headers=h).status_code == 403
    make_ngo_admin(db, "pending@example.com", verified=False, ngo_name="Pending")
    d = dash(client, login(client, "pending@example.com"))
    assert d["verification_status"] == "PENDING"  # unverified NGOs still get their dashboard


def test_activity_feed(client, ngo_headers, other_ngo_headers):
    for i in range(3):
        post_opp(client, ngo_headers, title=f"O{i}")
    page = client.get(f"{API}/ngos/me/activity?page_size=2", headers=ngo_headers).json()
    assert page["total"] == 3 and page["pages"] == 2 and page["items"][0]["details"]["title"] == "O2"
    assert client.get(f"{API}/ngos/me/activity", headers=other_ngo_headers).json()["total"] == 0
