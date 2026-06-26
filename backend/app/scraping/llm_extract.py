#!/usr/bin/env python3
"""
Event-Extraktion aus Rohdaten via OpenRouter API.
Verarbeitet alle gescrapten Inhalte (extracted_text_full + text_blocks) per Chunking.
Erzwingt ein festes Event-Schema für den späteren SQLite-Import.
"""

import json
import os
import re
import time
from typing import Any

import requests

from app.scraping.llm_client import BaseLLMClient, LLMMessage, build_default_llm_client
from enums import Kategorie

MAX_CHUNK_CHARS = 60_000
ALLOWED_EVENT_TYPES = {"workshop", "vortrag", "netzwerken", "messe", "webinar", "hackathon", "sonstiges"}
ALLOWED_FORMATS = {"online", "offline", "hybrid"}

# Erlaubte Kategorien — ausschließlich die Werte aus der Kategorie-Enum (enums.py)
ALLOWED_CATEGORIES: list[str] = [k.value for k in Kategorie]
ALLOWED_CATEGORIES_SET: set[str] = set(ALLOWED_CATEGORIES)

EVENT_SCHEMA_FIELDS = [
    "title",
    "description",
    "start_date",
    "end_date",
    "start_time",
    "end_time",
    "location_name",
    "city",
    "organizer",
    "event_type",
    "tags",
    "categories",
    "registration_url",
    "source_url",
    "source_name",
    "is_free",
    "format",
]


def parse_json_response(text: str | None) -> dict[str, Any]:
    """Extrahiert JSON aus einer LLM-Antwort (auch aus Markdown-Codeblöcken)."""
    if text is None:
        raise ValueError("LLM-Antwort ist None (leere API-Antwort / Rate-Limit / Modell-Fehler)")

    text = text.strip()
    if not text:
        raise ValueError("Leere LLM-Antwort")

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fenced:
        text = fenced.group(1).strip()

    return json.loads(text)


def call_llm(prompt: str, llm_client: BaseLLMClient) -> str:
    """Sendet den Prompt über das gemeinsame LLM-Interface."""
    response = llm_client.chat(
        messages=[
            LLMMessage(
                role="system",
                content=(
                    "Du extrahierst Veranstaltungen aus Website-Rohdaten. "
                    "Antworte ausschließlich mit validem JSON, ohne Markdown oder Erklärungen."
                ),
            ),
            LLMMessage(role="user", content=prompt),
        ],
        temperature=0.1,
    )
    return response.content


def get_source_content_chunks(source_data: dict) -> list[str]:
    """
    Liefert alle Inhalte einer Quelle als Chunks.
    Priorität: extracted_text_full, Fallback: alle text_blocks.
    """
    full_text = source_data.get("extracted_text_full", "").strip()
    if full_text:
        return _split_text(full_text, MAX_CHUNK_CHARS)

    blocks = source_data.get("text_blocks", [])
    if not blocks:
        return []

    combined = ""
    for block in blocks:
        combined += f"\n--- BLOCK ---\n{block.get('text', '')}\n"

    return _split_text(combined.strip(), MAX_CHUNK_CHARS)


