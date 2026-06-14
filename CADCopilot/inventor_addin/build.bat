@echo off
REM Build + register the CADCopilot Inventor add-in. RUN AS ADMINISTRATOR (regasm writes HKCR).
setlocal
set "DIR=%~dp0"
set "OUT=%DIR%bin\x64\Release\net48"
set "DEST=%APPDATA%\Autodesk\Inventor 2027\Addins\CadCopilot"

echo === building ===
dotnet build "%DIR%CadCopilotAddin.csproj" -c Release -p:Platform=x64
if errorlevel 1 goto :err

echo === deploying to %DEST% ===
if not exist "%DEST%" mkdir "%DEST%"
xcopy /Y /E "%OUT%\*" "%DEST%\" >nul
copy /Y "%DIR%CadCopilot.addin" "%DEST%\" >nul

echo === registering for COM ===
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\regasm.exe" /codebase "%DEST%\CadCopilotAddin.dll"
if errorlevel 1 goto :err

echo.
echo DONE. Start (or restart) Inventor. If the pane doesn't appear, enable
echo "CADCopilot" under Tools ^> Add-Ins, and toggle View ^> User Interface ^> CADCopilot.
goto :eof
:err
echo.
echo BUILD/REGISTER FAILED — see messages above. (Did you run as Administrator?)
exit /b 1
