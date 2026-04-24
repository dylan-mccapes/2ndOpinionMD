<#!
Launch the PTV chatbot from **PowerShell on Windows** (Ollama on the same machine → 127.0.0.1).

Usage (from repo root or anywhere):

  cd C:\2OPMD\2ndOpinionMD-MVP
  .\server\scripts\ptv_chatbot.ps1

With options:

  .\server\scripts\ptv_chatbot.ps1 -Verbose
  .\server\scripts\ptv_chatbot.ps1 -Graph "C:\path\to\graph.json" -Model "eoh-llama-lucifer"

Advanced flags (max-turns, transcript, etc.): call Python directly:

  python .\server\scripts\ptv_chatbot_wsl.py --graph ... --max-turns 10
#>
param(
    [string] $Graph = "",
    [string] $Model = "eoh-llama-lucifer",
    [string] $OllamaUrl = "http://127.0.0.1:11434",
    [switch] $Verbose,
    [switch] $SkipOllamaProbe
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PyScript = Join-Path $RepoRoot "server\scripts\ptv_chatbot_wsl.py"

if (-not (Test-Path -LiteralPath $PyScript)) {
    Write-Error "Missing $PyScript"
    exit 1
}

if (-not $Graph) {
    $Graph = Join-Path $RepoRoot "artifacts\forward_kaleb_package_20260423\PTV_REAL_EHR_20260423.json"
}
elseif (-not [System.IO.Path]::IsPathRooted($Graph)) {
    $Graph = Join-Path $RepoRoot $Graph
}

if (-not (Test-Path -LiteralPath $Graph)) {
    Write-Error "Graph not found: $Graph"
    exit 1
}

$GraphFull = (Resolve-Path -LiteralPath $Graph).Path

$argv = @(
    $PyScript,
    "--graph", $GraphFull,
    "--model", $Model,
    "--ollama-url", $OllamaUrl
)
if ($Verbose) { $argv += "--verbose" }
if ($SkipOllamaProbe) { $argv += "--skip-ollama-probe" }

Set-Location -LiteralPath $RepoRoot
Write-Host "[ptv-chat.ps1] repo: $RepoRoot" -ForegroundColor DarkGray
& python @argv
