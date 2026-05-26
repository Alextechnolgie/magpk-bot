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

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx) as r:
    html = r.read().decode("utf-8")

soup = BeautifulSoup(html, "html.parser")

# Ищем все теги <script>
scripts = soup.find_all("script")
print(f"Найдено скриптов: {len(scripts)}")
for i, s in enumerate(scripts):
    src = s.get("src")
    if src:
        if "college" in src or "schedule" in src or "pcollege" in src:
            print(f"Скрипт {i} (внешний): {src}")
    else:
        content = s.string
        if content and ("uch_gr" in content or "schedule" in content or "pcollege" in content or "btn_schedule" in content):
            print(f"Скрипт {i} (встроенный):")
            print(content[:500])
            print("-" * 40)
