@echo off
chcp 65001 >nul
title ExplorerPro - Usertest

echo ============================================================
echo   ExplorerPro - Usertest
echo ============================================================
echo.

cd /d "%~dp0"

echo [INFO] Starte ExplorerPro...
echo.

set "EXE_PATH=%~dp0dist\ExplorerPro\ExplorerPro.exe"
if exist "%EXE_PATH%" (
    echo [INFO] Starte EXE: %EXE_PATH%
    "%EXE_PATH%"
    set EXIT_CODE=%ERRORLEVEL%
    goto after_start
)

REM Ins src-Verzeichnis wechseln (relativ zur BAT-Datei)
cd /d "%~dp0src"
if %ERRORLEVEL% NEQ 0 (
    echo [FEHLER] Konnte nicht ins src-Verzeichnis wechseln!
    echo [INFO] Erwarteter Pfad: %~dp0src
    pause
    exit /b 1
)

echo [INFO] Keine EXE gefunden, starte Python-Fallback.
echo [INFO] Pfad: %CD%
echo.

python main.py
set EXIT_CODE=%ERRORLEVEL%

:after_start
echo.
if %EXIT_CODE% EQU 0 (
    echo [OK] ExplorerPro normal beendet.
) else (
    echo ============================================================
    echo [FEHLER] ExplorerPro beendet mit Exit-Code: %EXIT_CODE%
    echo ============================================================
    echo.
    if %EXIT_CODE% EQU 3221225725 (
        echo [!] Access Violation 0xC0000005 - PySide6/Qt-DLL-Problem
        echo [!] Siehe BUGREPORT_StartupCrash.md für Details
    )
    if %EXIT_CODE% EQU 1 (
        echo [!] Python-Fehler - siehe Ausgabe oben
    )
    echo.
    pause
)
