"""FastAPI app exposing the events API to the React frontend."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .database import get_session
import json
from .models import Event, EventCreate, EventKategorie, EventRead, EventomatResponse, EventomatResponseCreate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and insert the demo data if the database is empty.
    # `seed()` calls `init_db()` and skips when events already exist.
    from seed import seed

    seed()
    yield


app = FastAPI(title="HackerthonITEvents API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_read(event: Event) -> EventRead:
    return EventRead(
        id=event.id,
        name=event.name,
        location=event.location,
        url=event.url,
        description=event.description,
        start=event.start,
        end=event.end,
        categories=[c.name for c in event.categories],
    )


from sqlalchemy import or_

@app.get("/events", response_model=list[EventRead])
def list_events(
    category: str | None = None,
    experience: str | None = None,
    format: str | None = None,
    session: Session = Depends(get_session)
):
    query = select(Event)

    if category:
        cat_lower = category.lower()
        search_terms = []
        if "künstliche" in cat_lower:
            search_terms = ["ki", "data", "machine learning", "künstliche intelligenz"]
        elif "ui/ux" in cat_lower:
            search_terms = ["ui", "ux", "design", "frontend", "web", "accessibility"]
        elif "software" in cat_lower:
            search_terms = ["software", "devops", "code", "cloud", "python", "react"]
        elif "security" in cat_lower:
            search_terms = ["security", "hardware", "infrastruktur", "ransomware", "kmu"]
        elif "networking" in cat_lower:
            search_terms = ["networking", "network", "netzwerk"]
            
        if search_terms:
            conditions = []
            for term in search_terms:
                conditions.append(Event.name.icontains(term))
                conditions.append(Event.description.icontains(term))
                conditions.append(Event.categories.any(EventKategorie.name.icontains(term)))
            query = query.where(or_(*conditions))

    if experience:
        exp_lower = experience.lower()
        search_terms = []
        if "anfänger" in exp_lower:
            search_terms = ["anfänger", "einsteiger", "studierende", "grundlagen", "basis"]
        elif "fortgeschritten" in exp_lower:
            search_terms = ["fortgeschritten", "praxis", "solide"]
        elif "experte" in exp_lower:
            search_terms = ["experte", "profi", "intensiv", "täglich"]
        
        if search_terms:
            conditions = []
            for term in search_terms:
                conditions.append(Event.description.icontains(term))
                conditions.append(Event.name.icontains(term))
                conditions.append(Event.categories.any(EventKategorie.name.icontains(term)))
            query = query.where(or_(*conditions))

    if format:
        fmt_lower = format.lower()
        search_terms = []
        if "fachvorträge" in fmt_lower:
            search_terms = ["vortrag", "vorträge", "keynote", "konferenz", "talk", "forum", "summit"]
        elif "workshops" in fmt_lower:
            search_terms = ["workshop", "hackathon", "hands-on", "projekt"]
        elif "networking" in fmt_lower:
            search_terms = ["meetup", "networking", "community", "treffen"]
        elif "karriere" in fmt_lower:
            search_terms = ["karriere", "recruiting", "job"]
            
        if search_terms:
            conditions = []
            for term in search_terms:
                conditions.append(Event.description.icontains(term))
                conditions.append(Event.name.icontains(term))
                conditions.append(Event.categories.any(EventKategorie.name.icontains(term)))
            query = query.where(or_(*conditions))

    events = session.exec(query).unique().all()
    return [to_read(e) for e in events]


@app.post("/events", response_model=EventRead, status_code=201)
def create_event(payload: EventCreate, session: Session = Depends(get_session)):
    event = Event(
        name=payload.name,
        location=payload.location,
        url=payload.url,
        description=payload.description,
        start=payload.start,
        end=payload.end,
        categories=[EventKategorie(name=name) for name in payload.categories],
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return to_read(event)


@app.get("/events/{event_id}", response_model=EventRead)
def get_event(event_id: int, session: Session = Depends(get_session)):
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return to_read(event)


@app.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, session: Session = Depends(get_session)):
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    session.delete(event)
    session.commit()


@app.post("/eventomat/responses", status_code=201)
def create_response(payload: EventomatResponseCreate, session: Session = Depends(get_session)):
    response = EventomatResponse(
        user_token=payload.user_token,
        payload=json.dumps(payload.payload),
    )
    session.add(response)
    session.commit()
    session.refresh(response)
    return {
        "id": response.id,
        "user_token": response.user_token,
        "created_at": response.created_at,
    }

