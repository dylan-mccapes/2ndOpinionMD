#Requires -Version 5.1
<#
.SYNOPSIS
  Install pilot Postgres + pgvector in WSL from the cloned repo (-InstallFromRepo), stage scp'd scripts (-Install), or restore MKG (-Restore).

.DESCRIPTION
  When you `scp file dylan@WINDOWS_HOST:~/` the file lands under C:\Users\dylan\ (OpenSSH), NOT inside WSL.
  Your WSL default user may differ from Windows (e.g. hilarious_marcupial); `~` in WSL is that user's home.

  From Mac, use a Windows path for scp only if you run scp *from* Windows with a valid path, e.g.:
    scp C:\Users\dylan\portalnode4090_install_postgres.sh dylan@192.168.0.245:C:\Users\dylan\
  Or keep using the Mac and `scp ... dylan@HOST:~/` then run -StageInstallFromWindowsProfile -Install here.

.EXAMPLE
  # Same machine: repo on C:\ (any path); no scp — runs scripts/portalnode4090_install_postgres.sh inside WSL
  cd C:\2OPMD\2ndOpinionMD-MVP\scripts
  .\portalnode4090_wsl.ps1 -InstallFromRepo -WslDistro Ubuntu

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
    # Run scripts/portalnode4090_install_postgres.sh from this repo clone (no scp to ~/).
    [switch]$InstallFromRepo,
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

if ($InstallFromRepo) {
    $installWin = Join-Path -Path $PSScriptRoot -ChildPath "portalnode4090_install_postgres.sh"
    if (-not (Test-Path -LiteralPath $installWin)) {
        Write-Error "Not found: $installWin"
        exit 1
    }
    $installUnix = (wsl -d $WslDistro -- wslpath -u ((Resolve-Path -LiteralPath $installWin).Path)).Trim()
    Write-Host "Installing Postgres + pgvector in WSL ($WslDistro) from repo: $installUnix"
    Invoke-WslBash "sudo bash '$installUnix'"
    exit 0
}

if ($Install) {
    Write-Host "Installing Postgres + pgvector in WSL ($WslDistro) using: $InstallScriptWsl"
    wsl -d $WslDistro -- bash -lc "test -f '$InstallScriptWsl'"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Script missing in WSL: $InstallScriptWsl`nRun -InstallFromRepo (same clone on /mnt/c/...), or -StageInstallFromWindowsProfile (after scp from Mac to Windows OpenSSH home)."
        exit 1
    }
    Invoke-WslBash "sudo bash '$InstallScriptWsl'"
    exit 0
}

if ($Restore) {
    if ([string]::IsNullOrWhiteSpace($RestoreScriptWsl)) {
        $restoreWin = Join-Path -Path $PSScriptRoot -ChildPath "portalnode4090_restore_mkg.sh"
        if (Test-Path -LiteralPath $restoreWin) {
            $RestoreScriptWsl = (wsl -d $WslDistro -- wslpath -u ((Resolve-Path -LiteralPath $restoreWin).Path)).Trim()
        }
        else {
            # Typical Windows clone: C:\Users\<win>\2ndOpinionMD-MVP
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
    }
    Write-Host "Restoring from $DumpDirWsl using $RestoreScriptWsl"
    # TCP localhost: SCRAM when WSL login ≠ portalnode — pass PGPASSWORD from Windows env (any chars) via base64.
    $pwPrefix = ""
    if (-not [string]::IsNullOrWhiteSpace($env:PGPASSWORD)) {
        $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:PGPASSWORD))
        # Single-quoted so PowerShell does not treat $( as a subexpression; bash runs command substitution.
        $pwPrefix = 'export PGPASSWORD=$(printf %s ''' + $b64 + ''' | base64 -d); '
    }
    $inner = "${pwPrefix}export DUMP_DIR='$DumpDirWsl' PGHOST=127.0.0.1 PGPORT=5432 PGUSER=portalnode PGDATABASE=portalnode && bash '$RestoreScriptWsl'"
    Invoke-WslBash $inner
    exit 0
}

Write-Host @"
No action. Use one of:
  -InstallFromRepo          (same machine: Postgres from this repo under $PSScriptRoot)
  -StageInstallFromWindowsProfile -Install   (after scp install script to Windows profile)
  -Restore

Why `~/portalnode4090_install_postgres.sh` was missing in WSL:
  - scp to dylan@WINDOWS:~/ puts the file in C:\Users\dylan\ (OpenSSH home), not in \\wsl$\...\home\...
  - `wsl ... bash -lc ""...""` uses your WSL default user ($resolvedUser); ~ is $wslHome

Quick fix (manual copy):
  wsl -d Ubuntu -- cp /mnt/c/Users/dylan/portalnode4090_install_postgres.sh ~/
  wsl -d Ubuntu -- chmod +x ~/portalnode4090_install_postgres.sh
  wsl -d Ubuntu -- bash -lc "sudo bash ~/portalnode4090_install_postgres.sh"

Same Windows machine, repo already cloned (e.g. C:\2OPMD\2ndOpinionMD-MVP):
  cd <repo>\scripts
  .\portalnode4090_wsl.ps1 -InstallFromRepo -WslDistro Ubuntu

One command (after scp from Mac to ~/):
  .\portalnode4090_wsl.ps1 -StageInstallFromWindowsProfile -Install -WslDistro Ubuntu

scp from Windows PowerShell (paths are Windows-style):
  scp C:\Users\dylan\portalnode4090_install_postgres.sh dylan@192.168.0.245:C:\Users\dylan\

Restore (set Windows env PGPASSWORD first if portalnode uses SCRAM; defaults restore script path under /mnt/c/...):
  `$env:PGPASSWORD = '…'; .\portalnode4090_wsl.ps1 -Restore -WslDistro Ubuntu -DumpDirWsl '/mnt/c/Users/dylan/forward_pilot_dump/forward_pilot_dump_20260424T205758Z'

From WSL bash (repo on /mnt/c; omit DUMP_DIR to auto-find 05b under `$HOME/forward_pilot_dump or /mnt/c/Users/*/forward_pilot_dump):
  cd /mnt/c/Users/dylan/2ndOpinionMD-MVP && git pull
  export PGUSER=portalnode PGDATABASE=portalnode PGPASSWORD='…'
  ./scripts/portalnode4090_restore_mkg.sh
"@