def _split_text(text: str, chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            split_at = text.rfind("\n\n", start, end)
            if split_at > start + chunk_size // 2:
                end = split_at
        chunks.append(text[start:end].strip())
        start = end

    return [chunk for chunk in chunks if chunk]


def build_extraction_prompt(source_data: dict, content: str, chunk_index: int, chunk_total: int) -> str:
    """Erzeugt den Extraktions-Prompt für einen Content-Chunk."""
    chunk_info = f" (Teil {chunk_index}/{chunk_total})" if chunk_total > 1 else ""
    categories_list_str = "\n".join(f"  - {c}" for c in ALLOWED_CATEGORIES)

    return f"""Du extrahierst strukturierte Veranstaltungsdaten aus gescrapten Rohdaten einer Website{chunk_info}.

QUELLE: {source_data['source_name']}
URL: {source_data['source_url']}
TITEL DER SEITE: {source_data.get('page_title', 'N/A')}
SEITEN GESCRAPED: {source_data.get('pages_scraped', 1)}

AUFGABE:
Extrahiere alle echten Veranstaltungen / Events aus den bereitgestellten Inhalten.

WICHTIGE REGELN:
- Gib ausschließlich valides JSON zurück.
- Gib ein JSON-Objekt mit dem Feld "events" zurück.
- "events" muss immer ein JSON-Array sein.
- Erfinde keine Informationen.
- Wenn ein Wert nicht explizit oder nicht verlässlich erkennbar ist, setze ihn auf null.
- Extrahiere nur echte Veranstaltungen, keine allgemeinen News, keine bloßen Hinweise, keine statischen Infotexte.
- Wenn auf der Seite mehrere Veranstaltungen vorkommen, gib mehrere Event-Objekte zurück.
- Beschreibungen kurz, sachlich und neutral formulieren.
- Datumsformat: YYYY-MM-DD
- Uhrzeitformat: HH:MM im 24-Stunden-Format
- tags muss immer ein Array sein.
- format darf nur "online", "offline", "hybrid" oder null sein.
- event_type darf nur einer dieser Werte sein: "workshop", "vortrag", "netzwerken", "messe", "webinar", "hackathon", "sonstiges".
- source_url muss die URL der Quellseite sein: {source_data['source_url']}
- source_name muss der Name der Quelle sein: {source_data['source_name']}

KATEGORIEN (sehr wichtig):
- Das Feld "categories" muss ein Array von Strings sein.
- Es dürfen AUSSCHLIESSLICH die folgenden Werte verwendet werden — keine anderen:
{categories_list_str}
- Wähle für jedes Event alle passenden Kategorien aus dieser Liste.
- Wenn keine Kategorie passt, setze categories auf ein leeres Array [].
- Erfinde keine eigenen Kategorien und verwende keine Synonyme.

OUTPUT-SCHEMA:
{{
  "events": [
    {{
      "title": "string",
      "description": "string oder null",
      "start_date": "YYYY-MM-DD oder null",
      "end_date": "YYYY-MM-DD oder null",
      "start_time": "HH:MM oder null",
      "end_time": "HH:MM oder null",
      "location_name": "string oder null",
      "city": "string oder null",
      "organizer": "string oder null",
      "event_type": "workshop|vortrag|netzwerken|messe|webinar|hackathon|sonstiges oder null",
      "tags": ["string"],
      "categories": ["{ALLOWED_CATEGORIES[0]}", "{ALLOWED_CATEGORIES[1]}", ...],
      "registration_url": "string oder null",
      "source_url": "{source_data['source_url']}",
      "source_name": "{source_data['source_name']}",
      "is_free": "true|false|null",
      "format": "online|offline|hybrid|null"
    }}
  ]
}}

WENN KEINE EVENTS VORHANDEN SIND:
{{"events": []}}

ROHDATEN:
{content}
"""


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _normalize_date(value: Any) -> str | None:
    value = _clean_str(value)
    if not value:
        return None
    return value if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None


def _normalize_time(value: Any) -> str | None:
    value = _clean_str(value)
    if not value:
        return None
    return value if re.fullmatch(r"\d{2}:\d{2}", value) else None


def normalize_event(event: dict[str, Any], source_data: dict[str, Any]) -> dict[str, Any] | None:
    title = _clean_str(event.get("title"))
    if not title:
        return None

    event_type = _clean_str(event.get("event_type"))
    if event_type and event_type not in ALLOWED_EVENT_TYPES:
        event_type = "sonstiges"

    event_format = _clean_str(event.get("format"))
    if event_format and event_format not in ALLOWED_FORMATS:
        event_format = None

    tags = event.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(tag).strip() for tag in tags if str(tag).strip()]

    # Kategorien validieren — nur Werte aus der Enum erlauben
    raw_categories = event.get("categories", [])
    if not isinstance(raw_categories, list):
        raw_categories = []
    categories: list[str] = []
    for cat in raw_categories:
        cat_clean = _clean_str(cat)
        if cat_clean and cat_clean in ALLOWED_CATEGORIES_SET and cat_clean not in categories:
            categories.append(cat_clean)

    is_free = event.get("is_free")
    if isinstance(is_free, str):
        lowered = is_free.strip().lower()
        if lowered in {"true", "ja", "yes", "1"}:
            is_free = True
        elif lowered in {"false", "nein", "no", "0"}:
            is_free = False
        else:
            is_free = None
    elif not isinstance(is_free, bool):
        is_free = None

    normalized = {
        "title": title,
        "description": _clean_str(event.get("description")),
        "start_date": _normalize_date(event.get("start_date")),
        "end_date": _normalize_date(event.get("end_date")),
        "start_time": _normalize_time(event.get("start_time")),
        "end_time": _normalize_time(event.get("end_time")),
        "location_name": _clean_str(event.get("location_name")),
        "city": _clean_str(event.get("city")),
        "organizer": _clean_str(event.get("organizer")),
        "event_type": event_type,
        "tags": tags,
        "categories": categories,
        "registration_url": _clean_str(event.get("registration_url")),
        "source_url": _clean_str(event.get("source_url")) or source_data["source_url"],
        "source_name": _clean_str(event.get("source_name")) or source_data["source_name"],
        "is_free": is_free,
        "format": event_format,
    }

    for field in EVENT_SCHEMA_FIELDS:
        if field in ("tags", "categories"):
            normalized.setdefault(field, [])
        else:
            normalized.setdefault(field, None)

    return normalized


def _event_key(event: dict) -> str:
    title = str(event.get("title", "")).strip().lower()
    date = str(event.get("start_date", "")).strip()
    city = str(event.get("city", "")).strip().lower()
    return f"{title}|{date}|{city}"


