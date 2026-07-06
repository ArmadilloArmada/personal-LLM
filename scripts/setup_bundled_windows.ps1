# Download llama.cpp + bundled GGUF models into dist/Persona/_internal/llama
param(
    [string]$DestRoot = "dist\Persona\_internal\llama",
    [string]$LlamaRelease = "b9861"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null
$modelsDir = Join-Path $DestRoot "models"
New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null

Write-Host "Downloading llama.cpp Windows CPU binaries..."
$llamaZip = Join-Path $env:TEMP "llama-win-cpu.zip"
$extractTmp = Join-Path $env:TEMP "llama-extract"
$llamaUrl = "https://github.com/ggml-org/llama.cpp/releases/download/$LlamaRelease/llama-$LlamaRelease-bin-win-cpu-x64.zip"
Invoke-WebRequest -Uri $llamaUrl -OutFile $llamaZip
if (Test-Path $extractTmp) { Remove-Item $extractTmp -Recurse -Force }
Expand-Archive -Path $llamaZip -DestinationPath $extractTmp -Force

$server = Get-ChildItem -Path $extractTmp -Filter "llama-server.exe" -Recurse | Select-Object -First 1
if (-not $server) { throw "llama-server.exe not found in archive" }
Copy-Item $server.FullName -Destination (Join-Path $DestRoot "llama-server.exe") -Force
Get-ChildItem $server.Directory -Filter "*.dll" -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item $_.FullName -Destination $DestRoot -Force
}

Write-Host "Downloading Fast model (Qwen2.5 0.5B)..."
$fastUrl = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
$fastDest = Join-Path $modelsDir "fast.gguf"
Invoke-WebRequest -Uri $fastUrl -OutFile $fastDest

Write-Host "Downloading Balanced model (Llama 3.2 1B)..."
$balancedUrl = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
$balancedDest = Join-Path $modelsDir "balanced.gguf"
Invoke-WebRequest -Uri $balancedUrl -OutFile $balancedDest

if (-not (Test-Path (Join-Path $DestRoot "llama-server.exe"))) {
    throw "llama-server.exe not found after setup"
}
if (-not (Test-Path $fastDest)) { throw "fast.gguf missing" }
if (-not (Test-Path $balancedDest)) { throw "balanced.gguf missing" }

Write-Host "Bundled LLM setup complete:"
Get-ChildItem $DestRoot -Recurse | Select-Object FullName, Length
