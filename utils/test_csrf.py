import urllib.request
import urllib.parse
import http.cookiejar
import ssl
import json
import re
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

# 1. GET запрос
print("1. Делаем GET запрос...")
with opener.open(urllib.request.Request(url, headers=headers)) as resp:
    html = resp.read().decode("utf-8")

# Ищем csrf.token в HTML-коде страницы
csrf_token = None
match = re.search(r'"csrf.token"\s*:\s*"([a-f0-9]{32})"', html)
if match:
    csrf_token = match.group(1)
    print(f"Найден CSRF-токен Joomla: {csrf_token}")
else:
    print("CSRF-токен не найден в JSON-опциях! Ищем в input...")
    soup = BeautifulSoup(html, "html.parser")
    # Попробуем найти скрытые инпуты без имени, у которых значение "1" и имя из 32 hex символов
    for inp in soup.find_all("input", {"type": "hidden"}):
        name = inp.get("name")
        if name and len(name) == 32 and inp.get("value") == "1":
            csrf_token = name
            print(f"Найден CSRF-токен в скрытом инпуте: {csrf_token}")
            break

# 2. Делаем POST запрос с токеном
payload = {
    "uch_gr_html": "ТМ9-23-2",
    "date_sch_html": "2026-05-25",
    "btn_schedule_html": "Расписание"
}

if csrf_token:
    # В Joomla токен безопасности передается как имя поля со значением "1"
    payload[csrf_token] = "1"

print("2. Делаем POST запрос с токеном...")
data = urllib.parse.urlencode(payload).encode("utf-8")
req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")

with opener.open(req_post) as resp:
    html_post = resp.read().decode("utf-8")

soup = BeautifulSoup(html_post, "html.parser")
table = soup.find("table")

print("\n--- РЕЗУЛЬТАТ ---")
if table:
    rows = table.find_all("tr")
    print(f"Найдена таблица! Количество строк: {len(rows)}")
    for i, r in enumerate(rows):
        cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
        print(f"Строка {i}: {cols}")
else:
    print("Таблица не найдена.")
