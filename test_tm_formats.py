import urllib.request
import urllib.parse
import http.cookiejar
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://magpk.ru/studentu/raspisanie-zanyatij"

def run_test(name, date_val):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx)
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://magpk.ru/studentu/raspisanie-zanyatij"
    }
    
    # 1. GET
    opener.open(urllib.request.Request(url, headers=headers))
    
    # 2. POST
    payload = {
        "uch_gr_html": "ТМ9-23-2",
        "date_sch_html": date_val,
        "btn_schedule_html": "Расписание"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    with opener.open(req_post) as resp:
        html = resp.read().decode("utf-8")
        
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    print(f"\n[{name}] Дата: {date_val}")
    if table:
        rows = table.find_all("tr")
        print(f"  Найдена таблица! Строк: {len(rows)}")
        for i, r in enumerate(rows):
            cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
            print(f"  Строка {i}: {cols}")
    else:
        print("  Таблица не найдена.")

# Пробуем два формата
run_test("Формат DD.MM.YYYY", "25.05.2026")
run_test("Формат YYYY-MM-DD", "2026-05-25")
