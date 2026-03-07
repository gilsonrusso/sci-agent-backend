from fastapi.testclient import TestClient
from app.core.config import settings
from sqlmodel import Session, select
import uuid
from app.models.project import Project
from app.models.project_task import ProjectTask
from app.models.project_member import ProjectMember


def get_auth_token(client: TestClient, email: str, password: str) -> str:
    # Register
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": email,
            "full_name": "Onboarding Tester",
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


def test_onboarding_create_project_integration(client: TestClient, session: Session):
    # Setup
    email = "tester_onboarding@example.com"
    password = "password123"
    token = get_auth_token(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "topic": "Energia Renovável",
        "project_title": "Futuro da Energia",
        "project_structure": {"abstract": "Estudo sobre painéis solares."},
        "roadmap": [
            {
                "title": "Pesquisa Inicial",
                "description": "Coleta de dados",
                "due_in_days": 3,
            },
            {
                "title": "Análise Técnica",
                "description": "Simulações",
                "due_in_days": 10,
            },
        ],
        "selected_articles": [
            {"title": "Solar Energy 2025", "year": 2025, "url": "http://solar.com"}
        ],
    }

    # Execute
    response = client.post(
        f"{settings.API_V1_STR}/onboarding/create-project", headers=headers, json=data
    )

    # Assert Response
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["title"] == data["project_title"]
    project_id = uuid.UUID(res_data["id"])

    # Assert Database - Project
    project = session.get(Project, project_id)
    assert project is not None
    assert "Energia Renovável" in project.description
    assert "\\title{Futuro da Energia}" in project.content

    # Assert Database - Tasks
    statement = select(ProjectTask).where(ProjectTask.project_id == project_id)
    tasks = session.exec(statement).all()
    assert len(tasks) == 2
    task_titles = [t.title for t in tasks]
    assert "Pesquisa Inicial" in task_titles
    assert "Análise Técnica" in task_titles

    # Assert Database - Membership (Owner)
    statement_mem = select(ProjectMember).where(ProjectMember.project_id == project_id)
    members = session.exec(statement_mem).all()
    assert len(members) == 1
    assert members[0].user_id == project.owner_id
