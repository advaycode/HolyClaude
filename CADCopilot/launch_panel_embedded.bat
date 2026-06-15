@echo off
REM Started by the in-Inventor add-in: runs the panel server WITHOUT opening an external browser tab.
setlocal
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
set "PYTHONIOENCODING=utf-8"
set "CAD_PANEL_NO_BROWSER=1"
if not defined CAD_BACKEND set "CAD_BACKEND=inventor"
if not defined CAD_AGENT set "CAD_AGENT=ollama"
if not defined CAD_OLLAMA_MODEL set "CAD_OLLAMA_MODEL=qwen2.5:14b-instruct"
if not defined CAD_OUTPUT_DIR set "CAD_OUTPUT_DIR=C:\Users\advay\Documents\CacheCAD"
"%ROOT%.venv\Scripts\python.exe" -m cad_mcp.panel
endlocal
