$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$required = 'app.py','censor_engine.py','keyword_audio_detector.py','models_setup.py','bad_words.txt','bad_words_el.txt','bad_words_en.txt','bad_words_greeklish.txt','requirements-build.txt','README.md','installer.iss','app.ico'
foreach ($name in $required) { if (-not (Test-Path -LiteralPath $name)) { throw "Missing $name beside build_windows.ps1" } }
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
if ($LASTEXITCODE -ne 0 -or -not $voskDir -or -not (Test-Path -LiteralPath $voskDir)) { throw 'Cannot find Vosk in the build virtual environment.' }
$voskDll = Join-Path $voskDir 'libvosk.dll'
if (-not (Test-Path -LiteralPath $voskDll)) { throw "Missing Vosk DLL: $voskDll" }
Write-Host "Bundling Vosk DLL: $voskDll"
& $python -m PyInstaller --clean --noconfirm --onedir --windowed --name BadWordBeep --icon "$PSScriptRoot\app.ico" --add-binary "${voskDll}:vosk" --hidden-import keyword_audio_detector --collect-all torch --collect-all transformers app.py
if ($LASTEXITCODE -ne 0) { throw 'GUI build failed.' }
$bundledDll = Join-Path $PSScriptRoot 'dist\BadWordBeep\_internal\vosk\libvosk.dll'
if (-not (Test-Path -LiteralPath $bundledDll)) { throw "Bundled DLL not found: $bundledDll" }
& $python -m PyInstaller --clean --noconfirm --onefile --console --name BadWordBeep-Models --icon "$PSScriptRoot\app.ico" models_setup.py
if ($LASTEXITCODE -ne 0) { throw 'Model downloader build failed.' }
Copy-Item -LiteralPath 'dist\BadWordBeep-Models.exe' -Destination 'dist\BadWordBeep\BadWordBeep-Models.exe' -Force
foreach ($wordList in 'bad_words.txt','bad_words_el.txt','bad_words_en.txt','bad_words_greeklish.txt') { Copy-Item -LiteralPath $wordList -Destination (Join-Path 'dist\BadWordBeep' $wordList) -Force }
$v4Checkpoint = Join-Path $PSScriptRoot 'keyword_lab\runs\wordfocused_xlsr_v4_context\model.pt'
if (-not (Test-Path -LiteralPath $v4Checkpoint)) { throw "Missing trained v4 checkpoint: $v4Checkpoint" }
$aiModelDir = Join-Path $PSScriptRoot 'dist\BadWordBeep\models\keyword_v4'
New-Item -ItemType Directory -Force -Path $aiModelDir | Out-Null
Copy-Item -LiteralPath $v4Checkpoint -Destination (Join-Path $aiModelDir 'model.pt') -Force
$compilerPath = $null; $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($compiler) { $compilerPath = $compiler.Source }
if (-not $compilerPath) {
    $roots = @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)
    foreach ($root in $roots) { if (-not $root) { continue }; foreach ($suffix in @('Inno Setup 6\ISCC.exe','Inno Setup 7\ISCC.exe','Programs\Inno Setup 6\ISCC.exe','Programs\Inno Setup 7\ISCC.exe')) { $candidate = Join-Path $root $suffix; if (Test-Path -LiteralPath $candidate) { $compilerPath = $candidate; break } }; if ($compilerPath) { break } }
}
if (-not $compilerPath) { throw 'Inno Setup ISCC.exe not found. Install Inno Setup 6 or 7.' }
& $compilerPath 'installer.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compile failed.' }
Write-Host 'Complete: release\BadWordBeep-Setup.exe and dist\BadWordBeep\BadWordBeep.exe'
