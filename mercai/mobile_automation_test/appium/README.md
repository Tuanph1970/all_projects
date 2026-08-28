# Mercai mobile E2E — Appium

Ported from the Appium harness in `mathematic-mobile/front-end/mobile_automation_test/appium`,
which is the pattern followed throughout: pytest + Page Objects + a per-test
driver fixture that screenshots on failure. Maestro flows still live in
`../maestro/`; this suite exists alongside them, not instead of them.

## What this layer is for

| Layer | Asserts | Needs a device |
|---|---|---|
| `front_end` jest (9) | the right components render with the right text | no |
| `../__tests__/api` (46) | the numbers are right | no |
| **this suite (10)** | **the pixels are right** | **yes** |
| `base/layout.py` unit tests (19) | the assertions themselves are correct | no |

The middle two cannot fail on layout. jest mocks React Native's native layer,
so nothing is ever measured, positioned or drawn — a scale overflowing its
card, a button under the navigation bar, or a truncated Vietnamese product name
all pass there and hit the user on first launch.

## Running

```bash
pip install -r requirements.txt
cp .env.example .env          # then edit

# 1. an emulator
~/Android/Sdk/emulator/emulator -avd Pixel_3a_API_36_extension_level_17_x86_64 &
adb wait-for-device

# 2. an Appium server
appium &

# 3. the tests
pytest tests/test_price_position_layout.py -v
```

The helper unit tests need none of that:

```bash
pytest tests/test_layout_helpers.py -q
```

## The prerequisite that is not yet met

**There is no mercai APK.** `front_end` is an Expo *managed* project — no
`android/` directory — so nothing is installable on a device yet:

```bash
cd front_end
npx expo prebuild -p android      # generates android/, one time
cd android && ./gradlew assembleDebug
# then set APK_PATH in .env to app/build/outputs/apk/debug/app-debug.apk
```

That writes a large `android/` tree into the repo and is a deliberate decision,
not a side effect of running tests — which is why it has not been done.

Java 17 is required and is present at `/usr/lib/jvm/java-17-openjdk-amd64`,
though `java` on `PATH` is 11. `JAVA_HOME` is already set correctly.

## Fixtures these tests assume

* the seeded catalogue — `back_end/scripts/seed_catalogue.py`
* `INTEL_PRICE_ENABLED=true`, or the price-insights control is hidden by design
  and `open_price_insights` fails with a message saying so
* `SEEDED_PRODUCT_ID = 2` — `SEED-BAT-002`, owned by `gomthuha` at 185,000₫,
  chosen because it is the seeded listing with a real price history

## Locator strategy

Inherited from the mathematic-mobile harness, and not obvious:

> React Native exposes a `TextInput`'s `testID` as an Android `resource-id`,
> but plain `Text` and most composed `Pressable`s do **not** reliably do so.

So inputs are addressed by `resource-id` and section headings by visible text.
If a locator stops matching after a component library upgrade, dump the tree
with `driver.page_source` before assuming the screen changed.
