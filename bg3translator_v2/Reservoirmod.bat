@echo off
cd /d "C:\Users\NZXT\Desktop\bg3translator_v2"

echo === Traduction Better Battleaxes ===
echo.

REM Variables
set "MOD_FILE=config\mods\Better Battleaxes-18264-1-0-1755927868.zip"
set "AUTHOR_NAME=Aqu1lae"
set "DIVINE_PATH=tools\divine.exe"

REM Test simulation
echo === TEST SIMULATION ===
python translate_mod.py "%MOD_FILE%" --author "%AUTHOR_NAME%" --divine "%DIVINE_PATH%" --dry-run --verbose

echo.
pause
echo.

REM Traduction réelle
echo === TRADUCTION REELLE ===
python translate_mod.py "%MOD_FILE%" --author "%AUTHOR_NAME%" --divine "%DIVINE_PATH%" --use-llm --verbose

echo.
echo Traduction terminée - vérifiez le dossier output/
pause