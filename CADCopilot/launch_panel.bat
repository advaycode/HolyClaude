@echo off
REM CADCopilot in-browser panel. LOCAL + FREE by default (Ollama on your CPU).
REM Just have Inventor open and the Ollama app running. No API key, no cost.
setlocal
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
set "PYTHONIOENCODING=utf-8"
if not defined CAD_BACKEND set "CAD_BACKEND=inventor"
if not defined CAD_AGENT set "CAD_AGENT=ollama"
if not defined CAD_OLLAMA_MODEL set "CAD_OLLAMA_MODEL=qwen2.5:14b-instruct"
if not defined CAD_OUTPUT_DIR set "CAD_OUTPUT_DIR=C:\Users\advay\Documents\CacheCAD"
"%ROOT%.venv\Scripts\python.exe" -m cad_mcp.panel
endlocal
