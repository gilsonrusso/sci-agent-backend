from sqlmodel import Session, select, delete
from app.db.session import engine
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
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


if __name__ == "__main__":
    seed_users()
