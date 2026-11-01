function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && data.detail
        ? data.detail
        : `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}

export function createVehicle(payload) {
  return request("/api/vehicles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVehicle(id) {
  return request(`/api/vehicles/${id}`);
}

export function getListings() {
  return request("/auction-api/listings");
}

export function getListing(id) {
  return request(`/auction-api/listings/${id}`);
}

export function getListingByVehicle(vehicleId) {
  return request(`/auction-api/listings/by-vehicle/${vehicleId}`);
}

export function reserveListing(id) {
  return request(`/auction-api/listings/${id}/reserve`, {
    method: "POST",
  });
}

export function registerAccount(payload) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginAccount(payload) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function me() {
  return request("/api/auth/me");
}

export function listChatSessions(q = "") {
  const query = q.trim() ? `?q=${encodeURIComponent(q.trim())}` : "";
  return request(`/api/chat/sessions${query}`);
}

export function createChatSession() {
  return request("/api/chat/sessions", { method: "POST" });
}

export function getChatSession(id) {
  return request(`/api/chat/sessions/${id}`);
}

export function deleteChatSession(id) {
  return request(`/api/chat/sessions/${id}`, { method: "DELETE" });
}

export function sendChatMessage(id, content) {
  return request(`/api/chat/sessions/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}
