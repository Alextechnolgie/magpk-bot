from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("tm_result.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Ищем элемент, содержащий текст "Понедельник (25.05.2026)"
target = soup.find(string=lambda text: text and "Понедельник (25.05.2026)" in text)

if target:
    parent = target.parent
    print(f"Родительский тег: {parent.name}, Класс: {parent.get('class')}")
    
    # Выведем 10 родительских уровней вверх, чтобы понять структуру
    curr = parent
    for i in range(5):
        curr = curr.parent
        print(f"Уровень {i+1} вверх: тег={curr.name}, класс={curr.get('class')}, id={curr.get('id')}")
        
    # Выведем HTML-код вокруг этого блока (родительский элемент 3 уровня вверх)
    grandparent = parent.parent.parent
    print("\n--- HTML код расписания ---")
    print(grandparent.prettify()[:1500])
else:
    print("Текст 'Понедельник (25.05.2026)' не найден в HTML!")
