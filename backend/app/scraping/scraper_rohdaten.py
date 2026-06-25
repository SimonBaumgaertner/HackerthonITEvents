#!/usr/bin/env python3
"""
Mainfranken Event Scraper — ROHDATEN-EXTRACTION
Scrapt alle konfigurierten Quellen inkl. Pagination und JS-Seiten (Playwright).
Gibt pro Quelle vollständigen HTML-Content, bereinigten Text und strukturierte Blöcke aus.

Output: events_raw.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

# Ensure backend/ is on sys.path so `from app...` works when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
from bs4 import BeautifulSoup, Comment, Tag
from dotenv import load_dotenv

# ───────────────────────────────────────────────
# KONFIGURATION
# ───────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8",
}

MAX_HTML_SIZE = 2_000_000
MAX_PAGES_PER_SOURCE = 25
MIN_BLOCK_TEXT_LEN = 40
REQUEST_DELAY = 0.5

# Wenn wenig Text bei großem HTML → Playwright-Fallback
JS_FALLBACK_MIN_HTML_BYTES = 20_000
JS_FALLBACK_MAX_TEXT_CHARS = 1_500

BLOCK_SELECTORS_SPECIFIC = [
    "article",
    "div.event",
    "div.veranstaltung",
    "div.termin",
    "li.event",
    "li.veranstaltung",
    "details",
    "tr.vevent",
    "div[class*='event']",
    "div[class*='termin']",
    "div[class*='veranstaltung']",
    "li[class*='event']",
    "li[class*='termin']",
    ".post",
    ".entry",
    ".card",
    "div[class*='news']",
]

BLOCK_SELECTORS_BROAD = ["section", "main", "div.content", "#content"]

PAGINATION_LINK_TEXT = re.compile(
    r"(weiter|nächste|next|»|›|vor|previous|prev|«|‹|\d+)",
    re.IGNORECASE,
)
PAGINATION_URL_HINTS = re.compile(
    r"(page=\d+|/page/\d+|p=\d+|offset=\d+|start=\d+|/p/\d+)",
    re.IGNORECASE,
)

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ───────────────────────────────────────────────
# FETCH
# ───────────────────────────────────────────────

def fetch(url: str, retries: int = 2) -> tuple[str, int, str]:
    """HTTP-Fetch mit Retry (auch bei temporären HTTP-Fehlern)."""
    retriable_status = {408, 429, 500, 502, 503, 504}
    last_error = "Unknown error"

    for attempt in range(retries + 1):
        try:
            resp = SESSION.get(url, timeout=30)
            if resp.status_code >= 400:
                if resp.status_code in retriable_status and attempt < retries:
                    time.sleep(1 + attempt)
                    continue
                return "", resp.status_code, f"HTTP {resp.status_code}"
            resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.text, resp.status_code, ""
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt < retries:
                time.sleep(1 + attempt)

    return "", 0, last_error


def fetch_with_playwright(url: str) -> tuple[str, int, str]:
    """JS-Rendering via Playwright (Fallback für dynamische Seiten)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "", 0, "Playwright nicht installiert (pip install playwright && playwright install chromium)"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(1500)
            html = page.content()
            browser.close()
        return html, 200, ""
    except Exception as exc:
        return "", 0, f"Playwright-Fehler: {exc}"


def needs_js_fallback(html: str, extracted_text: str) -> bool:
    """Erkennt Seiten, bei denen statisches HTML offensichtlich unvollständig ist."""
    if len(html) < JS_FALLBACK_MIN_HTML_BYTES:
        return False
    if len(extracted_text) >= JS_FALLBACK_MAX_TEXT_CHARS:
        return False
    return True


# ───────────────────────────────────────────────
# PAGINATION
# ───────────────────────────────────────────────

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def same_domain(base_url: str, candidate: str) -> bool:
    return urlparse(base_url).netloc == urlparse(candidate).netloc


