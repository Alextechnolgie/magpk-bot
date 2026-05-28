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
select = soup.find("select", {"name": "uch_gr_html"})

# Найдем опцию, которая содержит "ТМ9-23-2"
found_option = None
for opt in select.find_all("option"):
    if "ТМ9-23-2" in opt.text or "TM9-23-2" in opt.text or "ТМ" in opt.text:
        if "23-2" in opt.text:
            found_option = opt
            break

if found_option:
    val = found_option.get("value")
    text = found_option.text
    print(f"Найдена опция: '{text}' с value='{val}'")
    
    # Выведем коды символов для value
    print("Коды символов в value:")
    for char in val:
        print(f"  '{char}': U+{ord(char):04X} ({'Английская' if ord(char) < 128 else 'Русская'})")
else:
    print("Опция ТМ9-23-2 не найдена в списке!")
