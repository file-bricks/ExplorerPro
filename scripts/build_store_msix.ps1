param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$builder = 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\_STORE\msstore_build_msix.ps1'
$iconGate = 'C:\Users\User\OneDrive\.TOPICS\.SOFTWARE\_STORE\icon_consistency_check.py'
$config = Get-Content (Join-Path $projectRoot 'store_package.json') -Raw | ConvertFrom-Json
$releaseVersion = $config.version -replace '\.0$', ''
$output = Join-Path $projectRoot "releases\windowsstore\v$releaseVersion\ExplorerPro.msix"
$exe = Join-Path $projectRoot 'dist\ExplorerPro\ExplorerPro.exe'

$env:PYTHONIOENCODING = 'utf-8'
& python (Join-Path $PSScriptRoot 'gen_store_icons.py')
if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
& python $iconGate $projectRoot
if ($LASTEXITCODE -ne 0) { throw 'Source icon gate failed.' }
& (Join-Path $projectRoot 'build_exe.bat')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
& $builder -ProjectRoot $projectRoot -ExePath $exe -OutputMsix $output
if ($LASTEXITCODE -ne 0) { throw 'MSIX builder or package gate failed.' }
