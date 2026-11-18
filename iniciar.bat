@echo off
REM Prepara el entorno (solo la primera vez tarda) y abre FIAshion en el navegador.
REM IMPORTANTE: no cierre esta ventana mientras use el programa; si la cierra, la pagina deja de funcionar.
cd /d "%~dp0"

REM Busca Python (en algunos equipos el comando es "py" y no "python")
set PY=python
python --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || (
  echo No se encontro Python. Instalelo desde python.org y marque "Add Python to PATH".
  pause
  exit /b 1
)

if not exist .venv (
  echo Creando el entorno virtual...
  %PY% -m venv .venv
)
echo Instalando librerias (la primera vez tarda un poco)...
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo Se creo el archivo .env. Se va a abrir en el Bloc de notas:
  echo  - en DATABASE_URL cambie tu_clave por la clave de root de MySQL
  echo  - en GEMINI_API_KEY ponga la clave de Gemini ^(opcional^)
  echo Guarde, cierre el Bloc de notas y vuelva a esta ventana.
  notepad .env
  pause
)
.venv\Scripts\python.exe seed.py || (pause & exit /b 1)

REM Abre el navegador 5 segundos despues, cuando el servidor ya este listo
start "" cmd /c "timeout /t 5 >nul & start http://127.0.0.1:8000/app/"
echo.
echo FIAshion esta corriendo en http://127.0.0.1:8000/app/  (Ctrl + C para detenerlo)
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
pause
