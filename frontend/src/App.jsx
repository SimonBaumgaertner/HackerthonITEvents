import { useEffect, useState, useRef } from "react";
import { getEvents, saveEventomatResponse, getEvent } from "./api";
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

function HighlightCard({ event, navigate }) {
  const start = parseDate(event?.start);
  const end = parseDate(event?.end);

  return (
    <article className="highlight-card">
      <div className="highlight-top">
        <DateBadge date={start} />
        <div className="highlight-heading">
          <span className="highlight-tag">✦ HIGHLIGHT EVENT</span>
          <h2 
            style={event ? { cursor: "pointer" } : {}} 
            onClick={() => event && navigate(`/event/${event.id}`)}
          >
            {event ? event.name : "Noch keine Events"}
          </h2>
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
        <button
          className="btn btn-primary"
          onClick={() => event && navigate(`/event/${event.id}`)}
        >
          Details anzeigen ↗
        </button>
        <button className="btn btn-ghost" onClick={() => navigate("/eventomat")}>
          Zum Eventomat
        </button>
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

function EventWidget({ event, navigate }) {
  const start = parseDate(event?.start);
  return (
    <article 
      className="event-widget" 
      style={{ cursor: "pointer" }}
      onClick={() => navigate(`/event/${event.id}`)}
    >
      <div className="event-widget-date">
        <DateBadge date={start} />
      </div>
      <div className="event-widget-content">
        <h3>{event.name}</h3>
        <p className="event-widget-location">📍 {event.location}</p>
      </div>
    </article>
  );
}

// --- Navigation & Routing Helpers ---
function getOrCreateUserToken() {
  let token = localStorage.getItem("eventomat_user_token");
  if (!token) {
    token = "user_" + Math.random().toString(36).substring(2, 11);
    localStorage.setItem("eventomat_user_token", token);
  }
  return token;
}

const TOPIC_MAPPING = {
  "Künstliche Intelligenz": ["KI", "Data Science"],
  "UI/UX Design & Frontend": ["Frontend", "React"],
  "Softwareentwicklung & DevOps": ["DevOps", "Cloud"],
  "IT-Security & Infrastruktur": ["Security"],
  "IT-Management & Networking": ["Networking", "Meetup", "Community"]
};

const FORMAT_MAPPING = {
  "Fachvorträge & Keynotes": ["Konferenz"],
  "Workshops & Hackathons": ["Workshop", "Hackathon"],
  "Networking & Meetups": ["Networking", "Meetup", "Community"],
  "Karriere & Recruiting": []
};

function calculateMatchScore(event, responses) {
  let userTags = [];
  if (responses?.themen) {
    responses.themen.forEach(t => {
      if (TOPIC_MAPPING[t]) userTags.push(...TOPIC_MAPPING[t]);
    });
  }
  if (responses?.format) {
    responses.format.forEach(f => {
      if (FORMAT_MAPPING[f]) userTags.push(...FORMAT_MAPPING[f]);
    });
  }
  const eventCategories = event.categories || [];
  const overlap = eventCategories.filter(cat => userTags.includes(cat));
  let baseScore = 60 + overlap.length * 15;
  if (baseScore > 95) baseScore = 95;
  const offset = (event.id * 3) % 5;
  let finalScore = baseScore + offset;
  if (overlap.length === 0) {
    finalScore = 60 + ((event.id * 2) % 10);
  }
  return Math.min(100, finalScore);
}

function Icon({ name, className = "" }) {
  if (name === "brain") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
        <path d="M12 6v12" />
        <path d="M8 10a2 2 0 0 1 2-2" />
        <path d="M14 8a2 2 0 0 1 2 2" />
        <path d="M6 12a3 3 0 0 1 3-3" />
        <path d="M15 9a3 3 0 0 1 3 3" />
      </svg>
    );
  }
  if (name === "palette") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12c0 2.7 1 5.2 2.8 7a.5.5 0 0 0 .3.1c.1 0 .2 0 .3-.1.2-.2.3-.5.2-.8C5 18.1 4.4 16 4.4 13.7C4.4 9 8.2 5.2 12.9 5.2c4.7 0 8.5 3.8 8.5 8.5 0 1.4-.4 2.7-1 3.9a.5.5 0 0 0 .2.7.5.5 0 0 0 .7-.2c.7-1.4 1.1-2.9 1.1-4.4C22.4 7.6 18.2 3.4 13.5 3.4c-4.7 0-8.9 4.2-8.9 9.3c0 2.2.6 4.3 1.6 6.1v.2C6.2 20.3 7 21 8 21.5V19c0-.7.6-1.3 1.3-1.3h1.4c.7 0 1.3.6 1.3 1.3v3Z" />
        <circle cx="7.5" cy="10.5" r="1.5" fill="currentColor" />
        <circle cx="11.5" cy="7.5" r="1.5" fill="currentColor" />
        <circle cx="16.5" cy="9.5" r="1.5" fill="currentColor" />
      </svg>
    );
  }
  if (name === "code") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </svg>
    );
  }
  if (name === "shield") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    );
  }
  if (name === "briefcase") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </svg>
    );
  }
  if (name === "microphone") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="22" />
      </svg>
    );
  }
  if (name === "wrench") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
      </svg>
    );
  }
  if (name === "users") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    );
  }
  if (name === "graduation") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
        <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5" />
      </svg>
    );
  }
  if (name === "calendar") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    );
  }
  if (name === "chat") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    );
  }
  if (name === "mail") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
        <polyline points="22,6 12,13 2,6" />
      </svg>
    );
  }
  if (name === "bookmark") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
      </svg>
    );
  }
  if (name === "sparkles") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      </svg>
    );
  }
  if (name === "arrow-left") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <line x1="19" y1="12" x2="5" y2="12" />
        <polyline points="12 19 5 12 12 5" />
      </svg>
    );
  }
  if (name === "arrow-right") {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <line x1="5" y1="12" x2="19" y2="12" />
        <polyline points="12 5 19 12 12 19" />
      </svg>
    );
  }
  return null;
}

