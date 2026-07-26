import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import SearchSelect from "../components/SearchSelect";
import { BRANDS, CARS } from "../data/cars";
import { BODY_TYPES, COLORS, STATUS_LABELS, YEARS } from "../data/options";
import { createVehicle, getListingByVehicle, getVehicle } from "../api";

const emptyForm = {
  brand: "",
  model: "",
  year: YEARS[0],
  body_type: BODY_TYPES[0],
  mileage: "",
  color: "",
};

export default function EvaluatePage() {
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [vehicleId, setVehicleId] = useState(null);
  const [status, setStatus] = useState(null);
  const [auctionListingId, setAuctionListingId] = useState(null);

  const models = useMemo(() => {
    if (!form.brand || !CARS[form.brand]) return [];
    return CARS[form.brand];
  }, [form.brand]);

  useEffect(() => {
    if (!vehicleId) return undefined;
    if (status === "ready" || status === "failed") return undefined;

    let cancelled = false;

    async function tick() {
      try {
        const vehicle = await getVehicle(vehicleId);
        if (cancelled) return;
        setStatus(vehicle.status);

        if (vehicle.status === "ready") {
          try {
            const listing = await getListingByVehicle(vehicleId);
            if (!cancelled) setAuctionListingId(listing.id);
          } catch {
            // listing may appear a second later
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    tick();
    const timer = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [vehicleId, status]);

  // keep trying to resolve listing after ready
  useEffect(() => {
    if (status !== "ready" || auctionListingId) return undefined;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const listing = await getListingByVehicle(vehicleId);
        if (!cancelled) {
          setAuctionListingId(listing.id);
          clearInterval(timer);
        }
      } catch {
        // wait
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [status, auctionListingId, vehicleId]);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setAuctionListingId(null);

    if (!form.brand || !form.model) {
      setError("Выберите марку и модель");
      return;
    }

    const mileage = Number(form.mileage);
    if (!Number.isFinite(mileage) || mileage < 0) {
      setError("Укажите корректный пробег");
      return;
    }

    setSubmitting(true);
    try {
      const result = await createVehicle({
        brand: form.brand,
        model: form.model,
        year: Number(form.year),
        mileage,
        color: form.color || null,
        body_type: form.body_type,
      });
      setVehicleId(result.id);
      setStatus("created");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1>Оценка автомобиля</h1>
      <p className="muted">
        Заполните данные — отправим на enrichment и ML, потом появится ссылка на
        аукцион.
      </p>

      <form className="card form" onSubmit={onSubmit}>
        <SearchSelect
          label="Марка"
          value={form.brand}
          options={BRANDS}
          placeholder="Начните вводить марку..."
          required
          onChange={(brand) =>
            setForm((prev) => ({ ...prev, brand, model: "" }))
          }
        />

        <SearchSelect
          label="Модель"
          value={form.model}
          options={models}
          placeholder={form.brand ? "Найдите модель..." : "Сначала выберите марку"}
          disabled={!form.brand}
          required
          onChange={(model) => setForm((prev) => ({ ...prev, model }))}
        />

        <label className="field">
          <span>Год</span>
          <select
            value={form.year}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, year: Number(e.target.value) }))
            }
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Кузов</span>
          <select
            value={form.body_type}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, body_type: e.target.value }))
            }
          >
            {BODY_TYPES.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Пробег (км)</span>
          <input
            type="number"
            min="0"
            required
            value={form.mileage}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, mileage: e.target.value }))
            }
          />
        </label>

        <label className="field">
          <span>Цвет (необязательно)</span>
          <select
            value={form.color}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, color: e.target.value }))
            }
          >
            <option value="">—</option>
            {COLORS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        {error && <p className="error">{error}</p>}

        <button type="submit" className="btn primary" disabled={submitting}>
          {submitting ? "Отправка..." : "Отправить на оценку"}
        </button>
      </form>

      {vehicleId && (
        <div className="card status-box">
          <h2>Статус заявки #{vehicleId}</h2>
          <ol className="steps">
            <li className={status ? "done" : ""}>Принято</li>
            <li
              className={
                status === "processing" || status === "ready"
                  ? "done"
                  : status === "failed"
                    ? "fail"
                    : ""
              }
            >
              Оценивается (CV / enrichment + ML)
            </li>
            <li className={status === "ready" ? "done" : status === "failed" ? "fail" : ""}>
              Готово
            </li>
          </ol>
          <p>
            Сейчас: <strong>{STATUS_LABELS[status] || status || "—"}</strong>
          </p>
          {status === "ready" && (
            <p>
              {auctionListingId ? (
                <Link className="btn primary" to={`/auction/${auctionListingId}`}>
                  Открыть на аукционе
                </Link>
              ) : (
                <span className="muted">Ждём появление лота на аукционе...</span>
              )}
            </p>
          )}
          {status === "failed" && (
            <p className="error">Оценка не удалась. Попробуйте ещё раз.</p>
          )}
        </div>
      )}
    </div>
  );
}
