from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings


def _register_and_login(
    client: TestClient,
    email: str,
    password: str = "strong-password-123",
) -> dict[str, str]:
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _assert_validation_error(response_json: dict[str, object]) -> None:
    assert set(response_json.keys()) == {"detail", "code"}
    assert response_json["code"] == "VALIDATION_ERROR"
    assert isinstance(response_json["detail"], str) and response_json["detail"]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/monitors", {"name": "API", "url": "https://api.example.com"}),
        ("GET", "/monitors", None),
        ("GET", f"/monitors/{uuid4()}", None),
        ("PATCH", f"/monitors/{uuid4()}", {"name": "Renamed"}),
        ("DELETE", f"/monitors/{uuid4()}", None),
    ],
)
def test_all_monitors_endpoints_reject_missing_invalid_and_expired_jwt(
    client: TestClient,
    test_settings: Settings,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    missing = client.request(method, path, json=payload)
    assert missing.status_code == 401
    assert missing.json() == {"detail": "Not authenticated", "code": "UNAUTHORIZED"}

    non_bearer = client.request(
        method, path, json=payload, headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert non_bearer.status_code == 401
    assert non_bearer.json() == {"detail": "Not authenticated", "code": "UNAUTHORIZED"}

    malformed = client.request(
        method, path, json=payload, headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert malformed.status_code == 401
    assert malformed.json() == {"detail": "Invalid or expired token", "code": "INVALID_TOKEN"}

    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        test_settings.jwt_secret_key.get_secret_value(),
        algorithm=test_settings.jwt_algorithm,
    )
    expired = client.request(
        method, path, json=payload, headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert expired.status_code == 401
    assert expired.json() == {"detail": "Invalid or expired token", "code": "INVALID_TOKEN"}


def test_monitors_reject_valid_jwt_for_unknown_user_or_wrong_secret(
    client: TestClient,
    test_settings: Settings,
) -> None:
    now = datetime.now(UTC)
    orphan_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        test_settings.jwt_secret_key.get_secret_value(),
        algorithm=test_settings.jwt_algorithm,
    )
    orphan_resp = client.get("/monitors", headers={"Authorization": f"Bearer {orphan_token}"})
    assert orphan_resp.status_code == 401
    assert orphan_resp.json() == {"detail": "Invalid or expired token", "code": "INVALID_TOKEN"}

    wrong_secret_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        "a-completely-different-secret-key-at-least-32-chars",
        algorithm=test_settings.jwt_algorithm,
    )
    wrong_secret_resp = client.get(
        "/monitors", headers={"Authorization": f"Bearer {wrong_secret_token}"}
    )
    assert wrong_secret_resp.status_code == 401
    assert wrong_secret_resp.json() == {
        "detail": "Invalid or expired token",
        "code": "INVALID_TOKEN",
    }


def test_monitors_crud_lifecycle_and_defaults(client: TestClient) -> None:
    headers = _register_and_login(client, "alice@example.com")

    empty_list = client.get("/monitors", headers=headers)
    assert empty_list.status_code == 200
    assert empty_list.json() == {"items": [], "total": 0}

    created = client.post(
        "/monitors",
        headers=headers,
        json={"name": "API Production", "url": "https://api.example.com/health"},
    )
    assert created.status_code == 201
    body = created.json()
    monitor_id = body["id"]
    UUID(monitor_id)
    assert body["name"] == "API Production"
    assert body["url"] == "https://api.example.com/health"
    assert body["interval_seconds"] == 60
    assert body["expected_status"] == 200
    assert body["is_active"] is True
    assert "created_at" in body
    initial_updated_at = body["updated_at"]

    listed = client.get("/monitors", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == monitor_id

    fetched = client.get(f"/monitors/{monitor_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == monitor_id

    patched = client.patch(
        f"/monitors/{monitor_id}",
        headers=headers,
        json={
            "name": "API Staging",
            "url": "https://staging.example.com/health",
            "interval_seconds": 120,
            "expected_status": 204,
            "is_active": False,
        },
    )
    assert patched.status_code == 200
    patched_body = patched.json()
    assert patched_body["name"] == "API Staging"
    assert patched_body["url"] == "https://staging.example.com/health"
    assert patched_body["interval_seconds"] == 120
    assert patched_body["expected_status"] == 204
    assert patched_body["is_active"] is False
    assert patched_body["updated_at"] >= initial_updated_at

    empty_patch = client.patch(f"/monitors/{monitor_id}", headers=headers, json={})
    assert empty_patch.status_code == 200
    assert empty_patch.json()["interval_seconds"] == 120
    assert empty_patch.json()["updated_at"] == patched_body["updated_at"]

    deleted = client.delete(f"/monitors/{monitor_id}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    expected_404 = {"detail": "Monitor not found", "code": "MONITOR_NOT_FOUND"}
    assert client.get(f"/monitors/{monitor_id}", headers=headers).json() == expected_404
    assert (
        client.patch(f"/monitors/{monitor_id}", headers=headers, json={"name": "X"}).status_code
        == 404
    )
    assert client.delete(f"/monitors/{monitor_id}", headers=headers).status_code == 404


def test_monitors_strict_user_isolation(client: TestClient) -> None:
    headers_a = _register_and_login(client, "alice@example.com")
    headers_b = _register_and_login(client, "bob@example.com")

    created = client.post(
        "/monitors",
        headers=headers_a,
        json={"name": "Alice Service", "url": "https://alice.example.com"},
    )
    assert created.status_code == 201
    monitor_id = created.json()["id"]

    list_b = client.get("/monitors", headers=headers_b)
    assert list_b.status_code == 200
    assert list_b.json() == {"items": [], "total": 0}

    expected_404 = {"detail": "Monitor not found", "code": "MONITOR_NOT_FOUND"}

    get_b = client.get(f"/monitors/{monitor_id}", headers=headers_b)
    assert get_b.status_code == 404
    assert get_b.json() == expected_404

    patch_b = client.patch(
        f"/monitors/{monitor_id}",
        headers=headers_b,
        json={"name": "Hijacked"},
    )
    assert patch_b.status_code == 404
    assert patch_b.json() == expected_404

    delete_b = client.delete(f"/monitors/{monitor_id}", headers=headers_b)
    assert delete_b.status_code == 404
    assert delete_b.json() == expected_404

    still_intact = client.get(f"/monitors/{monitor_id}", headers=headers_a)
    assert still_intact.status_code == 200
    assert still_intact.json()["name"] == "Alice Service"


def test_monitors_validation_on_post_patch_and_path_params(client: TestClient) -> None:
    headers = _register_and_login(client, "alice@example.com")

    invalid_post_payloads: list[dict[str, object]] = [
        {"name": "   ", "url": "https://api.example.com"},
        {"name": "FTP", "url": "ftp://files.example.com"},
        {"name": "CRLF", "url": "https://api.example.com/\r\nX-Injected: 1"},
        {"name": "Too Fast", "url": "https://api.example.com", "interval_seconds": 10},
        {"name": "Too Slow", "url": "https://api.example.com", "interval_seconds": 86401},
        {"name": "Low Code", "url": "https://api.example.com", "expected_status": 99},
        {"name": "High Code", "url": "https://api.example.com", "expected_status": 700},
    ]
    for bad_payload in invalid_post_payloads:
        resp = client.post("/monitors", headers=headers, json=bad_payload)
        assert resp.status_code == 422
        _assert_validation_error(resp.json())

    created = client.post(
        "/monitors",
        headers=headers,
        json={"name": "Valid Monitor", "url": "https://api.example.com/health"},
    )
    assert created.status_code == 201
    monitor_id = created.json()["id"]

    invalid_patch_payloads: list[dict[str, object]] = [
        {"name": "   "},
        {"name": None},
        {"url": "ftp://files.example.com"},
        {"url": "https://api.example.com/\r\nX-Injected: 1"},
        {"interval_seconds": 29},
        {"interval_seconds": 86401},
        {"expected_status": 99},
        {"expected_status": 600},
        {"is_active": None},
    ]
    for bad_patch in invalid_patch_payloads:
        resp = client.patch(f"/monitors/{monitor_id}", headers=headers, json=bad_patch)
        assert resp.status_code == 422
        _assert_validation_error(resp.json())

    unchanged = client.get(f"/monitors/{monitor_id}", headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["name"] == "Valid Monitor"
    assert unchanged.json()["url"] == "https://api.example.com/health"

    bad_uuid = client.get("/monitors/not-a-uuid", headers=headers)
    assert bad_uuid.status_code == 422
    _assert_validation_error(bad_uuid.json())
