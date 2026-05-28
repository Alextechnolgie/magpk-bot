from bs4 import BeautifulSoup

with open("tm_result.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Ищем селект с группами
select = soup.find("select", {"name": "uch_gr_html"})
if select:
    selected_option = select.find("option", {"selected": True})
    if selected_option:
        print("Выбранная группа в ответе сервера:", selected_option.text)
        print("Атрибут value у неё:", selected_option.get("value"))
    else:
        # Если атрибута selected нет, возможно выбран первый элемент по умолчанию
        print("Ни одна группа не помечена как selected!")
        # Выведем первые 5 опций
        options = select.find_all("option")
        print("Первые 5 опций:")
        for opt in options[:5]:
            print(f"  {opt.text} (selected={opt.has_attr('selected')})")
else:
    print("Селект групп не найден в ответе!")

# Также проверим дату в инпуте
date_input = soup.find("input", {"id": "date_sch"})
if date_input:
    print("Дата в инпуте в ответе сервера:", date_input.get("value"))
