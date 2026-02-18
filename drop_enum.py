from app.db.session import engine
from sqlalchemy import text
from sqlmodel import Session

with Session(engine) as session:
    try:
        session.exec(text("DROP TYPE IF EXISTS projectrole CASCADE;"))
        session.commit()
        print("Dropped projectrole type.")
    except Exception as e:
        print(f"Error dropping projectrole: {e}")

    try:
        session.exec(text("DROP TYPE IF EXISTS taskstatus CASCADE;"))
        session.commit()
        print("Dropped taskstatus type.")
    except Exception as e:
        print(f"Error dropping taskstatus: {e}")
