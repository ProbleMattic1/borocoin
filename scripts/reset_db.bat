@echo off
setlocal
cd /d %~dp0
cd ..\backend
del rewards.db 2>nul
echo Reset done.