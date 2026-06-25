"""Insert a handful of demo events into the database.

Run from the backend/ directory:  .venv/bin/python seed.py
Safe to re-run: it skips seeding if events already exist.
"""

from datetime import datetime

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import Event, EventKategorie

DEMO_EVENTS = [
    {
        "name": "IT-Forum Mainfranken 2026",
        "location": "Vogel Convention Center, Würzburg",
        "url": "https://it-mainfranken.de/forum",
        "description": (
            "Die größte IT-Leitkonferenz der Region — Keynotes, Expo & Networking "
            "auf höchstem Niveau. Die Leitkonferenz für die digitale Zukunft "
            "Mainfrankens — Keynotes, Expo, Workshops und das größte IT-Networking "
            "der Region."
        ),
        "start": datetime(2026, 10, 15, 9, 0),
        "end": datetime(2026, 10, 15, 18, 0),
        "categories": ["Konferenz", "Networking", "Highlight"],
    },
    {
        "name": "DevOps Meetup Schweinfurt",
        "location": "i-Campus, Schweinfurt",
        "url": "https://it-mainfranken.de/devops-meetup",
        "description": "Hands-on Vorträge rund um CI/CD, Container und Cloud Native.",
        "start": datetime(2026, 9, 24, 18, 30),
        "end": datetime(2026, 9, 24, 21, 0),
        "categories": ["DevOps", "Meetup", "Cloud"],
    },
    {
        "name": "Cyber Security Day Aschaffenburg",
        "location": "TH Aschaffenburg",
        "url": "https://it-mainfranken.de/security-day",
        "description": "Ein Tag voller Talks und Workshops zu IT-Sicherheit und Awareness.",
        "start": datetime(2026, 11, 12, 9, 30),
        "end": datetime(2026, 11, 12, 17, 0),
        "categories": ["Security", "Workshop"],
    },
    {
        "name": "Frontend Night Würzburg",
        "location": "Posthalle, Würzburg",
        "url": "https://it-mainfranken.de/frontend-night",
        "description": "React, TypeScript und modernes Web-Design im Fokus.",
        "start": datetime(2026, 9, 30, 19, 0),
        "end": datetime(2026, 9, 30, 22, 0),
        "categories": ["Frontend", "React", "Meetup"],
    },
    {
        "name": "KI & Data Science Summit",
        "location": "Vogel Convention Center, Würzburg",
        "url": "https://it-mainfranken.de/ki-summit",
        "description": "Praxisnahe Einblicke in Machine Learning und Data Engineering.",
        "start": datetime(2026, 12, 3, 9, 0),
        "end": datetime(2026, 12, 3, 16, 30),
        "categories": ["KI", "Data Science", "Konferenz"],
    },
    {
        "name": "Mainfranken Hack Day",
        "location": "ZDI Mainfranken, Würzburg",
        "url": "https://it-mainfranken.de/hack-day",
        "description": "Ein eintägiger Hackathon für Studierende und die Community.",
        "start": datetime(2026, 10, 25, 10, 0),
        "end": datetime(2026, 10, 25, 20, 0),
        "categories": ["Hackathon", "Community"],
    },
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(Event)).first() is not None:
            print("Events already present — skipping seed.")
            return
        for data in DEMO_EVENTS:
            categories = [EventKategorie(name=n) for n in data.pop("categories")]
            session.add(Event(**data, categories=categories))
        session.commit()
        print(f"Inserted {len(DEMO_EVENTS)} demo events.")


if __name__ == "__main__":
    seed()
