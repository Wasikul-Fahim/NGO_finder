from app.models import Application, ApplicationStatus, AuditLog, Task
from app.tests.conftest import login, make_ngo_admin

API = "/api/v1"
OPP = {"title": "Helper", "required_skills": [], "interests": [], "availability": []}


def post_opp(client, headers, **kw):
    return client.post(f"{API}/opportunities", json={**OPP, **kw}, headers=headers).json()["id"]


def apply(client, headers, oid):
    return client.post(f"{API}/opportunities/{oid}/applications", headers=headers)


def review(client, headers, aid, status, note=None):
    return client.patch(f"{API}/applications/{aid}/review", json={"status": status, "note": note}, headers=headers)


def accept(client, ngo_headers, vol_headers, oid):
    aid = apply(client, vol_headers, oid).json()["id"]
    assert review(client, ngo_headers, aid, "UNDER_REVIEW").status_code == 200
    assert review(client, ngo_headers, aid, "ACCEPTED").status_code == 200
    return aid


def vol_id(client, headers):
    return client.get(f"{API}/volunteers/me", headers=headers).json()["id"]


def campaign(client, headers, activate=True):
    cid = client.post(f"{API}/campaigns", json={"title": "C", "start_date": "2026-01-01",
                                                "end_date": "2026-12-01"}, headers=headers).json()["id"]
    if activate:
        client.post(f"{API}/campaigns/{cid}/status", json={"status": "ACTIVE"}, headers=headers)
    return cid


# ---------------------------------------------------------------- applications

