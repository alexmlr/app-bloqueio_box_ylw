@echo off
REM ===========================================
REM Script para gerar o executável do app Flask
REM ===========================================

echo Ativando ambiente virtual...
call .venv\Scripts\activate

echo Gerando executavel com PyInstaller...
py -m PyInstaller ^
  --onefile ^
  --noconsole ^
  --name BloqueiosYellow ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --collect-data openpyxl ^
  --collect-data pandas ^
  app.py

echo ===========================================
echo Build concluido!
echo O executavel esta em: dist\BloqueiosYellow.exe
echo ===========================================

pause
