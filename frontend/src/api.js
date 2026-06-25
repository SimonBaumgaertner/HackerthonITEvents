const API = "http://localhost:8000";

export async function getEvents(filters = {}) {
  const params = new URLSearchParams();
  if (filters.category) params.append("category", filters.category);
  if (filters.experience) params.append("experience", filters.experience);
  if (filters.format) params.append("format", filters.format);

  const url = `${API}/events${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load events (${res.status})`);
  return res.json();
}

export async function addEvent(payload) {
  const res = await fetch(`${API}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to add event (${res.status})`);
  return res.json();
}

export async function deleteEvent(id) {
  const res = await fetch(`${API}/events/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete event (${res.status})`);
}

export async function saveEventomatResponse(userToken, payload) {
  const res = await fetch(`${API}/eventomat/responses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_token: userToken, payload }),
  });
  if (!res.ok) throw new Error(`Failed to save response (${res.status})`);
  return res.json();
}

export async function getEvent(id) {
  const res = await fetch(`${API}/events/${id}`);
  if (!res.ok) throw new Error(`Failed to load event (${res.status})`);
  return res.json();
}

export async function getEventomatResults(userToken) {
  const res = await fetch(`${API}/eventomat/results?user_token=${encodeURIComponent(userToken)}`);
  if (!res.ok) throw new Error(`Failed to load recommendations (${res.status})`);
  return res.json();
}



