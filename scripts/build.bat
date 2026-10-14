@echo off
rem ============================================================================
rem  Windows build wrapper
rem
rem  Usage:  scripts\build.bat [compile|run|upload|logs|config]
rem          (default: compile)
rem
rem  Regenerates layout\generated\* and then runs esphome in a clean Windows
rem  PATH (no Git-Bash / MSys leakage, which breaks the ESP-IDF toolchain).
rem ============================================================================
setlocal

set "REPO=%~dp0.."
cd /d "%REPO%"

set "COMMAND=%~1"
if "%COMMAND%"=="" set "COMMAND=compile"

echo [build] regenerating layout\generated\ from layout\ui_layout.yaml ...
python tools\layout_to_h.py || exit /b 1

echo [build] esphome %COMMAND% e1003-dashboard.yaml
call "%~dp0run_esphome.bat" %COMMAND% e1003-dashboard.yaml

endlocal