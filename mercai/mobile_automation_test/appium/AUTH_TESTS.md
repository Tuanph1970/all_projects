# Appium authentication suite

Appium port of the Maestro auth scripts. No Metro, no ADB text-input hack — it
drives the **release APK**, which embeds its own JS bundle.

## Run it

```bash
# Prerequisites, all already satisfied on this machine:
#   emulator booted        adb devices  -> emulator-5554
#   Appium server running  curl -s localhost:4723/status
#   uiautomator2 driver    appium driver list --installed
#   app installed          adb shell pm list packages | grep mercai

cd mobile_automation_test/appium
python3 -m pytest tests/test_auth.py -v          # all of it
python3 -m pytest tests/test_auth.py -v -k login # just the login cases
python3 -m pytest -m auth -v                     # by marker
```

Failures screenshot to `mobile_automation_test/screenshots/appium/`.

## What is covered

| Case | Test | Migrated from |
|---|---|---|
| AUTH-001 | `test_auth_001_customer_login_succeeds` | `fast-customer-login-test.sh` |
| AUTH-002 | `test_auth_002_seller_login_succeeds` | `fast-seller-login-test.sh` |
| AUTH-003 | `test_auth_003_invalid_password_is_rejected` | `fast-auth-invalid-password-test.sh` |
| AUTH-004 | `test_auth_004_nonexistent_user_is_rejected` | `fast-auth-nonexistent-user-test.sh` |
| AUTH-005 | `test_auth_005_empty_fields_blocked` ×3 | `fast-auth-empty-fields-test.sh` |
| AUTH-006 | `test_auth_006_007_registration_returns_to_login[customer]` | `fast-auth-customer-registration-test.sh` |
| AUTH-007 | `test_auth_006_007_registration_returns_to_login[seller]` | `fast-auth-seller-registration-test.sh` |
| AUTH-009 | `test_auth_009_logout_returns_to_login` ×2 | `fast-auth-logout-test.sh` |

**AUTH-008 does not exist** — the old numbering skips it. Nothing was dropped.

11 test cases from 8 scripts (3481 lines of bash → ~200 lines of Python).

## Four bugs found in the Maestro scripts while porting

1. **Logout used one testID for both roles.** The scripts tap `logout-button`
   for customer and seller alike, but that ID only exists on
   `SellerProfileScreen`. The customer's is `profile-logout-button`. The
   customer logout assertion could not have been passing.
2. **Error assertions were English regexes** (`.*[Ii]nvalid.*`,
   `.*[Ss]uccess.*`) against a UI that defaults to **Vietnamese**
   (`LanguageContext.jsx:45` → `LANGUAGES.VI`). They could never match.
3. **Dead selectors.** `register-phone-input` and `register-shop-name-input`
   are referenced but no such fields exist — registration posts
   `phone_number: null` and has no shop-name field at all.
4. **`username-input` / `password-input` / `email-input`** are referenced
   alongside the real `login-*` / `register-*` IDs. Only the prefixed ones
   exist.

## Design decisions worth keeping

**Rejected logins assert "still on the login screen", not the error text.**
Login failure surfaces as a `react-native-toast-message` Toast, which is
transient — by the time Appium walks the accessibility tree it may be gone.
Staying on the login screen is the durable consequence. Each negative test
*also* asserts the app shell was not reached, so "stayed put" cannot pass for
the wrong reason.

**`logged_out_driver` runs `adb shell pm clear` before each test.** `NO_RESET`
is true because the APK is ~120MB and reinstalling per test is unaffordable —
but that means the app otherwise starts signed in from the previous test, and
every login test becomes a no-op that passes without logging in. `pm clear`
wipes AsyncStorage (the persisted token) in well under a second without
touching the install. It also resets the stored language to the vi default the
text locators assume.

**The role radio is tapped by label, not testID.**
`register-role-customer` / `-seller` sit on plain `<View>` wrappers around a
paper `<RadioButton>`; the radio owns its own press handler, so tapping the
wrapper does not reliably toggle it. The testIDs are used to *scroll* to the
control and the tap goes to the visible label.

## Test accounts

Created on production 2026-09-07, deliberately holding no products — auth does
not need a catalogue, and bare accounts keep this suite independent of the seed.

| Username | Password | Role |
|---|---|---|
| `e2e_customer` | `E2eTest@2026` | customer |
| `e2e_seller` | `E2eTest@2026` | seller |

`gomthuha` and the other seeded sellers are **not** on production — they come
from `back_end/scripts/seed_catalogue.py` and exist only on a seeded local
stack. The price-intelligence tests need them; these tests do not.

## Two things to know before changing the target backend

**The backend is fixed at APK build time**, in
`front_end/src/constants/config.js` (`ENVIRONMENT`). Setting `BACKEND_URL`
only affects API calls made from the test process — it does **not** repoint the
app. To test against a different backend, edit that constant and rebuild:

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
cd front_end && npm run build:android     # or: cd android && ./gradlew assembleRelease
adb install -r android/app/build/outputs/apk/release/app-release.apk
```

Verify what a built APK actually points at, rather than trusting the source:

```bash
unzip -p app-release.apk assets/index.android.bundle | strings \
  | grep -oE '[a-z0-9.-]*tuan1970\.com' | sort -u
```

**Registration tests leave real users behind.** There is no delete-account step,
so each run of AUTH-006/007 adds two rows to the live database. They are
prefixed `e2e_tmp_` for cleanup:

```sql
DELETE FROM users WHERE username LIKE 'e2e_tmp_%';
```
