import urllib.request
import urllib.parse
import http.cookiejar
import ssl
from bs4 import BeautifulSoup
from config import ALL_GROUPS

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPSHandler(context=ctx)
)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://magpk.ru/studentu/raspisanie-zanyatij"
}

url = "https://magpk.ru/studentu/raspisanie-zanyatij"
print("Получаем сессию...")
opener.open(urllib.request.Request(url, headers=headers))

print("Сканируем все группы на сегодня...")
active_groups = []

for group in ALL_GROUPS:
    payload = {
        "uch_gr_html": group,
        "date_sch_html": "2026-05-26",
        "btn_schedule_html": "Расписание"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with opener.open(req_post) as resp:
            html = resp.read().decode("utf-8")
        
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            if len(rows) > 1:
                print(f"✅ Найдено расписание для {group}! Строк: {len(rows)}")
                active_groups.append(group)
                # Выведем первые пару строк
                for r in rows:
                    print("  ", [td.get_text(strip=True) for td in r.find_all(["td", "th"])])
                break # Остановимся на первой найденной
    except Exception as e:
        print(f"Ошибка для {group}: {e}")

if not active_groups:
    print("❌ Ни для одной группы на сегодня расписание не заполнено на сайте (пустые таблицы).")
