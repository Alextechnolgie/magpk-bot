import urllib.request
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
url = "https://magpk.ru/studentu/raspisanie-zanyatij"

print("Делаем запрос...")
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx) as r:
    html = r.read().decode("utf-8")

soup = BeautifulSoup(html, "html.parser")

# 1. Проверяем дату по умолчанию в инпуте
date_input = soup.find("input", {"id": "date_sch"})
if date_input:
    print("Дата по умолчанию на сайте:", date_input.get("value"))
else:
    print("Инпут даты не найден!")

# 2. Посмотрим, есть ли на странице уже какая-то таблица с расписанием по умолчанию
table = soup.find("table")
if table:
    print("На странице по умолчанию есть таблица расписания!")
    rows = table.find_all("tr")
    print("Количество строк:", len(rows))
    for r in rows[:10]:
         print("  ", [td.get_text(strip=True) for td in r.find_all(["td", "th"])])
else:
    print("По умолчанию таблицы расписания на странице нет.")
