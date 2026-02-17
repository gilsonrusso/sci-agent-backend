# SciAgent Backend

This is the backend API for the SciAgent platform, built with FastAPI, SQLModel, and PostgreSQL.

## Prerequisites

- Python 3.10+
- PostgreSQL
- Docker (optional, for LaTeX compiler service)

## Setup

1.  Navigate to the directory:

    ```bash
    cd sci-agent-backend
    ```

2.  Create a virtual environment:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4.  Configure Environment Variables:
    Create a `.env` file (or set env vars) with database credentials:
    ```bash
    DATABASE_URL=postgresql://user:password@localhost/sciagent_db
    SECRET_KEY=your_secret_key
    ```

## Database Migrations

Use Alembic to manage database schema changes.

1.  Apply migrations:

    ```bash
    alembic upgrade head
    ```

2.  (Optional) Create a new migration:
    ```bash
    alembic revision --autogenerate -m "Message"
    ```

## Seeding the Database

To insert initial data (like the default LaTeX template), run the seed script:

```bash
python -m app.db.seed
```

## Seeding Users

To populate the database with test users (`alice@gmail.com`, etc.) and clear existing data:

```bash
PYTHONPATH=. .venv/bin/python app/db/seed_users.py
```

## Running the Server

Start the development server with hot-reload:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive documentation is at `http://localhost:8000/docs`.

## LaTeX Compiler Service

The backend expects a LaTeX compiler service. Ensure the Docker container or local `pdflatex` is available.
