from bs4 import BeautifulSoup
import sys

# Настраиваем вывод в UTF-8 для консоли
sys.stdout.reconfigure(encoding="utf-8")

with open("tm_result.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

for s in soup(["script", "style", "header", "footer", "nav"]):
    s.decompose()

content_div = soup.find("div", {"class": "platform-content"})
if not content_div:
    content_div = soup.find("main")
if not content_div:
    content_div = soup

text = content_div.get_text("\n", strip=True)
lines = [line.strip() for line in text.split("\n") if line.strip()]

print("--- Текст контента (всего строк:", len(lines), ") ---")
for idx, line in enumerate(lines[:120]):
    print(f"{idx}: {line}")
