# CSROI

Аналитика окупаемости кейсов Counter-Strike 2. Каталог берётся из ByMykel, цены и история продаж — из Skinport. Запросы к API читают Postgres и в Skinport не ходят.

## Запуск

Порт 5432 на компьютере часто занят другим Postgres, поэтому контейнер открыт на 5433.

```bash
docker compose up -d postgres redis
uv sync
uv run alembic upgrade head
uv run python -m app.jobs.load_catalog
uv run python -m app.jobs.sync_prices
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Документация ручек: http://127.0.0.1:8000/docs

## Воркер

Сбор цен запускайте одним процессом. Второй воркер или параллельный `uv run python -m app.jobs.sync_prices` упирается в лимит Skinport: 8 запросов за 5 минут. Замок в Redis не даст второму процессу начать сбор, пока первый не закончит.

```bash
uv run python -m app.jobs.worker
```

Цены обновляются каждые 5 минут. Каталог — раз в сутки в 03:10 UTC и один раз при старте воркера.

Миграции можно запускать из нескольких процессов сразу: `alembic upgrade head` берёт advisory lock в Postgres, поэтому `api` и `worker` в docker compose не мешают друг другу.

## Ручки

- `GET /api/v1/health`
- `GET /api/v1/cases` — список кейсов. Параметры: `crate_type` (по умолчанию `Case`), `sort` (`name`, `case_price`, `expected_value`, `unboxing_roi`, `roi_7d`, `roi_30d`, `roi_90d`) и `order` (`asc` или `desc`). Кейсы без значения в поле сортировки идут в конце.
- `GET /api/v1/cases/{id}` — кейс с предметами, шансами и ценами.
- `GET /api/v1/cases/{id}/history?days=90` — дневные снэпшоты цены кейса. Воркер сохраняет первую цену за сутки.

Самые выгодные кейсы для открытия:

```bash
curl "http://127.0.0.1:8000/api/v1/cases?sort=unboxing_roi&order=desc"
```

## Как считается ROI

- Шансы — официальные шансы Valve: Mil-Spec 79.92%, Restricted 15.98%, Classified 3.2%, Covert 0.64%, нож или перчатки 0.26%. Внутри редкости шанс делится между записями пула поровну.
- Каждая фаза Doppler и Gamma Doppler — отдельная запись пула. На Skinport у фаз одно имя и одна цена, поэтому у Doppler-ножа шанс в 5–7 раз выше, чем у других скинов того же ножа.
- Цена предмета — Field-Tested, если она есть. Иначе берётся износ, который занимает большую часть float-диапазона скина: у Doppler (0–0.08) это Factory New.
- `unboxing_roi = (EV − (цена кейса + ключ)) / (цена кейса + ключ)`. StatTrak не учитывается.

## Проверки

```bash
make check
```

Команда запускает `ruff format`, `mypy --strict`, `ruff check --fix`, `deptry` и `pytest`. Разовые скрипты проверки источников лежат в `scripts/probes` и в проверки не входят.
