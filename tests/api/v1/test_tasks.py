from fastapi.testclient import TestClient
from app.core.config import settings
from sqlmodel import Session
from uuid import uuid4
from app.models.project import Project
from app.models.project_task import ProjectTask, TaskStatus


def get_auth_token(client: TestClient, email: str, password: str) -> str:
    # Register/Login helper
    reg_resp = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": email,
            "full_name": "Task Tester",
            "password": password,
            "is_active": True,
        },
    )
    # Register might fail if user exists, that's fine for testing

    response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data={"username": email, "password": password},
    )
    if response.status_code != 200:
        print(f"Login failed: {response.status_code} - {response.text}")

    res_data = response.json()
    assert "access_token" in res_data, f"Login failed: {res_data}"
    return res_data["access_token"], res_data["user_id"]


def test_onboarding_task_update_integration(client: TestClient, session: Session):
    # 1. Setup
    import uuid

    random_id = str(uuid.uuid4())[:8]
    email = f"task_{random_id}@example.com"
    password = "password123"  # length 11 >= 8

    token, user_id = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create Project and Task manually in DB
    project = Project(title="Test Proj", owner_id=uuid.UUID(user_id))
    session.add(project)
    session.commit()
    session.refresh(project)

    task = ProjectTask(title="Initial Task", project_id=project.id, status="pending")
    session.add(task)
    session.commit()
    session.refresh(task)

    # 2. Execute Update (US03)
    update_data = {"status": "in_progress"}
    response = client.patch(
        f"{settings.API_V1_STR}/tasks/{task.id}", headers=headers, json=update_data
    )

    # 3. Assert
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "in_progress"

    # Verify in DB
    session.expire_all()  # Ensure fresh read
    db_task = session.get(ProjectTask, task.id)
    assert db_task.status == "in_progress"
