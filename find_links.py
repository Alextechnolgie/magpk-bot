import urllib.request
import ssl
from bs4 import BeautifulSoup
from urllib.parse import urljoin

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scan_page(url):
    print(f"\nСканируем ссылки на странице: {url}")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            html = r.read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a")
        found = False
        for a in links:
            href = a.get("href")
            text = a.get_text(" ", strip=True)
            if href and any(word in text.lower() or word in href.lower() for word in ["расписан", "raspis", "shedule", "zanyat"]):
                full_url = urljoin(url, href)
                print(f"  Ссылка: '{text}' -> {full_url}")
                found = True
        if not found:
            print("  Ничего не найдено.")
    except Exception as e:
        print(f"  Ошибка при сканировании: {e}")

scan_page("https://magpk.ru/")
scan_page("https://magpk.ru/studentu")
