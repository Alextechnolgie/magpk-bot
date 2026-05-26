import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
url = "https://magpk.ru/studentu/raspisanie-zanyatij"

print("Скачиваем страницу GET-запросом...")
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx) as r:
    html = r.read().decode("utf-8")

# Ищем упоминания преподавателя или предмета
search_terms = ["Красноперова", "МДК 01.02", "Котунова", "Кузин"]

print("\n--- Результаты поиска на исходной странице (GET) ---")
for term in search_terms:
    matches = [m.start() for m in re.finditer(term, html, re.IGNORECASE)]
    print(f"Слово '{term}': найдено {len(matches)} раз(а)")
    for idx, pos in enumerate(matches[:2]):
        start = max(0, pos - 100)
        end = min(len(html), pos + 200)
        print(f"  Совпадение {idx + 1}:")
        print("  ...", html[start:end].strip().replace("\n", " "), "...")
