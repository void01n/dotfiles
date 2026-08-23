alias neofetch "fastfetch --config ~/.config/fastfetch/config.jsonc"
alias lolfetch "neofetch | catppuccinize"
alias lmao "lolfetch"
alias loltsay "fortune | cowsay | catppuccinize"
alias xcmatrix "timeout 2 cmatrix"
set -gx NIXPKGS_ALLOW_UNFREE 1
set -gx EDITOR nvim
set -gx VISUAL nvim
function catppuccinize
    python3 ~/.config/shell/catppuccinize.py
end
lolfetch

alias ls "eza --icons --group-directories-first"
alias ll "eza -la --icons --group-directories-first --git"
alias lt "eza --tree --icons"
alias rm "rm -i"
alias cp "cp -i"
alias mv "mv -i"
alias mkdir "mkdir -p"
alias nano "nvim"

zoxide init fish | source
