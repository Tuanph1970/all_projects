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
| **this suite (10, passing)** | **the pixels are right** | **yes** |
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

## Building the app — use the RELEASE build, not debug

`front_end` is an Expo *managed* project, so `android/` is generated (and
gitignored). One time:

```bash
cd front_end
npx expo prebuild -p android
cd android && ./gradlew assembleRelease
adb install -r app/build/outputs/apk/release/app-release.apk
```

**Release, not debug, and the reason matters.** A debug APK embeds no JS
bundle: it fetches one from a Metro dev server at runtime. That makes the whole
suite depend on Metro staying up and on hot-reload not breaking, and it failed
exactly that way here — a redbox reading
`TypeError: Cannot read property 'level' of undefined` on the second app
launch, with the first launch working fine. Release embeds the bundle, so the
app is self-contained and every run starts from the same bytes. It is also
half the size (115MB vs 218MB).

Release signs with the debug keystore already (see `android/app/build.gradle`),
so no keystore setup is needed.

### Two things generated `android/` needs

`android/local.properties` — `sdk.dir=$HOME/Android/Sdk`.

`android/build.gradle` — an `ext { supportLibVersion = "1.7.0" }` block.
Without it the build fails with `Duplicate class android.support.v4.*`:
`react-native-push-notification` picks between AndroidX and the legacy support
library by parsing `supportLibVersion`, which defaults to `"27.1.1"` — and 27
fails its own `< 20` test, so it pulls `com.android.support:appcompat-v7`
alongside `androidx.core`. Naming an AndroidX version makes its existing logic
choose correctly.

**Both edits live in a gitignored directory and are lost on the next
`expo prebuild`.** Making them durable means an Expo config plugin or
patch-package; that has not been done.

Java 17 is required and is at `/usr/lib/jvm/java-17-openjdk-amd64`, though
`java` on `PATH` is 11. `JAVA_HOME` is already set correctly.

## Status: 10/10 passing

Run 2026-08-28 on `Pixel_3a_API_36_extension_level_17_x86_64` against the live
backend at `https://mercai.tuan1970.com`. It found one real bug — see
below.

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

## What it caught

**The edit button was 40.0dp tall, below Android's 48dp minimum tap target.**
That is react-native-paper's default `Button` height, and `AddProductScreen`,
`CheckoutScreen` and `CartScreen` all already set `contentStyle={{ height: 48 }}`
explicitly — the new screen just didn't. Invisible to the eye, invisible to
jest (which measures nothing), and a real accessibility defect. Fixed, and the
same fix applied to the add-comparable button.

## A subtlety worth knowing before writing more of these

**Android reports element bounds clipped to the viewport.** A control scrolled
half into view measures as a fraction of its true height: the 48dp button, once
fixed, still failed at "31px" because the test measured it with only its top
edge on screen. `scroll_until_present` is therefore not enough for any geometry
assertion — use `scroll_until_fully_visible`, which scrolls until the element's
box is entirely inside the screen. Scrolling to a section *heading* has the same
problem: the controls beneath it are still off-screen, and Android omits
off-screen views from the accessibility tree entirely, so they read as "element
not found" rather than "not scrolled to yet".