def find_pagination_urls(html: str, base_url: str) -> list[str]:
    """Findet Pagination-Links auf derselben Domain."""
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    seen = {normalize_url(base_url)}

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        absolute = normalize_url(urljoin(base_url, href))
        if not same_domain(base_url, absolute):
            continue
        if absolute in seen:
            continue

        text = link.get_text(" ", strip=True)
        classes = " ".join(link.get("class", []))
        rel = " ".join(link.get("rel", []))
        looks_paginated = (
            "next" in rel
            or PAGINATION_URL_HINTS.search(absolute)
            or (
                PAGINATION_LINK_TEXT.search(text)
                and any(k in classes.lower() for k in ("page", "pager", "pagination", "next", "prev"))
            )
        )
        if looks_paginated:
            found.append(absolute)
            seen.add(absolute)

    return found[:MAX_PAGES_PER_SOURCE - 1]


def discover_all_page_urls(start_url: str, first_html: str) -> list[str]:
    """Start-URL + Pagination-URLs (dedupliziert)."""
    urls = [normalize_url(start_url)]
    seen = set(urls)

    for page_url in find_pagination_urls(first_html, start_url):
        if page_url not in seen:
            urls.append(page_url)
            seen.add(page_url)

    return urls[:MAX_PAGES_PER_SOURCE]


# ───────────────────────────────────────────────
# HTML / TEXT EXTRACTION
# ───────────────────────────────────────────────

def clean_html(html: str) -> str:
    """Bereinigt HTML für LLM-Verarbeitung."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
        tag.decompose()

    for tag in soup.find_all(["div", "span"]):
        if not tag.get_text(strip=True):
            tag.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    cleaned = str(soup)
    cleaned = re.sub(r">\s+<", "><", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned


def extract_full_text(html: str) -> str:
    """Vollständiger sichtbarer Text aus bereinigtem HTML."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find("body") or soup
    return main.get_text(separator="\n", strip=True)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def filter_parent_elements(elements: list[Tag]) -> list[Tag]:
    """Entfernt Eltern-Elemente, wenn ein spezifischeres Kind bereits matched."""
    kept: list[Tag] = []
    for el in elements:
        if any(other in el.find_all() and other is not el for other in elements):
            continue
        kept.append(el)
    return kept


def collect_block_elements(soup: BeautifulSoup, selectors: list[str]) -> list[Tag]:
    elements: list[Tag] = []
    seen_ids: set[int] = set()

    for selector in selectors:
        try:
            for el in soup.select(selector):
                el_id = id(el)
                if el_id in seen_ids:
                    continue
                text = el.get_text(separator=" ", strip=True)
                if len(text) >= MIN_BLOCK_TEXT_LEN:
                    elements.append(el)
                    seen_ids.add(el_id)
        except Exception:
            continue

    return filter_parent_elements(elements)


def extract_text_blocks(html: str) -> list[dict]:
    """Extrahiert deduplizierte Text-Blöcke ohne Kürzung."""
    soup = BeautifulSoup(html, "html.parser")
    elements = collect_block_elements(soup, BLOCK_SELECTORS_SPECIFIC)

    if len(elements) < 3:
        elements = collect_block_elements(soup, BLOCK_SELECTORS_SPECIFIC + BLOCK_SELECTORS_BROAD)

    blocks: list[dict] = []
    seen_text: set[str] = set()

    for el in elements:
        text = el.get_text(separator=" ", strip=True)
        key = normalize_text(text)
        if key in seen_text:
            continue
        seen_text.add(key)
        blocks.append({
            "selector": el.name + (f".{el['class'][0]}" if el.get("class") else ""),
            "text": text,
            "html": str(el),
        })

    if not blocks:
        body = soup.find("body") or soup
        text = body.get_text(separator=" ", strip=True)
        blocks.append({
            "selector": "body",
            "text": text,
            "html": str(body),
        })

    return blocks


def merge_html_pages(pages: list[dict]) -> tuple[str, str]:
    """Kombiniert HTML mehrerer Seiten."""
    raw_parts = []
    cleaned_parts = []

    for page in pages:
        marker = f"<!-- PAGE: {page['url']} -->"
        raw_parts.append(marker + page["html_raw"])
        cleaned_parts.append(marker + page["html_cleaned"])

    html_raw = "\n".join(raw_parts)[:MAX_HTML_SIZE]
    html_cleaned = "\n".join(cleaned_parts)[:MAX_HTML_SIZE]
    return html_raw, html_cleaned


