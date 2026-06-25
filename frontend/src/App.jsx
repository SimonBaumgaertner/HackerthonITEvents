import { useEffect, useState } from "react";
import { addEvent, deleteEvent, getEvents } from "./api";
import "./App.css";

const EMPTY_FORM = {
  name: "",
  location: "",
  url: "",
  description: "",
  categories: "",
};

function App() {
  const [events, setEvents] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      setEvents(await getEvents());
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function update(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const payload = {
      name: form.name,
      location: form.location,
      url: form.url,
      description: form.description,
      categories: form.categories
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean),
    };
    try {
      await addEvent(payload);
      setForm(EMPTY_FORM);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteEvent(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <h1>IT Events</h1>

      {error && <p className="error">{error}</p>}

      <form className="event-form" onSubmit={handleSubmit}>
        <h2>Add an event</h2>
        <input
          placeholder="Name"
          value={form.name}
          onChange={update("name")}
          required
        />
        <input
          placeholder="Location"
          value={form.location}
          onChange={update("location")}
          required
        />
        <input
          placeholder="URL"
          type="url"
          value={form.url}
          onChange={update("url")}
          required
        />
        <textarea
          placeholder="Description"
          value={form.description}
          onChange={update("description")}
          required
        />
        <input
          placeholder="Categories (comma separated)"
          value={form.categories}
          onChange={update("categories")}
        />
        <button type="submit">Add event</button>
      </form>

      <ul className="event-list">
        {events.map((ev) => (
          <li key={ev.id} className="event-card">
            <div className="event-head">
              <h3>{ev.name}</h3>
              <button
                className="delete"
                onClick={() => handleDelete(ev.id)}
                aria-label="Delete event"
              >
                ×
              </button>
            </div>
            <p className="location">{ev.location}</p>
            <p className="description">{ev.description}</p>
            <a href={ev.url} target="_blank" rel="noreferrer">
              {ev.url}
            </a>
            <div className="chips">
              {ev.categories.map((c, i) => (
                <span key={i} className="chip">
                  {c}
                </span>
              ))}
            </div>
          </li>
        ))}
        {events.length === 0 && <p>No events yet. Add the first one!</p>}
      </ul>
    </div>
  );
}

export default App;
