#!/usr/bin/env bash
export GI_TYPELIB_PATH="$(find /nix/store -maxdepth 3 -name "Gtk-4.0.typelib" -path "*/home-manager-path/*" 2>/dev/null | head -1 | xargs dirname):${GI_TYPELIB_PATH:-}"
export LD_LIBRARY_PATH="$(find /nix/store -maxdepth 3 -name "Gtk-4.0.typelib" -path "*/home-manager-path/*" 2>/dev/null | head -1 | xargs dirname | sed 's|/girepository-1.0||'):${LD_LIBRARY_PATH:-}"
exec python3 ~/v0wwa.py ~/.config/v0wwa/main