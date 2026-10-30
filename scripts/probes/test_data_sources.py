import asyncio
import httpx
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


async def test_bymykel_schema(client: httpx.AsyncClient) -> dict:
    base = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en"
    endpoints = {
        "crates (кейсы)": f"{base}/crates.json",
        "skins (скины)": f"{base}/skins.json",
        "collections": f"{base}/collections.json",
    }
    results = {}
    for name, url in endpoints.items():
        try:
            r = await client.get(url, timeout=15)
            data = r.json()
            count = len(data)
            sample_keys = list(data[0].keys()) if data else []
            results[name] = {
                "status": "OK",
                "count": count,
                "sample_keys": str(sample_keys[:5]),
            }
        except Exception as e:
            results[name] = {"status": f"{e}", "count": 0, "sample_keys": ""}
    return results


async def test_skinport(client: httpx.AsyncClient) -> dict:
    results = {}

    try:
        r = await client.get(
            "https://api.skinport.com/v1/items",
            params={"app_id": 730, "currency": "USD"},
            headers={"Accept-Encoding": "br"},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            count = len(data)
            sample = data[0] if data else {}
            results["items (цены)"] = {
                "status": "OK",
                "count": f"{count} предметов",
                "note": f"Пример: {sample.get('market_hash_name', '?')} = ${sample.get('suggested_price', '?')}",
            }
        else:
            results["items (цены)"] = {
                "status": f"HTTP {r.status_code}",
                "count": "0",
                "note": r.text[:100],
            }
    except Exception as e:
        results["items (цены)"] = {"status": f"{e}", "count": "0", "note": ""}

    try:
        r = await client.get(
            "https://api.skinport.com/v1/sales/history",
            params={
                "app_id": 730,
                "market_hash_name": "AK-47 | Redline (Field-Tested)",
                "currency": "USD",
            },
            headers={"Accept-Encoding": "br"},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            results["sales/history (история)"] = {
                "status": "OK",
                "count": f"{len(data)} периодов",
                "note": f"Ключи: {list(data[0].keys()) if data else 'нет данных'}",
            }
        else:
            results["sales/history (история)"] = {
                "status": f"HTTP {r.status_code}",
                "count": "0",
                "note": r.text[:100],
            }
    except Exception as e:
        results["sales/history (история)"] = {
            "status": f"{e}",
            "count": "0",
            "note": "",
        }

    return results


async def test_csgotrader_prices(client: httpx.AsyncClient) -> dict:
    results = {}
    try:
        r = await client.get(
            "https://prices.csgotrader.app/latest/prices_v6.json",
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            total = len(data)
            sample_key = "AK-47 | Redline (Field-Tested)"
            sample = data.get(sample_key, {})
            results["prices_v6.json"] = {
                "status": "OK",
                "count": f"{total} предметов",
                "note": f"AK Redline FT: {sample}",
            }
        else:
            results["prices_v6.json"] = {
                "status": f"HTTP {r.status_code}",
                "count": "0",
                "note": "",
            }
    except Exception as e:
        results["prices_v6.json"] = {"status": f"{e}", "count": "0", "note": ""}

    return results


async def test_steamtracking(client: httpx.AsyncClient) -> dict:
    results = {}
    url = "https://raw.githubusercontent.com/SteamTracking/GameTracking-CS2/master/game/csgo/scripts/items/items_game.txt"
    try:
        r = await client.get(url, timeout=20)
        if r.status_code == 200:
            content = r.text
            results["items_game.txt"] = {
                "status": "OK",
                "count": f"{len(content)} байт",
                "note": f"Первые 100 символов: {content[:100].strip()}",
            }
        else:
            results["items_game.txt"] = {
                "status": f"HTTP {r.status_code}",
                "count": "0",
                "note": "",
            }
    except Exception as e:
        results["items_game.txt"] = {"status": f"{e}", "count": "0", "note": ""}

    return results


async def test_pricempire_public(client: httpx.AsyncClient) -> dict:
    results = {}
    try:
        r = await client.get("https://pricempire.com/api", timeout=10)
        results["pricempire.com/api (сайт)"] = {
            "status": f"доступен (HTTP {r.status_code})" if r.status_code < 400 else f"HTTP {r.status_code}",
            "count": "-",
            "note": "Нужна регистрация для API ключа",
        }
    except Exception as e:
        results["pricempire.com/api (сайт)"] = {
            "status": f"{e}",
            "count": "-",
            "note": "",
        }
    return results


async def main():
    console.rule("[bold cyan]CS2 ROI — Проверка источников данных[/bold cyan]")

    async with httpx.AsyncClient(follow_redirects=True) as client:

        console.print("\n[bold yellow]1. Item Schema (ByMykel/CSGO-API)[/bold yellow]")
        schema_results = await test_bymykel_schema(client)
        t = Table(show_lines=True)
        t.add_column("Эндпоинт", style="cyan")
        t.add_column("Статус")
        t.add_column("Кол-во")
        t.add_column("Поля примера")
        for name, r in schema_results.items():
            t.add_row(name, r["status"], str(r["count"]), r["sample_keys"])
        console.print(t)

        console.print("\n[bold yellow]2. Skinport Public API (цены + история)[/bold yellow]")
        skinport_results = await test_skinport(client)
        t2 = Table(show_lines=True)
        t2.add_column("Эндпоинт", style="cyan")
        t2.add_column("Статус")
        t2.add_column("Кол-во")
        t2.add_column("Примечание")
        for name, r in skinport_results.items():
            t2.add_row(name, r["status"], r["count"], r["note"])
        console.print(t2)

        console.print("\n[bold yellow]3. CSGOTrader Prices JSON (неофициальный)[/bold yellow]")
        trader_results = await test_csgotrader_prices(client)
        t3 = Table(show_lines=True)
        t3.add_column("Файл", style="cyan")
        t3.add_column("Статус")
        t3.add_column("Кол-во")
        t3.add_column("Пример")
        for name, r in trader_results.items():
            t3.add_row(name, r["status"], r["count"], str(r["note"])[:150])
        console.print(t3)

        console.print("\n[bold yellow]4. SteamTracking GameTracking-CS2 (raw dumps)[/bold yellow]")
        tracking_results = await test_steamtracking(client)
        t4 = Table(show_lines=True)
        t4.add_column("Файл", style="cyan")
        t4.add_column("Статус")
        t4.add_column("Размер")
        t4.add_column("Примечание")
        for name, r in tracking_results.items():
            t4.add_row(name, r["status"], r["count"], r["note"])
        console.print(t4)

        console.print("\n[bold yellow]5. Pricempire (нужна регистрация для ключа)[/bold yellow]")
        pe_results = await test_pricempire_public(client)
        t5 = Table(show_lines=True)
        t5.add_column("URL", style="cyan")
        t5.add_column("Статус")
        t5.add_column("Примечание")
        for name, r in pe_results.items():
            t5.add_row(name, r["status"], r["note"])
        console.print(t5)

    console.rule("[bold green]ИТОГ[/bold green]")
    console.print("""
[green]РЕКОМЕНДУЕМЫЙ стек данных:[/green]

  [cyan]1. Item Schema:[/cyan]   ByMykel/CSGO-API (GitHub raw JSON) — без ключей
  [cyan]2. Цены (MVP):[/cyan]    Skinport Public API — без ключей, лимит 8 req/5min
  [cyan]3. Цены (prod):[/cyan]   Pricempire Starter tier — бесплатный ключ на сайте
  [cyan]4. Арбитраж:[/cyan]      DMarket API — бесплатный ключ после регистрации
  [cyan]5. История:[/cyan]       Skinport /sales/history + накапливаем свои снэпшоты в Postgres

[yellow]NE ИСПОЛЬЗОВАТЬ в продакшне:[/yellow]
  - csgotrader prices (unoffical, нестабильно)
  - Прямой парсинг Steam Market (429 навсегда)
""")


if __name__ == "__main__":
    asyncio.run(main())
