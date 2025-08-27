@echo off
REM ===========================================
REM Script para rodar o executavel e abrir no navegador
REM ===========================================

echo Iniciando o aplicativo BloqueiosYellow...
start "" http://127.0.0.1:5000

REM Executa o .exe gerado (ajuste o caminho se precisar)
dist\BloqueiosYellow.exe

pause
