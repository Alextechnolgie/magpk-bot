from bs4 import BeautifulSoup
import re

with open("tm_result.html", "r", encoding="utf-8") as f:
    html = f.read()
    soup = BeautifulSoup(html, "html.parser")

# 1. Распечатаем ВСЕ таблицы на странице
tables = soup.find_all("table")
print(f"Всего таблиц на странице: {len(tables)}")
for idx, table in enumerate(tables):
    print(f"\nТаблица {idx} (класс: {table.get('class')}):")
    for r in table.find_all("tr")[:10]: # первые 10 строк
        print("  ", [td.get_text(strip=True) for td in r.find_all(["td", "th"])])

# 2. Ищем упоминания типичных учебных слов или названия предметов
# Попробуем найти любые слова длиной более 4 букв на русском, которые есть в body,
# но исключим пункты меню (типа "Студентам", "Колледж", "Контакты").
body_text = soup.get_text(" ", strip=True)

# Ищем слова, которые могут быть предметами
keywords = ["матем", "физик", "литер", "русск", "информ", "химия", "история", "физра", "физическ", "эконом", "технолог", "черчен", "инженер"]
found_keywords = []
for kw in keywords:
    if re.search(kw, body_text, re.IGNORECASE):
        found_keywords.append(kw)

print("\nНайденные ключевые слова предметов в тексте страницы:")
print(found_keywords)

# Выведем кусок текста вокруг первого найденного ключевого слова
if found_keywords:
    pos = body_text.lower().find(found_keywords[0])
    start = max(0, pos - 100)
    end = min(len(body_text), pos + 200)
    print("\nКонтекст вокруг ключевого слова:")
    print("...", body_text[start:end], "...")
