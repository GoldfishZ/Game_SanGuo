param(
    [string]$Python = "python"
)

# Windows PowerShell 5 treats native stderr output as PowerShell errors when
# Stop is used. PyInstaller writes normal progress logs to stderr, so rely on
# the native process exit code instead.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$entry = Join-Path $root "desktop_launcher.py"
$dist = Join-Path $root "dist"
$work = Join-Path $root "build"
$staticData = (Join-Path $root "src\web\static") + ";src\web\static"
$generalData = (Join-Path $root "assets\images\generals_webp") + ";assets\images\generals_webp"
$backgroundData = (Join-Path $root "assets\images\backgrounds_webp") + ";assets\images\backgrounds_webp"
$modelData = (Join-Path $root "assets\models\pve") + ";assets\models\pve"
$releaseReadme = Join-Path $root "docs\release-readme-windows.txt"

Push-Location $root
try {
    & $Python -m PyInstaller --version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is not installed. Run: python -m pip install -r requirements/build.txt"
    }

    $pyiArgs = @(
        "--noconfirm",
        "--clean",
        "--onedir",
        "--console",
        "--name", "Game_SanGuo",
        "--distpath", $dist,
        "--workpath", $work,
        "--specpath", $work,
        "--exclude-module", "pygame",
        "--exclude-module", "pytest",
        "--add-data", $staticData,
        "--add-data", $generalData,
        "--add-data", $backgroundData,
        "--add-data", $modelData,
        $entry
    )

    Write-Host "Building the Windows self-contained folder release..." -ForegroundColor Cyan
    & $Python -m PyInstaller @pyiArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    $bundle = Join-Path $dist "Game_SanGuo"
    $exe = Join-Path $bundle "Game_SanGuo.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Build completed but the executable was not found: $exe"
    }

    Write-Host "Running the packaged executable smoke test..." -ForegroundColor Cyan
    & $exe --smoke-test
    if ($LASTEXITCODE -ne 0) {
        throw "Packaged executable smoke test failed with exit code $LASTEXITCODE"
    }

    Copy-Item -LiteralPath $releaseReadme -Destination (Join-Path $bundle "游玩说明.txt") -Force
    $zip = Join-Path $dist "Game_SanGuo_Windows.zip"
    Compress-Archive -Path (Join-Path $bundle "*") -DestinationPath $zip -Force
    $size = [math]::Round(
        (Get-ChildItem -LiteralPath $bundle -Recurse -File |
            Measure-Object -Property Length -Sum).Sum / 1MB,
        1
    )
    $zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath (Join-Path $dist "Game_SanGuo_Windows.sha256") `
        -Value "$zipHash  Game_SanGuo_Windows.zip" -Encoding Ascii
    Write-Host "Build complete: $bundle ($size MiB)" -ForegroundColor Green
    Write-Host "Share this archive: $zip" -ForegroundColor Green
    Write-Host "SHA-256: $zipHash" -ForegroundColor Green
}
finally {
    Pop-Location
}
