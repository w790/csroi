# CSROI

Аналитика окупаемости кейсов Counter-Strike 2. Каталог берётся из ByMykel, цены и история продаж — из Skinport. Запросы к API читают Postgres и в Skinport не ходят.

## Запуск

Порт 5432 на компьютере часто занят другим Postgres, поэтому контейнер открыт на 5433.

```bash
docker compose up -d postgres redis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.jobs.load_catalog
python -m app.jobs.sync_prices
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Документация ручек: http://127.0.0.1:8000/docs

## Воркер

Сбор цен запускайте одним процессом. Второй воркер или параллельный `python -m app.jobs.sync_prices` упирается в лимит Skinport: 8 запросов за 5 минут. Замок в Redis не даст второму процессу начать сбор, пока первый не закончит.

```bash
python -m app.jobs.worker
```

Цены обновляются каждые 5 минут. Каталог — раз в сутки в 03:10 UTC и один раз при старте воркера.

## Ручки

- `GET /api/v1/health`
- `GET /api/v1/cases`
- `GET /api/v1/cases/{id}`
