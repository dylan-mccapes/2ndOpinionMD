$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$Modelfile = Join-Path $Root "server\ollama\eoh-llama3.1-8b-lucifer.Modelfile"
Write-Host "Using Modelfile: $Modelfile"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Error "ollama not found in PATH"
}
Set-Location $Root
ollama create eoh-llama-lucifer -f $Modelfile
Write-Host "Created model: eoh-llama-lucifer"
ollama list
