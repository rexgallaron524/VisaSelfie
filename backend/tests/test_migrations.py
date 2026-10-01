import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, Table, create_engine, inspect, select

from app.core.database import Base


def test_migration_matches_models_and_can_downgrade(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    env = {**os.environ, "DATABASE_URL": url, "APP_ENV": "test"}
    cwd = Path(__file__).resolve().parents[1]

    def migrate(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    migrate("upgrade", "0003_recording_assessment")
    engine = create_engine(url)
    legacy_id = uuid.uuid4().hex
    with engine.begin() as connection:
        clients = Table("client_processes", MetaData(), autoload_with=connection)
        connection.execute(
            clients.insert().values(
                id=legacy_id,
                full_name="Existing Applicant",
                phone_number="+244923456789",
                status="registered",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    engine.dispose()
    migrate("upgrade", "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
        clients = Table("client_processes", MetaData(), autoload_with=connection)
        row = connection.execute(select(clients).where(clients.c.id == legacy_id)).mappings().one()
        assert row["full_name"] == "Existing Applicant"
        assert row["phone_number"] == "+244923456789"
        assert row["email"] is row["alternative_phone_number"] is row["address"] is None
    engine.dispose()
    migrate("downgrade", "base")
    engine = create_engine(url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
