import pytest
from starlette.websockets import WebSocketDisconnect

from app.models import AuditLog, Notification, NotificationStatus
from app.services import notifications as svc
from app.tests.conftest import login, make_ngo_admin, make_user
from app.tests.test_finance import active_campaign, donate, set_status
from app.tests.test_impact import make_event
from app.tests.test_workflow import accept, apply, campaign, make_task, post_opp, review, vol_id

API = "/api/v1"


def token(headers):
    return headers["Authorization"].split()[1]


def inbox(client, headers, **params):
    return client.get(f"{API}/notifications", params=params, headers=headers).json()


# ------------------------------------------------------------ triggers (REST)

def test_application_flow_notifies_both_sides(client, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    first = inbox(client, ngo_headers)
    assert first["total"] == 1 and first["items"][0]["title"] == "New application"
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    review(client, ngo_headers, aid, "ACCEPTED")
    items = inbox(client, volunteer_headers)["items"]
    assert [i["message"] for i in items] == [
        'Your application for "Helper" is now accepted.', 'Your application for "Helper" is now under review.']
    assert items[0]["priority"] == "HIGH" and items[0]["notification_type"] == "APPLICATION_UPDATE"
    assert items[0]["link"] == "/applications"


def test_task_assignment_and_status_notifications(client, ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    t = make_task(client, ngo_headers, cid, volunteer_id=vol_id(client, volunteer_headers)).json()
    assigned = inbox(client, volunteer_headers, notification_type="TASK_ASSIGNED")
    assert assigned["total"] == 1 and "Pack boxes" in assigned["items"][0]["message"]
    client.patch(f"{API}/tasks/{t['id']}/status", json={"status": "ACCEPTED"}, headers=volunteer_headers)
    updates = inbox(client, ngo_headers, notification_type="TASK_UPDATE")
    assert updates["total"] == 1 and "accepted" in updates["items"][0]["message"]


def test_donation_notifications(client, ngo_headers, donor_headers):
    cid = active_campaign(client, ngo_headers)
    did = donate(client, donor_headers, cid).json()["id"]
    assert inbox(client, ngo_headers, notification_type="DONATION_UPDATE")["total"] == 1
    set_status(client, ngo_headers, did, "RECEIVED")
    mine = inbox(client, donor_headers)
    assert mine["total"] == 1 and "received" in mine["items"][0]["message"]


def test_attendance_notification(client, ngo_headers, volunteer_headers):
    cid = campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    eid = make_event(client, ngo_headers, cid)
    client.post(f"{API}/participation", headers=ngo_headers,
                json={"event_id": eid, "volunteer_id": vol_id(client, volunteer_headers), "hours": 3})
    n = inbox(client, volunteer_headers, notification_type="ATTENDANCE")
    assert n["total"] == 1 and n["items"][0]["priority"] == "LOW"


def test_campaign_update_reaches_volunteers_and_donors(client, ngo_headers, volunteer_headers, donor_headers,
                                                       donor2_headers):
    cid = active_campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    donate(client, donor_headers, cid)
    client.post(f"{API}/campaigns/{cid}/status", json={"status": "COMPLETED"}, headers=ngo_headers)
    for h in (volunteer_headers, donor_headers):
        assert inbox(client, h, notification_type="CAMPAIGN_UPDATE")["total"] == 1
    assert inbox(client, donor2_headers)["total"] == 0  # unrelated donor hears nothing


def test_event_reminder(client, ngo_headers, volunteer_headers, other_ngo_headers):
    cid = campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    future = client.post(f"{API}/events", headers=ngo_headers, json={
        "campaign_id": cid, "event_name": "Big day", "event_date": "2026-11-20", "location": "Dhaka"}).json()["id"]
    past = make_event(client, ngo_headers, cid)
    assert client.post(f"{API}/events/{future}/reminders", headers=other_ngo_headers).status_code == 403
    assert client.post(f"{API}/events/{past}/reminders", headers=ngo_headers).status_code == 409
    r = client.post(f"{API}/events/{future}/reminders", headers=ngo_headers)
    assert r.status_code == 200 and r.json() == {"recipients": 1, "audience_size": 1}
    again = client.post(f"{API}/events/{future}/reminders", headers=ngo_headers)
    assert again.json()["recipients"] == 0  # deduped: the first reminder is still unread
    n = inbox(client, volunteer_headers, notification_type="EVENT_REMINDER")
    assert n["total"] == 1 and "Big day" in n["items"][0]["message"]


# ------------------------------------------------------------------ inbox API

def test_inbox_filters_read_and_privacy(client, db, ngo_headers, volunteer_headers, volunteer2_headers):
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    review(client, ngo_headers, aid, "ACCEPTED")
    assert client.get(f"{API}/notifications/unread-count", headers=volunteer_headers).json() == {
        "unread": 2, "high_priority_unread": 1}
    assert inbox(client, volunteer_headers, priority="HIGH")["total"] == 1
    assert inbox(client, volunteer_headers, status="READ")["total"] == 0
    nid = inbox(client, volunteer_headers)["items"][0]["id"]
    assert client.patch(f"{API}/notifications/{nid}/read", headers=volunteer2_headers).status_code == 404
    assert client.patch(f"{API}/notifications/{nid}/read", headers=volunteer_headers).json()["status"] == "READ"
    assert client.get(f"{API}/notifications/unread-count", headers=volunteer_headers).json()["unread"] == 1
    assert client.patch(f"{API}/notifications/read-all", headers=volunteer_headers).status_code == 204
    assert client.get(f"{API}/notifications/unread-count", headers=volunteer_headers).json()["unread"] == 0
    assert client.patch(f"{API}/notifications/read-all", headers=volunteer2_headers).status_code == 204
    assert client.get(f"{API}/notifications").status_code == 401
    assert db.query(Notification).filter_by(status=NotificationStatus.READ).count() == 2


def test_notify_dedupes_unread_only(db, volunteer_headers):
    from app.models import NotificationType, User

    uid = db.query(User).one().id
    kw = {"title": "T", "message": "m", "type": NotificationType.ANNOUNCEMENT, "dedupe_key": "k"}
    assert svc.notify(db, [uid], **kw) == 1
    assert svc.notify(db, [uid], **kw) == 0  # identical unread alert is not repeated
    db.query(Notification).update({"status": NotificationStatus.READ})
    assert svc.notify(db, [uid], **kw) == 1  # once read, the same alert may fire again


def test_notification_failure_never_breaks_core_flow(client, monkeypatch, ngo_headers, volunteer_headers):
    def boom(*a, **k):
        raise RuntimeError("delivery exploded")

    monkeypatch.setattr(svc, "Notification", boom)  # notify() fails while building rows
    oid = post_opp(client, ngo_headers)
    r = apply(client, volunteer_headers, oid)
    assert r.status_code == 201  # the application still went through
    assert inbox(client, ngo_headers)["total"] == 0


def test_live_delivery_failure_is_swallowed(client, monkeypatch, ngo_headers, volunteer_headers):
    from app.ws.manager import manager

    def boom(_):
        raise RuntimeError("socket layer down")

    monkeypatch.setattr(manager, "publish", boom)
    r = apply(client, volunteer_headers, post_opp(client, ngo_headers))
    assert r.status_code == 201
    assert inbox(client, ngo_headers)["total"] == 1  # still persisted


# ---------------------------------------------------------------- announcements

def test_announcement_audience_and_audit(client, db, ngo_headers, other_ngo_headers, volunteer_headers,
                                         volunteer2_headers, donor_headers, donor2_headers):
    cid = active_campaign(client, ngo_headers)
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    donate(client, donor_headers, cid)
    body = {"title": "Meeting", "message": "Volunteer meeting on Friday."}
    r = client.post(f"{API}/announcements", json={**body, "audience": "VOLUNTEERS"}, headers=ngo_headers)
    assert r.status_code == 201 and r.json() == {"recipients": 1, "audience_size": 1, "emergency": False}
    assert inbox(client, volunteer_headers, notification_type="ANNOUNCEMENT")["total"] == 1
    assert inbox(client, donor_headers, notification_type="ANNOUNCEMENT")["total"] == 0
    r = client.post(f"{API}/announcements", json={**body, "title": "Update", "audience": "ALL"}, headers=ngo_headers)
    assert r.json()["recipients"] == 2
    assert inbox(client, volunteer2_headers)["total"] == 0 and inbox(client, donor2_headers)["total"] == 0
    assert db.query(AuditLog).filter_by(action_type="SEND_ANNOUNCEMENT").count() == 2
    # sending the same message again does not repeat it while the first is unread
    again = client.post(f"{API}/announcements", json={**body, "audience": "VOLUNTEERS"}, headers=ngo_headers)
    assert again.json() == {"recipients": 0, "audience_size": 1, "emergency": False}
    # another NGO has no audience of its own
    other = client.post(f"{API}/announcements", json=body, headers=other_ngo_headers)
    assert other.json()["audience_size"] == 0


def test_emergency_alert_is_high_priority(client, db, ngo_headers, volunteer_headers):
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    r = client.post(f"{API}/announcements", headers=ngo_headers,
                    json={"title": "FLOOD", "message": "Evacuate zone B", "priority": "HIGH", "audience": "VOLUNTEERS"})
    assert r.json()["emergency"] is True
    n = inbox(client, volunteer_headers, priority="HIGH", notification_type="EMERGENCY_ALERT")
    assert n["total"] == 1 and n["items"][0]["title"] == "FLOOD"
    assert db.query(AuditLog).filter_by(action_type="SEND_EMERGENCY_ALERT").count() == 1


def test_announcement_permissions_and_validation(client, db, ngo_headers, volunteer_headers):
    ok = {"title": "A", "message": "B"}
    assert client.post(f"{API}/announcements", json=ok, headers=volunteer_headers).status_code == 403
    assert client.post(f"{API}/announcements", json=ok).status_code == 401
    make_ngo_admin(db, "pending@example.com", verified=False)
    assert client.post(f"{API}/announcements", json=ok, headers=login(client, "pending@example.com")
                       ).status_code == 403
    for bad in ({**ok, "message": "  "}, {**ok, "audience": "EVERYONE"}, {**ok, "priority": "LOW"},
                {**ok, "message": "x" * 1001}):
        assert client.post(f"{API}/announcements", json=bad, headers=ngo_headers).status_code == 422
    assert client.post(f"{API}/announcements", json={**ok, "campaign_id": 999}, headers=ngo_headers
                       ).status_code == 404


# ------------------------------------------------------------------ WebSocket

def test_ws_rejects_missing_and_bad_tokens(client):
    for url in ("/ws/notifications", "/ws/notifications?token=garbage"):
        with pytest.raises(WebSocketDisconnect), client.websocket_connect(url):
            pass


def test_ws_rejects_inactive_user_and_wrong_secret(client, db):
    user = make_user(db, "gone@example.com")
    headers = login(client, "gone@example.com")
    user.is_active = False
    db.commit()
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/notifications?token={token(headers)}"):
        pass


def test_ws_connect_reports_unread_and_pings(client, ngo_headers, volunteer_headers):
    apply(client, volunteer_headers, post_opp(client, ngo_headers))
    with client.websocket_connect(f"/ws/notifications?token={token(ngo_headers)}") as ws:
        assert ws.receive_json() == {"event": "connected", "unread": 1}
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_ws_receives_live_notification_after_commit(client, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    with client.websocket_connect(f"/ws/notifications?token={token(volunteer_headers)}") as ws:
        assert ws.receive_json()["event"] == "connected"
        review(client, ngo_headers, aid, "ACCEPTED")
        msg = ws.receive_json()
    assert msg["event"] == "notification"
    assert msg["notification"]["message"] == 'Your application for "Helper" is now accepted.'
    assert msg["notification"]["priority"] == "HIGH" and msg["notification"]["status"] == "UNREAD"


def test_ws_only_delivers_to_the_target_user(client, ngo_headers, volunteer_headers, volunteer2_headers):
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    review(client, ngo_headers, aid, "UNDER_REVIEW")
    with client.websocket_connect(f"/ws/notifications?token={token(volunteer2_headers)}") as other, \
            client.websocket_connect(f"/ws/notifications?token={token(volunteer_headers)}") as target:
        other.receive_json()
        target.receive_json()
        review(client, ngo_headers, aid, "ACCEPTED")
        assert target.receive_json()["event"] == "notification"
        other.send_text("ping")
        assert other.receive_text() == "pong"  # the next thing 'other' sees is our ping, not the alert


def test_ws_emergency_broadcast(client, ngo_headers, volunteer_headers):
    accept(client, ngo_headers, volunteer_headers, post_opp(client, ngo_headers))
    with client.websocket_connect(f"/ws/notifications?token={token(volunteer_headers)}") as ws:
        ws.receive_json()
        client.post(f"{API}/announcements", headers=ngo_headers, json={
            "title": "FLOOD", "message": "Go now", "priority": "HIGH", "audience": "VOLUNTEERS"})
        msg = ws.receive_json()
    assert msg["notification"]["notification_type"] == "EMERGENCY_ALERT"


def test_disconnected_user_still_gets_persisted_notification(client, ngo_headers, volunteer_headers):
    oid = post_opp(client, ngo_headers)
    aid = apply(client, volunteer_headers, oid).json()["id"]
    assert review(client, ngo_headers, aid, "UNDER_REVIEW").status_code == 200  # nobody connected
    assert inbox(client, volunteer_headers)["total"] == 1
