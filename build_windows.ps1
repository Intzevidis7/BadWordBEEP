$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$required = 'app.py','censor_engine.py','models_setup.py','bad_words.txt','requirements-build.txt','README.md','installer.iss'
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath $name)) { throw "Missing $name beside build_windows.ps1" }
}
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
    else { throw 'Python not found. Install Python for Windows first.' }
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& $python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$voskDir = & $python -c "import importlib.util, pathlib; spec=importlib.util.find_spec('vosk'); print(pathlib.Path(spec.origin).parent if spec and spec.origin else '')"
if ($LASTEXITCODE -ne 0 -or -not $voskDir -or -not (Test-Path -LiteralPath $voskDir)) {
    throw 'Cannot find Vosk in the build virtual environment.'
}
$voskDll = Join-Path $voskDir 'libvosk.dll'
if (-not (Test-Path -LiteralPath $voskDll)) { throw "Missing Vosk DLL: $voskDll" }
Write-Host "Bundling Vosk DLL: $voskDll"
& $python -m PyInstaller --clean --noconfirm --onedir --windowed --name BadWordBeep --add-binary "${voskDll}:vosk" app.py
if ($LASTEXITCODE -ne 0) { throw 'GUI build failed.' }
$bundledDll = Join-Path $PSScriptRoot 'dist\BadWordBeep\_internal\vosk\libvosk.dll'
if (-not (Test-Path -LiteralPath $bundledDll)) { throw "Bundled DLL not found: $bundledDll" }
Write-Host "Verified bundled DLL: $bundledDll"
& $python -m PyInstaller --clean --noconfirm --onefile --console --name BadWordBeep-Models models_setup.py
if ($LASTEXITCODE -ne 0) { throw 'Model downloader build failed.' }
Copy-Item -LiteralPath 'dist\BadWordBeep-Models.exe' -Destination 'dist\BadWordBeep\BadWordBeep-Models.exe' -Force
Copy-Item -LiteralPath 'bad_words.txt' -Destination 'dist\BadWordBeep\bad_words.txt' -Force
$compilerPath = $null
$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($compiler) { $compilerPath = $compiler.Source }
if (-not $compilerPath) {
    $roots = @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)
    foreach ($root in $roots) {
        if (-not $root) { continue }
        foreach ($suffix in @('Inno Setup 6\ISCC.exe','Inno Setup 7\ISCC.exe','Programs\Inno Setup 6\ISCC.exe','Programs\Inno Setup 7\ISCC.exe')) {
            $candidate = Join-Path $root $suffix
            if (Test-Path -LiteralPath $candidate) { $compilerPath = $candidate; break }
        }
        if ($compilerPath) { break }
    }
}
if (-not $compilerPath) { throw 'Inno Setup ISCC.exe not found. Install Inno Setup 6 or 7.' }
Write-Host "Compiling installer with $compilerPath"
& $compilerPath 'installer.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compile failed.' }
Write-Host 'Complete: release\BadWordBeep-Setup.exe and dist\BadWordBeep\BadWordBeep.exe'
