"""Seeds the alarms table from the synthetic JSON seed data (D-04). The JSON file
stays the source of truth (committed, labelled synthetic); this just makes it
queryable. Idempotent — safe to call on every app startup."""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from suryasutra.db.models import Alarm


def seed_alarms_from_json(session: Session, path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    existing_ids = {alarm_id for (alarm_id,) in session.query(Alarm.id).all()}

    for alarm_data in data["alarms"]:
        if alarm_data["id"] in existing_ids:
            continue
        session.add(
            Alarm(
                id=alarm_data["id"],
                site_id=alarm_data["site_id"],
                inverter_id=alarm_data["inverter_id"],
                brand=alarm_data["brand"],
                model=alarm_data["model"],
                code=alarm_data["code"],
                category=alarm_data["category"],
                message=alarm_data["message"],
                raised_at=datetime.fromisoformat(alarm_data["raised_at"]),
                is_synthetic=alarm_data["is_synthetic"],
                answerable=alarm_data.get("answerable"),
            )
        )
    session.commit()
