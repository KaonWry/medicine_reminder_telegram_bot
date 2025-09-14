#!/bin/bash
source ./env/bin/activate
pm2 start src/bot.py --interpreter ./env/bin/python --name telegram-bot --watch --ignore-watch="src/reminders.db"
pm2 status