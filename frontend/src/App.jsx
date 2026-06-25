import { useEffect, useState } from "react";
import { getEvents } from "./api";
import "./App.css";

const NAV_LINKS = [
  "IT-Verband",
  "IT-Events",
  "Eventomat",
  "Beispiel-Event",
  "Kontakt",
];

const LONG_DATE = new Intl.DateTimeFormat("de-DE", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

const TIME = new Intl.DateTimeFormat("de-DE", {
  hour: "2-digit",
  minute: "2-digit",
});

function parseDate(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatDateRange(start) {
  return start ? LONG_DATE.format(start) : "Datum folgt";
}

function formatTimeRange(start, end) {
  if (!start || !end) return "Uhrzeit folgt";
  return `${TIME.format(start)} – ${TIME.format(end)} Uhr`;
}

function DateBadge({ date }) {
  if (!date) {
    return (
      <div className="date-badge">
        <span className="date-badge-month">TBA</span>
      </div>
    );
  }
  const month = date
    .toLocaleString("de-DE", { month: "short" })
    .replace(".", "")
    .toUpperCase();
  return (
    <div className="date-badge">
      <span className="date-badge-month">{month}</span>
      <span className="date-badge-day">{date.getDate()}</span>
      <span className="date-badge-year">{date.getFullYear()}</span>
    </div>
  );
}

function HighlightCard({ event }) {
  const start = parseDate(event?.start);
  const end = parseDate(event?.end);

  return (
    <article className="highlight-card">
      <div className="highlight-top">
        <DateBadge date={start} />
        <div className="highlight-heading">
          <span className="highlight-tag">✦ HIGHLIGHT EVENT</span>
          <h2>{event ? event.name : "Noch keine Events"}</h2>
          <p className="highlight-location-eyebrow">
            {event ? event.location : "—"}
          </p>
        </div>
      </div>

      <p className="highlight-description">
        {event
          ? event.description
          : "Sobald Events verfügbar sind, erscheint hier das Highlight."}
      </p>

      <ul className="highlight-meta">
        <li>
          <span className="meta-icon" aria-hidden="true">
            📅
          </span>
          {formatDateRange(start)}
        </li>
        <li>
          <span className="meta-icon" aria-hidden="true">
            🕘
          </span>
          {formatTimeRange(start, end)}
        </li>
        <li>
          <span className="meta-icon" aria-hidden="true">
            📍
          </span>
          {event ? event.location : "—"}
        </li>
      </ul>

      {event?.categories?.length > 0 && (
        <div className="chips">
          {event.categories.map((c) => (
            <span key={c} className="chip">
              {c}
            </span>
          ))}
        </div>
      )}

      <div className="highlight-actions">
        <a
          className="btn btn-primary"
          href={event?.url || "#"}
          target="_blank"
          rel="noreferrer"
        >
          Im Eventomat anmelden ↗
        </a>
        <a className="btn btn-ghost" href="#events">
          Alle Events
        </a>
      </div>
    </article>
  );
}

function MapPlaceholder({ count }) {
  return (
    <div className="map-placeholder" role="img" aria-label="Karte der Region Mainfranken">
      <div className="map-zoom">
        <button type="button" aria-label="Hineinzoomen">
          +
        </button>
        <button type="button" aria-label="Herauszoomen">
          −
        </button>
      </div>

      <span className="map-pin" style={{ top: "48%", left: "62%" }}>
        📍
      </span>
      <span className="map-pin" style={{ top: "62%", left: "58%" }}>
        📍
      </span>
      <span className="map-pin" style={{ top: "37%", left: "78%" }}>
        📍
      </span>
      <span className="map-pin" style={{ top: "55%", left: "30%" }}>
        📍
      </span>

      <div className="map-badge">◆ {count} aktive Events</div>
      <div className="map-attribution">Leaflet | © OpenStreetMap © CARTO</div>
    </div>
  );
}

function App() {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getEvents()
      .then((data) => {
        setEvents(data);
        setError("");
      })
      .catch((err) => setError(err.message));
  }, []);

  const highlight = events[0];

  return (
    <div className="landing">
      <div className="announce">
        <span>
          ✦ Du suchst Events für dich? Nutze den <strong>Eventomat!</strong>
        </span>
        <a href="#eventomat">ÖFFNEN ↗</a>
      </div>

      <header className="navbar">
        <a className="brand" href="#top">
          <span className="brand-logo">IT</span>
          <span className="brand-text">
            <strong>IT · MAINFRANKEN</strong>
            <small>VERBAND E.V.</small>
          </span>
        </a>

        <nav className="nav-links">
          {NAV_LINKS.map((link) => (
            <a key={link} href="#">
              {link}
            </a>
          ))}
        </nav>

        <div className="nav-actions">
          <a className="btn btn-primary" href="#join">
            Mitglied werden
          </a>
          <a className="nav-linkedin" href="#linkedin" aria-label="LinkedIn">
            in
          </a>
        </div>
      </header>

      <main className="hero">
        <div className="hero-head">
          <div>
            <p className="hero-eyebrow">IT-EVENTS PORTAL</p>
            <h1>MAINFRANKEN IT-EVENTS PORTAL</h1>
            <p className="hero-subtitle">Deine Community, deine Zukunft.</p>
            <a className="btn btn-primary btn-lg" href="#eventomat">
              Zum Eventomat (Anmeldung) ↗
            </a>
          </div>
          <p className="hero-regions">
            Würzburg · Schweinfurt · Aschaffenburg
          </p>
        </div>

        {error && <p className="error">{error}</p>}

        <section className="hero-grid">
          <HighlightCard event={highlight} />
          <MapPlaceholder count={events.length} />
        </section>
      </main>
    </div>
  );
}

export default App;
