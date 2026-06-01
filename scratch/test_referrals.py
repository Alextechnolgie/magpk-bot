import sys
import os

# Add parent directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import (
    _get_cache,
    _save,
    update_user_activity,
    get_referred_users_count,
    is_promo_dismissed,
    dismiss_promo,
    can_show_promo_today,
    record_promo_show,
)
from datetime import date, timedelta

print("🧪 Starting Referral System Tests...")

# 1. Clean test environment/cache
cache = _get_cache()
test_user_id = 999999999
test_referrer_id = 888888888

# Remove test users if they exist
if str(test_user_id) in cache:
    del cache[str(test_user_id)]
if str(test_referrer_id) in cache:
    del cache[str(test_referrer_id)]
_save(cache)

# 2. Test initial activity tracking with referrer
print("👉 Registering new user referred by", test_referrer_id)
is_new = update_user_activity(test_user_id, "test_username", "TestFirstName", "TestLastName", test_referrer_id)
assert is_new == True, "Should be a new user"

cache = _get_cache()
user_info = cache.get(str(test_user_id))
assert user_info is not None, "User should be saved"
assert user_info.get("invited_by") == test_referrer_id, f"invited_by should be {test_referrer_id}"

# 3. Test referral count
count = get_referred_users_count(test_referrer_id)
assert count == 1, f"Referrals count for {test_referrer_id} should be 1, got {count}"
print("✅ Referral tracking is working correctly!")

# 4. Test promo limits
promo_id = "test_promo_2026"
print("👉 Testing promo display logic...")
assert is_promo_dismissed(test_user_id, promo_id) == False, "Promo shouldn't be dismissed initially"
assert can_show_promo_today(test_user_id, promo_id) == True, "Promo should be showable today"

# Record promo show
record_promo_show(test_user_id, promo_id)
assert can_show_promo_today(test_user_id, promo_id) == False, "Promo shouldn't be showable again today"

# Manually fake last shown to yesterday to test if it is showable on a different day
cache = _get_cache()
cache[str(test_user_id)]["promos"][promo_id]["last_shown_at"] = (date.today() - timedelta(days=1)).isoformat()
_save(cache)

assert can_show_promo_today(test_user_id, promo_id) == True, "Promo should be showable on a different day"

# Test dismiss promo
dismiss_promo(test_user_id, promo_id)
assert is_promo_dismissed(test_user_id, promo_id) == True, "Promo should be marked dismissed"
assert can_show_promo_today(test_user_id, promo_id) == False, "Promo shouldn't be showable if dismissed"

print("✅ Promo limits and dismiss logic working correctly!")

# Cleanup test users
cache = _get_cache()
if str(test_user_id) in cache:
    del cache[str(test_user_id)]
if str(test_referrer_id) in cache:
    del cache[str(test_referrer_id)]
_save(cache)

print("🎉 All Referral Tests Passed successfully!")
