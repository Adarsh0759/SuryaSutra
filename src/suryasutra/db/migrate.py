"""Runs Alembic migrations programmatically at app startup, so there's no separate
migration step for the one-command local demo (CLAUDE.md §16). A real deploy against
Postgres would normally run `alembic upgrade head` as an explicit release step instead
of implicitly on every process start — fine here, prototype stage, SQLite, D-15."""

from pathlib import Path

from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parents[3]


def run_migrations() -> None:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
