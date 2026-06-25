"""SQLModel tables and API schemas.

`Event` and `EventKategorie` are the SQLite tables, linked one-to-many via a
relationship: one event has many categories. The `*Create` / `*Read` classes are
plain (non-table) schemas used by the API.
"""

from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class EventKategorie(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", ondelete="CASCADE")
    name: str

    event: "Event" = Relationship(back_populates="categories")


class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    location: str
    url: str
    description: str
    start: datetime
    end: datetime

    categories: list[EventKategorie] = Relationship(
        back_populates="event",
        cascade_delete=True,
    )


# --- API schemas (not tables) ---


class EventCreate(SQLModel):
    name: str
    location: str
    url: str
    description: str
    start: datetime
    end: datetime
    categories: list[str] = []


class EventRead(SQLModel):
    id: int
    name: str
    location: str
    url: str
    description: str
    start: datetime
    end: datetime
    categories: list[str] = []
