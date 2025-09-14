@echo off
call .\env\Scripts\activate.bat
pm2 start src\bot.py --interpreter .\env\Scripts\python.exe --name telegram-bot --watch --ignore-watch="src\\reminders.db"
pm2 status
