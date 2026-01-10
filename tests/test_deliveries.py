def notif_payload(reference="N-100", recipient="nathan@example.com", channel="email", message="Hello"):
    return {
        "reference": reference,
        "recipient": recipient,
        "channel": channel,
        "message": message,
    }

def test_create_delivery_flat_requires_parent(client):
    # no notification yet
    r = client.post("/api/deliveries", json={"provider": "smtp", "result": "queued", "attempt_no": 1, "notification_id": 1})
    assert r.status_code == 404

def test_create_delivery_nested_ok_and_list(client):
    n = client.post("/api/notifications", json=notif_payload(reference="N-101")).json()
    nid = n["id"]

    r = client.post(f"/api/notifications/{nid}/deliveries", json={"provider": "smtp", "result": "queued", "attempt_no": 1})
    assert r.status_code == 201
    d = r.json()
    assert d["notification_id"] == nid

    r2 = client.get(f"/api/notifications/{nid}/deliveries")
    assert r2.status_code == 200
    assert len(r2.json()) == 1

def test_cascade_delete_notification_deletes_deliveries(client):
    n = client.post("/api/notifications", json=notif_payload(reference="N-102")).json()
    nid = n["id"]
    client.post(f"/api/notifications/{nid}/deliveries", json={"provider": "smtp", "result": "queued", "attempt_no": 1})

    # delete parent
    r = client.delete(f"/api/notifications/{nid}")
    assert r.status_code == 204

    # deliveries for that parent should be empty or 404 parent
    r2 = client.get(f"/api/notifications/{nid}/deliveries")
    assert r2.status_code == 404
