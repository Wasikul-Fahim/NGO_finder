from app.models import AuditLog, Participation
from app.tests.test_workflow import accept, campaign, make_task, post_opp, review, vol_id

API = "/api/v1"


def make_event(client, headers, cid, date="2026-02-01", name="Packing day"):
    r = client.post(f"{API}/events", json={"campaign_id": cid, "event_name": name, "event_date": date},
                    headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def setup(client, ngo_headers, vol_headers, event_date="2026-02-01"):
    cid = campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    accept(client, ngo_headers, vol_headers, oid)
    return cid, make_event(client, ngo_headers, cid, event_date), vol_id(client, vol_headers)


def record(client, headers, eid, vid, **kw):
    return client.post(f"{API}/participation", json={"event_id": eid, "volunteer_id": vid, **kw}, headers=headers)


def test_record_attendance(client, db, ngo_headers, volunteer_headers):
    _, eid, vid = setup(client, ngo_headers, volunteer_headers)
    r = record(client, ngo_headers, eid, vid, hours=3.5)
    assert r.status_code == 201
    body = r.json()
    assert body["hours"] == 3.5 and body["attendance"] and body["participation_date"] == "2026-02-01"
    assert db.query(AuditLog).filter_by(action_type="RECORD_ATTENDANCE").count() == 1


def test_duplicate_attendance_409(client, ngo_headers, volunteer_headers):
    _, eid, vid = setup(client, ngo_headers, volunteer_headers)
    record(client, ngo_headers, eid, vid, hours=2)
    assert record(client, ngo_headers, eid, vid, hours=2).status_code == 409


def test_hours_validation(client, ngo_headers, volunteer_headers):
    _, eid, vid = setup(client, ngo_headers, volunteer_headers)
    assert record(client, ngo_headers, eid, vid, hours=25).status_code == 422
    assert record(client, ngo_headers, eid, vid, hours=-1).status_code == 422
    r = record(client, ngo_headers, eid, vid, attendance=False, hours=2)
    assert r.status_code == 422 and "hours" in str(r.json()["error"]["fields"])
    r = record(client, ngo_headers, eid, vid, attendance=False)
    assert r.status_code == 201 and r.json()["hours"] == 0


def test_future_event_rejected(client, ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    client.patch(f"{API}/campaigns/{cid}", json={"end_date": "2099-12-31"}, headers=ngo_headers)
    oid = post_opp(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, oid)
    eid = make_event(client, ngo_headers, cid, "2099-06-01")
    assert record(client, ngo_headers, eid, vol_id(client, volunteer_headers), hours=1).status_code == 409


def test_only_accepted_volunteers(client, ngo_headers, volunteer_headers, volunteer2_headers):
    cid = campaign(client, ngo_headers)
    eid = make_event(client, ngo_headers, cid)
    oid = post_opp(client, ngo_headers)
    v2 = vol_id(client, volunteer2_headers)
    assert record(client, ngo_headers, eid, v2, hours=1).status_code == 409  # never applied
    aid = client.post(f"{API}/opportunities/{oid}/applications", headers=volunteer2_headers).json()["id"]
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    assert record(client, ngo_headers, eid, v2, hours=1).status_code == 409  # not accepted yet


def test_attendance_permissions(client, ngo_headers, other_ngo_headers, volunteer_headers):
    _, eid, vid = setup(client, ngo_headers, volunteer_headers)
    assert record(client, other_ngo_headers, eid, vid, hours=1).status_code == 403
    assert record(client, volunteer_headers, eid, vid, hours=1).status_code == 403
    assert record(client, ngo_headers, 999, vid, hours=1).status_code == 404
    pid = record(client, ngo_headers, eid, vid, hours=1).json()["id"]
    assert client.patch(f"{API}/participation/{pid}", json={"hours": 2}, headers=other_ngo_headers).status_code == 403
    assert client.get(f"{API}/participation", headers=other_ngo_headers).json()["total"] == 0
    assert client.get(f"{API}/participation", headers=volunteer_headers).status_code == 403


def test_update_attendance(client, db, ngo_headers, volunteer_headers):
    _, eid, vid = setup(client, ngo_headers, volunteer_headers)
    pid = record(client, ngo_headers, eid, vid, hours=2).json()["id"]
    url = f"{API}/participation/{pid}"
    r = client.patch(url, json={"hours": 4}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["hours"] == 4
    assert client.patch(url, json={"hours": 99}, headers=ngo_headers).status_code == 422
    assert client.patch(url, json={"hours": None}, headers=ngo_headers).status_code == 422
    r = client.patch(url, json={"attendance": False}, headers=ngo_headers)  # marking absent zeroes hours
    assert r.json()["attendance"] is False and r.json()["hours"] == 0
    assert db.query(AuditLog).filter_by(action_type="UPDATE_ATTENDANCE").count() == 2


def test_contributions_summary(client, ngo_headers, volunteer_headers):
    cid, e1, vid = setup(client, ngo_headers, volunteer_headers, "2026-02-01")
    e2 = make_event(client, ngo_headers, cid, "2026-03-05", "Second")
    e3 = make_event(client, ngo_headers, cid, "2026-03-06", "Third")
    record(client, ngo_headers, e1, vid, hours=2.5)
    record(client, ngo_headers, e2, vid, hours=4)
    record(client, ngo_headers, e3, vid, attendance=False)
    t = make_task(client, ngo_headers, cid, volunteer_id=vid).json()
    for s in ("ACCEPTED", "IN_PROGRESS", "COMPLETED"):
        client.patch(f"{API}/tasks/{t['id']}/status", json={"status": s}, headers=volunteer_headers)
    make_task(client, ngo_headers, cid, volunteer_id=vid)  # a second, still pending

    c = client.get(f"{API}/contributions/me", headers=volunteer_headers).json()
    assert c["total_hours"] == 6.5 and c["events_attended"] == 2
    assert c["tasks_completed"] == 1 and c["tasks_total"] == 2
    assert c["monthly_hours"] == [{"month": "2026-02", "hours": 2.5}, {"month": "2026-03", "hours": 4.0}]
    assert len(c["history"]) == 3 and c["history"][0]["event_name"] == "Third"  # newest first


def test_contributions_empty_and_scoped(client, ngo_headers, volunteer_headers, volunteer2_headers):
    _, eid, vid = setup(client, ngo_headers, volunteer_headers)
    record(client, ngo_headers, eid, vid, hours=3)
    empty = client.get(f"{API}/contributions/me", headers=volunteer2_headers).json()
    assert empty["total_hours"] == 0 and empty["history"] == [] and empty["monthly_hours"] == []
    assert client.get(f"{API}/contributions/me", headers=ngo_headers).status_code == 403
    assert client.get(f"{API}/contributions/me").status_code == 401


def test_performance_ranking(client, ngo_headers, other_ngo_headers, volunteer_headers, volunteer2_headers,
                             platform_headers):
    cid, eid, v1 = setup(client, ngo_headers, volunteer_headers)
    oid = post_opp(client, ngo_headers, title="Second role")
    accept(client, ngo_headers, volunteer2_headers, oid)
    v2 = vol_id(client, volunteer2_headers)
    e2 = make_event(client, ngo_headers, cid, "2026-02-02", "Second")
    record(client, ngo_headers, eid, v1, hours=2)
    record(client, ngo_headers, eid, v2, hours=5)
    record(client, ngo_headers, e2, v2, hours=1)
    t = make_task(client, ngo_headers, cid, volunteer_id=v1).json()
    for s in ("ACCEPTED", "IN_PROGRESS", "COMPLETED"):
        client.patch(f"{API}/tasks/{t['id']}/status", json={"status": s}, headers=volunteer_headers)

    rows = client.get(f"{API}/reports/volunteer-performance", headers=ngo_headers).json()["items"]
    assert [(r["volunteer_id"], r["rank"], r["total_hours"], r["tasks_completed"]) for r in rows] == [
        (v2, 1, 6.0, 0), (v1, 2, 2.0, 1)]
    assert rows[0]["events_attended"] == 2
    # Other NGOs see none of this; platform admin sees all; volunteers are blocked.
    assert client.get(f"{API}/reports/volunteer-performance", headers=other_ngo_headers).json()["total"] == 0
    assert client.get(f"{API}/reports/volunteer-performance", headers=platform_headers).json()["total"] == 2
    assert client.get(f"{API}/reports/volunteer-performance", headers=volunteer_headers).status_code == 403
    assert client.get(f"{API}/reports/volunteer-performance?campaign_id=9999", headers=ngo_headers).json()["total"] == 0


def test_performance_tie_shares_rank(client, ngo_headers, volunteer_headers, volunteer2_headers):
    _, eid, v1 = setup(client, ngo_headers, volunteer_headers)
    accept(client, ngo_headers, volunteer2_headers, post_opp(client, ngo_headers, title="B"))
    v2 = vol_id(client, volunteer2_headers)
    record(client, ngo_headers, eid, v1, hours=3)
    record(client, ngo_headers, eid, v2, hours=3)
    rows = client.get(f"{API}/reports/volunteer-performance", headers=ngo_headers).json()["items"]
    assert [r["rank"] for r in rows] == [1, 1]


def test_attendance_row_exists(client, db, ngo_headers, volunteer_headers):
    _, eid, vid = setup(client, ngo_headers, volunteer_headers)
    record(client, ngo_headers, eid, vid, hours=1)
    assert db.query(Participation).count() == 1
