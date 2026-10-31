from app.models import AuditLog, Donation, Resource
from app.tests.conftest import login, make_ngo_admin

API = "/api/v1"


def active_campaign(client, headers, title="Flood Relief"):
    cid = client.post(f"{API}/campaigns", json={"title": title, "start_date": "2026-01-01",
                                                "end_date": "2026-12-31"}, headers=headers).json()["id"]
    client.post(f"{API}/campaigns/{cid}/status", json={"status": "ACTIVE"}, headers=headers)
    return cid


def donate(client, headers, cid, **kw):
    body = {"campaign_id": cid, "donation_type": "MONEY", "amount": 500, **kw}
    return client.post(f"{API}/donations", json=body, headers=headers)


def set_status(client, headers, did, status):
    return client.patch(f"{API}/donations/{did}/status", json={"status": status}, headers=headers)


# ------------------------------------------------------------------ donations

def test_donate_and_history(client, ngo_headers, donor_headers, donor2_headers):
    cid = active_campaign(client, ngo_headers)
    r = donate(client, donor_headers, cid, note="For the flood")
    assert r.status_code == 201
    d = r.json()
    assert d["status"] == "PENDING" and d["amount"] == 500 and d["campaign_title"] == "Flood Relief"
    mine = client.get(f"{API}/donations/me", headers=donor_headers).json()
    assert mine["total"] == 1
    assert client.get(f"{API}/donations/me", headers=donor2_headers).json()["total"] == 0
    assert client.get(f"{API}/donations/me?status=RECEIVED", headers=donor_headers).json()["total"] == 0


def test_only_donors_donate(client, ngo_headers, volunteer_headers, beneficiary_headers):
    cid = active_campaign(client, ngo_headers)
    for h in (ngo_headers, volunteer_headers, beneficiary_headers):
        assert donate(client, h, cid).status_code == 403
    assert donate(client, {}, cid).status_code == 401


def test_donation_validation(client, ngo_headers, donor_headers):
    cid = active_campaign(client, ngo_headers)
    assert donate(client, donor_headers, cid, amount=0).status_code == 422  # money needs an amount
    assert donate(client, donor_headers, cid, amount=-5).status_code == 422
    assert donate(client, donor_headers, cid, donation_type="BITCOIN").status_code == 422
    assert donate(client, donor_headers, 999).status_code == 404
    ok = donate(client, donor_headers, cid, donation_type="FOOD", amount=0, note="50 kg rice")
    assert ok.status_code == 201 and ok.json()["donation_type"] == "FOOD"


def test_payment_details_never_accepted(client, db, ngo_headers, donor_headers):
    cid = active_campaign(client, ngo_headers)
    for field in ("card_number", "cvv", "bank_account", "payment_payload"):
        r = donate(client, donor_headers, cid, **{field: "4242424242424242"})
        assert r.status_code == 422, field
    assert db.query(Donation).count() == 0
    assert not {c.name for c in Donation.__table__.columns} & {"card_number", "cvv", "bank_account"}


def test_cannot_donate_to_draft_or_closed_campaign(client, ngo_headers, donor_headers):
    draft = client.post(f"{API}/campaigns", json={"title": "D", "start_date": "2026-01-01",
                                                  "end_date": "2026-02-01"}, headers=ngo_headers).json()["id"]
    assert donate(client, donor_headers, draft).status_code == 404
    cid = active_campaign(client, ngo_headers)
    client.post(f"{API}/campaigns/{cid}/status", json={"status": "COMPLETED"}, headers=ngo_headers)
    assert donate(client, donor_headers, cid).status_code == 409


