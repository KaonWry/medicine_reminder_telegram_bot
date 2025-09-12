@echo off
call .\env\Scripts\activate.bat
pm2 start bot.py --interpreter .\env\Scripts\python.exe --name telegram-bot --watch
pm2 status
