<#
.SYNOPSIS
    Launch script for Codex Desktop App using Ollama + local model
    Project: D:\CHIPTUNEPALACE
.DESCRIPTION
    This script:
    1. Ensures the project folder exists
    2. Checks that Ollama is installed and running
    3. Lets you select or download a base model
    4. Verifies AGENTS.md exists for project instructions
    5. Launches Codex Desktop App connected to Ollama via OpenAI-compatible API
#>

# --- 0. Close any running Codex instances ---
Write-Host "[*] Closing any active Codex instances..." -ForegroundColor Cyan
$processes = Get-Process | Where-Object { $_.ProcessName -like "*codex*" }
if ($processes) {
    $processes | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "[+] Instances terminated." -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "[+] No active instances found." -ForegroundColor Gray
}

# --- Configuration ---
$ProjectPath = "D:\CHIPTUNEPALACE"
$BaseModel   = $null
$AgentsFile  = Join-Path $ProjectPath "AGENTS.md"

# --- 0.5 Verify Codex CLI is available ---
Write-Host "[*] Checking for Codex CLI..." -ForegroundColor Cyan
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Codex CLI not found. Installing via npm..." -ForegroundColor Yellow
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Host "[-] npm is not available. Please install Node.js first." -ForegroundColor Red
        exit 1
    }
    npm install -g @openai/codex
    $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# --- 1. Basic requirements ---
if (-not (Test-Path $ProjectPath)) {
    Write-Host "[-] Error: Project path not found: $ProjectPath" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "[-] Error: 'ollama' not found. Install Ollama v0.24.0+ first." -ForegroundColor Red
    exit 1
}

# --- 2. Ensure Ollama server is running ---
Write-Host "[*] Checking Ollama server..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3 | Out-Null
    Write-Host "[+] Ollama is running." -ForegroundColor Green
} catch {
    Write-Host "[!] Ollama not responding. Starting server..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
    Write-Host "[*] Waiting for Ollama (10 seconds)..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}

# --- 2.5 Model selection ---
Write-Host "[*] Fetching available Ollama models..." -ForegroundColor Cyan
$ollamaList = ollama list
$availableModels = $ollamaList | Select-Object -Skip 1 | ForEach-Object { ($_ -split '\s+')[0] } | Where-Object { $_ }

if ($availableModels.Count -eq 0) {
    Write-Host "[!] No models found locally." -ForegroundColor Yellow
    Write-Host "Choose an option:" -ForegroundColor Magenta
    Write-Host " [Q] Download Qwen 2.5 Coder 14B (qwen2.5-coder:14b)" -ForegroundColor Blue
    Write-Host " [G] Download Gemma 4 (gemma4:e4b)" -ForegroundColor Green
    $choice = Read-Host "`nEnter Q or G (default Q)"
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "Q" }
} else {
    Write-Host "`nSelect base model for the agent:" -ForegroundColor Magenta
    for ($i = 0; $i -lt $availableModels.Count; $i++) {
        $color = if ($availableModels[$i] -match "gemma") { "Green" } elseif ($availableModels[$i] -match "qwen") { "Blue" } else { "Gray" }
        Write-Host " [$($i+1)] " -NoNewline -ForegroundColor Cyan
        Write-Host $availableModels[$i] -ForegroundColor $color
    }
    Write-Host " [Q] " -NoNewline -ForegroundColor Cyan; Write-Host "Download Qwen 2.5 Coder 14B" -ForegroundColor Blue
    Write-Host " [G] " -NoNewline -ForegroundColor Cyan; Write-Host "Download Gemma 4" -ForegroundColor Green
    $choice = Read-Host "`nEnter number, Q, or G (Enter = first model)"
}

# Process selection
if ($choice -match "^\d+$" -and $availableModels.Count -gt 0) {
    $idx = [int]$choice - 1
    if ($idx -ge 0 -and $idx -lt $availableModels.Count) {
        $BaseModel = $availableModels[$idx]
    } else {
        $BaseModel = $availableModels[0]
    }
} elseif ($choice -eq "Q" -or $choice -eq "q") {
    $BaseModel = "qwen2.5-coder:14b"
} elseif ($choice -eq "G" -or $choice -eq "g") {
    $BaseModel = "gemma4:e4b"
} else {
    $BaseModel = $availableModels[0]
}

Write-Host "[+] Base model selected: $BaseModel" -ForegroundColor Green

# --- Ensure base model exists ---
if ($ollamaList -notmatch [regex]::Escape($BaseModel)) {
    Write-Host "[!] Model not found locally. Downloading $BaseModel ..." -ForegroundColor Yellow
    ollama pull $BaseModel
}

# --- Verify AGENTS.md ---
Write-Host "[*] Checking for project instructions..." -ForegroundColor Cyan
if (-not (Test-Path $AgentsFile)) {
    Write-Host "[!] AGENTS.md not found in $ProjectPath" -ForegroundColor Yellow
    Write-Host "    Create it to provide project-specific rules and context to the LLM." -ForegroundColor Gray
} else {
    Write-Host "[+] AGENTS.md found. Will be used for project context." -ForegroundColor Green
}

# --- Set environment variables for Codex ---
Write-Host "[*] Configuring environment variables for Codex..." -ForegroundColor Cyan
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_API_KEY  = "ollama"
$env:CODEX_MODEL     = $BaseModel
# Optional: Control Ollama context window globally (adjust based on VRAM)
# $env:OLLAMA_NUM_CTX  = "32768"

# --- Launch Codex ---
Set-Location $ProjectPath

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Magenta
Write-Host "         CODEX AGENT LAUNCHER - CHIPTUNE PALACE"        -ForegroundColor Magenta
Write-Host "=========================================================" -ForegroundColor Magenta
Write-Host " Model        : $BaseModel"
Write-Host " Project      : $ProjectPath"
Write-Host " Instructions : $AgentsFile"
Write-Host " API Endpoint : $env:OPENAI_BASE_URL"
Write-Host "========================================================="
Write-Host ""

Write-Host "[>] Launching Codex Desktop App..." -ForegroundColor Gray
codex app

Write-Host ""
Write-Host "[OK] Session complete."
Write-Host ""