# ───────────────────────────────────────────────
# ROHDATEN-SCRAPER (pro Quelle)
# ───────────────────────────────────────────────

def scrape_page(url: str, method: str = "requests") -> tuple[str, int, str, str]:
    """Scrapt eine einzelne Seite. Returns: html, status, error, method_used."""
    if method == "playwright":
        html, status, error = fetch_with_playwright(url)
        return html, status, error, "playwright"

    html, status, error = fetch(url)
    return html, status, error, "requests"


def scrape_source(name: str, url: str) -> dict:
    """Scrapt eine Quelle inkl. Pagination und JS-Fallback."""
    print(f"[FETCH] {name} — {url}")

    html, status, error, method = scrape_page(url)
    if error:
        print(f"  [ERROR] Status {status}: {error}")
        return _error_result(name, url, status, error)

    page_urls = discover_all_page_urls(url, html)
    pages_data: list[dict] = []

    for index, page_url in enumerate(page_urls):
        if index == 0:
            page_html, page_status, page_error, page_method = html, status, error, method
        else:
            print(f"  [PAGE {index + 1}/{len(page_urls)}] {page_url}")
            page_html, page_status, page_error, page_method = scrape_page(page_url)
            time.sleep(REQUEST_DELAY)
            if page_error:
                print(f"    [WARN] Seite übersprungen: {page_error}")
                continue

        cleaned = clean_html(page_html)
        full_text = extract_full_text(cleaned)
        blocks = extract_text_blocks(cleaned)

        pages_data.append({
            "url": page_url,
            "method": page_method,
            "html_raw": page_html[:MAX_HTML_SIZE],
            "html_cleaned": cleaned[:MAX_HTML_SIZE],
            "extracted_text": full_text,
            "text_blocks": blocks,
        })

    if not pages_data:
        return _error_result(name, url, status, "Keine Seiteninhalte geladen")

    combined_text = "\n\n".join(page["extracted_text"] for page in pages_data)
    combined_blocks: list[dict] = []
    seen_block_text: set[str] = set()
    for page in pages_data:
        for block in page["text_blocks"]:
            key = normalize_text(block["text"])
            if key in seen_block_text:
                continue
            seen_block_text.add(key)
            block = dict(block)
            block["page_url"] = page["url"]
            combined_blocks.append(block)

    first_html = pages_data[0]["html_raw"]
    if needs_js_fallback(first_html, combined_text):
        print("  [JS-FALLBACK] Wenig Text bei großem HTML → Playwright")
        pw_html, pw_status, pw_error, _ = scrape_page(url, method="playwright")
        if not pw_error:
            cleaned = clean_html(pw_html)
            full_text = extract_full_text(cleaned)
            blocks = extract_text_blocks(cleaned)
            if len(full_text) > len(combined_text):
                pages_data = [{
                    "url": url,
                    "method": "playwright",
                    "html_raw": pw_html[:MAX_HTML_SIZE],
                    "html_cleaned": cleaned[:MAX_HTML_SIZE],
                    "extracted_text": full_text,
                    "text_blocks": blocks,
                }]
                combined_text = full_text
                combined_blocks = [{**block, "page_url": url} for block in blocks]
                method = "playwright"
        else:
            print(f"  [WARN] Playwright-Fallback fehlgeschlagen: {pw_error}")

    html_raw, html_cleaned = merge_html_pages(pages_data)
    methods = sorted({page["method"] for page in pages_data})

    print(
        f"  [OK] {len(pages_data)} Seite(n), {len(combined_text):,} Zeichen Text, "
        f"{len(combined_blocks)} Blöcke, Methoden: {', '.join(methods)}"
    )

    soup = BeautifulSoup(pages_data[0]["html_raw"], "html.parser")
    title_tag = soup.find("title")
    meta_desc = soup.find("meta", attrs={"name": "description"})

    return {
        "source_name": name,
        "source_url": url,
        "status_code": status,
        "error": None,
        "fetch_timestamp": datetime.now().isoformat(),
        "fetch_methods": methods,
        "pages_scraped": len(pages_data),
        "page_urls": [page["url"] for page in pages_data],
        "page_title": title_tag.get_text(strip=True) if title_tag else "",
        "meta_description": meta_desc["content"] if meta_desc and meta_desc.get("content") else "",
        "html_raw": html_raw,
        "html_cleaned": html_cleaned,
        "extracted_text_full": combined_text,
        "text_blocks": combined_blocks,
        "stats": {
            "html_bytes": len(html_raw),
            "extracted_text_chars": len(combined_text),
            "block_count": len(combined_blocks),
            "pages_count": len(pages_data),
        },
    }


