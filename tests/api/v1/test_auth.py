from fastapi.testclient import TestClient
from app.core.config import settings


def test_register_user(client: TestClient):
    data = {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "password123",
        "is_active": True,
    }
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == data["email"]
    assert "id" in content
    assert "password" not in content
    assert "hashed_password" not in content


def test_login_access_token(client: TestClient):
    # Create user first
    register_data = {
        "email": "login@example.com",
        "full_name": "Login User",
        "password": "password123",
        "is_active": True,
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=register_data)

    login_data = {
        "username": "login@example.com",
        "password": "password123",
    }
    response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data=login_data,
    )
    assert response.status_code == 200
    content = response.json()
    assert "access_token" in content
    assert content["token_type"] == "bearer"


def test_read_users_me(client: TestClient):
    # Create user and login
    email = "me@example.com"
    password = "password123"

    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": email,
            "full_name": "Me User",
            "password": password,
            "is_active": True,
        },
    )

    login_response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data={"username": email, "password": password},
    )
    token = login_response.json()["access_token"]

    # Test /me
    response = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == email
    assert "hashed_password" not in content
