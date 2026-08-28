#!/usr/bin/env bash
mode=$(makoctl mode)
if echo "$mode" | grep -q "do-not-disturb"; then
  echo '{"text":"󰂛","tooltip":"Do Not Disturb: ON","class":"dnd"}'
else
  echo '{"text":"󰂚","tooltip":"Do Not Disturb: OFF","class":"active"}'
fi
