@echo off
cd /d "%~dp0"

if not exist "_internal\" (
  echo.
  echo ERROR: The _internal folder is missing next to Persona.exe.
  echo Unzip the ENTIRE Persona-Windows-portable.zip folder and run from there.
  echo Do not move Persona.exe out of the folder by itself.
  echo.
  pause
  exit /b 1
)

echo Starting Persona...
Persona.exe
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% neq 0 (
  echo.
  echo Persona exited with error code %EXITCODE%.
)

if exist "%USERPROFILE%\.persona\error.log" (
  echo.
  echo --- error.log ---
  type "%USERPROFILE%\.persona\error.log"
)

if exist "%USERPROFILE%\.persona\startup.log" (
  echo.
  echo --- startup.log ---
  type "%USERPROFILE%\.persona\startup.log"
)

if %EXITCODE% neq 0 (
  echo.
  pause
)
