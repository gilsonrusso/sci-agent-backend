#!/bin/bash
set -e

echo "⚠️  WARNING: This will drop all data in the database!"
echo "Stopping for 3 seconds (Ctrl+C to cancel)..."
sleep 3

echo "📉 Downgrading database to base..."
.venv/bin/alembic downgrade base

echo "🗑️ Dropping Enum Types..."
PYTHONPATH=. .venv/bin/python drop_enum.py

echo "📈 Upgrading database to head..."
.venv/bin/alembic upgrade head

echo "🌱 Seeding data..."
PYTHONPATH=. .venv/bin/python app/db/seed_users.py

echo "✅ Database reset complete!"
