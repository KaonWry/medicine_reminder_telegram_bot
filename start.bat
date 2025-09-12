@echo off
REM Activate virtual environment
call .\env\Scripts\activate.bat

REM Start the bot with PM2
pm2 start bot.py --interpreter .\env\Scripts\python.exe --name telegram-bot --watch

REM Show PM2 status
pm2 status
