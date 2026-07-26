# Car Auction AI

Платформа помогает быстрее выводить автомобили на аукцион: по параметрам машины система оценивает рыночную стоимость и дополняет карточку полезным описанием для менеджеров и покупателей. Вместо ручного сбора данных и «на глаз» продавец получает ориентир по цене, сегменту рынка и типичной комплектации. После обработки автомобиль автоматически появляется в каталоге аукциона и готов к публикации. Это сокращает время подготовки лота и делает оценку более прозрачной для бизнеса.

Технический поток: создание авто → оценка (ML) и обогащение (LLM) → карточка на аукционе.

## Скриншоты
### Форма оценки
![Форма оценки автомобиля](media/форма.png)
### Карточка машины
![Карточка автомобиля](media/каточка_машины.png)
### Аукцион
![Список аукциона](media/аукцион.png)

## Архитектура (кратко)

| Сервис | Порт | Назначение |
|---|---|---|
| Frontend (React) | 8080 (Docker) / 5173 (dev) | UI оценки и аукциона |
| Gateway | 8000 | HTTP API автомобилей, публикация `vehicle.created` |
| Enrichment | 8002 | LLM-обогащение (trim, options, segment) |
| ML Service | 8001 | Оценка цены |
| Market Price | — | Consumer: `price.requested` → ML → `price.completed` |
| Orchestrator | — | Saga: координация этапов, статусы в Postgres + state в Mongo |
| Auction API / worker | 8003 / — | Listings + consumer `processing.completed` |
| PostgreSQL | 5433→5432 | Автомобили, listings |
| MongoDB | 27017 | Состояние saga |
| RabbitMQ | 5672 / UI 15672 | События между сервисами |

### HTTP-роутинг (фронт → бэкенд)

Frontend не ходит в сервисы напрямую по абсолютным URL. В dev Vite-прокси, в Docker — nginx:

| Запрос с фронта | Куда уходит | Backend |
|---|---|---|
| `POST/GET /api/vehicles…` | Gateway `:8000` | `/vehicles` |
| `GET/POST /auction-api/listings…` | Auction API `:8003` | `/listings…` |

Основные endpoint’ы:

- Gateway: `POST /vehicles`, `GET /vehicles`, `GET /vehicles/{id}`
- Auction: `GET /listings`, `GET /listings/{id}`, `GET /listings/by-vehicle/{id}`, `POST /listings/{id}/reserve`
- Enrichment (внутренний): `POST /enrich`
- ML (внутренний): `POST /predict`

### Роутинг событий (RabbitMQ, exchange `vehicle`)

```
POST /vehicles
    → vehicle.created
        → Orchestrator
            → HTTP Enrichment
            → vehicle.price.requested
                → Market Price → ML
                → vehicle.price.completed
                    → Orchestrator (когда enrichment + price готовы)
                        → status READY
                        → vehicle.processing.completed
                            → Auction Platform (listing)
```

| Routing key | Кто публикует | Кто слушает |
|---|---|---|
| `vehicle.created` | Gateway | Orchestrator |
| `vehicle.price.requested` | Orchestrator | Market Price |
| `vehicle.price.completed` | Market Price | Orchestrator |
| `vehicle.processing.completed` | Orchestrator | Auction worker |

## Развёртывание (Docker)

Требования: Docker + Docker Compose, файл `.env` в корне (см. пример ниже).

```bash
# поднять всё
docker compose -f infra/docker-compose.yml --env-file .env up --build -d

# логи
docker compose -f infra/docker-compose.yml logs -f

# остановить
docker compose -f infra/docker-compose.yml down
```

Открыть:

- Сайт: http://localhost:8080  
- Gateway docs: http://localhost:8000/docs  
- Auction docs: http://localhost:8003/docs  
- RabbitMQ UI: http://localhost:15672 (`admin` / `secret`)

Минимальный `.env`:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret
POSTGRES_DB=car_auction
POSTGRES_PORT=5433
POSTGRES_HOST=localhost
POSTGRES_URL=postgresql+psycopg2://admin:secret@localhost:5433/car_auction
RABBITMQ_URL=amqp://admin:secret@localhost:5672/
MONGO_URL=mongodb://admin:secret@localhost:27017/?authSource=admin
MONGO_DB=car_auction
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ENRICHMENT_URL=http://127.0.0.1:8002
ML_SERVICE_URL=http://127.0.0.1:8001
```

`OPENAI_API_KEY` нужен для Enrichment. Не коммить ключ в git.

## Локальный запуск (без Docker-приложений)

1. Инфраструктура:

```bash
docker compose -f infra/docker-compose.yml --env-file .env up -d postgres rabbitmq mongodb
```

2. Python-зависимости:

```bash
pip install -r requirements.txt
```

3. Сервисы (отдельные терминалы, из корня репозитория):

```bash
uvicorn backend.gateway.app.main:app --reload
uvicorn backend.enrichment.app.main:app --reload --port 8002
uvicorn backend.ml_service.app.main:app --reload --port 8001
python -m backend.market_price.app.main
python -m backend.orchestrator.app.main
python -m backend.auction_platform.app.main
uvicorn backend.auction_platform.app.api:app --reload --port 8003
```

4. Frontend:

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:5173 (прокси на Gateway и Auction уже в `vite.config.js`).
