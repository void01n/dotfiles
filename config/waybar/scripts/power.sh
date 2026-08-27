#!/bin/sh
choice=$(printf "Shutdown\nReboot\n" | fuzzel --dmenu -p "Power: ")
case "$choice" in
  Shutdown) systemctl poweroff ;;
  Reboot) systemctl reboot ;;
esac