// Map configuration for coordinates of local events
const EVENT_MAP_POSITIONS = {
  1: { top: "48%", left: "62%", label: "Würzburg (VCC)" },
  2: { top: "37%", left: "78%", label: "Schweinfurt (i-Campus)" },
  3: { top: "55%", left: "30%", label: "Aschaffenburg (TH)" },
  4: { top: "50%", left: "60%", label: "Würzburg (Posthalle)" },
  5: { top: "46%", left: "64%", label: "Würzburg (VCC)" },
  6: { top: "52%", left: "63%", label: "Würzburg (ZDI)" }
};

function EventomatMap({ events, selectedEventId, onSelectEvent }) {
  return (
    <div className="map-placeholder" role="img" aria-label="Karte der Region Mainfranken mit Event-Matches">
      <div className="map-zoom">
        <button type="button" aria-label="Hineinzoomen">+</button>
        <button type="button" aria-label="Herauszoomen">−</button>
      </div>

      {events.map((event) => {
        const pos = EVENT_MAP_POSITIONS[event.id] || { top: "50%", left: "50%" };
        const isSelected = selectedEventId === event.id;
        return (
          <span
            key={event.id}
            className={`map-pin ${isSelected ? "map-pin-active" : ""}`}
            style={{ top: pos.top, left: pos.left, cursor: "pointer" }}
            onClick={() => onSelectEvent(event.id)}
            title={event.name}
          >
            📍
          </span>
        );
      })}

      <div className="map-badge">
        {selectedEventId
          ? `Ziel: ${events.find((e) => e.id === selectedEventId)?.location}`
          : `◆ ${events.length} passende Events in der Nähe`}
      </div>
      <div className="map-attribution">Leaflet | © OpenStreetMap © CARTO</div>
    </div>
  );
}

