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
            "Die größte IT-Leitkonferenz der Region — Keynotes, Expo & Networking auf höchstem Niveau. "
            "Das IT-FORUM MAINFRANKEN 2026 bringt Entscheider:innen, Entwickler:innen und Innovator:innen der Region zusammen. "
            "Erwarte hochkarätige Keynotes, praxisnahe Workshops und eine Expo mit den spannendsten Tech-Anbietern Mainfrankens. "
            "Tausche dich mit der Community aus, entdecke neue Technologien und finde Partner für deine nächsten Projekte — alles an einem Tag, an einem Ort."
        ),
        "start": datetime(2026, 10, 15, 9, 0),
        "end": datetime(2026, 10, 15, 18, 0),
        "categories": ["Networking", "Innovation", "KI"],
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
    {
        "name": "Würzburg Web Week 2026",
        "location": "Verschiedene Orte, Würzburg",
        "url": "https://wueww.de",
        "description": "Die Festival-Woche voller Digital-Themen im Rückblick.",
        "start": datetime(2026, 4, 10, 9, 0),
        "end": datetime(2026, 4, 17, 18, 0),
        "categories": ["Festival", "Digitalisierung", "Networking"],
    },
    {
        "name": "Winter Hackathon 2025",
        "location": "TH Aschaffenburg",
        "url": "https://it-mainfranken.de/winter-hackathon",
        "description": "Kreative Coding-Projekte gegen die Kälte des Winters.",
        "start": datetime(2025, 1, 15, 10, 0),
        "end": datetime(2025, 1, 16, 18, 0),
        "categories": ["Hackathon", "Studierende"],
    },
    {
        "name": "IT-Forum Mainfranken 2025",
        "location": "Vogel Convention Center, Würzburg",
        "url": "https://it-mainfranken.de/forum-2025",
        "description": "Rückblick auf die erfolgreiche IT-Konferenz des vergangenen Jahres.",
        "start": datetime(2025, 10, 10, 9, 0),
        "end": datetime(2025, 10, 10, 18, 0),
        "categories": ["Konferenz", "Networking", "Highlight"],
    },
    {
        "name": "Cloud Native Meetup #4",
        "location": "i-Campus, Schweinfurt",
        "url": "https://it-mainfranken.de/cloud-meetup",
        "description": "Kubernetes, Docker und Serverless im praktischen Einsatz (vergangen).",
        "start": datetime(2025, 11, 20, 18, 0),
        "end": datetime(2025, 11, 20, 21, 0),
        "categories": ["Cloud", "Meetup", "DevOps"],
    },
    {
        "name": "Web Accessibility Workshop",
        "location": "Online",
        "url": "https://it-mainfranken.de/a11y",
        "description": "Wie bauen wir barrierefreie Webanwendungen? Ein Intensiv-Workshop.",
        "start": datetime(2026, 2, 5, 14, 0),
        "end": datetime(2026, 2, 5, 17, 0),
        "categories": ["Frontend", "Workshop", "Accessibility"],
    },
    {
        "name": "Agile Leadership Konferenz",
        "location": "CCW Würzburg",
        "url": "https://it-mainfranken.de/agile-leadership",
        "description": "Neue Wege in der Führung von IT-Teams.",
        "start": datetime(2026, 11, 5, 9, 0),
        "end": datetime(2026, 11, 5, 18, 0),
        "categories": ["Agile", "Leadership", "Konferenz"],
    },
    {
        "name": "Women in Tech Würzburg",
        "location": "Posthalle, Würzburg",
        "url": "https://it-mainfranken.de/wit",
        "description": "Das Netzwerk-Event für Frauen in der IT-Branche Mainfrankens.",
        "start": datetime(2026, 10, 12, 18, 0),
        "end": datetime(2026, 10, 12, 22, 0),
        "categories": ["Networking", "Diversity"],
    },
    {
        "name": "Mainfranken IoT Summit",
        "location": "Vogel Convention Center",
        "url": "https://it-mainfranken.de/iot-summit",
        "description": "Die Zukunft des Internet of Things in der Industrie.",
        "start": datetime(2027, 1, 20, 10, 0),
        "end": datetime(2027, 1, 20, 17, 0),
        "categories": ["IoT", "Hardware", "Konferenz"],
    },
    {
        "name": "Python User Group Treffen",
        "location": "TH Aschaffenburg",
        "url": "https://it-mainfranken.de/python-meetup",
        "description": "Austausch über neue Python-Features, FastAPI und SQLModel.",
        "start": datetime(2026, 8, 15, 19, 0),
        "end": datetime(2026, 8, 15, 21, 30),
        "categories": ["Python", "Meetup", "Community"],
    },
    {
        "name": "E-Commerce Day 2026",
        "location": "i-Campus, Schweinfurt",
        "url": "https://it-mainfranken.de/ecommerce",
        "description": "Trends im Online-Handel, Shopsysteme und Payment-Lösungen.",
        "start": datetime(2026, 9, 5, 9, 0),
        "end": datetime(2026, 9, 5, 16, 0),
        "categories": ["E-Commerce", "Web"],
    },
    {
        "name": "Startup Weekend Würzburg",
        "location": "ZDI Mainfranken",
        "url": "https://it-mainfranken.de/startup-weekend",
        "description": "In 54 Stunden von der Idee zum Prototypen. Ein Rückblick.",
        "start": datetime(2025, 5, 12, 17, 0),
        "end": datetime(2025, 5, 14, 20, 0),
        "categories": ["Startup", "Hackathon", "Business"],
    },
    {
        "name": "Data Analytics Meetup",
        "location": "Online",
        "url": "https://it-mainfranken.de/data-analytics",
        "description": "Wie visualisieren wir große Datenmengen effektiv?",
        "start": datetime(2025, 8, 20, 18, 0),
        "end": datetime(2025, 8, 20, 20, 0),
        "categories": ["Data", "Meetup"],
    },
    {
        "name": "Retro Gaming Hackathon",
        "location": "FH Würzburg-Schweinfurt",
        "url": "https://it-mainfranken.de/retro-hack",
        "description": "Entwicklung von Spielen für alte Konsolen – Eine Nostalgiereise.",
        "start": datetime(2024, 12, 1, 10, 0),
        "end": datetime(2024, 12, 2, 18, 0),
        "categories": ["Gaming", "Hackathon", "Fun"],
    },
    {
        "name": "IT-Sicherheit für KMU",
        "location": "IHK Würzburg",
        "url": "https://it-mainfranken.de/kmu-security",
        "description": "Best Practices zum Schutz vor Ransomware (vergangenes Event).",
        "start": datetime(2026, 1, 15, 14, 0),
        "end": datetime(2026, 1, 15, 18, 0),
        "categories": ["Security", "Business"],
    },
    {
        "name": "Blockchain Forum Mainfranken",
        "location": "Vogel Convention Center",
        "url": "https://it-mainfranken.de/blockchain",
        "description": "Krypto, Web3 und Smart Contracts in der Praxis.",
        "start": datetime(2025, 3, 10, 9, 0),
        "end": datetime(2025, 3, 10, 16, 0),
        "categories": ["Web3", "Blockchain", "Konferenz"],
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
