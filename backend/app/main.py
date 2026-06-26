"""FastAPI app exposing the events API to the React frontend."""

from contextlib import asynccontextmanager
import json
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Load OpenRouter API key and details from scraping module .env
load_dotenv(os.path.join(os.path.dirname(__file__), "scraping", ".env"))

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .database import get_session
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
async def create_response(payload: EventomatResponseCreate, session: Session = Depends(get_session)):
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


@app.get("/eventomat/results")
async def get_results(user_token: str, session: Session = Depends(get_session)):
    # Fetch user responses
    stmt = select(EventomatResponse).where(EventomatResponse.user_token == user_token).order_by(EventomatResponse.created_at.desc())
    user_resp = session.exec(stmt).first()
    if not user_resp:
        raise HTTPException(status_code=404, detail="User responses not found")

    user_profile = json.loads(user_resp.payload)
    
    # Get all active events in the future
    events = session.exec(select(Event).where(Event.start >= datetime.now())).all()
    if not events:
        return []

    # Parse cached results
    cached_results = {}
    if user_resp.results:
        try:
            cached_results = json.loads(user_resp.results)
        except Exception:
            cached_results = {}

    # Check if there are missing events in cache
    missing_ids = [e.id for e in events if str(e.id) not in cached_results]
    
    if missing_ids:
        # Construct parameters for OpenRouter call
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash").strip()
        
        events_data = []
        for e in events:
            events_data.append({
                "event_id": e.id,
                "title": e.name,
                "location": e.location,
                "tags": [cat.name for cat in e.categories],
                "description": e.description
            })

        system_msg = (
            "You are the core personalization engine for 'IT-Events Mainfranken'. "
            "Analyze the user's profile data against the provided list of events and calculate "
            "a semantic match percentage (0 to 100) and a concise German matching explanation sentence. "
            "Calculation Rules:\n"
            "1. Topic & Format Alignment (Weight: 60%): Overlap between User Topics/Formats and Event Tags.\n"
            "2. Experience & Context Match (Weight: 40%): Semantically evaluate user experience level and freetext against event descriptions.\n"
            "3. Make sure one has a really high score! at least 85%"
            "Return a single, valid JSON object matching the requested schema. No conversational prose, markdown, or text wrapping."
        )

        user_msg = (
            f"USER PROFILE DATA:\n"
            f"- Interested Topics: {', '.join(user_profile.get('themen', []))}\n"
            f"- Experience Level: {user_profile.get('erfahrung', '')}\n"
            f"- Preferred Formats: {', '.join(user_profile.get('format', []))}\n"
            f"- Preferred Communication: {user_profile.get('alltag', '')}\n"
            f"- Additional Context: {user_profile.get('freitext', '')}\n\n"
            f"AVAILABLE EVENTS:\n"
            f"{json.dumps(events_data, ensure_ascii=False)}"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mainfranken-events",
            "X-Title": "Mainfranken IT-Events Personalization Engine"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        success = False
        if api_key:
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60.0)
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        # Parse the JSON response
                        raw_matches = json.loads(content)
                        # We expect either a root object or a 'matches' key
                        matches_list = raw_matches.get("matches", []) if isinstance(raw_matches, dict) else []
                        for item in matches_list:
                            ev_id = str(item.get("event_id"))
                            cached_results[ev_id] = {
                                "match_percentage": int(item.get("match_percentage", 60)),
                                "matching_reason": item.get("matching_reason", "Dieses Event passt gut zu deinen ausgewählten Profilpräferenzen.")
                            }
                        success = True
            except Exception as ex:
                print("OpenRouter error, falling back to local heuristic:", ex)

        # Fallback heuristic if API failed or API key missing
        if not success:
            for e in events:
                ev_id_str = str(e.id)
                if ev_id_str not in cached_results:
                    # Calculate simple heuristic
                    user_tags = []
                    for t in user_profile.get("themen", []):
                        user_tags.append(t)
                    for f in user_profile.get("format", []):
                        user_tags.append(f)
                    event_cats = [cat.name for cat in e.categories]
                    overlap = len(set(user_tags) & set(event_cats))
                    score = min(100, 60 + overlap * 15 + ((e.id * 3) % 7))
                    cached_results[ev_id_str] = {
                        "match_percentage": score,
                        "matching_reason": "Basierend auf deinen Themen- und Formatangaben passt dieses Event gut in dein Profil."
                    }

        # Save to database
        user_resp.results = json.dumps(cached_results)
        session.add(user_resp)
        session.commit()

    # Map parsed results back to frontend response schema
    output_matches = []
    for e in events:
        info = cached_results.get(str(e.id), {"match_percentage": 60, "matching_reason": "Basierend auf deinen Interessen."})
        output_matches.append({
            "id": e.id,
            "name": e.name,
            "location": e.location,
            "url": e.url,
            "description": e.description,
            "start": e.start,
            "end": e.end,
            "categories": [cat.name for cat in e.categories],
            "matchScore": info["match_percentage"],
            "matchingReason": info["matching_reason"]
        })

    # Sort descending by matchScore
    output_matches.sort(key=lambda x: x["matchScore"], reverse=True)
    return output_matches


