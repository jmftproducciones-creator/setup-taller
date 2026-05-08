@echo off
REM Ir a la carpeta del proyecto
cd /d "%~dp0"

if not exist ".env" (
  echo No encontre .env. Podes copiar .env.example a .env si queres configurar la DB.
)

start http://127.0.0.1:5000
REM Ejecutar Flask con el Python disponible en Windows
py app.py

REM Cuando cierres Flask, la consola se queda para ver mensajes
pause
