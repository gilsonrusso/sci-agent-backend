from app.db.session import engine
from sqlalchemy import text


def drop_enum():
    with engine.connect() as conn:
        conn.execute(text("DROP TYPE IF EXISTS userrole CASCADE;"))
        conn.commit()
        print("Dropped userrole enum successfully.")


if __name__ == "__main__":
    drop_enum()
