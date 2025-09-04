@echo off
setlocal
cd /d %~dp0
cd ..\backend
IF NOT EXIST venv (
  py -3 -m venv venv
)
call venv\Scripts\activate
pip install --upgrade pip >nul
pip install -r requirements.txt
set JWT_SECRET=change-me
uvicorn app:app --reload --port 8000