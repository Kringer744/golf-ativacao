@echo off
title Golf Challenge - Modo Offline
cd /d "%~dp0"
echo ============================================
echo   GOLF CHALLENGE - iniciando modo offline
echo   (o navegador vai abrir sozinho)
echo ============================================
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py servidor.py
) else (
  python servidor.py
)
echo.
echo Se apareceu erro acima, o Python nao esta instalado.
echo Baixe em https://python.org e marque "Add to PATH".
pause
