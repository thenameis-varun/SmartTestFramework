#!/bin/bash
# ------------------------------
# SmartTestFramework Launcher (macOS/Linux)
# ------------------------------

# Check Python version
if ! python3 --version &>/dev/null; then
    echo "Python not found! Please install Python 3.10 or higher."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Run Streamlit app
echo "Launching SmartTestFramework..."
streamlit run src/standalone/app.py
