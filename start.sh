#!/bin/bash
source ./env/Scripts/activate
pm2 start src/bot.py --interpreter ./env/Scripts/python --name telegram-bot --watch --ignore-watch="src/reminders.db"
pm2 status
