import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getListings } from "../api";

function formatPrice(value) {
  if (value == null) return "цена уточняется";
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function AuctionListPage() {
  const [listings, setListings] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const highlightVehicle = searchParams.get("vehicle");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getListings();
        if (!cancelled) setListings(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <h1>Аукцион</h1>
      <p className="muted">Машины, готовые к продаже / бронированию.</p>

      {loading && <p>Загрузка...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && listings.length === 0 && (
        <p className="muted">Пока нет лотов. Сначала отправьте авто на оценку.</p>
      )}

      <div className="listing-grid">
        {listings.map((item) => {
          const highlight =
            highlightVehicle && String(item.vehicle_id) === String(highlightVehicle);
          return (
            <Link
              key={item.id}
              to={`/auction/${item.id}`}
              className={`card listing-card ${highlight ? "highlight" : ""}`}
            >
              <h3>
                {item.brand} {item.model}
              </h3>
              <p>
                {item.year} · {item.body_type} · {item.mileage.toLocaleString("ru-RU")} км
              </p>
              <p className="price">{formatPrice(item.predicted_price)}</p>
              <p className="muted small">
                {item.status === "listed" ? "Забронировано" : "Доступно"}
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
