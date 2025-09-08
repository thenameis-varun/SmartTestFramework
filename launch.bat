@echo off
:: ------------------------------
:: SmartTestFramework Launcher (Windows)
:: ------------------------------

:: Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python not found! Please install Python 3.10 or higher.
    pause
    exit /b
)

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Run Streamlit app
echo Launching SmartTestFramework...
streamlit run src\standalone\app.py

pause
