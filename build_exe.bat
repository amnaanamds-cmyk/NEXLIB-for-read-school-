@echo off
echo ========================================================
echo   NexLib - Windows Builder
echo ========================================================
echo.
echo Installing PyInstaller and dependencies...
pip install -r requirements.txt
pip install pyinstaller
echo.
echo Building the executable...
python -m PyInstaller --noconfirm --clean --name NexLib --icon assets\nexlib.ico --windowed main.py
echo.
echo ========================================================
echo   Build Complete!
echo   Your .exe file is located in the 'dist' folder.
echo ========================================================
pause