function OnboardingPage({ navigate }) {
  const [step, setStep] = useState(1);
  const [responses, setResponses] = useState(() => {
    const saved = localStorage.getItem("eventomat_responses");
    return saved
      ? JSON.parse(saved)
      : { themen: [], erfahrung: "", format: [], alltag: "", freitext: "" };
  });

  useEffect(() => {
    localStorage.setItem("eventomat_responses", JSON.stringify(responses));
  }, [responses]);

  const toggleMultiSelect = (key, value) => {
    setResponses((prev) => {
      const current = prev[key] || [];
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return { ...prev, [key]: updated };
    });
  };

  const setSingleSelect = (key, value) => {
    setResponses((prev) => ({ ...prev, [key]: value }));
  };

  const handleTextChange = (e) => {
    const val = e.target.value.substring(0, 1000);
    setResponses((prev) => ({ ...prev, freitext: val }));
  };

  const handleNext = () => {
    if (step < 5) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    } else {
      navigate("/");
    }
  };

  const handleSubmit = async () => {
    const token = getOrCreateUserToken();
    try {
      await saveEventomatResponse(token, responses);
      // Clean temporary storage or keep it for results page logic
      navigate("/eventomat/results");
    } catch (e) {
      alert("Fehler beim Speichern der Antworten: " + e.message);
    }
  };

  const progressPercent = (step / 5) * 100;

  return (
    <div className="eventomat-flow-page">
      <header className="eventomat-top-header">
        <button className="eventomat-top-back-btn" onClick={() => navigate("/")}>
          <Icon name="arrow-left" className="icon-sm" />
          <span>Zurück</span>
        </button>
        <span className="eventomat-top-title">EVENTOMAT · IT-EVENTS FÜR DICH</span>
      </header>

      <div className="eventomat-content-container">
        {/* Sticky Progress Bar */}
        <div className="eventomat-progress-bar-container">
          <div className="eventomat-progress-text">
            <span className="progress-step-indicator">FRAGE {step} VON 5</span>
            <span className="progress-percentage">{Math.round(progressPercent)} %</span>
          </div>
          <div className="eventomat-progress-track">
            <div className="eventomat-progress-fill" style={{ width: `${progressPercent}%` }}></div>
          </div>
        </div>

        {/* Step Cards */}
        <div className="eventomat-card">
          {step === 1 && (
            <div className="eventomat-step-body">
              <span className="eventomat-step-eyebrow">SCHRITT 1 · THEMEN</span>
              <h2>Welche IT-Themen interessieren dich am meisten?</h2>
              <p className="eventomat-step-desc">Mehrfachauswahl möglich.</p>

              <div className="eventomat-options-grid">
                {[
                  { label: "Künstliche Intelligenz", sub: "KI / Data Science", icon: "brain" },
                  { label: "UI/UX Design & Frontend", sub: "Design, Web, Mobile", icon: "palette" },
                  { label: "Softwareentwicklung & DevOps", sub: "Code, Cloud, CI/CD", icon: "code" },
                  { label: "IT-Security & Infrastruktur", sub: "Hardware & Netzwerke", icon: "shield" },
                  { label: "IT-Management & Networking", sub: "Strategie & Unternehmen", icon: "briefcase" }
                ].map((opt) => {
                  const isSel = responses.themen.includes(opt.label);
                  return (
                    <div
                      key={opt.label}
                      className={`eventomat-option ${isSel ? "eventomat-option-selected" : ""}`}
                      onClick={() => toggleMultiSelect("themen", opt.label)}
                    >
                      <div className="eventomat-option-icon-wrapper">
                        <Icon name={opt.icon} className="icon-main" />
                      </div>
                      <div className="eventomat-option-details">
                        <span className="option-title-text">{opt.label}</span>
                        <span className="option-subtitle-text">{opt.sub}</span>
                      </div>
                      <div className="eventomat-option-control">
                        <span className={`custom-checkbox-dot ${isSel ? "active" : ""}`}></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="eventomat-step-body">
              <span className="eventomat-step-eyebrow">SCHRITT 2 · ERFAHRUNG</span>
              <h2>Wie würdest du dein Erfahrungslevel in diesen Bereichen einordnen?</h2>
              <p className="eventomat-step-desc">Wähle eine Option aus.</p>

              <div className="eventomat-options-list">
                {[
                  { label: "Anfänger / Einsteiger", sub: "Ich tauche gerade ein." },
                  { label: "Fortgeschritten", sub: "Ich kenne mich solide aus." },
                  { label: "Experte / Profi", sub: "Ich arbeite täglich damit." }
                ].map((opt) => {
                  const isSel = responses.erfahrung === opt.label;
                  return (
                    <div
                      key={opt.label}
                      className={`eventomat-option option-full-width ${isSel ? "eventomat-option-selected" : ""}`}
                      onClick={() => setSingleSelect("erfahrung", opt.label)}
                    >
                      <div className="eventomat-option-details">
                        <span className="option-title-text">{opt.label}</span>
                        <span className="option-subtitle-text">{opt.sub}</span>
                      </div>
                      <div className="eventomat-option-control">
                        <span className={`custom-radio-dot ${isSel ? "active" : ""}`}></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="eventomat-step-body">
              <span className="eventomat-step-eyebrow">SCHRITT 3 · FORMAT</span>
              <h2>Welches Format bringt dich am ehesten zu einem Event?</h2>
              <p className="eventomat-step-desc">Mehrfachauswahl möglich.</p>

              <div className="eventomat-options-grid">
                {[
                  { label: "Fachvorträge & Keynotes", icon: "microphone" },
                  { label: "Workshops & Hackathons", icon: "wrench" },
                  { label: "Networking & Meetups", icon: "users" },
                  { label: "Karriere & Recruiting", icon: "graduation" }
                ].map((opt) => {
                  const isSel = responses.format.includes(opt.label);
                  return (
                    <div
                      key={opt.label}
                      className={`eventomat-option ${isSel ? "eventomat-option-selected" : ""}`}
                      onClick={() => toggleMultiSelect("format", opt.label)}
                    >
                      <div className="eventomat-option-icon-wrapper">
                        <Icon name={opt.icon} className="icon-main" />
                      </div>
                      <div className="eventomat-option-details">
                        <span className="option-title-text">{opt.label}</span>
                      </div>
                      <div className="eventomat-option-control">
                        <span className={`custom-checkbox-dot ${isSel ? "active" : ""}`}></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="eventomat-step-body">
              <span className="eventomat-step-eyebrow">SCHRITT 4 · ALLTAG</span>
              <h2>Wie möchtest du im Alltag über Updates informiert werden?</h2>
              <p className="eventomat-step-desc">Damit Events nicht im Posteingang verloren gehen.</p>

              <div className="eventomat-options-list">
                {[
                  { label: "Kalender (.ics)", sub: "Automatische Einladung direkt im Kalender.", icon: "calendar" },
                  { label: "WhatsApp", sub: "Schnelle Kurznachricht mit den wichtigsten Updates.", icon: "chat" },
                  { label: "E-Mail", sub: "Klassisch, monatlich kompakt zusammengefasst.", icon: "mail" },
                  { label: "Browser-Lesezeichen", sub: "Schnellzugriff per Bookmark im Browser.", icon: "bookmark" }
                ].map((opt) => {
                  const isSel = responses.alltag === opt.label;
                  return (
                    <div
                      key={opt.label}
                      className={`eventomat-option option-full-width ${isSel ? "eventomat-option-selected" : ""}`}
                      onClick={() => setSingleSelect("alltag", opt.label)}
                    >
                      <div className="eventomat-option-icon-wrapper">
                        <Icon name={opt.icon} className="icon-main" />
                      </div>
                      <div className="eventomat-option-details">
                        <span className="option-title-text">{opt.label}</span>
                        <span className="option-subtitle-text">{opt.sub}</span>
                      </div>
                      <div className="eventomat-option-control">
                        <span className={`custom-radio-dot ${isSel ? "active" : ""}`}></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="eventomat-step-body">
              <span className="eventomat-step-eyebrow">SCHRITT 5 · WAS DIR NOCH WICHTIG IST</span>
              <h2>Schritt 5 - Was dir noch wichtig ist</h2>
              <p className="eventomat-step-desc">Optional. Hilft uns, dich besser einzuordnen.</p>

              <div className="textarea-wrapper">
                <textarea
                  className="eventomat-textarea"
                  value={responses.freitext}
                  onChange={handleTextChange}
                  placeholder="z.B. Hochschule/Unternehmen, Wünsche an das Catering, Barrierefreiheit..."
                  maxLength={1000}
                ></textarea>
                <div className="eventomat-char-count">{responses.freitext.length} / 1000</div>
              </div>
            </div>
          )}

          {/* Navigation controls */}
          <div className="eventomat-card-footer">
            <button className="btn btn-secondary-back" onClick={handleBack}>
              <Icon name="arrow-left" className="icon-sm" />
              <span>Zurück</span>
            </button>

            {step < 5 ? (
              <button
                className="btn btn-primary"
                onClick={handleNext}
                disabled={
                  (step === 1 && responses.themen.length === 0) ||
                  (step === 2 && !responses.erfahrung) ||
                  (step === 3 && responses.format.length === 0) ||
                  (step === 4 && !responses.alltag)
                }
              >
                <span>Weiter</span>
                <Icon name="arrow-right" className="icon-sm" />
              </button>
            ) : (
              <button className="btn btn-submit-onboarding" onClick={handleSubmit}>
                <span>Direkt zu deinen Event-Empfehlungen</span>
                <Icon name="sparkles" className="icon-sm" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultsPage({ navigate }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeChannel, setActiveChannel] = useState("");
  const [emailValue, setEmailValue] = useState("");
  const [emailSaved, setEmailSaved] = useState(false);
  const [showBookmarkTooltip, setShowBookmarkTooltip] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [directionsText, setDirectionsText] = useState("");
  const [showPast, setShowPast] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const responses = JSON.parse(localStorage.getItem("eventomat_responses") || "{}");
    getEvents()
      .then((data) => {
        // Calculate match scores and store
        const scoredEvents = data.map((e) => ({
          ...e,
          matchScore: calculateMatchScore(e, responses),
        }));
        // Sort descending by score
        scoredEvents.sort((a, b) => b.matchScore - a.matchScore);
        setEvents(scoredEvents);
        if (scoredEvents.length > 0) {
          // Select top event by default
          setSelectedEventId(scoredEvents[0].id);
          updateDirections(scoredEvents[0]);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });

    // Set initial active channel from Step 4
    if (responses.alltag) {
      if (responses.alltag.includes("Kalender")) {
        setActiveChannel("Kalender");
      } else if (responses.alltag.includes("WhatsApp")) {
        setActiveChannel("WhatsApp");
      } else if (responses.alltag.includes("E-Mail")) {
        setActiveChannel("E-Mail");
      } else if (responses.alltag.includes("Lesezeichen")) {
        setActiveChannel("Bookmark");
      }
    } else {
      setActiveChannel("WhatsApp");
    }
  }, []);

  const updateDirections = (event) => {
    if (!event) return;
    if (event.location.includes("Würzburg")) {
      setDirectionsText(`Route zum ${event.location}: Nimm die Straßenbahn 5 vom Hauptbahnhof Würzburg Richtung Sanderau/Rottenbauer und steige an der passenden Haltestelle aus.`);
    } else if (event.location.includes("Schweinfurt")) {
      setDirectionsText(`Route zum ${event.location}: Vom Hauptbahnhof Schweinfurt mit dem Bus Linie 12 direkt zum i-Campus.`);
    } else if (event.location.includes("Aschaffenburg")) {
      setDirectionsText(`Route zum ${event.location}: Fußweg ca. 15 Minuten vom Bahnhof Aschaffenburg Richtung TH-Campus.`);
    } else {
      setDirectionsText(`Wegbeschreibung zum Event: ${event.location}`);
    }
  };

  const handleCardClick = (event) => {
    setSelectedEventId(event.id);
    updateDirections(event);
  };

  const handleEmailSubmit = (e) => {
    e.preventDefault();
    if (emailValue.trim()) {
      setEmailSaved(true);
      setTimeout(() => setEmailSaved(false), 4000);
    }
  };

  const triggerBookmarkTooltip = () => {
    setShowBookmarkTooltip(true);
    setTimeout(() => setShowBookmarkTooltip(false), 5000);
  };

  const allChannels = [
    { key: "WhatsApp", label: "WhatsApp", icon: "chat" },
    { key: "Kalender", label: "Kalender (.ics)", icon: "calendar" },
    { key: "E-Mail", label: "E-Mail", icon: "mail" },
    { key: "Bookmark", label: "Lesezeichen", icon: "bookmark" }
  ];

  const secondaryChannels = allChannels.filter((c) => c.key !== activeChannel);

  return (
    <div className="eventomat-results-page">
      <header className="eventomat-top-header">
        <button className="eventomat-top-back-btn" onClick={() => navigate("/eventomat")}>
          <Icon name="arrow-left" className="icon-sm" />
          <span>Zurück zum Eventomat</span>
        </button>
        <span className="eventomat-top-title">DEINE EMPFEHLUNGEN</span>
      </header>

      <main className="results-container">
        {loading && <p className="loading-text">Deine Empfehlungen werden geladen...</p>}
        {error && <p className="error">{error}</p>}

        {!loading && !error && (
          <div className="results-layout">
            <div className="results-main-col">
              {/* Premium Primary Action Card */}
              <section className="primary-focus-section">
                <div className="primary-focus-card">
                  {activeChannel === "WhatsApp" && (
                    <div className="focus-channel-content">
                      <div className="focus-header">
                        <Icon name="chat" className="icon-lg green-accent" />
                        <div>
                          <h3>Dein primärer Infokanal: WhatsApp</h3>
                          <p>Erhalte kurze Updates zu passenden IT-Events direkt auf dein Smartphone.</p>
                        </div>
                      </div>
                      <a href="https://wa.me/mock" target="_blank" rel="noreferrer" className="btn btn-whatsapp-join">
                        <Icon name="chat" className="icon-sm" />
                        <span>Jetzt offiziellem WhatsApp-Infokanal beitreten</span>
                      </a>
                    </div>
                  )}

                  {activeChannel === "Kalender" && (
                    <div className="focus-channel-content">
                      <div className="focus-header">
                        <Icon name="calendar" className="icon-lg green-accent" />
                        <div>
                          <h3>Dein primärer Infokanal: Kalender-Feed</h3>
                          <p>Verpasse kein Event mehr mit deinem persönlichen .ics Kalenderabo.</p>
                        </div>
                      </div>
                      <button className="btn btn-calendar-sub" onClick={() => alert("Kalender abonniert!")}>
                        <Icon name="calendar" className="icon-sm" />
                        <span>Meinen persönlichen Kalender-Feed abonnieren</span>
                      </button>
                    </div>
                  )}

                  {activeChannel === "E-Mail" && (
                    <div className="focus-channel-content">
                      <div className="focus-header">
                        <Icon name="mail" className="icon-lg green-accent" />
                        <div>
                          <h3>Dein primärer Infokanal: E-Mail-Newsletter</h3>
                          <p>Monatlich kompakte Updates und Highlights direkt in dein Postfach.</p>
                        </div>
                      </div>
                      <form onSubmit={handleEmailSubmit} className="results-email-form">
                        <input
                          type="email"
                          required
                          placeholder="Deine E-Mail-Adresse"
                          value={emailValue}
                          onChange={(e) => setEmailValue(e.target.value)}
                          className="results-email-input"
                        />
                        <button type="submit" className="btn btn-primary btn-save-email">
                          <span>Speichern</span>
                        </button>
                      </form>
                      {emailSaved && (
                        <div className="email-toast-success">
                          ✓ E-Mail-Adresse erfolgreich gespeichert!
                        </div>
                      )}
                    </div>
                  )}

                  {activeChannel === "Bookmark" && (
                    <div className="focus-channel-content">
                      <div className="focus-header">
                        <Icon name="bookmark" className="icon-lg green-accent" />
                        <div>
                          <h3>Dein primärer Infokanal: Lesezeichen</h3>
                          <p>Speichere diese Ergebnisseite als Bookmark für den schnellen Zugriff.</p>
                        </div>
                      </div>
                      <div className="bookmark-action-wrapper">
                        <button className="btn btn-bookmark-add" onClick={triggerBookmarkTooltip}>
                          <Icon name="bookmark" className="icon-sm" />
                          <span>Lesezeichen setzen</span>
                        </button>
                        {showBookmarkTooltip && (
                          <div className="bookmark-tooltip">
                            Tipp: Drücke <strong>Strg + D</strong> (Windows) oder <strong>Cmd + D</strong> (Mac)
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Alternative secondary channels row */}
                <div className="alternative-channels-row">
                  <span className="alternative-label">Alternative Kanäle:</span>
                  <div className="alternative-buttons">
                    {secondaryChannels.map((c) => (
                      <button
                        key={c.key}
                        className="btn-alternative-opt"
                        onClick={() => setActiveChannel(c.key)}
                        title={`Zu ${c.label} wechseln`}
                      >
                        <Icon name={c.icon} className="icon-xs" />
                        <span>{c.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </section>

              {/* Event Matches Grid */}
              <section className="matches-section">
                <div className="matches-header">
                  <h2>Deine Top-Matches</h2>
                  <span className="matches-count-badge">{events.length} passende Events</span>
                </div>

                <div className="matches-grid">
                  {events.map((event) => {
                    const isSelected = selectedEventId === event.id;
                    const start = parseDate(event?.start);
                    return (
                      <article
                        key={event.id}
                        className={`match-card ${isSelected ? "match-card-active" : ""}`}
                        onClick={() => handleCardClick(event)}
                      >
                        <div className="match-card-top">
                          <span className="match-percentage-pill">
                            {event.matchScore}% Match
                          </span>
                          <h3>{event.name}</h3>
                          <p className="match-card-location">{event.location}</p>
                        </div>

                        <p className="match-card-desc">{event.description}</p>

                        <div className="match-card-meta">
                          <span className="meta-item">
                            📅 {start ? start.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }) : "TBA"}
                          </span>
                          <span className="meta-item">
                            📍 {event.location.split(",")[1] || event.location}
                          </span>
                        </div>

                        {event.categories?.length > 0 && (
                          <div className="match-card-chips">
                            {event.categories.map((cat) => (
                              <span key={cat} className="match-chip">{cat}</span>
                            ))}
                          </div>
                        )}

                        <div className="match-card-action" style={{ display: "flex", gap: "0.5rem" }}>
                          <button
                            className="btn btn-ghost"
                            style={{ color: "var(--brand-dark)", borderColor: "var(--brand-dark)", padding: "0.5rem 1rem", fontSize: "0.85rem" }}
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/event/${event.id}`);
                            }}
                          >
                            <span>Details</span>
                          </button>
                          <a
                            href={event.url || "#"}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-ticket-sichern"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span>Ticket sichern</span>
                            <Icon name="arrow-right" className="icon-xs" />
                          </a>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            </div>

            {/* Sticky Sidebar Map */}
            <div className="results-sidebar-col">
              <div className="sticky-sidebar-wrapper">
                <h3>Interaktive Karte</h3>
                <EventomatMap
                  events={events}
                  selectedEventId={selectedEventId}
                  onSelectEvent={(id) => {
                    setSelectedEventId(id);
                    const ev = events.find((e) => e.id === id);
                    if (ev) updateDirections(ev);
                  }}
                />
                {selectedEventId && (
                  <div className="directions-box">
                    <h4>Anfahrtsbeschreibung</h4>
                    <p>{directionsText}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="results-footer">
          <button className="btn-tertiary-link" onClick={() => navigate("/")}>
            Alle Events der Region anzeigen
          </button>
        </div>
      </main>
    </div>
  );
}

const EVENT_COORDINATES = {
  1: { lat: 49.7997, lng: 9.8978, venue: "Vogel Convention Center", city: "Würzburg, Mainfranken" },
  2: { lat: 50.0463, lng: 10.2185, venue: "i-Campus", city: "Schweinfurt, Mainfranken" },
  3: { lat: 49.9702, lng: 9.1558, venue: "TH Aschaffenburg", city: "Aschaffenburg, Mainfranken" },
  4: { lat: 49.8016, lng: 9.9328, venue: "Posthalle Würzburg", city: "Würzburg, Mainfranken" },
  5: { lat: 49.7997, lng: 9.8978, venue: "Vogel Convention Center", city: "Würzburg, Mainfranken" },
  6: { lat: 49.7946, lng: 9.9602, venue: "ZDI Mainfranken", city: "Würzburg, Mainfranken" }
};

function LeafletMap({ lat, lng, popupText }) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (typeof window.L === "undefined") {
      console.warn("Leaflet is not loaded on window");
      return;
    }

    const L = window.L;

    mapRef.current = L.map(mapContainerRef.current, {
      center: [lat, lng],
      zoom: 15,
      zoomControl: true,
      scrollWheelZoom: false
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20
    }).addTo(mapRef.current);

    const pinSvg = `
      <svg width="32" height="42" viewBox="0 0 32 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 0C7.16 0 0 7.16 0 16C0 28 16 42 16 42C16 42 32 28 32 16C32 7.16 24.84 0 16 0ZM16 22C12.68 22 10 19.32 10 16C10 12.68 12.68 10 16 10C19.32 10 22 12.68 22 16C22 19.32 19.32 22 16 22Z" fill="#84cc16" stroke="white" stroke-width="2"/>
        <circle cx="16" cy="16" r="4" fill="white"/>
      </svg>
    `;

    const customIcon = L.divIcon({
      className: "custom-map-marker",
      html: `<div style="width: 32px; height: 42px; margin-top: -42px; margin-left: -16px;">${pinSvg}</div>`,
      iconSize: [32, 42],
      iconAnchor: [16, 42]
    });

    L.marker([lat, lng], { icon: customIcon }).addTo(mapRef.current)
      .bindPopup(popupText)
      .openPopup();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [lat, lng, popupText]);

  return <div ref={mapContainerRef} className="leaflet-map-container" style={{ width: "100%", height: "100%" }} />;
}

function EventDetailPage({ navigate, eventId }) {
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    getEvent(eventId)
      .then((data) => {
        setEvent(data);
        setError("");
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [eventId]);

  const handleDownloadIcs = () => {
    if (!event) return;
    const startStr = new Date(event.start).toISOString().replace(/-|:|\.\d+/g, "");
    const endStr = new Date(event.end).toISOString().replace(/-|:|\.\d+/g, "");
    const icsContent = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//HackerthonITEvents//Event Calendar//DE",
      "BEGIN:VEVENT",
      `UID:event-${event.id}@it-mainfranken.de`,
      `DTSTAMP:${new Date().toISOString().replace(/-|:|\.\d+/g, "")}`,
      `DTSTART:${startStr}`,
      `DTEND:${endStr}`,
      `SUMMARY:${event.name}`,
      `DESCRIPTION:${event.description.replace(/\n/g, "\\n")}`,
      `LOCATION:${event.location}`,
      `URL:${event.url}`,
      "END:VEVENT",
      "END:VCALENDAR"
    ].join("\r\n");

    const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${event.name.replace(/\s+/g, "_")}.ics`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="event-detail-loading">
        <header className="navbar">
          <a className="brand" href="#" onClick={(e) => { e.preventDefault(); navigate("/"); }}>
            <span className="brand-logo">IT</span>
            <span className="brand-text">
              <strong>IT · MAINFRANKEN</strong>
              <small>VERBAND E.V.</small>
            </span>
          </a>
        </header>
        <div className="event-detail-loading-inner">
          <p>Event-Details werden geladen...</p>
        </div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="event-detail-error-page">
        <header className="navbar">
          <a className="brand" href="#" onClick={(e) => { e.preventDefault(); navigate("/"); }}>
            <span className="brand-logo">IT</span>
            <span className="brand-text">
              <strong>IT · MAINFRANKEN</strong>
              <small>VERBAND E.V.</small>
            </span>
          </a>
        </header>
        <div className="event-detail-error-inner">
          <p className="error">{error || "Event nicht gefunden"}</p>
          <button className="btn btn-primary" onClick={() => navigate("/")}>
            Zurück zur Startseite
          </button>
        </div>
      </div>
    );
  }

  const locationParts = event.location.split(",");
  const venueName = locationParts[0]?.trim() || event.location;
  const venueCity = locationParts[1]?.trim() || "Mainfranken";

  const coords = EVENT_COORDINATES[event.id] || {
    lat: 49.7997,
    lng: 9.8978,
    venue: venueName,
    city: venueCity
  };

  const start = parseDate(event.start);
  const end = parseDate(event.end);

  const sentences = event.description.split(/(?<=\.)\s+/);
  const leadParagraph = sentences[0] || "";
  const bodyParagraphs = sentences.slice(1);

  return (
    <div className="event-detail-page">
      <header className="navbar">
        <a className="brand" href="#" onClick={(e) => { e.preventDefault(); navigate("/"); }}>
          <span className="brand-logo">IT</span>
          <span className="brand-text">
            <strong>IT · MAINFRANKEN</strong>
            <small>VERBAND E.V.</small>
          </span>
        </a>

        <nav className="nav-links">
          {NAV_LINKS.map((link) => (
            <a
              key={link}
              href="#"
              onClick={(e) => {
                e.preventDefault();
                if (link === "Eventomat") {
                  navigate("/eventomat");
                } else if (link === "IT-Events") {
                  navigate("/");
                } else if (link === "Beispiel-Event") {
                  navigate("/event/1");
                }
              }}
            >
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

      <main className="event-detail-container">
        {event.categories && event.categories.length > 0 && (
          <div className="event-detail-tags">
            {event.categories.map((cat) => (
              <span key={cat} className="event-detail-tag-badge">
                {cat}
              </span>
            ))}
          </div>
        )}

        <h1 className="event-detail-heading">{event.name}</h1>

        <div className="event-detail-metabar">
          <div className="metabar-item">
            <span className="metabar-icon">📅</span>
            <span>{formatDateRange(start)}</span>
          </div>
          <div className="metabar-item">
            <span className="metabar-icon">🕘</span>
            <span>{formatTimeRange(start, end)}</span>
          </div>
          <div className="metabar-item">
            <span className="metabar-icon">📍</span>
            <span>{event.location}</span>
          </div>
        </div>

        <div className="event-detail-grid">
          <div className="event-detail-left-col">
            <section className="detail-card about-card">
              <h2 className="detail-card-eyebrow">Über das Event</h2>
              <div className="about-card-content">
                {leadParagraph && (
                  <p className="about-lead">
                    {leadParagraph}
                  </p>
                )}
                {bodyParagraphs.map((para, i) => (
                  <p key={i} className="about-paragraph">
                    {para}
                  </p>
                ))}
              </div>
            </section>

            <section className="detail-card action-hub-card">
              <h2 className="detail-card-eyebrow">Action Hub</h2>
              <p className="action-hub-text">
                Sichere dir deinen Platz oder packe das Event direkt in deinen Kalender.
              </p>
              <div className="action-hub-buttons">
                <button className="btn btn-calendar-ics" onClick={handleDownloadIcs}>
                  <span className="btn-icon">📅</span>
                  <span>In den Kalender hinzufügen (.ics)</span>
                </button>
                <a
                  className="btn btn-primary btn-ticket-sichern-large"
                  href={event.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span>Jetzt registrieren / Ticket sichern ↗</span>
                </a>
              </div>
            </section>
          </div>

          <div className="event-detail-right-col">
            <section className="detail-card location-card">
              <div className="location-card-map-wrapper">
                <LeafletMap
                  lat={coords.lat}
                  lng={coords.lng}
                  popupText={`${event.name} @ ${venueName}`}
                />
              </div>
              <div className="location-card-details">
                <h2 className="detail-card-eyebrow">Location</h2>
                <h3 className="location-venue-name">{venueName}</h3>
                <p className="location-venue-city">{venueCity}, Mainfranken</p>
                <a
                  className="btn btn-route-planen"
                  href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(event.location)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span className="btn-icon">✈</span>
                  <span>Route planen</span>
                </a>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function LandingPage({ navigate, events, error }) {
  const now = new Date();
  const [showPast, setShowPast] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const searchLower = searchTerm.toLowerCase();

  const baseUpcoming = events
    .filter((e) => {
      const d = parseDate(e.start);
      return d && d >= now;
    })
    .sort((a, b) => parseDate(a.start) - parseDate(b.start));

  const basePast = events
    .filter((e) => {
      const d = parseDate(e.start);
      return d && d < now;
    })
    .sort((a, b) => parseDate(b.start) - parseDate(a.start));

  const baseEvents = showPast ? basePast : baseUpcoming;
  const highlight = baseEvents[0];

  const gridEvents = searchLower
    ? baseEvents.filter(e => e.name.toLowerCase().includes(searchLower))
    : baseEvents.slice(1);

  return (
    <div className="landing">
      <div className="announce">
        <span>
          ✦ Du suchst Events für dich? Nutze den <strong>Eventomat!</strong>
        </span>
        <button className="announce-link-btn" onClick={() => navigate("/eventomat")}>ÖFFNEN ↗</button>
      </div>

      <header className="navbar">
        <a className="brand" href="#" onClick={(e) => { e.preventDefault(); navigate("/"); }}>
          <span className="brand-logo">IT</span>
          <span className="brand-text">
            <strong>IT · MAINFRANKEN</strong>
            <small>VERBAND E.V.</small>
          </span>
        </a>

        <nav className="nav-links">
          {NAV_LINKS.map((link) => (
            <a
              key={link}
              href="#"
              onClick={(e) => {
                if (link === "Eventomat") {
                  e.preventDefault();
                  navigate("/eventomat");
                } else if (link === "IT-Events") {
                  e.preventDefault();
                  navigate("/");
                }
              }}
            >
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
          <h1>MAINFRANKEN IT-EVENTS PORTAL</h1>
          <button className="btn btn-primary btn-lg" onClick={() => navigate("/eventomat")}>
            Zum Eventomat (Anmeldung) ↗
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        <section className="hero-grid">
          <HighlightCard event={highlight} navigate={navigate} />
          <MapPlaceholder count={searchLower ? gridEvents.length : baseEvents.length} />
        </section>

        <div className="events-controls">
          <div className="search-filters">
            <div className="search-bar">
              <input 
                type="text" 
                placeholder="Events durchsuchen..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="pill-filters">
              <select className="pill-select" defaultValue="">
                <option value="" disabled>Kategorie</option>
                <option value="Künstliche Intelligenz">Künstliche Intelligenz</option>
                <option value="UI/UX Design und Frontend">UI/UX Design und Frontend</option>
                <option value="Software Development">Software Development</option>
                <option value="IT und Security">IT und Security</option>
              </select>
              <select className="pill-select" defaultValue="">
                <option value="" disabled>Empfohlen für</option>
                <option value="Anfänger / Einsteiger">Anfänger / Einsteiger</option>
                <option value="Fortgeschritten">Fortgeschritten</option>
                <option value="Experte / Profi">Experte / Profi</option>
              </select>
              <select className="pill-select" defaultValue="">
                <option value="" disabled>Format</option>
                <option value="Fachvorträge & Keynotes">Fachvorträge & Keynotes</option>
                <option value="Workshops & Hackathons">Workshops & Hackathons</option>
                <option value="Networking & Meetups">Networking & Meetups</option>
                <option value="Karriere & Recruiting">Karriere & Recruiting</option>
              </select>
            </div>
          </div>
          <div className="filter-toggle">
            <button 
              className={`btn ${!showPast ? 'btn-primary' : 'btn-ghost-dark'}`} 
              onClick={() => setShowPast(false)}
            >
              Aktuell
            </button>
            <button 
              className={`btn ${showPast ? 'btn-primary' : 'btn-ghost-dark'}`} 
              onClick={() => setShowPast(true)}
            >
              Rückblick
            </button>
          </div>
        </div>

        {gridEvents.length > 0 && (
          <section className="events-grid">
            {gridEvents.map((event) => (
              <EventWidget key={event.id || event.name} event={event} navigate={navigate} />
            ))}
          </section>
        )}
      </main>
    </div>
  );
}

function App() {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [currentPath, setCurrentPath] = useState(window.location.pathname);

  useEffect(() => {
    getEvents()
      .then((data) => {
        setEvents(data);
        setError("");
      })
      .catch((err) => setError(err.message));

    const handleLocationChange = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener("popstate", handleLocationChange);
    return () => window.removeEventListener("popstate", handleLocationChange);
  }, []);

  const navigate = (path) => {
    window.history.pushState({}, "", path);
    setCurrentPath(path);
    window.scrollTo(0, 0);
  };

  if (currentPath === "/eventomat") {
    return <OnboardingPage navigate={navigate} />;
  }

  if (currentPath === "/eventomat/results") {
    return <ResultsPage navigate={navigate} />;
  }

  const eventMatch = currentPath.match(/^\/event\/(\d+)/);
  if (eventMatch) {
    const eventId = parseInt(eventMatch[1], 10);
    return <EventDetailPage navigate={navigate} eventId={eventId} />;
  }

  return <LandingPage navigate={navigate} events={events} error={error} />;
}

export default App;

