from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from backend.middleware.jwt_auth import ALGORITHM
from backend.routers import auth


def test_hash_refresh_token_is_deterministic_and_not_raw():
    first = auth._hash_refresh_token("refresh-token")
    second = auth._hash_refresh_token("refresh-token")

    assert first == second
    assert first != "refresh-token"
    assert len(first) == 64


def test_dev_password_placeholder_verification():
    assert auth._verify_password("dev-password-hash-change-me", "dev-password-hash-change-me")
    assert not auth._verify_password("wrong", "dev-password-hash-change-me")
    assert not auth._verify_password("password", "plain-text-not-accepted")


def test_access_token_contains_required_claims(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-with-enough-length")

    token = auth._access_token_for(
        {
            "id": "user-1",
            "email": "omar.elfassi@n7chat.local",
            "role": "student",
            "is_active": True,
        }
    )
    payload = jwt.decode(token, "unit-test-secret-with-enough-length", algorithms=[ALGORITHM])

    assert payload["sub"] == "user-1"
    assert payload["email"] == "omar.elfassi@n7chat.local"
    assert payload["role"] == "student"
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]


def test_refresh_rotates_token_and_issues_new_pair(monkeypatch):
    old_token = "old-refresh-token-with-valid-length"
    old_hash = auth._hash_refresh_token(old_token)
    executed = []

    def fake_fetch_one(query, params):
        if "FROM refresh_tokens" in query:
            assert params == {"token": old_hash}
            return {
                "id": "refresh-row-1",
                "user_id": "user-1",
                "expires_at": datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(days=1),
                "revoked": False,
            }
        if "FROM users" in query:
            return {
                "id": "user-1",
                "email": "omar.elfassi@n7chat.local",
                "role": "student",
                "is_active": True,
            }
        return None

    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-with-enough-length")
    monkeypatch.setattr(auth, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(auth, "execute", lambda query, params: executed.append((query, params)) or 1)
    monkeypatch.setattr(auth, "_store_refresh_token", lambda user_id: f"new-refresh-for-{user_id}")

    response = auth.refresh(auth.RefreshRequest(refresh_token=old_token))

    assert response.refresh_token == "new-refresh-for-user-1"
    assert response.access_token
    assert executed[0][1] == {"id": "refresh-row-1"}


def test_refresh_rejects_revoked_token(monkeypatch):
    monkeypatch.setattr(
        auth,
        "fetch_one",
        lambda *_: {
            "id": "refresh-row-1",
            "user_id": "user-1",
            "expires_at": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
            "revoked": True,
        },
    )

    with pytest.raises(HTTPException) as exc:
        auth.refresh(auth.RefreshRequest(refresh_token="revoked-refresh-token"))

    assert exc.value.status_code == 401
