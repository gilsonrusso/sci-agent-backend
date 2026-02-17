import pytest
import uuid
from sqlmodel import Session
from fastapi.testclient import TestClient
from app.core.config import settings


# --- Helpers ---
def random_email() -> str:
    return f"user_{uuid.uuid4()}@example.com"


def get_auth_token(client: TestClient, email: str, password: str) -> str:
    # Register/Login helper
    # Try register first
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": email,
            "full_name": "Test User",
            "password": password,
            "is_active": True,
        },
    )
    # Login
    response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data={"username": email, "password": password},
    )
    return response.json().get("access_token")


def create_user_and_get_headers(client: TestClient) -> tuple[dict, dict]:
    email = random_email()
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}
    # Get user info for ID
    r = client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    user = r.json()
    return user, headers


# ----------------


def test_read_users(client: TestClient) -> None:
    # Create a user to authenticate
    user, headers = create_user_and_get_headers(client)

    r = client.get(f"{settings.API_V1_STR}/users/", headers=headers)
    assert r.status_code == 200
    users = r.json()
    assert len(users) > 0
    # Verify the created user is in the list
    assert any(u["email"] == user["email"] for u in users)


def test_read_users_unauthenticated(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/")
    assert r.status_code == 401
