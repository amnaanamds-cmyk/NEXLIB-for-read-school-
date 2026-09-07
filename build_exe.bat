@echo off
echo ========================================================
echo   GDC Library50 Enterprise Edition - Windows Builder
echo ========================================================
echo.
echo Installing PyInstaller and dependencies...
pip install -r requirements.txt
pip install pyinstaller
echo.
echo Building the executable...
python -m PyInstaller --noconfirm --clean gdc_desktop.spec
echo.
echo ========================================================
echo   Build Complete!
echo   Your .exe file is located in the 'dist' folder.
echo ========================================================
pause
