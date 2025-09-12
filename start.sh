#!/bin/bash
source ./env/bin/activate
pm2 start bot.py --interpreter ./env/bin/python --name telegram-bot --watch
pm2 status