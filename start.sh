#!/bin/bash
source ./env/bin/activate
pm2 start bot.py --interpreter ./env/bin/python --name telegram-bot --watch --ignore-watch="reminders.db"
pm2 status