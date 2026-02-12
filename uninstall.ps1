$ErrorActionPreference = "Stop"

$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$CsmhHome = Join-Path $CodexHome "csmh"
$SkillsDir = Join-Path $CodexHome "skills"
$BinDir = Join-Path $CodexHome "bin"
$UserBinDir = Join-Path $env:USERPROFILE ".local\bin"

if (Test-Path $CsmhHome) { Remove-Item -Recurse -Force $CsmhHome }
Get-ChildItem $SkillsDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "csmh-*" } | ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
Remove-Item -Force (Join-Path $BinDir "csmh.ps1") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $UserBinDir "csmh.ps1") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $UserBinDir "csmh.cmd") -ErrorAction SilentlyContinue

Write-Host "csmh uninstalled from $CodexHome"
