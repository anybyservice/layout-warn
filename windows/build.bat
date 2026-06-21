@echo off
REM Build a single-file LayoutWarn.exe. Run on Windows.
REM Steps (first time): python get_dicts.py  before this.

python -m pip install -r requirements.txt
python get_dicts.py
pyinstaller --onefile --noconsole --name LayoutWarn --add-data "dict;dict" layoutwarn.py

echo.
echo Built: dist\LayoutWarn.exe
pause
