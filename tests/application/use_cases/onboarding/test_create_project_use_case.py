import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime

from app.domain.onboarding.entities import OnboardingProposta, OnboardingTask
from app.application.use_cases.onboarding.create_project_use_case import (
    CreateProjectFromOnboardingUseCase,
)
from app.models.project import Project
from app.models.project_task import ProjectTask


def test_create_project_from_onboarding_success():
    # Setup
    mock_repo = MagicMock()
    mock_event_bus = MagicMock()
    use_case = CreateProjectFromOnboardingUseCase(mock_repo, mock_event_bus)

    owner_id = uuid4()
    proposta = OnboardingProposta(
        topic="IA em Redes Neurais",
        title="Redes Neurais 2026",
        abstract="Um estudo sobre o futuro da IA.",
        roadmap=[
            OnboardingTask(title="Intro", description="Write intro", due_in_days=5),
            OnboardingTask(
                title="State of Art", description="Literature review", due_in_days=10
            ),
        ],
        selected_articles=[
            {"title": "Paper 1", "year": 2024, "url": "http://example.com"}
        ],
        owner_id=owner_id,
    )

    # Mock behavior
    created_project = Project(
        id=uuid4(), title=proposta.title, owner_id=owner_id, content="mock content"
    )
    mock_repo.create.return_value = created_project

    # Execute
    result = use_case.execute(proposta)

    # Assert
    assert result == created_project
    mock_repo.create.assert_called_once()

    # Verify tasks were mapped
    args, kwargs = mock_repo.create.call_args
    project_arg, tasks_arg = args
    assert len(tasks_arg) == 2
    assert tasks_arg[0].title == "Intro"
    assert tasks_arg[1].title == "State of Art"
    assert "\\section{Introduction}" in project_arg.content
    assert "\\begin{abstract}" in project_arg.content


def test_create_project_from_onboarding_validation_error():
    # Setup
    mock_repo = MagicMock()
    mock_event_bus = MagicMock()
    use_case = CreateProjectFromOnboardingUseCase(mock_repo, mock_event_bus)

    # Invalid proposta (empty roadmap)
    proposta = OnboardingProposta(
        topic="IA",
        title="Valid Title",
        abstract="Short abstract",
        roadmap=[],
        owner_id=uuid4(),
    )

    # Execute & Assert
    with pytest.raises(
        ValueError, match="O roadmap inicial deve conter pelo menos uma tarefa"
    ):
        use_case.execute(proposta)
