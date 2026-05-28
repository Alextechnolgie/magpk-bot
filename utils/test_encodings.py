import urllib.request
import urllib.parse
import http.cookiejar
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://magpk.ru/studentu/raspisanie-zanyatij"

def run_test(name, payload_dict, encoding="utf-8"):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx)
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://magpk.ru/studentu/raspisanie-zanyatij"
    }
    
    # GET
    opener.open(urllib.request.Request(url, headers=headers))
    
    # POST
    data = urllib.parse.urlencode(payload_dict, encoding=encoding).encode(encoding)
    req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with opener.open(req_post) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            print(f"[{name}] Найдена таблица! Строк: {len(rows)}")
            if len(rows) > 1:
                for r in rows[:3]:
                    print("  ", [td.get_text(strip=True) for td in r.find_all(["td", "th"])])
        else:
            print(f"[{name}] Таблица не найдена")
    except Exception as e:
        print(f"[{name}] Ошибка: {e}")

# Тест 1: Стандартный UTF-8
run_test("UTF-8 с кнопкой", {
    "uch_gr_html": "ТМ9-23-2",
    "date_sch_html": "2026-05-25",
    "btn_schedule_html": "Расписание"
})

# Тест 2: UTF-8 БЕЗ кнопки (только группа и дата)
run_test("UTF-8 без кнопки", {
    "uch_gr_html": "ТМ9-23-2",
    "date_sch_html": "2026-05-25"
})

# Тест 3: Кодировка Windows-1251 (CP1251) для кнопки и группы
run_test("CP1251 с кнопкой", {
    "uch_gr_html": "ТМ9-23-2",
    "date_sch_html": "2026-05-25",
    "btn_schedule_html": "Расписание"
}, encoding="cp1251")
