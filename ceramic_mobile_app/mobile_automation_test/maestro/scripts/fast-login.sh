#!/bin/bash
# Fast text input using ADB's input command (much faster than character-by-character)
# Usage: ./fast-login.sh "username" "password"

USERNAME="$1"
PASSWORD="$2"

# Input text directly (faster than typing each character)
adb shell input text "$USERNAME"
adb shell input keyevent 61  # TAB to next field
adb shell input text "$PASSWORD"
