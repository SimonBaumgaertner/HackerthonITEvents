const API = "http://localhost:8000";

export async function getEvents() {
  const res = await fetch(`${API}/events`);
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

