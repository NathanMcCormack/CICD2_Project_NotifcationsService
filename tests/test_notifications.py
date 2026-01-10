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