def test_apply_and_list(client, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    r = apply(client, volunteer_headers, oid)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "SUBMITTED" and body["opportunity_title"] == "Helper"
    mine = client.get(f"{API}/applications/me", headers=volunteer_headers).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == body["id"]


def test_duplicate_application_409(client, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    apply(client, volunteer_headers, oid)
    assert apply(client, volunteer_headers, oid).status_code == 409


def test_only_volunteers_apply_and_target_must_be_open(client, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    assert apply(client, ngo_headers, oid).status_code == 403
    assert apply(client, volunteer_headers, 999).status_code == 404
    client.delete(f"{API}/opportunities/{oid}", headers=ngo_headers)
    assert apply(client, volunteer_headers, oid).status_code == 409


def test_review_queue_scoped_to_own_ngo(client, ngo_headers, other_ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    apply(client, volunteer_headers, oid)
    q = client.get(f"{API}/applications", headers=ngo_headers).json()
    assert q["total"] == 1 and q["items"][0]["volunteer_name"]
    assert "email" not in str(q["items"][0])
    assert client.get(f"{API}/applications", headers=other_ngo_headers).json()["total"] == 0
    assert client.get(f"{API}/applications", headers=volunteer_headers).status_code == 403
    assert client.get(f"{API}/applications?status=ACCEPTED", headers=ngo_headers).json()["total"] == 0


def test_application_state_machine(client, db, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    assert review(client, ngo_headers, aid, "ACCEPTED").status_code == 409  # must be reviewed first
    assert review(client, ngo_headers, aid, "SUBMITTED").status_code == 422
    assert review(client, ngo_headers, aid, "UNDER_REVIEW").status_code == 200
    assert review(client, ngo_headers, aid, "UNDER_REVIEW").status_code == 409
    r = review(client, ngo_headers, aid, "REJECTED", "Not a fit")
    assert r.status_code == 200 and r.json()["review_note"] == "Not a fit"
    for target in ("ACCEPTED", "UNDER_REVIEW", "REJECTED"):
        r = review(client, ngo_headers, aid, target)
        assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"
    assert db.get(Application, aid).status == ApplicationStatus.REJECTED
    actions = [a.action_type for a in db.query(AuditLog).order_by(AuditLog.id)]
    assert actions == ["CREATE_OPPORTUNITY", "APPLICATION_UNDER_REVIEW", "APPLICATION_REJECTED"]


def test_review_permissions(client, ngo_headers, other_ngo_headers, volunteer_headers, db):
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    assert review(client, other_ngo_headers, aid, "UNDER_REVIEW").status_code == 403
    assert review(client, volunteer_headers, aid, "UNDER_REVIEW").status_code == 403
    assert review(client, ngo_headers, 999, "UNDER_REVIEW").status_code == 404
    make_ngo_admin(db, "pending@example.com", verified=False)
    assert review(client, login(client, "pending@example.com"), aid, "UNDER_REVIEW").status_code == 403


# ---------------------------------------------------------------------- tasks

def make_task(client, headers, cid, **kw):
    r = client.post(f"{API}/tasks", json={"campaign_id": cid, "task_name": "Pack boxes", **kw}, headers=headers)
    return r


def test_create_unassigned_task(client, db, ngo_headers):
    cid = campaign(client, ngo_headers)
    r = make_task(client, ngo_headers, cid, deadline="2026-06-01")
    assert r.status_code == 201
    assert r.json()["status"] == "PENDING" and r.json()["volunteer_id"] is None
    assert db.query(AuditLog).filter_by(action_type="CREATE_TASK").count() == 1


def test_task_requires_accepted_application(client, ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    vid = vol_id(client, volunteer_headers)
    # no application at all
    r = make_task(client, ngo_headers, cid, volunteer_id=vid)
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_ELIGIBLE"
    # submitted / under review / rejected are not enough
    aid = apply(client, volunteer_headers, oid).json()["id"]
    assert make_task(client, ngo_headers, cid, volunteer_id=vid).status_code == 409
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    assert make_task(client, ngo_headers, cid, volunteer_id=vid).status_code == 409
    review(client, ngo_headers, aid, "ACCEPTED")
    assert make_task(client, ngo_headers, cid, volunteer_id=vid).status_code == 201


def test_rejected_volunteer_cannot_get_task(client, ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    review(client, ngo_headers, aid, "REJECTED")
    t = make_task(client, ngo_headers, cid).json()
    r = client.post(f"{API}/tasks/{t['id']}/assign", json={"volunteer_id": vol_id(client, volunteer_headers)},
                    headers=ngo_headers)
    assert r.status_code == 409


def test_acceptance_is_per_ngo_and_per_opportunity(client, ngo_headers, other_ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    other_oid = post_opp(client, other_ngo_headers)
    mine_oid = post_opp(client, ngo_headers, title="Mine")
    accept(client, other_ngo_headers, volunteer_headers, other_oid)
    vid = vol_id(client, volunteer_headers)
    # accepted by someone else's NGO doesn't count
    assert make_task(client, ngo_headers, cid, volunteer_id=vid).status_code == 409
    accept(client, ngo_headers, volunteer_headers, mine_oid)
    other_mine = post_opp(client, ngo_headers, title="Another")
    # task tied to an opportunity needs acceptance for THAT opportunity
    assert make_task(client, ngo_headers, cid, volunteer_id=vid, opportunity_id=other_mine).status_code == 409
    assert make_task(client, ngo_headers, cid, volunteer_id=vid, opportunity_id=mine_oid).status_code == 201


def test_task_ownership(client, ngo_headers, other_ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    assert make_task(client, other_ngo_headers, cid).status_code == 403
    assert make_task(client, volunteer_headers, cid).status_code == 403
    assert make_task(client, ngo_headers, 999).status_code == 404
    foreign_opp = post_opp(client, other_ngo_headers)
    assert make_task(client, ngo_headers, cid, opportunity_id=foreign_opp).status_code == 422
    t = make_task(client, ngo_headers, cid).json()
    assert client.patch(f"{API}/tasks/{t['id']}", json={"task_name": "x"}, headers=other_ngo_headers).status_code == 403
    assert client.post(f"{API}/tasks/{t['id']}/assign", json={"volunteer_id": 1},
                       headers=other_ngo_headers).status_code == 403


def test_assign_then_volunteer_lifecycle(client, db, ngo_headers, volunteer_headers, volunteer2_headers):
    cid = campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, oid)
    t = make_task(client, ngo_headers, cid).json()
    r = client.post(f"{API}/tasks/{t['id']}/assign", json={"volunteer_id": vol_id(client, volunteer_headers)},
                    headers=ngo_headers)
    assert r.status_code == 200 and r.json()["volunteer_name"]
    assert db.query(AuditLog).filter_by(action_type="ASSIGN_TASK").count() == 1

    url = f"{API}/tasks/{t['id']}/status"

    def move(headers, status):
        return client.patch(url, json={"status": status}, headers=headers)

    assert move(volunteer2_headers, "ACCEPTED").status_code == 404  # not their task
    assert move(ngo_headers, "ACCEPTED").status_code == 403  # admins don't drive volunteer status
    assert move(volunteer_headers, "IN_PROGRESS").status_code == 409  # can't skip ACCEPTED
    assert move(volunteer_headers, "COMPLETED").status_code == 409
    assert move(volunteer_headers, "ACCEPTED").status_code == 200
    assert move(volunteer_headers, "DECLINED").status_code == 409  # too late to decline
    assert move(volunteer_headers, "IN_PROGRESS").status_code == 200
    assert move(volunteer_headers, "ACCEPTED").status_code == 409  # no going back
    r = move(volunteer_headers, "COMPLETED")
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"
    r = move(volunteer_headers, "IN_PROGRESS")
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"
    assert db.get(Task, t["id"]).status.value == "COMPLETED"


def test_decline_and_reassign(client, ngo_headers, volunteer_headers, volunteer2_headers):
    cid = campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, oid)
    accept(client, ngo_headers, volunteer2_headers, oid)
    t = make_task(client, ngo_headers, cid, volunteer_id=vol_id(client, volunteer_headers)).json()
    url = f"{API}/tasks/{t['id']}/status"
    assert client.patch(url, json={"status": "DECLINED"}, headers=volunteer_headers).status_code == 200
    assert client.patch(url, json={"status": "ACCEPTED"}, headers=volunteer_headers).status_code == 409
    r = client.post(f"{API}/tasks/{t['id']}/assign", json={"volunteer_id": vol_id(client, volunteer2_headers)},
                    headers=ngo_headers)
    assert r.status_code == 200 and r.json()["status"] == "PENDING"
    assert client.patch(url, json={"status": "ACCEPTED"}, headers=volunteer2_headers).status_code == 200
    # an accepted task can't be yanked away
    again = client.post(f"{API}/tasks/{t['id']}/assign",
                        json={"volunteer_id": vol_id(client, volunteer_headers)}, headers=ngo_headers)
    assert again.status_code == 409


def test_unassigned_task_cannot_be_actioned(client, ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    t = make_task(client, ngo_headers, cid).json()
    r = client.patch(f"{API}/tasks/{t['id']}/status", json={"status": "ACCEPTED"}, headers=volunteer_headers)
    assert r.status_code == 404


def test_task_lists(client, ngo_headers, volunteer_headers, volunteer2_headers):
    cid = campaign(client, ngo_headers)
    oid = post_opp(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, oid)
    vid = vol_id(client, volunteer_headers)
    make_task(client, ngo_headers, cid, volunteer_id=vid, task_name="Mine")
    make_task(client, ngo_headers, cid, task_name="Unassigned")
    mine = client.get(f"{API}/tasks/me", headers=volunteer_headers).json()
    assert [t["task_name"] for t in mine["items"]] == ["Mine"]
    assert client.get(f"{API}/tasks/me", headers=volunteer2_headers).json()["total"] == 0
    assert client.get(f"{API}/tasks/me?status=COMPLETED", headers=volunteer_headers).json()["total"] == 0
    assert client.get(f"{API}/tasks", headers=ngo_headers).json()["total"] == 2
    assert client.get(f"{API}/tasks?volunteer_id={vid}", headers=ngo_headers).json()["total"] == 1
    assert client.get(f"{API}/tasks", headers=volunteer_headers).status_code == 403


def test_closed_campaign_blocks_tasks(client, ngo_headers):
    cid = campaign(client, ngo_headers)
    t = make_task(client, ngo_headers, cid).json()
    client.post(f"{API}/campaigns/{cid}/status", json={"status": "COMPLETED"}, headers=ngo_headers)
    assert make_task(client, ngo_headers, cid).status_code == 409
    assert client.patch(f"{API}/tasks/{t['id']}", json={"task_name": "x"}, headers=ngo_headers).status_code == 409


def test_update_task(client, db, ngo_headers):
    cid = campaign(client, ngo_headers)
    t = make_task(client, ngo_headers, cid).json()
    r = client.patch(f"{API}/tasks/{t['id']}", json={"task_name": "Renamed", "deadline": "2026-09-09"}, headers=ngo_headers)
    assert r.status_code == 200 and r.json()["task_name"] == "Renamed"
    assert client.patch(f"{API}/tasks/{t['id']}", json={"task_name": None}, headers=ngo_headers).status_code == 422
    assert client.patch(f"{API}/tasks/{t['id']}", json={"status": "COMPLETED"}, headers=ngo_headers).status_code == 422
