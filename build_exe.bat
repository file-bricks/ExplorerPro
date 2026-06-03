@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

set "BUILD_ROOT=C:\_Local_DEV\codex_build\explorerpro"
set "WORK_PATH=%BUILD_ROOT%\work"

if not exist "%BUILD_ROOT%" mkdir "%BUILD_ROOT%"
if not exist "%WORK_PATH%" mkdir "%WORK_PATH%"

echo [INFO] Baue ExplorerPro.exe mit lokalem PyInstaller-Workpath...
python -m PyInstaller --clean --noconfirm --workpath "%WORK_PATH%" --distpath "%CD%\dist" ExplorerPro.spec
if errorlevel 1 (
    echo [FEHLER] PyInstaller-Build fehlgeschlagen.
    exit /b 1
)

if not exist "%CD%\dist\ExplorerPro\ExplorerPro.exe" (
    echo [FEHLER] Erwartete EXE nicht gefunden: dist\ExplorerPro\ExplorerPro.exe
    exit /b 1
)

echo [OK] EXE erstellt: dist\ExplorerPro\ExplorerPro.exe
endlocal
