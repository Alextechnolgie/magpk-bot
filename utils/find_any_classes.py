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
opener.open(urllib.request.Request(url, headers=headers))

# Проверим несколько прошедших дат (с понедельника 25.05 назад до среды 20.05)
dates = ["2026-05-25", "2026-05-22", "2026-05-21", "2026-05-20"]
groups = ["АСУ9-25", "АТ9-23", "МЛ-22-1", "ТМ9-23-1", "ПК-22"]

found = False
for d in dates:
    if found:
        break
    for g in groups:
        payload = {
            "uch_gr_html": g,
            "date_sch_html": d,
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
                    print(f"🎉 Найдено расписание на {d} для группы {g}!")
                    for r in rows:
                        cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
                        print("  ", cols)
                    found = True
                    break
        except Exception as e:
            pass

if not found:
    print("Ни на один из дней расписание не нашлось. Возможно, структура сайта изменилась сильнее.")
