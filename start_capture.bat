@echo off
cd /d E:\GitHubProjects\SpellScroll
mkdir recordings 2>nul
echo Starting ffmpeg capture...
start "FFMPEG" /B ffmpeg -f gdigrab -framerate 30 -i desktop -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p recordings\raw_capture.mp4
timeout /t 3 /nobreak >nul
echo Done.
