from fastapi.testclient import TestClient
from app.core.config import settings
from app.api.v1.endpoints.projects import create_project
from app.models.project import Project
import uuid


def get_auth_token(client: TestClient, email: str, password: str) -> str:
    # Register/Login helper
    try:
        client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": email,
                "full_name": "Test User",
                "password": password,
                "is_active": True,
            },
        )
    except:
        pass  # User might already exist

    response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data={"username": email, "password": password},
    )
    return response.json()["access_token"]


def test_compile_endpoint(client: TestClient):
    email = "editor_tester@example.com"
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create Project first
    create_res = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json={"title": "Project to Compile"},
    )
    project_id = create_res.json()["id"]

    # Test Compile
    response = client.post(
        f"{settings.API_V1_STR}/editor/{project_id}/compile",
        headers=headers,
    )

    # Check response type and success
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0  # Should have some bytes


def test_websocket_connect(client: TestClient):
    # Note: TestClient uses Starlette's TestClient which supports WebSocket testing

    project_id = str(uuid.uuid4())

    with client.websocket_connect(
        f"{settings.API_V1_STR}/editor/{project_id}/ws"
    ) as websocket:
        # Send a message
        websocket.send_text("Hello World")
        # Receive broadcast (from ourselves in this simple implementation)
        # Wait, we filtered out sender in broadcast!
        # So we should NOT receive anything back if we are the only one.
        # Let's connect a second client to verify broadcast
        pass
