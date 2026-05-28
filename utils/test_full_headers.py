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

# Полный набор заголовков реального браузера Chrome
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://magpk.ru",
    "Referer": "https://magpk.ru/studentu/raspisanie-zanyatij",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

url = "https://magpk.ru/studentu/raspisanie-zanyatij"

# 1. GET
print("1. GET...")
req_get = urllib.request.Request(url, headers={k: v for k, v in headers.items() if k not in ["Content-Type", "Origin"]})
opener.open(req_get)

# 2. POST
payload = {
    "uch_gr_html": "ТМ9-23-2",
    "date_sch_html": "2026-05-25",
    "btn_schedule_html": "Расписание"
}
data = urllib.parse.urlencode(payload).encode("utf-8")
req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")

print("2. POST...")
with opener.open(req_post) as resp:
    html = resp.read().decode("utf-8")

soup = BeautifulSoup(html, "html.parser")
table = soup.find("table")
if table:
    rows = table.find_all("tr")
    print(f"Успех! Строк: {len(rows)}")
    for r in rows:
        print([td.get_text(strip=True) for td in r.find_all(["td", "th"])])
else:
    print("Всё еще пустая таблица.")
