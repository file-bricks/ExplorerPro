param([switch]$CheckToolsOnly)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not [string]::IsNullOrWhiteSpace($env:STORE_TOOLS_ROOT)) {
    $storeToolsRoot = $env:STORE_TOOLS_ROOT
} elseif (-not [string]::IsNullOrWhiteSpace($env:OneDrive)) {
    $storeToolsRoot = Join-Path $env:OneDrive '.TOPICS\.SOFTWARE\_STORE'
} else {
    Write-Error 'Store tools root is missing. Set STORE_TOOLS_ROOT or OneDrive.' -ErrorAction Continue
    exit 1
}
$builder = Join-Path $storeToolsRoot 'msstore_build_msix.ps1'
$iconGate = Join-Path $storeToolsRoot 'icon_consistency_check.py'
foreach ($tool in @($builder, $iconGate)) {
    if (-not (Test-Path -LiteralPath $tool -PathType Leaf)) {
        Write-Error "Required Store tool is missing: $tool" -ErrorAction Continue
        exit 1
    }
}
if ($CheckToolsOnly) {
    Write-Output "Store tools found: $builder; $iconGate"
    return
}
$config = Get-Content (Join-Path $projectRoot 'store_package.json') -Raw | ConvertFrom-Json
$releaseVersion = $config.version -replace '\.0$', ''
$projectVersion = & python -c "import sys; sys.path.insert(0, r'$projectRoot\src'); from version import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0 -or $releaseVersion -ne $projectVersion) {
    throw "Store package version $($config.version) differs from pyproject.toml version $projectVersion."
}
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
