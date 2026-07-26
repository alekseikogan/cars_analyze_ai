import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getListing, reserveListing } from "../api";

function formatPrice(value) {
  if (value == null) return "цена уточняется";
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function AuctionDetailPage() {
  const { id } = useParams();
  const [listing, setListing] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reserving, setReserving] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalText, setModalText] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getListing(id);
        if (!cancelled) setListing(data);
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
  }, [id]);

  async function onReserve() {
    setReserving(true);
    setError("");
    try {
      const result = await reserveListing(id);
      setListing(result.listing);
      setModalText(result.message || "Вы успешно забронировали авто");
      setModalOpen(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setReserving(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p>Загрузка карточки...</p>
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="page">
        <p className="error">{error || "Лот не найден"}</p>
        <Link to="/auction">Назад к списку</Link>
      </div>
    );
  }

  const canReserve = listing.status === "ready_for_sale";

  return (
    <div className="page">
      <p>
        <Link to="/auction">← К списку</Link>
      </p>

      <div className="card detail">
        <h1>
          {listing.brand} {listing.model}
        </h1>
        <dl className="details">
          <div>
            <dt>Год</dt>
            <dd>{listing.year}</dd>
          </div>
          <div>
            <dt>Кузов</dt>
            <dd>{listing.body_type}</dd>
          </div>
          <div>
            <dt>Пробег</dt>
            <dd>{listing.mileage.toLocaleString("ru-RU")} км</dd>
          </div>
          <div>
            <dt>Цвет</dt>
            <dd>{listing.color || "—"}</dd>
          </div>
          <div>
            <dt>Оценка цены</dt>
            <dd className="price">{formatPrice(listing.predicted_price)}</dd>
          </div>
          <div>
            <dt>Уверенность ML</dt>
            <dd>
              {listing.confidence != null
                ? `${Math.round(listing.confidence * 100)}%`
                : "—"}
            </dd>
          </div>
          <div>
            <dt>Статус</dt>
            <dd>
              {listing.status === "listed" ? "Забронировано" : "Доступно к брони"}
            </dd>
          </div>
        </dl>

        {error && <p className="error">{error}</p>}

        <button
          type="button"
          className="btn primary"
          disabled={!canReserve || reserving}
          onClick={onReserve}
        >
          {canReserve
            ? reserving
              ? "Бронируем..."
              : "Забронировать авто"
            : "Уже забронировано"}
        </button>
      </div>

      {modalOpen && (
        <div className="modal-backdrop" onClick={() => setModalOpen(false)}>
          <div
            className="modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <h2>Готово!</h2>
            <p>{modalText}</p>
            <p className="muted">
              {listing.brand} {listing.model}, {listing.year}
            </p>
            <button
              type="button"
              className="btn primary"
              onClick={() => setModalOpen(false)}
            >
              Отлично
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
