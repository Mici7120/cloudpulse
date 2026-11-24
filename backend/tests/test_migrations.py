from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


def test_alembic_upgrade_downgrade_upgrade_is_reversible(tmp_path: Path) -> None:
    db_file = tmp_path / "migration_test.db"
    db_url = f"sqlite+pysqlite:///{db_file}"

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(alembic_cfg, "head")
    engine = create_engine(db_url)
    try:
        inspector = inspect(engine)
        tables_after_up = set(inspector.get_table_names())
        assert "users" in tables_after_up
        assert "monitors" in tables_after_up

        user_cols = {col["name"]: col for col in inspector.get_columns("users")}
        assert set(user_cols.keys()) == {"id", "email", "password_hash", "created_at"}
        assert all(not col["nullable"] for col in user_cols.values())

        user_indexes = {idx["name"]: idx for idx in inspector.get_indexes("users")}
        assert "ix_users_email" in user_indexes
        assert user_indexes["ix_users_email"]["unique"]

        monitor_cols = {col["name"]: col for col in inspector.get_columns("monitors")}
        assert set(monitor_cols.keys()) == {
            "id",
            "owner_id",
            "name",
            "url",
            "interval_seconds",
            "expected_status",
            "is_active",
            "created_at",
            "updated_at",
        }
        assert all(not col["nullable"] for col in monitor_cols.values())

        monitor_indexes = {idx["name"]: idx for idx in inspector.get_indexes("monitors")}
        assert "ix_monitors_owner_id" in monitor_indexes

        fks = inspector.get_foreign_keys("monitors")
        assert len(fks) == 1
        assert fks[0]["referred_table"] == "users"
        assert fks[0]["constrained_columns"] == ["owner_id"]
        assert fks[0]["referred_columns"] == ["id"]
        assert fks[0].get("options", {}).get("ondelete") == "CASCADE"

        command.downgrade(alembic_cfg, "base")
        tables_after_down = set(inspect(engine).get_table_names())
        assert "users" not in tables_after_down
        assert "monitors" not in tables_after_down

        command.upgrade(alembic_cfg, "head")
        tables_after_reup = set(inspect(engine).get_table_names())
        assert "users" in tables_after_reup
        assert "monitors" in tables_after_reup
    finally:
        engine.dispose()
