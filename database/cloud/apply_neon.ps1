# Applies the Cinema schema + runtime role + demo seed to the Neon database (Windows PowerShell).
# Needs Docker Desktop (uses the postgres:18 image for psql). Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File database\cloud\apply_neon.ps1
# Prompts for the Neon owner password (hidden). cinema_api password = DB_PASSWORD from .env.
param(
  [string]$NeonHost = 'ep-green-dream-bic8gxu9.c-5.ap-southeast-1.aws.neon.tech',
  [string]$NeonUser = 'neondb_owner',
  [string]$NeonDb   = 'cinema_test_demo',
  [switch]$Demo
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$dbPassword = (Get-Content "$root\.env" | Where-Object { $_ -match '^DB_PASSWORD=' } | Select-Object -First 1) -replace '^DB_PASSWORD=', ''
if (-not $dbPassword) { throw 'DB_PASSWORD is missing in .env' }
$sec = Read-Host 'Neon owner password' -AsSecureString
$ownerPw = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))

function Invoke-Psql([string[]]$PsqlArgs, [string]$Workdir = '/work') {
  docker run --rm -v "${root}:/work" -w $Workdir -e PGPASSWORD=$ownerPw -e PGSSLMODE=require `
    -e PGHOST=$NeonHost -e PGUSER=$NeonUser -e PGDATABASE=$NeonDb `
    postgres:18 psql -X -v ON_ERROR_STOP=1 @PsqlArgs
  if ($LASTEXITCODE -ne 0) { throw "psql failed: $PsqlArgs" }
}

if ($Demo) {
  foreach ($f in 'main.sql','exceptions.sql','permissions_grants.sql') {
    Write-Host "=== demo/$f ==="
    Invoke-Psql @('-f', $f) '/work/database/demo'
  }
  return
}

Invoke-Psql @('-c', 'SELECT version()')
Invoke-Psql @('-f', 'backend/migrations/0001_baseline.sql')
Invoke-Psql @('-v', "runtime_password=$dbPassword", '-f', 'database/cloud/setup_neon.sql')
foreach ($m in '0003_booking_integrity','0004_finite_money','0005_username_case_insensitive','0006_username_validation') {
  Invoke-Psql @('-f', "backend/migrations/$m.sql")
}
Invoke-Psql @('-f', 'backend/seeds/demo.sql')
Invoke-Psql @('-Atc', "SELECT 'movies='||count(*) FROM movies")
Write-Host 'Neon setup complete.'
