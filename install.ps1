$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/cjy5507/csmh.git"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$CsmhHome = Join-Path $CodexHome "csmh"
$SkillsDir = Join-Path $CodexHome "skills"
$BinDir = Join-Path $CodexHome "bin"
$UserBinDir = Join-Path $env:USERPROFILE ".local\bin"

function Write-Step($msg) {
  Write-Host "[csmh] $msg"
}

function Resolve-Source {
  if ((Test-Path (Join-Path $ScriptDir "scripts\csmh")) -and (Test-Path (Join-Path $ScriptDir "skills"))) {
    return $ScriptDir
  }

  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is required to install from remote source."
  }

  $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("csmh-" + [guid]::NewGuid().ToString())
  Write-Step "cloning $RepoUrl"
  git clone --depth 1 $RepoUrl $tmp | Out-Null
  return $tmp
}

$source = Resolve-Source

Write-Step "install target: $CodexHome"
New-Item -ItemType Directory -Force -Path $CsmhHome | Out-Null
New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path $UserBinDir | Out-Null

Write-Step "installing runtime"
Copy-Item -Force (Join-Path $source "scripts\csmh-orchestrator.py") (Join-Path $CsmhHome "csmh-orchestrator.py")
Copy-Item -Force (Join-Path $source "scripts\csmh-verify.sh") (Join-Path $CsmhHome "csmh-verify.sh")
Copy-Item -Force (Join-Path $source "scripts\csmh.py") (Join-Path $CsmhHome "csmh.py")
Copy-Item -Force (Join-Path $source "VERSION") (Join-Path $CsmhHome "VERSION")

Write-Step "installing templates"
New-Item -ItemType Directory -Force -Path (Join-Path $CsmhHome "templates") | Out-Null
Copy-Item -Force (Join-Path $source "templates\*.json") (Join-Path $CsmhHome "templates")

Write-Step "installing skills"
Get-ChildItem (Join-Path $source "skills") -Directory | ForEach-Object {
  $target = Join-Path $SkillsDir $_.Name
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  Copy-Item -Recurse -Force (Join-Path $_.FullName "*") $target
}

Write-Step "installing csmh command"
$psWrapper = @'
param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $Args)
python "{CSMH_HOME}\csmh.py" @Args
'@.Replace("{CSMH_HOME}", $CsmhHome)

$psWrapper | Set-Content -Path (Join-Path $BinDir "csmh.ps1") -Encoding UTF8
$psWrapper | Set-Content -Path (Join-Path $UserBinDir "csmh.ps1") -Encoding UTF8

$cmdWrapper = "@echo off`r`npowershell -ExecutionPolicy Bypass -File ""$UserBinDir\csmh.ps1"" %*`r`n"
$cmdWrapper | Set-Content -Path (Join-Path $UserBinDir "csmh.cmd") -Encoding ASCII

Write-Step "done"
Write-Host "- command (PowerShell): $(Join-Path $UserBinDir 'csmh.ps1')"
Write-Host "- command (cmd): $(Join-Path $UserBinDir 'csmh.cmd')"
Write-Host "- skills: $SkillsDir\csmh-*"
Write-Host "- runtime: $CsmhHome"
Write-Host ""
Write-Host "quick check:"
Write-Host "  csmh version"
Write-Host "  csmh init"
Write-Host "  csmh verify parallel"
