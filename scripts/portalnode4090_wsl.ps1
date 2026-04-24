#Requires -Version 5.1
<#
.SYNOPSIS
  Stage install script from Windows OpenSSH home into WSL, then install Postgres + pgvector — or restore MKG.

.DESCRIPTION
  When you `scp file dylan@WINDOWS_HOST:~/` the file lands under C:\Users\dylan\ (OpenSSH), NOT inside WSL.
  Your WSL default user may differ from Windows (e.g. hilarious_marcupial); `~` in WSL is that user's home.

  From Mac, use a Windows path for scp only if you run scp *from* Windows with a valid path, e.g.:
    scp C:\Users\dylan\portalnode4090_install_postgres.sh dylan@192.168.0.245:C:\Users\dylan\
  Or keep using the Mac and `scp ... dylan@HOST:~/` then run -StageInstallFromWindowsProfile -Install here.

.EXAMPLE
  # After Mac: scp ... dylan@192.168.0.245:~/   (file is now C:\Users\dylan\portalnode4090_install_postgres.sh)
  cd ~\2ndOpinionMD-MVP\scripts   # typical: C:\Users\dylan\2ndOpinionMD-MVP → /mnt/c/Users/dylan/2ndOpinionMD-MVP
  .\portalnode4090_wsl.ps1 -StageInstallFromWindowsProfile -Install -WslDistro Ubuntu

.EXAMPLE
  .\portalnode4090_wsl.ps1 -Restore -WslDistro Ubuntu
#>

param(
    [string]$WslDistro = "Ubuntu",
    [string]$WslUser = "",
    [switch]$Install,
    [switch]$Restore,
    [string]$DumpDirWsl = "",
    [string]$InstallScriptWsl = "",
    [string]$RestoreScriptWsl = "",
    [switch]$StageInstallFromWindowsProfile
)

function Invoke-WslBash {
    param([Parameter(Mandatory)][string]$Command)
    $wsl = "wsl.exe"
    if (-not (Get-Command $wsl -ErrorAction SilentlyContinue)) {
        Write-Error "wsl.exe not found. Install WSL2: wsl --install -d Ubuntu"
        exit 1
    }
    & $wsl -d $WslDistro -- bash -lc $Command
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Get-WslWhoami {
    (wsl -d $WslDistro -- bash -lc 'whoami').Trim()
}

function Get-WslHome {
    (wsl -d $WslDistro -- bash -lc 'echo -n $HOME').Trim()
}

$resolvedUser = if ($WslUser) { $WslUser } else { Get-WslWhoami }
$wslHome = Get-WslHome
if ([string]::IsNullOrWhiteSpace($DumpDirWsl)) {
    $DumpDirWsl = "$wslHome/forward_pilot_dump"
}
if ([string]::IsNullOrWhiteSpace($InstallScriptWsl)) {
    $InstallScriptWsl = "$wslHome/portalnode4090_install_postgres.sh"
}

if ($StageInstallFromWindowsProfile) {
    $winFile = Join-Path -Path $env:USERPROFILE -ChildPath "portalnode4090_install_postgres.sh"
    if (-not (Test-Path -LiteralPath $winFile)) {
        Write-Error "Not found: $winFile`nAfter scp from Mac to dylan@HOST:~/, the file should be here. Copy it to your Windows profile or fix the path."
        exit 1
    }
    $winUnix = (wsl -d $WslDistro -- wslpath -u "$winFile").Trim()
    Write-Host "Staging: $winFile  ->  WSL $InstallScriptWsl (user=$resolvedUser, HOME=$wslHome)"
    Invoke-WslBash "cp -f '$winUnix' '$InstallScriptWsl' && chmod +x '$InstallScriptWsl'"
    Write-Host "Staged OK."
}

if ($Install) {
    Write-Host "Installing Postgres + pgvector in WSL ($WslDistro) using: $InstallScriptWsl"
    wsl -d $WslDistro -- bash -lc "test -f '$InstallScriptWsl'"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Script missing in WSL: $InstallScriptWsl`nRun -StageInstallFromWindowsProfile first (after scp from Mac to Windows OpenSSH home)."
        exit 1
    }
    Invoke-WslBash "sudo bash '$InstallScriptWsl'"
    exit 0
}

if ($Restore) {
    if ([string]::IsNullOrWhiteSpace($RestoreScriptWsl)) {
        # Typical Windows clone: C:\Users\<win>\2ndOpinionMD-MVP (see /mnt/c/Users/dylan/2ndOpinionMD-MVP in WSL)
        $repoScriptsOnDrv = "/mnt/c/Users/$($env:USERNAME)/2ndOpinionMD-MVP/scripts/portalnode4090_restore_mkg.sh"
        $repoScriptsInHome = "$wslHome/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/scripts/portalnode4090_restore_mkg.sh"
        wsl -d $WslDistro -- bash -lc "test -f '$repoScriptsOnDrv'" | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $RestoreScriptWsl = $repoScriptsOnDrv
        }
        else {
            wsl -d $WslDistro -- bash -lc "test -f '$repoScriptsInHome'" | Out-Null
            if ($LASTEXITCODE -eq 0) { $RestoreScriptWsl = $repoScriptsInHome }
            else { $RestoreScriptWsl = $repoScriptsOnDrv }
        }
    }
    Write-Host "Restoring from $DumpDirWsl using $RestoreScriptWsl"
    # TCP localhost: peer auth on Unix socket fails when WSL login ≠ portalnode
    $inner = "export DUMP_DIR='$DumpDirWsl' PGHOST=127.0.0.1 PGPORT=5432 PGUSER=portalnode PGDATABASE=portalnode && bash '$RestoreScriptWsl'"
    Invoke-WslBash $inner
    exit 0
}

Write-Host @"
No action. Use -StageInstallFromWindowsProfile and/or -Install, or -Restore.

Why `~/portalnode4090_install_postgres.sh` was missing in WSL:
  - scp to dylan@WINDOWS:~/ puts the file in C:\Users\dylan\ (OpenSSH home), not in \\wsl$\...\home\...
  - `wsl ... bash -lc ""...""` uses your WSL default user ($resolvedUser); ~ is $wslHome

Quick fix (manual copy):
  wsl -d Ubuntu -- cp /mnt/c/Users/dylan/portalnode4090_install_postgres.sh ~/
  wsl -d Ubuntu -- chmod +x ~/portalnode4090_install_postgres.sh
  wsl -d Ubuntu -- bash -lc "sudo bash ~/portalnode4090_install_postgres.sh"

One command (after scp from Mac to ~/):
  .\portalnode4090_wsl.ps1 -StageInstallFromWindowsProfile -Install -WslDistro Ubuntu

scp from Windows PowerShell (paths are Windows-style):
  scp C:\Users\dylan\portalnode4090_install_postgres.sh dylan@192.168.0.245:C:\Users\dylan\

Restore (defaults to /mnt/c/Users/<WindowsUser>/2ndOpinionMD-MVP/scripts/... if present):
  .\portalnode4090_wsl.ps1 -Restore -WslDistro Ubuntu -DumpDirWsl $DumpDirWsl

From an Ubuntu shell (repo on C: drive — your layout):
  cd /mnt/c/Users/dylan/2ndOpinionMD-MVP
  export DUMP_DIR=`$HOME/forward_pilot_dump
  export PGHOST=/var/run/postgresql PGUSER=portalnode PGDATABASE=portalnode
  export PGPASSWORD='...'
  ./scripts/portalnode4090_restore_mkg.sh
"@
