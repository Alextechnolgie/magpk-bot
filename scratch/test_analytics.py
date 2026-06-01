import sys
import os
import json

# Add parent directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import (
    ACTIVITY_LOG_FILE,
    log_activity,
    get_activity_stats,
    generate_users_report,
)
from datetime import datetime, timedelta

print("🧪 Starting Activity Analytics Tests...")

# 1. Backup existing activity.log if it exists
backup_path = ACTIVITY_LOG_FILE + ".testbackup"
if os.path.exists(ACTIVITY_LOG_FILE):
    if os.path.exists(backup_path):
        os.remove(backup_path)
    os.rename(ACTIVITY_LOG_FILE, backup_path)
    print("👉 Backed up existing activity.log")

try:
    # 2. Log mock activities
    print("👉 Generating mock activities...")
    test_user_id = 777777777
    
    # We will manually write mock log records with various timestamps to simulate different times/days
    now = datetime.now()
    
    mock_records = [
        # Today
        {"user_id": test_user_id, "time": now.strftime("%Y-%m-%d %H:%M:%S"), "action": "/today"},
        {"user_id": test_user_id, "time": (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"), "action": "/today"},
        {"user_id": test_user_id, "time": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), "action": "/tomorrow"},
        # 3 days ago at 10 AM
        {"user_id": test_user_id, "time": (now - timedelta(days=3)).replace(hour=10, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"), "action": "/week"},
        {"user_id": 999999, "time": (now - timedelta(days=3)).replace(hour=10, minute=15, second=0).strftime("%Y-%m-%d %H:%M:%S"), "action": "/week"},
        # 5 days ago at 14 PM
        {"user_id": test_user_id, "time": (now - timedelta(days=5)).replace(hour=14, minute=30, second=0).strftime("%Y-%m-%d %H:%M:%S"), "action": "cb:toggle_interface"},
    ]
    
    with open(ACTIVITY_LOG_FILE, "w", encoding="utf-8") as f:
        for rec in mock_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            
    # 3. Test stats compilation
    print("👉 Compiling stats report...")
    stats = get_activity_stats()
    print("📊 Generated report:\n")
    print(stats)
    print("\n---------------------------")
    
    assert "DAU" in stats, "Stats should contain DAU"
    assert "WAU" in stats, "Stats should contain WAU"
    assert "Пиковое время" in stats, "Stats should contain peak time info"
    print("✅ Activity stats report parsed successfully!")
    
    # 4. Test Excel report generation
    print("👉 Generating Excel users report (multi-sheet)...")
    report_file = generate_users_report()
    assert os.path.exists(report_file), "Excel report file should be created"
    assert os.path.getsize(report_file) > 0, "Excel report file should not be empty"
    print("✅ Excel report generated successfully at", report_file)
    
    # Clean up generated Excel report
    try:
        os.remove(report_file)
    except OSError:
        pass

finally:
    # Cleanup activity.log
    if os.path.exists(ACTIVITY_LOG_FILE):
        os.remove(ACTIVITY_LOG_FILE)
        
    # Restore backup
    if os.path.exists(backup_path):
        os.rename(backup_path, ACTIVITY_LOG_FILE)
        print("👉 Restored original activity.log")

print("🎉 All Analytics Tests Passed successfully!")
