import sys
import os
import json

# Add parent directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 1. Setup local environment
# Ensure DATABASE_URL is not set for local SQLite test
if "DATABASE_URL" in os.environ:
    del os.environ["DATABASE_URL"]

# Setup users.json fallback mockup
mock_users = {
    "1111": {
        "group": "АСУ9-25",
        "username": "tester1",
        "first_name": "Test1",
        "last_name": "User1",
        "joined_at": "2026-06-01 10:00:00",
        "last_seen": "2026-06-01 10:05:00",
        "interface": "compact"
    },
    "2222": {
        "group": "АТ9-23",
        "username": "tester2",
        "first_name": "Test2",
        "last_name": "User2",
        "joined_at": "2026-06-01 11:00:00",
        "last_seen": "2026-06-01 11:15:00",
        "invited_by": 1111,
        "promos": {
            "referral_june_2026": {
                "dismissed": True,
                "last_shown_at": "2026-06-01"
            }
        }
    }
}

json_file = "users.json"
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(mock_users, f, ensure_ascii=False)

# Delete existing SQLite users.db if any to test fresh start
sqlite_db = "users.db"
if os.path.exists(sqlite_db):
    os.remove(sqlite_db)

# Now import database which triggers init_db and migrate_json_to_db
import database

print("🧪 Starting Database SQL Migration Tests...")

# Validate migration
print("👉 Checking if users were successfully migrated...")
assert os.path.exists(sqlite_db), "SQLite DB users.db should be created"

group1 = database.get_user_group(1111)
assert group1 == "АСУ9-25", f"User 1111 group should be АСУ9-25, got {group1}"

group2 = database.get_user_group(2222)
assert group2 == "АТ9-23", f"User 2222 group should be АТ9-23, got {group2}"

interface1 = database.get_user_interface(1111)
assert interface1 == "compact", f"User 1111 interface should be compact, got {interface1}"

ref_count = database.get_referred_users_count(1111)
assert ref_count == 1, f"User 1111 referral count should be 1, got {ref_count}"

dismissed = database.is_promo_dismissed(2222, "referral_june_2026")
assert dismissed == True, "User 2222 promo should be dismissed"

can_show = database.can_show_promo_today(2222, "referral_june_2026")
assert can_show == False, "User 2222 shouldn't show promo today since it's dismissed"

print("✅ Data migration and basic reading verified!")

# Validate updates and conflict resolution
print("👉 Checking updates (set_user_group, set_user_interface, update_user_activity)...")
database.set_user_group(1111, "АТ9-23")
assert database.get_user_group(1111) == "АТ9-23", "Group should be updated to АТ9-23"

database.set_user_interface(1111, "full")
assert database.get_user_interface(1111) == "full", "Interface should be updated to full"

# Register new user with referral
is_new = database.update_user_activity(3333, "tester3", "Test3", "User3", 1111)
assert is_new == True, "User 3333 should be new"
assert database.get_user_group(3333) is None, "New user group should be None"

ref_count = database.get_referred_users_count(1111)
assert ref_count == 2, f"User 1111 referral count should be 2, got {ref_count}"

# Update activity of existing user
is_new = database.update_user_activity(1111, "tester1_new", "Test1_N", "User1_N")
assert is_new == False, "User 1111 should not be new"

print("✅ User updates and CRUD verified!")

# Validate logging and stats
print("👉 Checking activity logging and reporting...")
database.log_activity(1111, "/today")
database.log_activity(2222, "/week")
database.log_activity(3333, "cb:toggle_interface")

stats_report = database.get_activity_stats()
assert "DAU" in stats_report, "Report should contain DAU"
assert "WAU" in stats_report, "Report should contain WAU"

admin_stats = database.get_admin_stats()
assert "Всего пользователей: *3*" in admin_stats, f"Should have 3 users in admin stats, got: {admin_stats}"

excel_report = database.generate_users_report()
assert os.path.exists(excel_report), "Excel report should be generated"
assert os.path.getsize(excel_report) > 0, "Excel report should not be empty"

# Cleanup
try:
    os.remove(excel_report)
except OSError:
    pass

if os.path.exists(sqlite_db):
    os.remove(sqlite_db)
    
if os.path.exists("users.json.migrated"):
    os.remove("users.json.migrated")

print("🎉 All SQL Database and Migration Tests Passed successfully!")
