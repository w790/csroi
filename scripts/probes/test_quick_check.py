import asyncio
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

async def quick_check():
    console.rule("[bold cyan]CS2 Quick Check — Источники данных[/bold cyan]")
    
    results = []
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        
        console.print("Проверяю ByMykel/CSGO-API (crates.json)...")
        try:
            r = await client.get(
                "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/crates.json"
            )
            data = r.json()
            sample = data[0] if data else {}
            results.append({
                "source": "ByMykel/CSGO-API (crates)",
                "status": f"OK",
                "detail": f"{len(data)} кейсов. Пример: {sample.get('name', '?')}",
                "note": "GitHub raw JSON, без ключей"
            })
        except Exception as e:
            results.append({"source": "ByMykel/CSGO-API (crates)", "status": f"{e}", "detail": "", "note": ""})
        
        console.print("Проверяю Skinport /v1/items...")
        try:
            r = await client.get(
                "https://api.skinport.com/v1/items",
                params={"app_id": 730, "currency": "USD"},
                headers={"Accept-Encoding": "br"},
            )
            if r.status_code == 200:
                data = r.json()
                sample = data[0] if data else {}
                results.append({
                    "source": "Skinport /v1/items",
                    "status": "OK",
                    "detail": f"{len(data)} предметов. {sample.get('market_hash_name','?')} = \${sample.get('suggested_price','?')}",
                    "note": "8 req/5min, Accept-Encoding: br"
                })
            else:
                results.append({
                    "source": "Skinport /v1/items",
                    "status": f"HTTP {r.status_code}",
                    "detail": r.text[:80],
                    "note": ""
                })
        except Exception as e:
            results.append({"source": "Skinport /v1/items", "status": f"{e}", "detail": "", "note": ""})
        
        console.print("Проверяю Skinport /v1/sales/history...")
        try:
            r = await client.get(
                "https://api.skinport.com/v1/sales/history",
                params={
                    "app_id": 730,
                    "market_hash_name": "AK-47 | Redline (Field-Tested)",
                    "currency": "USD",
                },
                headers={"Accept-Encoding": "br"},
            )
            if r.status_code == 200:
                data = r.json()
                results.append({
                    "source": "Skinport /v1/sales/history",
                    "status": "OK",
                    "detail": f"Данные: {data}",
                    "note": "История 24h/7d/30d/90d"
                })
            else:
                results.append({
                    "source": "Skinport /v1/sales/history",
                    "status": f"HTTP {r.status_code}",
                    "detail": r.text[:80],
                    "note": ""
                })
        except Exception as e:
            results.append({"source": "Skinport /v1/sales/history", "status": f"{e}", "detail": "", "note": ""})
        
        console.print("Проверяю csgotrader prices (HEAD request)...")
        try:
            r = await client.head("https://prices.csgotrader.app/latest/prices_v6.json")
            results.append({
                "source": "csgotrader prices_v6.json",
                "status": f"OK (HTTP {r.status_code})" if r.status_code == 200 else f"HTTP {r.status_code}",
                "detail": f"Content-Length: {r.headers.get('content-length', '?')} bytes",
                "note": "Неофициальный, только для теста"
            })
        except Exception as e:
            results.append({"source": "csgotrader prices_v6.json", "status": f"{e}", "detail": "", "note": ""})
        
        console.print("Проверяю Pricempire...")
        try:
            r = await client.get("https://pricempire.com")
            results.append({
                "source": "pricempire.com",
                "status": f"Доступен" if r.status_code < 400 else f"HTTP {r.status_code}",
                "detail": "Нужен API ключ (Starter free tier)",
                "note": "Регистрация: pricempire.com/api"
            })
        except Exception as e:
            results.append({"source": "pricempire.com", "status": f"{e}", "detail": "", "note": ""})
        
        console.print("Проверяю DMarket...")
        try:
            r = await client.head("https://api.dmarket.com/marketplace-api/v1/currency")
            results.append({
                "source": "DMarket API",
                "status": f"Достижим (HTTP {r.status_code})" if r.status_code < 500 else f"HTTP {r.status_code}",
                "detail": "Нужен API ключ (Ed25519 подпись)",
                "note": "Бесплатная регистрация на dmarket.com"
            })
        except Exception as e:
            results.append({"source": "DMarket API", "status": f"{e}", "detail": "", "note": ""})
    
    table = Table(title="Результаты проверки источников данных", show_lines=True)
    table.add_column("Источник", style="cyan", no_wrap=False)
    table.add_column("Статус", justify="center")
    table.add_column("Данные / Пример", no_wrap=False)
    table.add_column("Примечание", style="yellow", no_wrap=False)
    
    for r in results:
        table.add_row(r["source"], r["status"], str(r["detail"])[:120], r["note"])
    
    console.print()
    console.print(table)
    
    ok = sum(1 for r in results if r["status"].startswith(("OK", "доступен", "Доступен", "Достижим")))
    fail = len(results) - ok
    console.print(f"\nРаботает: {ok} источников")
    console.print(f"Недоступно: {fail} источников")

if __name__ == "__main__":
    asyncio.run(quick_check())
