import pytest
import uuid
from sqlmodel import Session
from fastapi.testclient import TestClient
from app.models.project_member import ProjectRole
from app.core.config import settings


# Helper functions
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
    if response.status_code != 200:
        # Maybe already exists
        pass
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


def test_project_rbac(client: TestClient) -> None:
    # 1. Create two users
    user1, headers1 = create_user_and_get_headers(client)
    user2, headers2 = create_user_and_get_headers(client)

    email2 = user2["email"]

    # 2. User 1 creates a project
    project_data = {"title": "RBAC Test Project", "description": "Testing permissions"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/", headers=headers1, json=project_data
    )
    assert r.status_code == 200
    project = r.json()
    project_id = project["id"]

    # 3. User 2 tries to read the project (Should fail - 403 or 404)
    r = client.get(f"{settings.API_V1_STR}/projects/{project_id}", headers=headers2)
    # We implemented 403 "Not a member" or 404 "Not found" (if security through obscurity)
    # In projects.py I implemented session.get(Project, id) which finds it, then checks permission.
    # So it should be 403.
    assert r.status_code == 403

    # 4. User 1 adds User 2 as VIEWER
    member_data = {"email": email2, "role": ProjectRole.VIEWER}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/members",
        headers=headers1,
        json=member_data,
    )
    assert r.status_code == 200

    # 5. User 2 tries to read project (Should succeed)
    r = client.get(f"{settings.API_V1_STR}/projects/{project_id}", headers=headers2)
    assert r.status_code == 200
    assert r.json()["title"] == "RBAC Test Project"

    # 6. User 2 tries to update project (Should fail - VIEWER)
    update_data = {"title": "Hacked Title"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=headers2,
        json=update_data,
    )
    assert r.status_code == 403

    # 7. User 1 updates project (Should succeed)
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=headers1,
        json=update_data,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Hacked Title"

    # 8. User 2 tries to delete project (Should fail)
    r = client.delete(f"{settings.API_V1_STR}/projects/{project_id}", headers=headers2)
    assert r.status_code == 403

    # 9. User 1 removes User 2
    user2_id = user2["id"]
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/members/{user2_id}",
        headers=headers1,
    )
    assert r.status_code == 200

    # 10. User 2 tries to read again (Should fail)
    r = client.get(f"{settings.API_V1_STR}/projects/{project_id}", headers=headers2)
    assert r.status_code == 403
