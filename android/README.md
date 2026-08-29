# Time Card — Android tablet app

Native Kotlin app for a Lenovo tablet with a Precision Pen. This is step 1 of the
build: a single Activity hosting one full-screen custom `View` that paints a solid
background. No ink handling yet.

## What's here

```
android/
├── app/src/main/
│   ├── java/com/ptgreening/timecard/
│   │   ├── MainActivity.kt     hosts the canvas, goes edge-to-edge full screen
│   │   └── CanvasView.kt       custom View; onDraw fills a solid background
│   ├── res/values/             strings, colors, theme (AppCompat, no action bar)
│   ├── res/drawable + mipmap/  adaptive launcher icon (vector, no PNGs)
│   └── AndroidManifest.xml
├── gradle/libs.versions.toml   version catalog
└── gradlew                     Gradle 8.9 wrapper
```

| | |
|---|---|
| Application ID | `com.ptgreening.timecard` |
| minSdk | 31 (Android 12) |
| targetSdk / compileSdk | 35 |
| AGP / Kotlin / Gradle | 8.7.3 / 2.0.21 / 8.9 |
| JDK | 17 (bundled with Android Studio) |

`minSdk 31` covers the recent Lenovo Tab P and Y series that ship with a Precision Pen.

## Build and install

### Android Studio

1. **File → Open**, select the `android/` directory (not the repo root).
2. Let it sync. It will write `local.properties` with your `sdk.dir` — that file is
   gitignored and machine-specific, so don't commit it.
3. If prompted, install SDK Platform 35 and Build-Tools 35.
4. Pick your tablet from the device dropdown and hit **Run**.

### Command line

```bash
cd android
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Or in one step with the device attached: `./gradlew :app:installDebug`

### Enabling USB debugging on the tablet

1. **Settings → About tablet**, tap **Build number** seven times.
2. **Settings → System → Developer options → USB debugging**, turn it on.
3. Plug in over USB, and accept the "Allow USB debugging?" RSA prompt on the tablet.
4. Confirm the host sees it: `adb devices` should list the tablet as `device`
   (not `unauthorized` — that means the prompt wasn't accepted).

If `adb devices` is empty on Linux, you likely need a udev rule for Lenovo's vendor
ID (`17ef`). On Windows, install Lenovo's USB driver.

## What this app does right now

Launches to a full-screen off-white canvas with the system bars hidden. Swiping from
an edge brings the bars back transiently; focus returning re-hides them. That's all —
it is deliberately a blank sheet.

## Next steps

Stylus input lands in `CanvasView`: override `onTouchEvent`, filter on
`MotionEvent.getToolType() == TOOL_TYPE_STYLUS`, and read pressure, tilt, orientation
and the historical points in each batched event.
