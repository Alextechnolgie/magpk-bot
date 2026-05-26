import urllib.request
import urllib.parse
import http.cookiejar
import ssl
from bs4 import BeautifulSoup

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

# 1. GET для кук
print("1. Делаем GET запрос...")
opener.open(urllib.request.Request(url, headers=headers))

# 2. POST для ТМ9-23-2 на 25.05.2026
# Обрати внимание: в HTML коде опция пишется как "ТМ9-23-2" (без пробелов)
payload = {
    "uch_gr_html": "ТМ9-23-2",
    "date_sch_html": "2026-05-25",
    "btn_schedule_html": "Расписание"
}

print("2. Делаем POST запрос...")
data = urllib.parse.urlencode(payload).encode("utf-8")
req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")

with opener.open(req_post) as resp:
    html = resp.read().decode("utf-8")

# Запишем HTML в файл для детального анализа
with open("tm_result.html", "w", encoding="utf-8") as f:
    f.write(html)

soup = BeautifulSoup(html, "html.parser")
table = soup.find("table")

print("\n--- РЕЗУЛЬТАТ ---")
if table:
    rows = table.find_all("tr")
    print(f"Найдена таблица! Количество строк: {len(rows)}")
    for i, r in enumerate(rows):
        cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
        # Используем безопасный вывод без эмодзи, чтобы не упало на Windows
        print(f"Строка {i}: {cols}")
else:
    print("Таблица вообще не найдена!")
    # Выведем кусок тела страницы
    body = soup.find("body")
    if body:
        print("Текст страницы (первые 500 символов):")
        print(body.get_text(" ", strip=True)[:500])
