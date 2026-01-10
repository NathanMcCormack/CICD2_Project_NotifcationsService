import pytest

def notif_payload(reference="N-001", recipient="nathan@example.com", channel="email", message="Hello"):
    return {
        "reference": reference,
        "recipient": recipient,
        "channel": channel,
        "message": message,
    }

def test_create_notification_201(client):
    r = client.post("/api/notifications", json=notif_payload())
    assert r.status_code == 201
    data = r.json()
    assert data["reference"] == "N-001"
    assert data["status"] == "pending"

def test_duplicate_notification_reference_409(client):
    client.post("/api/notifications", json=notif_payload(reference="N-dup"))
    r = client.post("/api/notifications", json=notif_payload(reference="N-dup"))
    assert r.status_code == 409

def test_get_notification_404(client):
    r = client.get("/api/notifications/999")
    assert r.status_code == 404

def test_patch_notification_ok(client):
    created = client.post("/api/notifications", json=notif_payload(reference="N-002")).json()
    nid = created["id"]
    r = client.patch(f"/api/notifications/{nid}", json={"status": "sent"})
    assert r.status_code == 200
    assert r.json()["status"] == "sent"

@pytest.mark.parametrize("bad_channel", ["EMAIL", "pushy", "sms1", ""])
def test_bad_channel_422(client, bad_channel):
    r = client.post("/api/notifications", json=notif_payload(reference="N-003", channel=bad_channel))
    assert r.status_code == 422

def test_delete_notification_204_then_404(client):
    created = client.post("/api/notifications", json=notif_payload(reference="N-004")).json()
    nid = created["id"]
    r1 = client.delete(f"/api/notifications/{nid}")
    assert r1.status_code == 204
    r2 = client.delete(f"/api/notifications/{nid}")
    assert r2.status_code == 404

def notif_payload(reference="N-001", recipient="nathan@example.com", channel="email", message="Hello"):
    return {
        "reference": reference,
        "recipient": recipient,
        "channel": channel,
        "message": message,
    }

def delivery_payload(notification_id: int, provider="twilio", result="queued", attempt_no=1):
    return {
        "provider": provider,
        "result": result,
        "attempt_no": attempt_no,
        "notification_id": notification_id,
    }

def test_list_notifications_default_empty(client):
    r = client.get("/api/notifications")
    assert r.status_code == 200
    assert r.json() == []

def test_list_notifications_pagination_limit_offset(client):
    # Create 3 notifications
    client.post("/api/notifications", json=notif_payload(reference="N-101"))
    client.post("/api/notifications", json=notif_payload(reference="N-102"))
    client.post("/api/notifications", json=notif_payload(reference="N-103"))

    r = client.get("/api/notifications?limit=2&offset=1")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Should be the 2nd + 3rd created when ordered by id
    assert data[0]["reference"] == "N-102"
    assert data[1]["reference"] == "N-103"

def test_put_notification_full_replace_ok(client):
    created = client.post("/api/notifications", json=notif_payload(reference="N-201")).json()
    nid = created["id"]

    new_payload = notif_payload(
        reference="N-201-REPLACED",
        recipient="updated@example.com",
        channel="sms",
        message="Updated message",
    )
    r = client.put(f"/api/notifications/{nid}", json=new_payload)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == nid
    assert body["reference"] == "N-201-REPLACED"
    assert body["recipient"] == "updated@example.com"
    assert body["channel"] == "sms"
    assert body["message"] == "Updated message"

def test_put_notification_404(client):
    r = client.put("/api/notifications/999999", json=notif_payload(reference="N-404"))
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()

def test_get_notification_includes_deliveries_empty_list(client):
    created = client.post("/api/notifications", json=notif_payload(reference="N-301")).json()
    nid = created["id"]

    r = client.get(f"/api/notifications/{nid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == nid
    assert "deliveries" in body
    assert body["deliveries"] == []


def test_create_delivery_201_then_get_delivery_includes_notification(client):
    n = client.post("/api/notifications", json=notif_payload(reference="N-401")).json()
    nid = n["id"]

    r = client.post("/api/deliveries", json=delivery_payload(notification_id=nid))
    assert r.status_code == 201
    d = r.json()
    assert d["notification_id"] == nid
    delivery_id = d["id"]

    r2 = client.get(f"/api/deliveries/{delivery_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["id"] == delivery_id
    assert "notification" in body
    assert body["notification"]["id"] == nid
    assert body["notification"]["reference"] == "N-401"


def test_create_delivery_notification_missing_404(client):
    r = client.post("/api/deliveries", json=delivery_payload(notification_id=999999))
    assert r.status_code == 404
    assert "notification not found" in r.json()["detail"].lower()


def test_list_notification_deliveries_and_create_via_nested_route(client):
    n = client.post("/api/notifications", json=notif_payload(reference="N-501")).json()
    nid = n["id"]

    r0 = client.get(f"/api/notifications/{nid}/deliveries")
    assert r0.status_code == 200
    assert r0.json() == []

    r1 = client.post(
        f"/api/notifications/{nid}/deliveries",
        json={"provider": "sendgrid", "result": "queued", "attempt_no": 1},
    )
    assert r1.status_code == 201
    d1 = r1.json()
    assert d1["notification_id"] == nid
    assert d1["provider"] == "sendgrid"

    r2 = client.get(f"/api/notifications/{nid}/deliveries")
    assert r2.status_code == 200
    data = r2.json()
    assert len(data) == 1
    assert data[0]["id"] == d1["id"]

def test_patch_delivery_ok(client):
    n = client.post("/api/notifications", json=notif_payload(reference="N-601")).json()
    nid = n["id"]

    d = client.post("/api/deliveries", json=delivery_payload(notification_id=nid, provider="twilio", result="queued")).json()
    did = d["id"]

    r = client.patch(f"/api/deliveries/{did}", json={"result": "sent", "attempt_no": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == did
    assert body["result"] == "sent"
    assert body["attempt_no"] == 2


def test_delete_notification_cascades_deliveries(client):
    n = client.post("/api/notifications", json=notif_payload(reference="N-701")).json()
    nid = n["id"]

    d = client.post("/api/deliveries", json=delivery_payload(notification_id=nid)).json()
    did = d["id"]

    r_del = client.delete(f"/api/notifications/{nid}")
    assert r_del.status_code == 204

    r_get = client.get(f"/api/deliveries/{did}")
    assert r_get.status_code == 404