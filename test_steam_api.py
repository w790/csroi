import asyncio
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

URLS = [
    {
        "name": "Steam Market Search (AK-47)",
        "url": "https://steamcommunity.com/market/search?q=AK-47&category_730_Weapon%5B%5D=tag_weapon_ak47",
        "expect": "Результаты поиска (HTML с ценами)",
    },
    {
        "name": "Steam Market Listing (конкретный предмет)",
        "url": "https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Slate%20(Field-Tested)",
        "expect": "Страница лота с графиком цен",
    },
    {
        "name": "Public Inventory Page (JSON endpoint)",
        "url": "https://steamcommunity.com/inventory/76561198000000000/730/2",
        "expect": "JSON инвентаря ИЛИ редирект на логин",
    },
    {
        "name": "CSGOStash (альтернативная база)",
        "url": "https://csgostash.com/",
        "expect": "Главная страница с базой скинов",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


async def test_url(client: httpx.AsyncClient, name: str, url: str, expect: str):
    result = {"name": name, "status": "UNKNOWN", "code": None, "snippet": "", "note": ""}
    try:
        resp = await client.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
        result["code"] = resp.status_code

        if resp.status_code == 200:
            text = resp.text[:500]
            result["snippet"] = text.replace("\n", " ")[:200]

            if "login" in text.lower() or "sign in" in text.lower():
                result["status"] = "REQUIRE LOGIN"
                result["note"] = "Требуется авторизация Steam"
            elif "captcha" in text.lower() or "access denied" in text.lower():
                result["status"] = "BLOCKED / CAPTCHA"
                result["note"] = "Steam заблокировал запрос"
            else:
                result["status"] = "ACCESSIBLE"
                result["note"] = expect
        elif resp.status_code == 403:
            result["status"] = "FORBIDDEN"
            result["note"] = "Доступ запрещен (возможно, нужен cookie/session)"
        elif resp.status_code == 429:
            result["status"] = "RATE LIMITED"
        else:
            result["status"] = f"HTTP {resp.status_code}"

    except Exception as e:
        result["status"] = "ERROR"
        result["note"] = str(e)[:100]

    return result


async def main():
    console.print("\n Тестирование веб-страниц Steam...\n")

    async with httpx.AsyncClient() as client:
        results = []
        for u in URLS:
            console.print(f"{u['name']}...")
            res = await test_url(client, **u)
            results.append(res)
            console.print(f"   {res['status']} — {res['note'][:80]}")
            console.print()

    table = Table(title=" Результаты теста веб-страниц", show_lines=True)
    table.add_column("URL", style="cyan", no_wrap=False)
    table.add_column("Статус", justify="center")
    table.add_column("HTTP")
    table.add_column("Примечание", no_wrap=False)

    for r in results:
        table.add_row(r["name"], r["status"], str(r["code"]), r["note"])

    console.print(table)

    accessible = [r for r in results if r["status"] == "ACCESSIBLE"]
    blocked = [r for r in results if "BLOCKED" in r["status"] or "FORBIDDEN" in r["status"]]
    login_req = [r for r in results if "LOGIN" in r["status"]]

    console.print(f"\nДоступных страниц: {len(accessible)}")
    console.print(f"Заблокированных: {len(blocked)}")
    console.print(f"Требуют логина: {len(login_req)}")


if __name__ == "__main__":
    asyncio.run(main())