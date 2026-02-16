from fastapi.testclient import TestClient
from app.core.config import settings


def get_auth_token(client: TestClient, email: str, password: str) -> str:
    # Register
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
    return response.json()["access_token"]


def test_create_project(client: TestClient):
    email = "project_creator@example.com"
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "title": "My New Project",
        "description": "A test project",
        "content": "Initial content",
    }
    response = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == data["title"]
    assert content["description"] == data["description"]
    assert "id" in content


def test_read_projects(client: TestClient):
    email = "project_reader@example.com"
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project
    client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json={"title": "Project 1"},
    )
    client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json={"title": "Project 2"},
    )

    response = client.get(f"{settings.API_V1_STR}/projects/", headers=headers)
    assert response.status_code == 200
    content = response.json()
    assert len(content) == 2
    assert content[0]["title"] == "Project 1"
    assert content[1]["title"] == "Project 2"


def test_read_project_by_id(client: TestClient):
    email = "project_owner@example.com"
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    create_res = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json={"title": "Single Project"},
    )
    project_id = create_res.json()["id"]

    # Read
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == project_id
    assert content["title"] == "Single Project"


def test_update_project(client: TestClient):
    email = "project_updater@example.com"
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    create_res = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json={"title": "Old Title", "content": "Old Content"},
    )
    project_id = create_res.json()["id"]

    # Update
    update_data = {"title": "New Title", "content": "New Content"}
    response = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=headers,
        json=update_data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == "New Title"
    assert content["content"] == "New Content"

    # Verify read
    read_res = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}", headers=headers
    )
    assert read_res.json()["title"] == "New Title"


def test_delete_project(client: TestClient):
    email = "project_deleter@example.com"
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    create_res = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json={"title": "To Delete"},
    )
    project_id = create_res.json()["id"]

    # Delete
    response = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=headers,
    )
    assert response.status_code == 200

    # Verify delete
    read_res = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}", headers=headers
    )
    assert read_res.status_code == 404
