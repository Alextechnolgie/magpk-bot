import urllib.request
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
req = urllib.request.Request("https://magpk.ru/studentu/raspisanie-zanyatij", headers=headers)

with urllib.request.urlopen(req) as r:
    html = r.read().decode("utf-8")

soup = BeautifulSoup(html, "html.parser")

# Ищем форму, содержащую селект uch_gr_html
select = soup.find("select", {"name": "uch_gr_html"})
if select:
    form = select.find_parent("form")
    print("Найдена форма расписания!")
    print("Action:", form.get("action"))
    inputs = form.find_all("input")
    for inp in inputs:
        print(f"Имя поля: {inp.get('name')}, Тип: {inp.get('type')}, Значение: {inp.get('value')}")
else:
    print("Форма расписания не найдена на странице!")
