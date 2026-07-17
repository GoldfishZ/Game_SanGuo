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

Push-Location $root
try {
    & $Python -m PyInstaller --version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is not installed. Run: python -m pip install -r requirements/build.txt"
    }

    $pyiArgs = @(
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name", "Game_SanGuo",
        "--distpath", $dist,
        "--workpath", $work,
        "--specpath", $work,
        "--exclude-module", "pygame",
        "--exclude-module", "numpy",
        "--exclude-module", "pytest",
        "--add-data", $staticData,
        "--add-data", $generalData,
        "--add-data", $backgroundData,
        $entry
    )

    Write-Host "Building the Windows single-file release..." -ForegroundColor Cyan
    & $Python -m PyInstaller @pyiArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    $exe = Join-Path $dist "Game_SanGuo.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Build completed but the executable was not found: $exe"
    }

    Write-Host "Running the packaged executable smoke test..." -ForegroundColor Cyan
    & $exe --smoke-test
    if ($LASTEXITCODE -ne 0) {
        throw "Packaged executable smoke test failed with exit code $LASTEXITCODE"
    }

    $zip = Join-Path $dist "Game_SanGuo_Windows.zip"
    Compress-Archive -LiteralPath $exe -DestinationPath $zip -Force
    $size = [math]::Round((Get-Item -LiteralPath $exe).Length / 1MB, 1)
    Write-Host "Build complete: $exe ($size MiB)" -ForegroundColor Green
    Write-Host "Share this archive: $zip" -ForegroundColor Green
}
finally {
    Pop-Location
}