def test_ngo_confirms_donation(client, db, ngo_headers, other_ngo_headers, donor_headers):
    cid = active_campaign(client, ngo_headers)
    did = donate(client, donor_headers, cid).json()["id"]
    q = client.get(f"{API}/donations?status=PENDING", headers=ngo_headers).json()
    assert q["total"] == 1 and q["items"][0]["donor_name"] == "Donor One"
    assert client.get(f"{API}/donations", headers=other_ngo_headers).json()["total"] == 0
    assert set_status(client, other_ngo_headers, did, "RECEIVED").status_code == 403
    assert set_status(client, donor_headers, did, "RECEIVED").status_code == 403
    assert set_status(client, ngo_headers, did, "PENDING").status_code == 422
    assert set_status(client, ngo_headers, did, "RECEIVED").json()["status"] == "RECEIVED"
    r = set_status(client, ngo_headers, did, "REJECTED")
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"
    assert db.query(AuditLog).filter_by(action_type="DONATION_RECEIVED").count() == 1


def test_donation_summary(client, ngo_headers, other_ngo_headers, donor_headers, platform_headers,
                          volunteer_headers):
    c1 = active_campaign(client, ngo_headers, "A")
    c2 = active_campaign(client, ngo_headers, "B")
    for amount, cid, final in ((100, c1, "RECEIVED"), (250.5, c1, "RECEIVED"), (40, c1, None),
                               (900, c2, "REJECTED")):
        did = donate(client, donor_headers, cid, amount=amount).json()["id"]
        if final:
            set_status(client, ngo_headers, did, final)
    food = donate(client, donor_headers, c1, donation_type="FOOD", amount=0).json()["id"]
    set_status(client, ngo_headers, food, "RECEIVED")

    rows = {r["campaign_title"]: r for r in
            client.get(f"{API}/reports/donation-summary", headers=ngo_headers).json()["items"]}
    a = rows["A"]
    assert a["money_received"] == 350.5 and a["money_pending"] == 40
    assert a["donation_count"] == 3 and a["donor_count"] == 1 and a["by_type"] == {"MONEY": 2, "FOOD": 1}
    assert rows["B"]["money_received"] == 0
    assert client.get(f"{API}/reports/donation-summary", headers=other_ngo_headers).json()["total"] == 0
    assert client.get(f"{API}/reports/donation-summary", headers=platform_headers).json()["total"] == 2
    assert client.get(f"{API}/reports/donation-summary", headers=volunteer_headers).status_code == 403


# ------------------------------------------------------------------ resources

def add_resource(client, headers, cid, **kw):
    return client.post(f"{API}/campaigns/{cid}/resources",
                       json={"name": "Rice", "quantity_total": 100, "unit": "kg", **kw}, headers=headers)


def enroll(client, headers, cid, **kw):
    return client.post(f"{API}/campaigns/{cid}/beneficiaries", json={"name": "Rahim", "location": "Sylhet", **kw},
                       headers=headers)


def test_resource_crud_and_limits(client, db, ngo_headers, other_ngo_headers, volunteer_headers):
    cid = active_campaign(client, ngo_headers)
    r = add_resource(client, ngo_headers, cid)
    assert r.status_code == 201 and r.json()["quantity_remaining"] == 100
    rid = r.json()["id"]
    assert add_resource(client, other_ngo_headers, cid).status_code == 403
    assert add_resource(client, volunteer_headers, cid).status_code == 403
    assert add_resource(client, ngo_headers, cid, quantity_total=-1).status_code == 422
    assert client.get(f"{API}/campaigns/{cid}/resources", headers=other_ngo_headers).status_code == 403
    assert len(client.get(f"{API}/campaigns/{cid}/resources", headers=ngo_headers).json()) == 1
    url = f"{API}/resources/{rid}"
    assert client.patch(url, json={"quantity_total": 150}, headers=ngo_headers).json()["quantity_total"] == 150
    assert client.patch(url, json={"quantity_allocated": 5}, headers=ngo_headers).status_code == 422
    assert client.patch(url, json={"name": "x"}, headers=other_ngo_headers).status_code == 403
    assert db.query(AuditLog).filter_by(action_type="CREATE_RESOURCE").count() == 1


