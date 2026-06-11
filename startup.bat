@echo off
setlocal

set VENV_PATH=%~dp0venv
set SCRIPT=%~dp0MedDataIngestion.py

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found!
    exit /b 1
)

call "%VENV_PATH%\Scripts\activate.bat"

if errorlevel 1 (
    echo Failed to activate virtual environment.
    exit /b 1
)

python "%SCRIPT%"
set EXIT_CODE=%ERRORLEVEL%

call deactivate

echo Script finished with exit code %EXIT_CODE%
endlocal
exit /b %EXIT_CODE%