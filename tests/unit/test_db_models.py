"""DB layer tests against a throwaway in-memory SQLite engine — independent of the
app's real DATABASE_URL, so these are fast and fully isolated."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from suryasutra.db.models import Alarm, Base, TriageRun
from suryasutra.db.models import Usage as UsageRow
from suryasutra.db.seed import seed_alarms_from_json


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_alarm_round_trips(session: Session) -> None:
    alarm = Alarm(
        id=1,
        site_id="site-1",
        inverter_id="inv-1",
        brand="Sungrow",
        model="SG150CX",
        code="370",
        category="boost_capacitor_overvoltage_fault",
        message="test alarm",
        raised_at=datetime(2026, 1, 1, tzinfo=UTC),
        is_synthetic=True,
        answerable=True,
    )
    session.add(alarm)
    session.commit()

    fetched = session.get(Alarm, 1)
    assert fetched is not None
    assert fetched.code == "370"
    assert fetched.answerable is True


def test_triage_run_and_usage_relationship(session: Session) -> None:
    session.add(
        Alarm(
            id=1,
            site_id="s",
            inverter_id="i",
            brand="b",
            model="m",
            code="c",
            category="cat",
            message="msg",
            raised_at=datetime(2026, 1, 1, tzinfo=UTC),
            is_synthetic=True,
        )
    )
    session.commit()

    run = TriageRun(
        alarm_id=1,
        method="requirement_complete",
        budget=1000,
        selected_chunk_ids=["c1", "c2"],
        status="ANSWERED",
        missing_requirements=[],
        answer_json={"status": "ANSWERED"},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    session.add(run)
    session.flush()
    session.add(
        UsageRow(
            run_id=run.id,
            input_tokens=100,
            output_tokens=50,
            token_source="provider",
            cost_inr=0.05,
        )
    )
    session.commit()

    fetched = session.get(TriageRun, run.id)
    assert fetched is not None
    assert fetched.selected_chunk_ids == ["c1", "c2"]
    assert fetched.usage is not None
    assert fetched.usage.input_tokens == 100
    assert fetched.alarm.code == "c"


def test_seed_alarms_from_json_loads_real_synthetic_data(session: Session, tmp_path: Path) -> None:
    alarms_path = Path(__file__).parents[2] / "data" / "synthetic" / "alarms.json"

    seed_alarms_from_json(session, alarms_path)

    count = session.query(Alarm).count()
    assert count == 32
    first = session.get(Alarm, 1)
    assert first is not None
    assert first.code == "370"


def test_seed_alarms_from_json_is_idempotent(session: Session) -> None:
    alarms_path = Path(__file__).parents[2] / "data" / "synthetic" / "alarms.json"

    seed_alarms_from_json(session, alarms_path)
    seed_alarms_from_json(session, alarms_path)  # second call must not duplicate rows

    assert session.query(Alarm).count() == 32
