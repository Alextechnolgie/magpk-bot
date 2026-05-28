from bs4 import BeautifulSoup

with open("test_post.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

form = soup.find("form")
if form:
    print("Action формы:", form.get("action"))
    print("Method формы:", form.get("method"))
    inputs = form.find_all(["input", "select"])
    print("Поля формы:")
    for inp in inputs:
        print(f"  Name: {inp.get('name')}, Type: {inp.get('type')}, Value: {inp.get('value')}")
else:
    print("Форма не найдена!")
