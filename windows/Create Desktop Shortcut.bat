@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Persona.lnk'); $sc.TargetPath = '%~dp0Persona.exe'; $sc.WorkingDirectory = '%~dp0'; $sc.Description = 'Persona AI agents'; $sc.Save()"
echo Desktop shortcut created.
