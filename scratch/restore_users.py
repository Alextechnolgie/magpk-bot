import sys
import os
import openpyxl
from datetime import datetime

# Add parent directory to path so we can import config/database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def parse_date(val):
    if not val or val == "-":
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(str(val), "%Y-%m-%d")
        except ValueError:
            return None

def main():
    if len(sys.argv) < 2:
        print("❌ Использование: python scratch/restore_users.py <DATABASE_URL>")
        sys.exit(1)
        
    db_url = sys.argv[1]
    
    excel_path = "c:/Users/alexi/Downloads/Telegram Desktop/users_report (3).xlsx"
    if not os.path.exists(excel_path):
        print(f"❌ Файл отчета не найден по пути: {excel_path}")
        sys.exit(1)
        
    print(f"📖 Чтение файла: {excel_path}...")
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    
    users = []
    # Начинаем с 5-й строки (после заголовков)
    for r in range(5, ws.max_row + 1):
        row_vals = [cell.value for cell in ws[r]]
        # Проверяем, что ID пользователя не пустой
        uid_val = row_vals[0]
        if not uid_val:
            continue
            
        try:
            uid = int(uid_val)
        except ValueError:
            continue
            
        group = row_vals[1]
        
        username = row_vals[2]
        if username == "-":
            username = None
        elif username and username.startswith("@"):
            username = username[1:]
            
        name = row_vals[3]
        first_name = None
        last_name = None
        if name and name != "Пользователь":
            parts = name.split(None, 1)
            first_name = parts[0]
            if len(parts) > 1:
                last_name = parts[1]
                
        joined_at = parse_date(row_vals[4])
        last_seen = parse_date(row_vals[5])
        
        # Получаем ID пригласившего и рефералов из отчета
        invited_by = None
        if len(row_vals) > 6 and row_vals[6] and row_vals[6] != "-":
            try:
                invited_by = int(row_vals[6])
            except ValueError:
                pass
                
        users.append((uid, group, username, first_name, last_name, joined_at, last_seen, invited_by))
        
    print(f"👥 Считано {len(users)} пользователей из отчета.")
    
    # Подключение к PostgreSQL
    print("🔌 Подключение к базе данных PostgreSQL...")
    import psycopg2
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Инициализация таблиц на всякий случай
        print("🛠 Проверка структуры таблиц...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                group_name VARCHAR(50),
                username VARCHAR(100),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                interface VARCHAR(20) DEFAULT 'full',
                joined_at TIMESTAMP,
                last_seen TIMESTAMP,
                invited_by BIGINT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS promos (
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                promo_id VARCHAR(100),
                dismissed BOOLEAN DEFAULT FALSE,
                last_shown_at DATE,
                PRIMARY KEY (user_id, promo_id)
            );
        """)
        
        print("📥 Запись пользователей в базу данных...")
        success = 0
        for user in users:
            uid, group, username, first_name, last_name, joined_at, last_seen, invited_by = user
            try:
                # Вставляем или обновляем пользователя
                cur.execute("""
                    INSERT INTO users (user_id, group_name, username, first_name, last_name, joined_at, last_seen, invited_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        group_name = COALESCE(users.group_name, EXCLUDED.group_name),
                        username = COALESCE(users.username, EXCLUDED.username),
                        first_name = COALESCE(users.first_name, EXCLUDED.first_name),
                        last_name = COALESCE(users.last_name, EXCLUDED.last_name),
                        joined_at = COALESCE(users.joined_at, EXCLUDED.joined_at),
                        last_seen = GREATEST(users.last_seen, EXCLUDED.last_seen);
                """, (uid, group, username, first_name, last_name, joined_at, last_seen, invited_by))
                success += 1
            except Exception as e:
                print(f"❌ Ошибка вставки {uid}: {e}")
                
        conn.commit()
        print(f"🎉 Восстановление завершено! Успешно перенесено: {success} из {len(users)} пользователей.")
        
    except Exception as e:
        print(f"❌ Ошибка подключения или запроса к базе данных: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
