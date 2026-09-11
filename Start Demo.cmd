@echo off
set "DEMO_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%DEMO_PYTHON%" (
  "%DEMO_PYTHON%" -I "%~dp0run_demo.py"
) else (
  python "%~dp0run_demo.py"
)
pause