def _error_result(name: str, url: str, status: int, error: str) -> dict:
    return {
        "source_name": name,
        "source_url": url,
        "status_code": status,
        "error": error,
        "fetch_timestamp": datetime.now().isoformat(),
        "fetch_methods": [],
        "pages_scraped": 0,
        "page_urls": [],
        "html_raw": "",
        "html_cleaned": "",
        "extracted_text_full": "",
        "text_blocks": [],
        "page_title": "",
        "meta_description": "",
        "stats": {},
    }


# ───────────────────────────────────────────────
# QUELLEN-KONFIGURATION
# ───────────────────────────────────────────────

SOURCES = [
    ("ZDI Mainfranken", "https://www.zdi-mainfranken.de/events/"),
    ("THWS Termine", "https://www.thws.de/termine/"),
    ("THWS CAIRO News", "https://www.thws.de/forschung/institute/cairothws/news/"),
    ("THWS Studieninteressierte", "https://www.thws.de/studieninteressierte/veranstaltungen/"),
    ("MetaComp IT-Veranstaltungen", "https://www.metacomp-wuerzburg.de/newsroom/it-veranstaltungen/"),
    ("KI-Regio", "https://ki-regio.de/veranstaltungen/"),
    ("Uni Würzburg Informatik", "https://www.informatik.uni-wuerzburg.de/aktuelles/veranstaltungen-und-termine/"),
    ("Gründen@Würzburg", "https://gruenden.wuerzburg.de/"),
    ("IHK Würzburg", "https://www.wuerzburg.ihk.de/veranstaltungen/"),
    ("HWK Unterfranken", "https://www.hwk-ufr.de/artikel/aktuelle-veranstaltungen-webinare-und-workshops-78,0,6052.html"),
    ("Startbahn27", "https://startbahn27.de/en/news-events"),
    ("Uni Würzburg Allgemein", "https://www.uni-wuerzburg.de/aktuelles/veranstaltungen/"),
    ("WueWW", "https://www.wueww.de/"),
    ("VDE Bayern", "https://www.vde-bayern.de/de/veranstaltungen"),
    ("Hackation", "https://hackation.de/de/"),
]


# ───────────────────────────────────────────────
# HAUPT-FUNKTION
# ───────────────────────────────────────────────

def scrape_all_raw() -> dict:
    """Scrapt alle Quellen und gibt ein Dict mit Rohdaten zurück."""
    results = {
        "scraped_at": datetime.now().isoformat(),
        "total_sources": len(SOURCES),
        "successful": 0,
        "failed": 0,
        "sources": [],
    }

    print(f"\n{'=' * 70}")
    print("MAINFRANKEN EVENT SCRAPER — ROHDATEN-MODUS")
    print(f"{'=' * 70}\n")

    for name, url in SOURCES:
        source_data = scrape_source(name, url)
        results["sources"].append(source_data)

        if source_data["error"]:
            results["failed"] += 1
        else:
            results["successful"] += 1

        time.sleep(REQUEST_DELAY)

    print(f"\n{'=' * 70}")
    print(f"ERGEBNIS: {results['successful']}/{results['total_sources']} Quellen erfolgreich")
    print(f"{'=' * 70}\n")

    return results


