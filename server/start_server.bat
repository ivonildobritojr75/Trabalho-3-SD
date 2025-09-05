@echo off
REM Ativa o ambiente virtual
call .venv\Scripts\activate

REM Instala dependências caso ainda não tenha
pip install -r requirements.txt

REM Roda o servidor Flask
python app.py

pause
