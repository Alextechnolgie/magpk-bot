import urllib.request
import urllib.parse
import http.cookiejar
import ssl
from bs4 import BeautifulSoup

# Отключаем проверку SSL (частая проблема учебных сайтов)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Создаем обработчик кук
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPSHandler(context=ctx)
)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://magpk.ru/studentu/raspisanie-zanyatij"
}

# 1. GET запрос для получения кук сессии
url = "https://magpk.ru/studentu/raspisanie-zanyatij"
req_get = urllib.request.Request(url, headers=headers)
print("Делаем GET запрос...")
with opener.open(req_get) as resp:
    html_get = resp.read().decode("utf-8")
print("Получено кук:", len(cj))
for cookie in cj:
    print(f"  Cookie: {cookie.name}={cookie.value}")

# 2. POST запрос с расписанием
payload = {
    "uch_gr_html": "АСУ9-25",
    "date_sch_html": "2026-05-26",
    "btn_schedule_html": "Расписание"
}
data = urllib.parse.urlencode(payload).encode("utf-8")
req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")

print("Делаем POST запрос...")
with opener.open(req_post) as resp:
    html_post = resp.read().decode("utf-8")

# Ищем таблицу в ответе
soup = BeautifulSoup(html_post, "html.parser")
table = soup.find("table")
if table:
    print("УРА! Таблица расписания найдена!")
    rows = table.find_all("tr")
    print(f"Всего строк в таблице: {len(rows)}")
    for r in rows[:5]:
        print([td.get_text(strip=True) for td in r.find_all(["td", "th"])])
else:
    print("Таблица всё еще НЕ НАЙДЕНА. Ищем текст с ошибкой...")
    # Сохраним в файл для ручного анализа
    with open("cookie_result.html", "w", encoding="utf-8") as f:
        f.write(html_post)