def save_raw(data: dict, filename: str = "events_raw.json"):
    """Speichert Rohdaten als JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_mb = os.path.getsize(filename) / (1024 * 1024)
    print(f"✅ Rohdaten gespeichert: {filename} ({size_mb:.1f} MB)")


def print_summary(data: dict):
    """Gibt eine Zusammenfassung der Rohdaten aus."""
    print("\n📊 ZUSAMMENFASSUNG:\n")

    for src in data["sources"]:
        status = "✅" if not src["error"] else "❌"
        stats = src.get("stats", {})
        text_chars = stats.get("extracted_text_chars", len(src.get("extracted_text_full", "")))
        blocks = stats.get("block_count", len(src.get("text_blocks", [])))
        pages = stats.get("pages_count", src.get("pages_scraped", 0))

        print(f"{status} {src['source_name']}")
        print(f"   URL: {src['source_url']}")
        print(f"   Status: {src['status_code']}")
        print(f"   Seiten: {pages}, Text: {text_chars:,} Zeichen, Blöcke: {blocks}")
        print(f"   Methoden: {', '.join(src.get('fetch_methods', [])) or 'n/a'}")
        print(f"   Titel: {src.get('page_title', 'N/A')[:80]}")

        if src["error"]:
            print(f"   Fehler: {src['error']}")
        elif src.get("extracted_text_full"):
            preview = src["extracted_text_full"][:200].replace("\n", " ")
            print(f"   Preview: {preview}...")

        print()


def load_raw(filename: str = "events_raw.json") -> dict:
    """Lädt zuvor gespeicherte Rohdaten."""
    with open(filename, encoding="utf-8") as f:
        return json.load(f)


def run_pipeline(
    scrape: bool = True,
    format_with_llm: bool = True,
    import_to_db: bool = True,
    raw_file: str = "events_raw.json",
    output_file: str = "events.json",
) -> tuple[dict | None, dict | None]:
    """Vollständige Pipeline: Scrapen → LLM-Formatierung → SQLite-Import."""
    load_dotenv()

    raw_data = None
    formatted_data = None

    if scrape:
        raw_data = scrape_all_raw()
        save_raw(raw_data, raw_file)
        print_summary(raw_data)
    elif format_with_llm or import_to_db:
        if not os.path.exists(raw_file):
            raise FileNotFoundError(
                f"{raw_file} nicht gefunden. Führe zuerst den Scraper aus oder nutze --scrape."
            )
        raw_data = load_raw(raw_file)
        print(f"📂 Rohdaten geladen: {raw_file}")

    if format_with_llm:
        from app.scraping.llm_extract import format_all_with_llm, save_formatted

        formatted_data = format_all_with_llm(raw_data)
        save_formatted(formatted_data, output_file)

    if import_to_db:
        from pathlib import Path

        from app.scraping.sqlite_import import import_events, load_events_from_json

        if not os.path.exists(output_file):
            print(f"⚠️  {output_file} nicht gefunden — überspringe DB-Import.")
        else:
            events = load_events_from_json(Path(output_file))
            inserted, skipped = import_events(events)
            print(f"📦 DB-Import: {inserted} eingefügt, {skipped} übersprungen")

    return raw_data, formatted_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mainfranken Event Scraper + OpenRouter LLM + SQLite-Import"
    )
    parser.add_argument("--scrape-only", action="store_true", help="Nur scrapen, keine LLM-Formatierung / kein DB-Import")
    parser.add_argument("--llm-only", action="store_true", help="Nur LLM aus vorhandener events_raw.json (kein Scrapen)")
    parser.add_argument("--import-only", action="store_true", help="Nur DB-Import aus vorhandener events.json")
    parser.add_argument("--no-import", action="store_true", help="DB-Import überspringen")
    parser.add_argument("--raw-file", default="events_raw.json", help="Pfad zur Rohdaten-JSON")
    parser.add_argument("--output", default="events.json", help="Pfad zur formatierten Events-JSON")
    args = parser.parse_args()

    if sum([args.scrape_only, args.llm_only, args.import_only]) > 1:
        parser.error("--scrape-only, --llm-only und --import-only schließen sich gegenseitig aus.")

    if args.import_only:
        from pathlib import Path

        from app.scraping.sqlite_import import import_events, load_events_from_json

        events = load_events_from_json(Path(args.output))
        inserted, skipped = import_events(events)
        print(f"📦 DB-Import: {inserted} eingefügt, {skipped} übersprungen")
    else:
        run_pipeline(
            scrape=not args.llm_only,
            format_with_llm=not args.scrape_only,
            import_to_db=not args.no_import and not args.scrape_only,
            raw_file=args.raw_file,
            output_file=args.output,
        )
