# SecureVOTE - Release Verification Script (PowerShell)
# Automates local verification across firmware, backend, dashboard, and verifier.
# Does NOT commit, push, or modify source code.

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '        SECUREVOTE v1.0.0 -- LOCAL RELEASE VERIFICATION       ' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan

$Results = [ordered]@{}

# 1. Backend Pytest Suite
Write-Host "`n[1/5] Running Backend Pytest Suite..." -ForegroundColor Yellow
try {
    & "$RepoRoot\backend\venv\Scripts\pytest.exe" "$RepoRoot\backend\tests" -q
    if ($LASTEXITCODE -eq 0) {
        $Results['Backend Pytest (80 tests)'] = 'PASS'
        Write-Host '  -> Backend Pytest PASSED' -ForegroundColor Green
    } else {
        $Results['Backend Pytest (80 tests)'] = 'FAIL'
        Write-Host '  -> Backend Pytest FAILED' -ForegroundColor Red
    }
} catch {
    $Results['Backend Pytest (80 tests)'] = 'ERROR'
    Write-Host "  -> Backend Pytest error: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Firmware Native Unit Tests
Write-Host "`n[2/5] Running Firmware Native Unit Tests (PlatformIO)..." -ForegroundColor Yellow
try {
    $OldPath = $env:PATH
    $env:PATH = "D:\DevTools\ucrt64\bin;$OldPath"
    Push-Location "$RepoRoot\firmware"
    & "$RepoRoot\backend\venv\Scripts\pio.exe" test -e native
    if ($LASTEXITCODE -eq 0) {
        $Results['Firmware Native Tests (17 tests)'] = 'PASS'
        Write-Host '  -> Firmware Native Tests PASSED' -ForegroundColor Green
    } else {
        $Results['Firmware Native Tests (17 tests)'] = 'FAIL'
        Write-Host '  -> Firmware Native Tests FAILED' -ForegroundColor Red
    }
} catch {
    $Results['Firmware Native Tests (17 tests)'] = 'ERROR'
    Write-Host "  -> Firmware Native Tests error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pop-Location
    $env:PATH = $OldPath
}

# 3. Firmware Arduino Uno Target Compilation
Write-Host "`n[3/5] Compiling Firmware for Arduino Uno (ATmega328P)..." -ForegroundColor Yellow
try {
    Push-Location "$RepoRoot\firmware"
    & "$RepoRoot\backend\venv\Scripts\pio.exe" run -e uno
    if ($LASTEXITCODE -eq 0) {
        $Results['Firmware Uno Build (Flash/SRAM)'] = 'SUCCESS'
        Write-Host '  -> Firmware Uno Build SUCCESS' -ForegroundColor Green
    } else {
        $Results['Firmware Uno Build (Flash/SRAM)'] = 'FAIL'
        Write-Host '  -> Firmware Uno Build FAILED' -ForegroundColor Red
    }
} catch {
    $Results['Firmware Uno Build (Flash/SRAM)'] = 'ERROR'
    Write-Host "  -> Firmware Uno Build error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pop-Location
}

# 4. Dashboard Vitest Suite
Write-Host "`n[4/5] Running Dashboard Vitest Suite..." -ForegroundColor Yellow
try {
    Push-Location "$RepoRoot\dashboard"
    & npm.cmd test -- --run
    if ($LASTEXITCODE -eq 0) {
        $Results['Dashboard Tests (14 tests)'] = 'PASS'
        Write-Host '  -> Dashboard Tests PASSED' -ForegroundColor Green
    } else {
        $Results['Dashboard Tests (14 tests)'] = 'FAIL'
        Write-Host '  -> Dashboard Tests FAILED' -ForegroundColor Red
    }
} catch {
    $Results['Dashboard Tests (14 tests)'] = 'ERROR'
    Write-Host "  -> Dashboard Tests error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pop-Location
}

# 5. Dashboard Production Build
Write-Host "`n[5/5] Building Next.js Dashboard..." -ForegroundColor Yellow
try {
    Push-Location "$RepoRoot\dashboard"
    & npm.cmd run build
    if ($LASTEXITCODE -eq 0) {
        $Results['Dashboard Production Build (10 pages)'] = 'SUCCESS'
        Write-Host '  -> Dashboard Production Build SUCCESS' -ForegroundColor Green
    } else {
        $Results['Dashboard Production Build (10 pages)'] = 'FAIL'
        Write-Host '  -> Dashboard Production Build FAILED' -ForegroundColor Red
    }
} catch {
    $Results['Dashboard Production Build (10 pages)'] = 'ERROR'
    Write-Host "  -> Dashboard Production Build error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pop-Location
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host '                 VERIFICATION SUMMARY REPORT                ' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
foreach ($Key in $Results.Keys) {
    $Status = $Results[$Key]
    $Color = if ($Status -in @('PASS', 'SUCCESS')) { 'Green' } else { 'Red' }
    Write-Host "  - $Key : " -NoNewline
    Write-Host "$Status" -ForegroundColor $Color
}
Write-Host "============================================================`n" -ForegroundColor Cyan
