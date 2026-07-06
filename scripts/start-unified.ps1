# Start unified Persona + Big Brain (dev). Stops old Persona.exe on port 8765 first.
param(
    [switch]$WithVite
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "Stopping old Persona processes on port 8765..."
Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-Process -Name "Persona" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Set-Location $Root

if (-not (Test-Path "$Root\big-brain\client\dist\index.html")) {
    Write-Host "Building Big Brain (first time)..."
    npm run build --prefix big-brain
}

$py = $null
foreach ($c in @("py -3", "python3", "python")) {
    try {
        & $c.Split(" ")[0] $c.Split(" ")[1..99] -c "import sys; print(sys.version)" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $py = $c; break }
    } catch {}
}
if (-not $py) {
    Write-Error "Python not found. Install Python 3.12+ then run: pip install -e persona-app[desktop]"
}

Write-Host "Installing Persona package (editable)..."
& $py.Split(" ")[0] @($py.Split(" ")[1..99]) -m pip install -e "$Root\persona-app[desktop]" -q

Write-Host ""
Write-Host "Starting unified app..."
Write-Host "  Persona + Brain: http://127.0.0.1:8765"
Write-Host "  Brain tab should appear as first button: Brain | Solo | Group | Project | Board"
Write-Host "  Press Ctrl+C to stop"
Write-Host ""

if ($WithVite) {
    npm run dev:all
} else {
    npm run dev
}
