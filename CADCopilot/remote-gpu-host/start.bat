@echo off
REM ===================================================================
REM  CADCopilot - GPU HOST start script  (run this on the 4070 PC)
REM  One double-click:  serve Ollama on the network -> open firewall
REM  -> pull the model -> print the address Advay's PC must use.
REM ===================================================================
title CADCopilot GPU Host

REM ---- self-elevate (needed ONCE for the firewall rule) ----
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting administrator rights ^(needed once, for the firewall rule^)...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

REM ---- which model to serve ----
set "MODEL=qwen2.5:14b-instruct"
REM  (optional second model tuned for code/structured output - uncomment to also pull)
REM set "MODEL2=qwen2.5-coder:14b"

set "OLLAMA_HOST=0.0.0.0:11434"
set "OLLAMA_FLASH_ATTENTION=1"
set "OLLAMA_KV_CACHE_TYPE=q8_0"

echo ============================================================
echo   CADCopilot GPU Host setup
echo ============================================================

REM ---- 1) make these settings stick across reboots ----
setx OLLAMA_HOST "0.0.0.0:11434" >nul
setx OLLAMA_FLASH_ATTENTION "1" >nul
setx OLLAMA_KV_CACHE_TYPE "q8_0" >nul
echo [ok] Ollama set to serve on the whole network ^(0.0.0.0:11434^)

REM ---- 2) open the Windows firewall for port 11434 (idempotent) ----
netsh advfirewall firewall delete rule name="Ollama 11434" >nul 2>&1
netsh advfirewall firewall add rule name="Ollama 11434" dir=in action=allow protocol=TCP localport=11434 >nul
echo [ok] firewall allows incoming TCP 11434

REM ---- 3) restart Ollama so it binds to 0.0.0.0 (not just localhost) ----
taskkill /f /im "ollama app.exe" >nul 2>&1
taskkill /f /im "ollama.exe" >nul 2>&1
timeout /t 2 >nul
start "Ollama Server (LEAVE THIS WINDOW OPEN)" /min cmd /k ollama serve
echo [..] starting the Ollama server...

REM ---- 4) wait until the server answers ----
set /a tries=0
:waitloop
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if not errorlevel 1 goto serverup
set /a tries+=1
if %tries% geq 30 (
  echo [WARN] server didn't answer after 60s - check the minimized "Ollama Server" window.
  goto serverup
)
timeout /t 2 >nul
goto waitloop
:serverup
echo [ok] server is up

REM ---- 5) pull the model (skips the download if already present) ----
echo [..] pulling %MODEL%  (first time only, ~9 GB)...
ollama pull %MODEL%
if defined MODEL2 (
  echo [..] pulling %MODEL2% ...
  ollama pull %MODEL2%
)

REM ---- 6) figure out the addresses Advay must use ----
set "LANIP="
for /f "delims=" %%a in ('powershell -NoProfile -Command "(Test-Connection -ComputerName (hostname) -Count 1 -ErrorAction SilentlyContinue).IPV4Address.IPAddressToString" 2^>nul') do set "LANIP=%%a"
set "TSIP="
where tailscale >nul 2>&1 && for /f "delims=" %%t in ('tailscale ip -4 2^>nul') do if not defined TSIP set "TSIP=%%t"

echo.
echo ============================================================
echo   READY - send ONE of these addresses to Advay:
echo ============================================================
if defined LANIP echo   Same Wi-Fi / LAN :  http://%LANIP%:11434
if defined TSIP  echo   Tailscale        :  http://%TSIP%:11434
if not defined LANIP echo   ^(couldn't auto-detect your IP - run: ipconfig, use the IPv4 Address^)
echo   Model            :  %MODEL%
echo ============================================================
echo  Keep the minimized "Ollama Server" window OPEN while he builds.
echo  Closing it stops serving. Next time you can just open the
echo  normal Ollama app - the network setting now sticks.
echo ============================================================
pause
