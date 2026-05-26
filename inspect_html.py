from bs4 import BeautifulSoup

with open("tm_result.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Ищем форму расписания
form = soup.find("select", {"name": "uch_gr_html"}).find_parent("form")

# Выведем весь HTML-код, который идет ПОСЛЕ формы до конца родительского контейнера
print("--- HTML после формы ---")
sibling = form.next_sibling
count = 0
while sibling and count < 10:
    if sibling.name:
        print(f"Тег: {sibling.name}, Класс: {sibling.get('class')}")
        # Если это таблица, выведем её полностью
        if sibling.name == "table" or sibling.find("table"):
            t = sibling if sibling.name == "table" else sibling.find("table")
            print("Содержимое таблицы:")
            for row in t.find_all("tr"):
                print("  ", [td.get_text(strip=True) for td in row.find_all(["td", "th"])])
        else:
            print("  Текст:", sibling.get_text(" ", strip=True)[:200])
        print("-" * 30)
        count += 1
    sibling = sibling.next_sibling
