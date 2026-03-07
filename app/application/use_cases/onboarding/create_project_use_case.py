from typing import List
from uuid import UUID
from datetime import datetime, timedelta

from app.domain.onboarding.entities import OnboardingProposta
from app.domain.repositories.project_repository import ProjectRepository
from app.domain.events.event_bus import EventBus
from app.models.project import Project
from app.models.project_task import ProjectTask, TaskStatus


class CreateProjectFromOnboardingUseCase:
    """
    Handles US01: Creating a project from onboarding data in a DDD way.
    It coordinates the repository to save the project and initial tasks.
    """

    def __init__(self, project_repository: ProjectRepository, event_bus: EventBus):
        self.project_repository = project_repository
        self.event_bus = event_bus

    def execute(self, proposta: OnboardingProposta) -> Project:
        # 1. Domain Validation
        proposta.validate()

        # 2. Build LaTeX Template (Infrastructure logic could be moved to a builder)
        references_section = ""
        for a in proposta.selected_articles:
            references_section += (
                f"\\item {a.get('title')} ({a.get('year')}). {a.get('url')}\n"
            )

        latex_content = f"""\\documentclass[conference]{{IEEEtran}}
\\IEEEoverridecommandlockouts
\\usepackage{{cite}}
\\usepackage{{amsmath,amssymb,amsfonts}}
\\usepackage{{algorithmic}}
\\usepackage{{graphicx}}
\\usepackage{{textcomp}}
\\usepackage{{xcolor}}

\\begin{{document}}
\\title{{{proposta.title}}}

\\maketitle

\\begin{{abstract}}
{proposta.abstract}
\\end{{abstract}}

\\section{{Introduction}}
Esta seção foi gerada automaticamente para o tema: {proposta.topic}.

\\section{{References}}
\\begin{{itemize}}
{references_section}
\\end{{itemize}}

\\end{{document}}
"""

        # 3. Create Models
        project = Project(
            title=proposta.title,
            description=f"Generated via SciAgent Onboarding. Focus: {proposta.topic}",
            owner_id=proposta.owner_id,
            content=latex_content,
        )

        # 4. Map Roadmap Tasks
        tasks = []
        for i, t in enumerate(proposta.roadmap):
            task = ProjectTask(
                title=t.title,
                description=t.description,
                status=TaskStatus.PENDING,
                # Simple deadline logic
                due_date=datetime.utcnow() + timedelta(days=t.due_in_days),
            )
            tasks.append(task)

        # 5. Persist via Repository
        created_project = self.project_repository.create(project, tasks)

        # 6. TODO: Publish Domain Event (ArticleCreated)
        # self.event_bus.publish(ProjectCreatedEvent(project_id=created_project.id))

        return created_project
