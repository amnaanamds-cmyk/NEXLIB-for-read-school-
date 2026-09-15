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
python -m PyInstaller --noconfirm --clean --onefile --windowed --name NexLib --icon assets\nexlib.ico main.py
echo.
echo ========================================================
echo   Build Complete!
echo   Your NexLib.exe file is located in the 'dist' folder.
echo ========================================================
pause
