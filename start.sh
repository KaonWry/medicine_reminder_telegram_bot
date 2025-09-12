#!/bin/bash

# Activate virtual environment
source ./env/bin/activate

# Start the bot with PM2
pm2 start bot.py --interpreter ./env/bin/python --name telegram-bot --watch

# Optional: show status
pm2 status
