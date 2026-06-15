@echo off
REM ===================================================================
REM  Point CADCopilot at a remote GPU host (run this on ADVAY'S PC).
REM  Usage:  connect_to_gpu_host.bat 192.168.1.50
REM          connect_to_gpu_host.bat 100.x.x.x
REM          connect_to_gpu_host.bat local      (go back to your own CPU)
REM  Or just double-click and paste the address when asked.
REM ===================================================================
setlocal
title Connect CADCopilot to GPU host

set "ARG=%~1"
if /i "%ARG%"=="local" (
  setx CAD_OLLAMA_URL "http://127.0.0.1:11434" >nul
  echo [ok] CADCopilot will use your LOCAL CPU again.
  echo Restart Inventor so the panel picks it up.
  pause & exit /b
)

set "IP=%ARG%"
if "%IP%"=="" set /p IP=Paste the GPU host address (e.g. 192.168.1.50 or 100.x.x.x):

REM allow pasting either "1.2.3.4" or a full "http://1.2.3.4:11434"
echo %IP% | findstr /c:"http" >nul && (set "URL=%IP%") || (set "URL=http://%IP%:11434")

echo.
echo Testing %URL% ...
curl -s -m 6 %URL%/api/tags >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Can't reach %URL%
  echo   - Is his start.bat running with the "Ollama Server" window open?
  echo   - Are you both on the same Wi-Fi, or both on Tailscale?
  echo   - Try again in a few seconds.
  pause & exit /b 1
)
echo [ok] reached the GPU host.

setx CAD_OLLAMA_URL "%URL%" >nul
echo [ok] CADCopilot now points at %URL%
echo.
echo  NEXT: restart Inventor so the panel relaunches using the remote GPU.
echo  ^(To switch back later:  connect_to_gpu_host.bat local^)
pause
endlocal
