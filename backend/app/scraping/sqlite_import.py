#!/usr/bin/env python3
"""
Importiert strukturierte Events aus events.json in eine SQLite-Datenbank.
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def build_dedupe_key(event: dict[str, Any]) -> str:
    title = normalize_text(event.get("title"))
    start_date = normalize_text(event.get("start_date"))
    city = normalize_text(event.get("city"))
    location_name = normalize_text(event.get("location_name"))
    fallback_place = city or location_name
    return f"{title}|{start_date}|{fallback_place}"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            end_date TEXT,
            start_time TEXT,
            end_time TEXT,
            location_name TEXT,
            city TEXT,
            organizer TEXT,
            event_type TEXT,
            tags_json TEXT,
            registration_url TEXT,
            source_url TEXT,
            source_name TEXT,
            is_free INTEGER,
            format TEXT,
            dedupe_key TEXT,
            raw_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_dedupe_key
        ON events(dedupe_key)
        """
    )
    conn.commit()


def load_events(json_path: Path) -> list[dict[str, Any]]:
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)

    events = data.get("events", [])
    if not isinstance(events, list):
        raise ValueError("events.json enthält kein gültiges events-Array")
    return events


def import_events(events: list[dict[str, Any]], db_path: Path) -> tuple[int, int]:
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        inserted = 0
        skipped = 0

        for event in events:
            title = str(event.get("title", "")).strip()
            if not title:
                skipped += 1
                continue

            dedupe_key = build_dedupe_key(event)
            is_free = event.get("is_free")
            if is_free is True:
                is_free_db = 1
            elif is_free is False:
                is_free_db = 0
            else:
                is_free_db = None

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    title,
                    description,
                    start_date,
                    end_date,
                    start_time,
                    end_time,
                    location_name,
                    city,
                    organizer,
                    event_type,
                    tags_json,
                    registration_url,
                    source_url,
                    source_name,
                    is_free,
                    format,
                    dedupe_key,
                    raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    event.get("description"),
                    event.get("start_date"),
                    event.get("end_date"),
                    event.get("start_time"),
                    event.get("end_time"),
                    event.get("location_name"),
                    event.get("city"),
                    event.get("organizer"),
                    event.get("event_type"),
                    json.dumps(event.get("tags", []), ensure_ascii=False),
                    event.get("registration_url"),
                    event.get("source_url"),
                    event.get("source_name"),
                    is_free_db,
                    event.get("format"),
                    dedupe_key,
                    json.dumps(event, ensure_ascii=False),
                ),
            )

            if cursor.rowcount == 0:
                skipped += 1
            else:
                inserted += 1

        conn.commit()
        return inserted, skipped
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Importiere extrahierte Events in SQLite")
    parser.add_argument("--input", default="events.json", help="Pfad zur formatierten Events-JSON")
    parser.add_argument("--db", default="events.db", help="Pfad zur SQLite-Datenbank")
    args = parser.parse_args()

    events = load_events(Path(args.input))
    inserted, skipped = import_events(events, Path(args.db))

    print(f"✅ SQLite-Import abgeschlossen: {inserted} eingefügt, {skipped} übersprungen")
    print(f"📦 Datenbank: {args.db}")


if __name__ == "__main__":
    main()
