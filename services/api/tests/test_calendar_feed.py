from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.helpers import bootstrap_owner, invite_and_register_contact
from waymark.main import create_app


def _login(client: TestClient, email: str, password: str = "password1234") -> None:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text


def test_mint_rotate_revoke_and_public_ics() -> None:
    client = TestClient(create_app())
    bootstrap_owner(client)
    status = client.get("/api/me/calendar-feed")
    assert status.status_code == 200
    assert status.json() == {
        "active": False,
        "created_at": None,
        "last_accessed_at": None,
        "revoked_at": None,
    }

    due = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    owned = client.post(
        "/api/tasks",
        json={
            "title": "Owner due",
            "priority": 2,
            "due_at": due,
            "description": "Secret note with person@example.com",
        },
    )
    assert owned.status_code == 201, owned.text
    owned_id = owned.json()["id"]
    assert (
        client.post("/api/tasks", json={"title": "No due", "priority": 2}).status_code
        == 201
    )
    done = client.post(
        "/api/tasks",
        json={"title": "Done due", "priority": 2, "due_at": due},
    )
    assert done.status_code == 201
    assert (
        client.post(
            f"/api/tasks/{done.json()['id']}/status",
            json={"status": "done"},
        ).status_code
        == 200
    )

    created = client.post("/api/me/calendar-feed")
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    assert token.startswith("wcf_")
    assert created.json()["active"] is True
    assert "token" not in client.get("/api/me/calendar-feed").json()
    assert client.post("/api/me/calendar-feed").status_code == 409

    guest = TestClient(create_app())
    ics = guest.get(f"/api/public/calendar/{token}.ics")
    assert ics.status_code == 200, ics.text
    assert "text/calendar" in ics.headers["content-type"]
    body = ics.text
    assert "BEGIN:VCALENDAR" in body
    assert "SUMMARY:Owner due" in body
    assert f"UID:{owned_id}@waymark" in body
    assert f"/tasks/{owned_id}" in body
    assert "Secret note with person@example.com" in body
    assert "SUMMARY:No due" not in body
    assert "SUMMARY:Done due" not in body

    redacted = guest.get(f"/api/public/calendar/{token}/redacted.ics")
    assert redacted.status_code == 200, redacted.text
    red_body = redacted.text
    assert "SUMMARY:Waymark task" in red_body
    assert "SUMMARY:Owner due" not in red_body
    assert "person@example.com" not in red_body
    assert f"/tasks/{owned_id}" not in red_body

    rotated = client.post("/api/me/calendar-feed/rotate")
    assert rotated.status_code == 200, rotated.text
    new_token = rotated.json()["token"]
    assert guest.get(f"/api/public/calendar/{token}.ics").status_code == 404
    assert guest.get(f"/api/public/calendar/{new_token}.ics").status_code == 200
    assert guest.get(f"/api/public/calendar/{new_token}/redacted.ics").status_code == 200

    assert client.post("/api/me/calendar-feed/revoke").status_code == 200
    assert guest.get(f"/api/public/calendar/{new_token}.ics").status_code == 404
    assert guest.get(f"/api/public/calendar/{new_token}/redacted.ics").status_code == 404
    assert guest.get("/api/public/calendar/wcf_not-real.ics").status_code == 404


def test_shared_task_prefixed_in_sharee_feed() -> None:
    client = TestClient(create_app())
    bootstrap_owner(client)
    due = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    shared = client.post(
        "/api/tasks",
        json={"title": "Team deadline", "priority": 2, "due_at": due},
    )
    assert shared.status_code == 201
    shared_id = shared.json()["id"]
    invite_and_register_contact(
        client, email="alex@example.com", display_name="Alex"
    )
    assert (
        client.post(
            f"/api/tasks/{shared_id}/shares",
            json={"email": "alex@example.com", "role": "viewer"},
        ).status_code
        == 201
    )

    _login(client, "alex@example.com")
    mine = client.post(
        "/api/tasks",
        json={"title": "Alex own", "priority": 2, "due_at": due},
    )
    assert mine.status_code == 201
    feed = client.post("/api/me/calendar-feed")
    assert feed.status_code == 201, feed.text
    token = feed.json()["token"]

    guest = TestClient(create_app())
    body = guest.get(f"/api/public/calendar/{token}.ics").text
    assert "SUMMARY:Alex own" in body
    assert "SUMMARY:[Shared] Team deadline" in body
    red = guest.get(f"/api/public/calendar/{token}/redacted.ics").text
    assert "SUMMARY:Alex own" not in red
    assert "Team deadline" not in red
    assert "SUMMARY:Waymark task" in red
    assert "SUMMARY:[Shared] Waymark task" in red
