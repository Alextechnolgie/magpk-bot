from bs4 import BeautifulSoup

with open("test_post.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

tables = soup.find_all("table")
print("Найдено таблиц:", len(tables))

for i, t in enumerate(tables):
    print(f"Таблица {i}: класс={t.get('class')}, строк={len(t.find_all('tr'))}")
    print(t.get_text(" ", strip=True)[:300])
    print("-" * 50)

# Также выведем все п-теги или дивы, которые могут содержать сообщения о расписании
custom_div = soup.find("div", id="mod-custom234")
if custom_div:
    print("Содержимое mod-custom234:")
    print(custom_div.get_text(" ", strip=True)[:500])
