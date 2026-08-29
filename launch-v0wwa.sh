#!/usr/bin/env bash
source /etc/profiles/per-user/void01/etc/profile.d/hm_session_vars.sh 2>/dev/null
source ~/.profile 2>/dev/null
source ~/.zshenv 2>/dev/null
exec python3 ~/v0wwa.py ~/.config/v0wwa/main