def merge_events(existing: list[dict], new_events: list[dict], source_data: dict[str, Any]) -> list[dict]:
    """Führt Event-Listen zusammen, normalisiert und dedupliziert."""
    merged = list(existing)
    seen = {_event_key(event) for event in merged}

    for event in new_events:
        normalized = normalize_event(event, source_data)
        if not normalized:
            continue
        key = _event_key(normalized)
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)

    return merged


def extract_events_from_source(
    source_data: dict,
    llm_client: BaseLLMClient,
    retries: int = 2,
) -> dict[str, Any]:
    """Extrahiert Events für eine Quelle via OpenRouter (alle Chunks)."""
    if source_data.get("error"):
        return {
            "source": source_data["source_name"],
            "source_url": source_data["source_url"],
            "events_found": 0,
            "events": [],
            "llm_error": source_data["error"],
            "skipped": True,
            "chunks_processed": 0,
        }

    chunks = get_source_content_chunks(source_data)
    if not chunks:
        return {
            "source": source_data["source_name"],
            "source_url": source_data["source_url"],
            "events_found": 0,
            "events": [],
            "llm_error": "Kein extrahierter Text vorhanden",
            "skipped": False,
            "chunks_processed": 0,
        }

    all_events: list[dict] = []
    last_error = ""

    for chunk_index, chunk in enumerate(chunks, start=1):
        prompt = build_extraction_prompt(source_data, chunk, chunk_index, len(chunks))

        for attempt in range(retries + 1):
            try:
                raw_response = call_llm(prompt, llm_client=llm_client)
                parsed = parse_json_response(raw_response)
                events = parsed.get("events", [])
                if not isinstance(events, list):
                    raise ValueError("LLM-Antwort enthält kein gültiges events-Array")
                all_events = merge_events(all_events, events, source_data)
                last_error = ""
                break
            except (json.JSONDecodeError, ValueError, requests.RequestException, RuntimeError) as exc:
                last_error = str(exc)
                if attempt < retries:
                    time.sleep(2)

        if last_error:
            return {
                "source": source_data["source_name"],
                "source_url": source_data["source_url"],
                "events_found": len(all_events),
                "events": all_events,
                "llm_error": last_error,
                "skipped": False,
                "chunks_processed": chunk_index,
            }

        if len(chunks) > 1:
            time.sleep(0.5)

    return {
        "source": source_data["source_name"],
        "source_url": source_data["source_url"],
        "events_found": len(all_events),
        "events": all_events,
        "llm_error": None,
        "skipped": False,
        "chunks_processed": len(chunks),
    }


def format_all_with_llm(
    raw_data: dict,
    api_key: str | None = None,
    model: str | None = None,
    llm_client: BaseLLMClient | None = None,
    delay_seconds: float = 1.0,
) -> dict[str, Any]:
    """Formatiert alle Quellen aus den Rohdaten über das gemeinsame LLM-Interface."""
    llm_client = llm_client or build_default_llm_client(api_key=api_key, model=model)

    results: dict[str, Any] = {
        "formatted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": getattr(llm_client, "model", model or os.environ.get("OPENROUTER_MODEL", "unknown")),
        "total_sources": len(raw_data.get("sources", [])),
        "successful": 0,
        "failed": 0,
        "total_events": 0,
        "sources": [],
        "events": [],
    }

    print(f"\n{'=' * 70}")
    print("LLM-FORMATIERUNG via OpenRouter")
    print(f"Modell: {model}")
    print(f"{'=' * 70}\n")

    for source_data in raw_data.get("sources", []):
        name = source_data["source_name"]
        chunks = get_source_content_chunks(source_data)
        print(f"[LLM] {name} ({len(chunks)} Chunk(s))")

        extracted = extract_events_from_source(source_data, llm_client=llm_client)
        results["sources"].append(extracted)

        if extracted.get("skipped"):
            print(f"  [SKIP] Scraping-Fehler: {extracted.get('llm_error')}")
            results["failed"] += 1
        elif extracted.get("llm_error"):
            print(f"  [ERROR] {extracted['llm_error']}")
            results["failed"] += 1
        else:
            count = extracted.get("events_found", 0)
            print(f"  [OK] {count} Events extrahiert")
            results["successful"] += 1
            results["total_events"] += count

            for event in extracted.get("events", []):
                results["events"].append(dict(event))

        time.sleep(delay_seconds)

    print(f"\n{'=' * 70}")
    print(
        f"ERGEBNIS: {results['successful']}/{results['total_sources']} Quellen OK, "
        f"{results['total_events']} Events gesamt"
    )
    print(f"{'=' * 70}\n")

    return results


def save_formatted(data: dict, filename: str = "events.json") -> None:
    """Speichert formatierte Events als JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(filename) / 1024
    print(f"✅ Formatierte Events gespeichert: {filename} ({size_kb:.1f} KB)")
