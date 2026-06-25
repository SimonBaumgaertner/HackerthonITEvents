"""FastAPI app exposing the events API to the React frontend."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .database import get_session
from .models import Event, EventCreate, EventKategorie, EventRead


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


@app.get("/events", response_model=list[EventRead])
def list_events(session: Session = Depends(get_session)):
    events = session.exec(select(Event)).all()
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
