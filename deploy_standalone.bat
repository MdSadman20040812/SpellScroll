@echo off
echo =======================================================
echo   SpellScroll Standalone On-Device Edition Installer
echo =======================================================
echo.
echo Waiting for device connection via ADB...
adb wait-for-device
echo Device connected!
echo.
echo Installing SpellScroll Standalone (2.26 MB)...
adb install -r "android\app\build\outputs\apk\release\SpellScroll-v1.0-release.apk"
if %errorlevel% neq 0 (
    echo.
    echo Installation failed, attempting debug APK...
    adb install -r "android\app\build\outputs\apk\debug\SpellScroll-v1.0-debug.apk"
)
echo.
echo Launching SpellScroll Standalone on phone...
adb shell am force-stop com.spellscroll.app
adb shell am start -n com.spellscroll.app/.MainActivity
echo.
echo =======================================================
echo   DONE! SpellScroll is now running standalone on device!
echo =======================================================
pause
