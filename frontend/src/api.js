async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
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
