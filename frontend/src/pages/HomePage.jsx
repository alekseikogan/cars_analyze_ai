import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getListings } from "../api";
import { formatPrice } from "../format";

export default function HomePage() {
  const [listings, setListings] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    getListings()
      .then((data) => {
        if (!cancelled) setListings(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const available = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return listings.filter((item) => {
      if (item.status !== "ready_for_sale") return false;
      if (!needle) return true;
      const haystack = `${item.brand} ${item.model} ${item.year} ${item.body_type} ${item.color || ""}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [listings, query]);

  return (
    <div className="page home">
      <section className="hero">
        <p className="eyebrow">Аукцион открыт</p>
        <h1>Автомобили, доступные к торгам</h1>
        <p className="lede">
          Цена уже посчитана. Откройте карточку лота или, если вы в штате, спросите ассистента в чате.
        </p>
        <label className="search-field">
          <span className="sr-only">Поиск по каталогу</span>
          <input
            value={query}
            placeholder="Марка, модель или кузов"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </section>

      {loading && <p className="muted">Загружаем лоты...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && (
        <p className="muted count-line">{available.length} доступно</p>
      )}

      <div className="listing-grid">
        {available.map((item) => (
          <Link key={item.id} to={`/auction/${item.id}`} className="card listing-card">
            <div className="swatch" aria-hidden="true">
              <span>{item.brand.slice(0, 1)}</span>
            </div>
            <h3>
              {item.brand} {item.model}
            </h3>
            <p className="muted">
              {item.year} · {item.body_type} · {item.mileage.toLocaleString("ru-RU")} км
            </p>
            <p className="price">{formatPrice(item.predicted_price)}</p>
            <p className="badge">Доступно</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
