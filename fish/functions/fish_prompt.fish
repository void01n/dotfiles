function fish_prompt
    set dir (prompt_pwd)
    set text "$USER@nixos: $dir/"
    set raw (echo -n $text | python3 ~/.config/shell/catppuccinize.py)
    set first_color (echo -n $raw | grep -oP '\x1b\[38;2;[\d;]+m' | head -n1)
    echo -n $raw
    echo -e "\n$first_color>\e[0m "
end
