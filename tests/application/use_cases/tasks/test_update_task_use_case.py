import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from app.domain.entities.task import DomainTask, TaskStatus
from app.application.use_cases.tasks.update_task_use_case import UpdateTaskUseCase
from app.domain.workflow.types import Role


def test_update_task_status_success():
    mock_repo = MagicMock()
    use_case = UpdateTaskUseCase(mock_repo)

    task_id = uuid4()
    project_id = uuid4()
    existing_task = DomainTask(
        id=task_id, project_id=project_id, title="Test Task", status=TaskStatus.PENDING
    )
    mock_repo.get_by_id.return_value = existing_task

    # Execute
    use_case.execute(
        task_id=task_id,
        user_id=uuid4(),
        user_role=Role.AUTHOR,
        new_status=TaskStatus.IN_PROGRESS,
    )

    # Assert
    assert existing_task.status == TaskStatus.IN_PROGRESS
    mock_repo.save.assert_called_once_with(existing_task)


def test_update_task_assignee_success():
    mock_repo = MagicMock()
    use_case = UpdateTaskUseCase(mock_repo)

    task_id = uuid4()
    assignee_id = uuid4()
    existing_task = DomainTask(
        id=task_id, project_id=uuid4(), title="Test Task", status=TaskStatus.PENDING
    )
    mock_repo.get_by_id.return_value = existing_task

    # Execute
    use_case.execute(
        task_id=task_id,
        user_id=uuid4(),
        user_role=Role.AUTHOR,
        new_assignee=assignee_id,
    )

    # Assert
    assert existing_task.assigned_to == assignee_id
    mock_repo.save.assert_called_once_with(existing_task)


def test_invalid_transition_throws_error():
    mock_repo = MagicMock()
    use_case = UpdateTaskUseCase(mock_repo)

    task_id = uuid4()
    existing_task = DomainTask(
        id=task_id, project_id=uuid4(), title="Done Task", status=TaskStatus.DONE
    )
    mock_repo.get_by_id.return_value = existing_task

    # Execute & Assert
    with pytest.raises(
        ValueError,
        match="Não é possível mover uma tarefa concluída de volta para Pendente.",
    ):
        use_case.execute(
            task_id=task_id,
            user_id=uuid4(),
            user_role=Role.AUTHOR,
            new_status=TaskStatus.PENDING,
        )
