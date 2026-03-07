from sqlmodel import Session, select, delete
from app.db.session import engine
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.core.security import get_password_hash
from app.models.user_role import UserRole


def seed_users():
    dummy_users = [
        {
            "email": "gilson@gmail.com",
            "full_name": "Gilson Russo",
            "password": "123456",
            "is_superuser": True,
            "role": UserRole.AUTHOR,
        },
        {
            "email": "roci@gmail.com",
            "full_name": "Roce Araujo",
            "password": "123456",
            "is_superuser": False,
            "role": UserRole.COORDINATOR,
        },
        {
            "email": "bob@gmail.com",
            "full_name": "Bob Scientist",
            "password": "123456",
            "is_superuser": False,
            "role": UserRole.AUTHOR,
        },
        {
            "email": "charlie@gmail.com",
            "full_name": "Charlie Professor",
            "password": "123456",
            "is_superuser": False,
            "role": UserRole.MENTOR,
        },
        {
            "email": "dave@gmail.com",
            "full_name": "Dave Student",
            "password": "123456",
            "is_superuser": False,
            "role": UserRole.AUTHOR,
        },
    ]

    with Session(engine) as session:
        # Clear existing data
        print("Clearing existing data...")
        # Delete dependent tables first to avoid FK violations
        session.exec(delete(ProjectMember))
        session.exec(delete(Project))
        session.exec(delete(User))
        session.commit()
        print("Existing data cleared.")

        for user_data in dummy_users:
            print(f"Creating user: {user_data['email']} with role {user_data['role']}")
            new_user = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash(user_data["password"]),
                is_superuser=user_data["is_superuser"],
                role=user_data["role"],
            )
            session.add(new_user)

        session.commit()

        print("Seeding a mock project...")
        # Get users for the project
        author_user = session.exec(
            select(User).where(User.email == "gilson@gmail.com")
        ).first()
        mentor_user = session.exec(
            select(User).where(User.email == "charlie@gmail.com")
        ).first()
        coordinator_user = session.exec(
            select(User).where(User.email == "roci@gmail.com")
        ).first()

        from app.domain.workflow.types import MacroStage
        from datetime import datetime, timedelta

        # Create mock project
        mock_content = r"""\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts

% Pacotes essenciais para artigos IEEE
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}

\begin{document}
\title{Detection of Soybean Pests using Computer Vision}

\author{\IEEEauthorblockN{1\textsuperscript{st} Gilson Russo}
\IEEEauthorblockA{\textit{Computer Science Dept} \\
\textit{University of X}\\
City, Country \\
email@domain.com}}

\maketitle

\begin{abstract}
This document is a template.
\end{abstract}

\section{Introduction}
Start here.
\end{document}
"""

        mock_project = Project(
            title="Detection of Soybean Pests using Computer Vision",
            description="Abstract: This paper presents a novel approach...",
            content=mock_content,
            stage=MacroStage.WRITING,
            deadline=datetime.utcnow() + timedelta(days=30),
            owner_id=author_user.id,
        )
        session.add(mock_project)
        session.commit()
        session.refresh(mock_project)

        # Create Project Memberships
        member1 = ProjectMember(
            project_id=mock_project.id, user_id=author_user.id, role=ProjectRole.OWNER
        )
        member2 = ProjectMember(
            project_id=mock_project.id, user_id=mentor_user.id, role=ProjectRole.EDITOR
        )
        member3 = ProjectMember(
            project_id=mock_project.id,
            user_id=coordinator_user.id,
            role=ProjectRole.VIEWER,
        )

        session.add_all([member1, member2, member3])
        session.commit()

        print("Mock project created successfully.")


if __name__ == "__main__":
    seed_users()
