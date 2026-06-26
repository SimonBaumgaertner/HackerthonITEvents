#!/usr/bin/env python3
"""
Importiert strukturierte Events aus events.json in die SQLite-Datenbank.

Verwendet SQLModel — models.py ist die Source of Truth.
Mappt die LLM-extrahierten Felder auf Event + EventKategorie.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, delete, select

from app.database import engine, init_db
from app.models import Event, EventKategorie
from enums import Kategorie


# ───────────────────────────────────────────────
# HELPER: Feld-Mapping (LLM-Schema → models.py)
# ───────────────────────────────────────────────

def _clean(value: Any) -> str | None:
    """Bereinigt einen Wert zu einem stripped String oder None."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _combine_location(event: dict[str, Any]) -> str:
    """Kombiniert location_name und city zu einem Location-String."""
    parts: list[str] = []
    loc = _clean(event.get("location_name"))
    city = _clean(event.get("city"))
    if loc:
        parts.append(loc)
    if city and city.lower() != (loc.lower() if loc else ""):
        parts.append(city)
    return ", ".join(parts) if parts else "Ort folgt"


def _parse_datetime(date_str: Any, time_str: Any) -> datetime | None:
    """Baut aus Datum (YYYY-MM-DD) und Uhrzeit (HH:MM) ein datetime-Objekt."""
    date_val = _clean(date_str)
    if not date_val or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_val):
        return None

    time_val = _clean(time_str)
    time_part = time_val if time_val and re.fullmatch(r"\d{2}:\d{2}", time_val) else "00:00"

    try:
        return datetime.fromisoformat(f"{date_val}T{time_part}:00")
    except ValueError:
        return None


def _resolve_url(event: dict[str, Any]) -> str:
    """Wählt die beste verfügbare URL (registration_url > source_url)."""
    return _clean(event.get("registration_url")) or _clean(event.get("source_url")) or ""


def _extract_categories(event: dict[str, Any]) -> list[str]:
    """
    Extrahiert Kategorien aus dem Event.
    Verwendet ausschließlich das 'categories'-Feld, das bereits im LLM-Extraction-Schritt
    gegen die Kategorie-Enum (enums.py) validiert wurde. Fällt nicht auf tags/event_type zurück.
    """
    allowed = {k.value for k in Kategorie}

    categories: list[str] = []

    raw_categories = event.get("categories", [])
    if isinstance(raw_categories, list):
        for cat in raw_categories:
            c = _clean(cat)
            if c and c in allowed and c not in categories:
                categories.append(c)

    return categories


def _dedupe_key(event: dict[str, Any]) -> str:
    """Dedupe-Key aus Titel + Startdatum (robust, unabhängig vom Ort)."""
    title = str(event.get("title", "")).strip().lower()
    start_date = str(event.get("start_date", "")).strip()
    return f"{title}|{start_date}"


# ───────────────────────────────────────────────
# IMPORT
# ───────────────────────────────────────────────

def clear_database() -> None:
    """Löscht alle Events und Kategorien aus der Datenbank (frischer Start)."""
    init_db()
    with Session(engine) as session:
        session.exec(delete(EventKategorie))
        session.exec(delete(Event))
        session.commit()
    print("🗑️  Datenbank geleert (alle Events + Kategorien gelöscht).")


def import_events(
    events: list[dict[str, Any]],
    skip_existing: bool = True,
) -> tuple[int, int]:
    """
    Importiert eine Liste von Event-Dicts in die SQLite-Datenbank.

    Nutzt SQLModel (Event + EventKategorie) aus models.py.
    Dedupliziert anhand von Titel + Datum + Ort.

    Returns: (inserted, skipped)
    """
    init_db()

    inserted = 0
    skipped = 0

    with Session(engine) as session:
        # Bestehende Dedupe-Keys laden
        existing_keys: set[str] = set()
        if skip_existing:
            for ev in session.exec(select(Event)).all():
                date_str = ev.start.strftime("%Y-%m-%d") if ev.start else ""
                existing_keys.add(f"{ev.name.lower()}|{date_str}")

        for raw in events:
            title = _clean(raw.get("title"))
            if not title:
                skipped += 1
                continue

            start = _parse_datetime(raw.get("start_date"), raw.get("start_time"))
            if not start:
                # models.py: start ist Pflichtfeld — ohne Datum überspringen
                skipped += 1
                continue

            end = _parse_datetime(raw.get("end_date"), raw.get("end_time")) or start

            key = _dedupe_key(raw)
            if skip_existing and key in existing_keys:
                skipped += 1
                continue
            existing_keys.add(key)

            event = Event(
                name=title,
                location=_combine_location(raw),
                url=_resolve_url(raw),
                description=_clean(raw.get("description")) or "Keine Beschreibung verfügbar.",
                start=start,
                end=end,
                categories=[EventKategorie(name=c) for c in _extract_categories(raw)],
            )
            session.add(event)
            inserted += 1

        session.commit()

    return inserted, skipped


def load_events_from_json(json_path: Path) -> list[dict[str, Any]]:
    """Lädt Events aus einer JSON-Datei (formatiertes LLM-Output)."""
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)

    events = data.get("events", [])
    if not isinstance(events, list):
        raise ValueError(f"{json_path} enthält kein gültiges events-Array")
    return events


# ───────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importiere extrahierte Events in SQLite (SQLModel-Schema)"
    )
    parser.add_argument(
        "--input",
        default="events.json",
        help="Pfad zur formatierten Events-JSON (Default: events.json)",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Deaktiviert Deduplizierung (alle Events werden eingefügt)",
    )
    args = parser.parse_args()

    events = load_events_from_json(Path(args.input))

    # DB vor dem Import leeren, damit nur die neuen Daten dieser Pipeline übrig bleiben
    clear_database()

    inserted, skipped = import_events(events, skip_existing=not args.no_dedupe)

    print(f"✅ Import abgeschlossen: {inserted} eingefügt, {skipped} übersprungen")


if __name__ == "__main__":
    main()
