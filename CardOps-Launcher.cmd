@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%SCRIPT_DIR%tools\CardOps-Launcher.ps1"

if not exist "%LAUNCHER%" (
  echo CardOps launcher script was not found:
  echo   %LAUNCHER%
  pause
  exit /b 1
)

set "POWERSHELL_EXE="
where pwsh.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  for /f "delims=" %%P in ('where pwsh.exe') do (
    if not defined POWERSHELL_EXE set "POWERSHELL_EXE=%%P"
  )
)

if not defined POWERSHELL_EXE (
  where powershell.exe >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    for /f "delims=" %%P in ('where powershell.exe') do (
      if not defined POWERSHELL_EXE set "POWERSHELL_EXE=%%P"
    )
  )
)

if not defined POWERSHELL_EXE (
  echo CardOps could not find PowerShell 7 or Windows PowerShell.
  echo Install PowerShell 7 from https://learn.microsoft.com/powershell/
  pause
  exit /b 1
)

"%POWERSHELL_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%LAUNCHER%" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo CardOps Launcher exited with code %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%
