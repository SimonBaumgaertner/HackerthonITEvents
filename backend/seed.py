"""Insert a handful of demo events into the database.

Run from the backend/ directory:  .venv/bin/python seed.py
Safe to re-run: it skips seeding if events already exist.
"""

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import Event, EventKategorie

DEMO_EVENTS = [
    {
        "name": "PyCon DE 2026",
        "location": "Darmstadt, Germany",
        "url": "https://pycon.de",
        "description": "The largest German conference for the Python community.",
        "categories": ["Python", "Conference"],
    },
    {
        "name": "FOSDEM 2026",
        "location": "Brussels, Belgium",
        "url": "https://fosdem.org",
        "description": "Free and open-source software developers meeting.",
        "categories": ["Open Source", "Conference", "Free"],
    },
    {
        "name": "React Summit",
        "location": "Amsterdam, Netherlands",
        "url": "https://reactsummit.com",
        "description": "The biggest React conference worldwide.",
        "categories": ["JavaScript", "React", "Frontend"],
    },
    {
        "name": "KubeCon + CloudNativeCon Europe",
        "location": "Munich, Germany",
        "url": "https://www.cncf.io/kubecon-cloudnativecon-events/",
        "description": "Cloud native and Kubernetes ecosystem conference.",
        "categories": ["Cloud", "Kubernetes", "DevOps"],
    },
    {
        "name": "Local Hack Day",
        "location": "Berlin, Germany",
        "url": "https://hackday.example.com",
        "description": "A one-day hackathon for students and hobbyists.",
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
