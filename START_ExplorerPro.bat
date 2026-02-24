@echo off
chcp 65001 >nul
title ExplorerPro - Usertest

echo ============================================================
echo   ExplorerPro - Usertest
echo ============================================================
echo.

REM Ins src-Verzeichnis wechseln (relativ zur BAT-Datei)
cd /d "%~dp0src"
if %ERRORLEVEL% NEQ 0 (
    echo [FEHLER] Konnte nicht ins src-Verzeichnis wechseln!
    echo [INFO] Erwarteter Pfad: %~dp0src
    pause
    exit /b 1
)

echo [INFO] Starte ExplorerPro...
echo [INFO] Pfad: %CD%
echo.

REM App starten und Exit-Code speichern
python main.py
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% EQU 0 (
    echo [OK] ExplorerPro normal beendet.
) else (
    echo ============================================================
    echo [FEHLER] ExplorerPro beendet mit Exit-Code: %EXIT_CODE%
    echo ============================================================
    echo.
    if %EXIT_CODE% EQU 3221225725 (
        echo [!] Access Violation 0xC0000005 - PyQt6/DLL Problem
        echo [!] Siehe BUGREPORT_StartupCrash.md fuer Details
    )
    if %EXIT_CODE% EQU 1 (
        echo [!] Python-Fehler - siehe Ausgabe oben
    )
    echo.
    pause
)
