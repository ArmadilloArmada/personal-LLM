@echo off
cd /d "%~dp0"
echo Starting Persona...
start "" "%~dp0Persona.exe"
timeout /t 8 /nobreak >nul
curl.exe -s -o NUL -w "%%{http_code}" http://127.0.0.1:8765/api/health | findstr 200 >nul
if errorlevel 1 (
  echo.
  echo Persona did not respond on port 8765.
  echo Check %%USERPROFILE%%\.persona\startup.log
  echo.
  pause
) else (
  echo Persona is running. If no window appeared, open http://127.0.0.1:8765 in your browser.
)
