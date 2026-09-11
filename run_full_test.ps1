Write-Host "=== STARTING FULL RUN TEST ON ANDROID DEVICE ==="

# 1. Start screen recording for 30 seconds in background
$recordProc = Start-Process -FilePath "adb" -ArgumentList "shell", "screenrecord", "--time-limit", "30", "--size", "720x1600", "--bit-rate", "4M", "/sdcard/full_run_test.mp4" -PassThru

Start-Sleep -Seconds 1

# 2. Cold launch SpellScroll
Write-Host "[1/7] Cold launching app..."
adb shell am force-stop com.spellscroll.app
adb shell am start -n com.spellscroll.app/.MainActivity
Start-Sleep -Seconds 3

# 3. Open Detail modal from Feed
Write-Host "[2/7] Opening webtoon detail modal on Feed..."
adb shell input tap 360 600
Start-Sleep -Seconds 2

# Dismiss modal
adb shell input keyevent 4
Start-Sleep -Milliseconds 600

# 4. Interact with Feed actions (Reading, Skip, Complete)
Write-Host "[3/7] Testing Feed action cards (Reading, Skip, Complete)..."
adb shell input tap 360 1150
Start-Sleep -Seconds 1
adb shell input tap 230 1150
Start-Sleep -Seconds 1
adb shell input tap 490 1150
Start-Sleep -Seconds 1

# 5. Switch to Archive tab
Write-Host "[4/7] Navigating to Archive tab..."
adb shell input tap 360 1530
Start-Sleep -Seconds 2

# 6. Test Live Search
Write-Host "[5/7] Testing live filter search for 'Solo'..."
adb shell input tap 360 150
Start-Sleep -Milliseconds 600
adb shell input text "Solo"
Start-Sleep -Seconds 2

# Dismiss keyboard and tap card
adb shell input keyevent 111
Start-Sleep -Milliseconds 500
adb shell input tap 200 450
Start-Sleep -Seconds 2

# Dismiss modal
adb shell input keyevent 4
Start-Sleep -Milliseconds 600

# Clear search text
adb shell input tap 360 150
Start-Sleep -Milliseconds 300
adb shell input keyevent 123  # MOVE_END
for ($i=0; $i -lt 8; $i++) {
    adb shell input keyevent 67  # DEL
}
adb shell input keyevent 111
Start-Sleep -Seconds 1

# Scroll catalogue grid
adb shell input swipe 360 1100 360 400 300
Start-Sleep -Seconds 1

# 7. Switch to Sanctum tab and test connection
Write-Host "[6/7] Testing Sanctum settings and Wi-Fi connection..."
adb shell input tap 600 1530
Start-Sleep -Seconds 1
adb shell input tap 215 465  # Wi-Fi preset
Start-Sleep -Milliseconds 500
adb shell input tap 520 465  # Apply
Start-Sleep -Seconds 2

# Return to Feed tab
Write-Host "[7/7] Returning to Feed tab..."
adb shell input tap 120 1530
Start-Sleep -Seconds 2

# Wait for recording to finalize
Write-Host "Waiting for screenrecord to finish..."
$recordProc.WaitForExit(10000)

Write-Host "Pulling video recording from phone..."
adb pull /sdcard/full_run_test.mp4 .full_run_test.mp4

Write-Host "=== FULL RUN TEST COMPLETE ==="