def test_distribution_decrements_stock_and_blocks_overallocation(client, db, ngo_headers):
    cid = active_campaign(client, ngo_headers)
    rid = add_resource(client, ngo_headers, cid).json()["id"]
    bid = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    url = f"{API}/resources/{rid}/distributions"
    r = client.post(url, json={"beneficiary_id": bid, "quantity": 60}, headers=ngo_headers)
    assert r.status_code == 201 and r.json()["beneficiary_name"] == "Rahim"
    assert db.get(Resource, rid).quantity_allocated == 60
    over = client.post(url, json={"beneficiary_id": bid, "quantity": 41}, headers=ngo_headers)
    assert over.status_code == 409
    assert db.get(Resource, rid).quantity_allocated == 60  # unchanged by the failed attempt
    assert client.post(url, json={"beneficiary_id": bid, "quantity": 40}, headers=ngo_headers).status_code == 201
    assert client.post(url, json={"beneficiary_id": bid, "quantity": 1}, headers=ngo_headers).status_code == 409
    assert client.post(url, json={"beneficiary_id": bid, "quantity": 0}, headers=ngo_headers).status_code == 422
    # cannot shrink total below what's already gone out
    assert client.patch(f"{API}/resources/{rid}", json={"quantity_total": 50}, headers=ngo_headers).status_code == 409
    listing = client.get(url, headers=ngo_headers).json()
    assert listing["total"] == 2 and sum(d["quantity"] for d in listing["items"]) == 100


def test_distribution_needs_enrolled_beneficiary_and_ownership(client, ngo_headers, other_ngo_headers):
    cid = active_campaign(client, ngo_headers)
    other_cid = active_campaign(client, other_ngo_headers, "Other")
    rid = add_resource(client, ngo_headers, cid).json()["id"]
    foreign = enroll(client, other_ngo_headers, other_cid).json()["beneficiary_id"]
    url = f"{API}/resources/{rid}/distributions"
    assert client.post(url, json={"beneficiary_id": foreign, "quantity": 1}, headers=ngo_headers).status_code == 409
    assert client.post(url, json={"beneficiary_id": foreign, "quantity": 1}, headers=other_ngo_headers).status_code == 403
    assert client.get(url, headers=other_ngo_headers).status_code == 403


def test_archived_campaign_blocks_finance_writes(client, ngo_headers):
    cid = active_campaign(client, ngo_headers)
    rid = add_resource(client, ngo_headers, cid).json()["id"]
    bid = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    client.delete(f"{API}/campaigns/{cid}", headers=ngo_headers)
    assert add_resource(client, ngo_headers, cid).status_code == 409
    assert enroll(client, ngo_headers, cid, name="Another").status_code == 409
    assert client.post(f"{API}/resources/{rid}/distributions", json={"beneficiary_id": bid, "quantity": 1},
                       headers=ngo_headers).status_code == 409


# ------------------------------------------------------------- beneficiaries

def test_enroll_new_and_registered_beneficiary(client, db, ngo_headers, beneficiary_headers):
    cid = active_campaign(client, ngo_headers)
    assert enroll(client, ngo_headers, cid).status_code == 201
    assert client.post(f"{API}/campaigns/{cid}/beneficiaries", json={}, headers=ngo_headers).status_code == 422
    r = client.post(f"{API}/campaigns/{cid}/beneficiaries", json={"email": "ben@example.com"}, headers=ngo_headers)
    assert r.status_code == 201 and r.json()["name"] == "Ben Eficiary" and r.json()["support_status"] == "PENDING"
    assert client.post(f"{API}/campaigns/{cid}/beneficiaries", json={"email": "ben@example.com"},
                       headers=ngo_headers).status_code == 409
    assert client.post(f"{API}/campaigns/{cid}/beneficiaries", json={"email": "ngo@example.com"},
                       headers=ngo_headers).status_code == 404  # only real beneficiary accounts
    assert len(client.get(f"{API}/campaigns/{cid}/beneficiaries", headers=ngo_headers).json()) == 2


