from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings


def test_settings_requires_non_placeholder_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            JWT_SECRET_KEY=SecretStr("replace-with-a-long-random-secret-key-at-least-32-chars"),
        )


def test_register_creates_user_with_hashed_password(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "  Alice@Example.com  ", "password": "strong-password-123"},
    )

    assert response.status_code == 201
    body = response.json()
    UUID(body["id"])
    assert body["email"] == "alice@example.com"
    assert "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body

    from app.models.user import User

    stored = db_session.scalar(select(User).where(User.email == "alice@example.com"))
    assert stored is not None
    assert stored.password_hash != "strong-password-123"
    assert stored.password_hash.startswith("$argon2")


def test_register_duplicate_email_case_insensitive_returns_409(client: TestClient) -> None:
    first = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "strong-password-123"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/auth/register",
        json={"email": "ALICE@EXAMPLE.COM", "password": "another-password-456"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "Email already registered",
        "code": "EMAIL_ALREADY_EXISTS",
    }


def test_register_rejects_short_password_and_invalid_email(client: TestClient) -> None:
    short_pw = client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "short"},
    )
    assert short_pw.status_code == 422
    short_body = short_pw.json()
    assert set(short_body.keys()) == {"detail", "code"}
    assert short_body["code"] == "VALIDATION_ERROR"
    assert isinstance(short_body["detail"], str) and short_body["detail"]

    bad_email = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "strong-password-123"},
    )
    assert bad_email.status_code == 422
    bad_body = bad_email.json()
    assert set(bad_body.keys()) == {"detail", "code"}
    assert bad_body["code"] == "VALIDATION_ERROR"
    assert isinstance(bad_body["detail"], str) and bad_body["detail"]


def test_login_returns_valid_jwt_claims_for_valid_credentials(
    client: TestClient,
    test_settings: Settings,
) -> None:
    reg = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "strong-password-123"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = client.post(
        "/auth/login",
        json={"email": "ALICE@example.com", "password": "strong-password-123"},
    )
    assert login.status_code == 200
    body = login.json()
    assert isinstance(body["access_token"], str)
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600

    claims = jwt.decode(
        body["access_token"],
        test_settings.jwt_secret_key.get_secret_value(),
        algorithms=[test_settings.jwt_algorithm],
    )
    assert claims["sub"] == user_id
    assert isinstance(claims["iat"], int)
    assert claims["exp"] - claims["iat"] == 3600


def test_login_returns_identical_401_for_wrong_password_or_unknown_email(
    client: TestClient,
) -> None:
    client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "strong-password-123"},
    )

    wrong_pw = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password-999"},
    )
    unknown_email = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "strong-password-123"},
    )

    expected = {
        "detail": "Invalid email or password",
        "code": "INVALID_CREDENTIALS",
    }
    assert wrong_pw.status_code == 401
    assert wrong_pw.json() == expected
    assert unknown_email.status_code == 401
    assert unknown_email.json() == expected