def test_beneficiary_data_is_private(client, ngo_headers, other_ngo_headers, volunteer_headers, donor_headers,
                                     beneficiary_headers):
    cid = active_campaign(client, ngo_headers)
    enroll(client, ngo_headers, cid)
    url = f"{API}/campaigns/{cid}/beneficiaries"
    for h in (volunteer_headers, donor_headers, beneficiary_headers, other_ngo_headers):
        assert client.get(url, headers=h).status_code == 403
    assert client.get(url).status_code == 401
    assert client.post(url, json={"name": "x"}, headers=other_ngo_headers).status_code == 403


def test_support_status_update(client, db, ngo_headers, other_ngo_headers):
    cid = active_campaign(client, ngo_headers)
    bid = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    url = f"{API}/campaigns/{cid}/beneficiaries/{bid}"
    assert client.patch(url, json={"support_status": "ACTIVE"}, headers=ngo_headers).json()["support_status"] == "ACTIVE"
    assert client.patch(url, json={"support_status": "NOPE"}, headers=ngo_headers).status_code == 422
    assert client.patch(url, json={"support_status": "COMPLETED"}, headers=other_ngo_headers).status_code == 403
    assert client.patch(f"{API}/campaigns/{cid}/beneficiaries/999", json={"support_status": "ACTIVE"},
                        headers=ngo_headers).status_code == 404
    assert db.query(AuditLog).filter_by(action_type="UPDATE_SUPPORT_STATUS").count() == 1


def test_beneficiary_sees_only_own_support(client, ngo_headers, beneficiary_headers):
    cid = active_campaign(client, ngo_headers)
    rid = add_resource(client, ngo_headers, cid).json()["id"]
    mine = client.post(f"{API}/campaigns/{cid}/beneficiaries", json={"email": "ben@example.com"},
                       headers=ngo_headers).json()["beneficiary_id"]
    other = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    client.post(f"{API}/resources/{rid}/distributions", json={"beneficiary_id": mine, "quantity": 10}, headers=ngo_headers)
    client.post(f"{API}/resources/{rid}/distributions", json={"beneficiary_id": other, "quantity": 30}, headers=ngo_headers)
    support = client.get(f"{API}/support/me", headers=beneficiary_headers).json()
    assert len(support) == 1 and support[0]["campaign_title"] == "Flood Relief"
    assert [x["quantity"] for x in support[0]["received"]] == [10]
    assert "30" not in str(support)
    assert client.get(f"{API}/support/me", headers=ngo_headers).status_code == 403


# --------------------------------------------------------------- utilization

def test_utilization_access(client, db, ngo_headers, other_ngo_headers, donor_headers, donor2_headers,
                            volunteer_headers, platform_headers):
    cid = active_campaign(client, ngo_headers)
    rid = add_resource(client, ngo_headers, cid).json()["id"]
    bid = enroll(client, ngo_headers, cid).json()["beneficiary_id"]
    client.post(f"{API}/resources/{rid}/distributions", json={"beneficiary_id": bid, "quantity": 25}, headers=ngo_headers)
    url = f"{API}/campaigns/{cid}/utilization"

    did = donate(client, donor_headers, cid, amount=700).json()["id"]
    assert client.get(url, headers=donor_headers).status_code == 403  # pending doesn't count yet
    set_status(client, ngo_headers, did, "RECEIVED")
    body = client.get(url, headers=donor_headers).json()
    assert body["money_received"] == 700 and body["resources"][0]["quantity_allocated"] == 25
    assert body["resources"][0]["quantity_remaining"] == 75
    assert "Rahim" not in str(body)  # aggregate only: no beneficiary info

    assert client.get(url, headers=ngo_headers).status_code == 200
    assert client.get(url, headers=platform_headers).status_code == 200
    for h in (donor2_headers, volunteer_headers, other_ngo_headers):
        assert client.get(url, headers=h).status_code == 403
    assert client.get(f"{API}/campaigns/999/utilization", headers=ngo_headers).status_code == 404


def test_unverified_ngo_cannot_write_finance(client, db):
    make_ngo_admin(db, "pending@example.com", verified=False)
    h = login(client, "pending@example.com")
    assert add_resource(client, h, 1).status_code in (403, 404)
