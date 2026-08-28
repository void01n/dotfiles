🌌 void01n's dotfiles

a minimal, fast, and highly customized nixos rice built around niri, ghostty, waybar, and a hybrid zsh + fish shell environment.

✨ features
🪟 window manager — niri for smooth, scrollable tiling across an infinite canvas.
🖥️ terminal — ghostty for fast GPU-accelerated rendering and clean font handling.
🚀 application launcher — fuzzel for a lightweight native Wayland application picker.
📊 status bar — waybar with custom telemetry, system information, and power controls.
🐚 shell — Zsh as the primary interactive shell, enhanced with Oh My Zsh, autosuggestions, syntax highlighting, and Git integration.
🐟 fish utilities — Fish handles package-management helpers and remains available alongside Zsh.
🧭 navigation — zoxide provides smarter directory jumping directly from Zsh.
🎨 theme — Catppuccin Macchiato across the desktop and shell environment.
🖥️ system information — Fastfetch with a custom Catppuccinized output.
📜 history — persistent, shared Zsh history with duplicate filtering and incremental saving.
⚡ deployment — automated installation with backups, package configuration, theming, and NixOS rebuild support.
❄️ system — NixOS for declarative and reproducible system configuration.
📁 repository layout
.
├── config/
│   ├── fastfetch/       # 🖥️ system information and system summary
│   ├── fuzzel/          # 🚀 application launcher
│   ├── ghostty/         # 🖥️ terminal configuration
│   ├── niri/            # 🪟 window manager configuration
│   └── waybar/          # 📊 status bar and styling
├── fish/                # 🐟 fish modules and package helpers
├── .zshrc               # 🐚 primary interactive shell configuration
├── catppuccinize.py     # 🎨 shell/theme transformation utility
└── install.sh           # ⚡ nixos deployment script

📥 installation

clone the repository and run the installer:

git clone https://github.com/void01n/dotss.git ~/dots
cd ~/dots

chmod +x install.sh
./install.sh


the installer handles deployment and system configuration automatically. ✨

🔧 what it does
💾 backs up existing configuration files
📂 creates required XDG directories
🔗 deploys the dotfiles
📦 configures package management
📝 updates /etc/nixos/packages.nix
🎨 applies the selected theme
❄️ rebuilds the NixOS system
🐚 shell environment

Zsh is the primary interactive shell and is configured through Oh My Zsh.

the setup uses:

robbyrussell as the base Oh My Zsh theme
git integration
zsh-autosuggestions for history-based command suggestions
zsh-syntax-highlighting for command feedback
zoxide for intelligent directory navigation
compinit for completion support
persistent and shared command history
duplicate-history filtering
incremental history saving

the shell also includes a custom prompt inspired by Fish:

void01n@nixos: ~/dots/
>


the prompt is dynamically colorized through the Catppuccin theme utility.

📜 history

Zsh history is configured for a large persistent history:

HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000

setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS
setopt APPEND_HISTORY
setopt INC_APPEND_HISTORY


autosuggestions are sourced directly from command history:

ZSH_AUTOSUGGEST_STRATEGY=(history)


this keeps frequently used commands immediately available without requiring additional shell tooling.

🐟 fish + package management

the interactive environment is centered around Zsh, while Fish is retained for package-management functionality.

Zsh exposes the Fish package helper through:

pkg() {
    fish -c 'pkg $argv' -- "$@"
}


this allows package-related functionality to remain modular inside the fish/ directory without moving the entire interactive environment back to Fish.

🧰 aliases & utilities

the shell includes a small collection of quality-of-life aliases:

alias neofetch="fastfetch --config ~/.config/fastfetch/config.jsonc"
alias lolfetch="neofetch | catppuccinize"
alias lmao="lolfetch"

alias xcmatrix="timeout 2 cmatrix"

alias ls="eza --icons --group-directories-first"
alias ll="eza -la --icons --group-directories-first --git"
alias lt="eza --tree --icons"

alias rm="rm -i"
alias cp="cp -i"
alias mv="mv -i"
alias mkdir="mkdir -p"


the eza aliases provide a more informative replacement for traditional ls, while destructive filesystem commands prompt before proceeding.

🖥️ fastfetch

system information is handled by Fastfetch with a custom configuration:

alias neofetch="fastfetch --config ~/.config/fastfetch/config.jsonc"


the environment also includes a themed variant:

lolfetch


which pipes the Fastfetch output through the custom Catppuccinizer.

🎨 shell theming

Catppuccin Macchiato is used as the primary visual language throughout the desktop.

the shell goes a step further by dynamically transforming prompt and Fastfetch output through:

python3 ~/.config/shell/catppuccinize.py


the custom prompt:

detects the current working directory
shortens $HOME to ~
displays the current user and hostname
dynamically applies the generated theme color
renders the prompt across multiple lines
integrates cleanly with Zsh's prompt expansion

this allows the shell to maintain the same visual identity as the rest of the desktop without hardcoding every color directly into .zshrc.

🧭 navigation

zoxide
 is initialized directly inside Zsh:

eval "$(zoxide init zsh)"


this provides smarter directory navigation based on frequently visited locations while keeping the standard shell workflow intact.

📦 nixos integration

the environment is designed around NixOS rather than a conventional mutable Linux installation.

system-level packages are managed declaratively, while the dotfiles installer handles the connection between the user configuration and /etc/nixos/packages.nix.

the result is a setup that can be deployed onto a fresh system without manually reconstructing the desktop environment.

🛡️ safe deployments

existing configuration files are never blindly overwritten.

if a file or directory already exists, the installer moves it to a timestamped backup:

~/.config/niri.bak.1787860861


this makes the installer safe to run repeatedly while keeping previous configurations available for recovery.

🎨 theming

the entire environment follows the Catppuccin Macchiato palette.

the theme is applied across:

🪟 niri
🖥️ ghostty
📊 waybar
🚀 fuzzel
🐚 Zsh
🐟 Fish
🖥️ Fastfetch

theme generation and shell-specific transformations are handled automatically through:

python3 catppuccinize.py


rather than requiring colors to be manually synchronized between every configuration.

🧠 design philosophy

this setup is built around a few simple ideas:

🧼 minimal — keep the environment focused and avoid unnecessary software.
⚡ fast — prioritize low overhead, quick startup, and responsive tools.
🧩 modular — keep applications and shell components independently configurable.
🐚 practical — use Zsh for the interactive experience while retaining Fish where its scripting is useful.
❄️ declarative — let NixOS handle system-level configuration.
🎨 consistent — keep the entire environment visually unified.
🔁 repeatable — make deployments safe, automated, and reproducible.
🛠️ custom — favor small personal utilities over large frameworks where possible.

the goal isn't to build the most complicated rice possible.

it's to build a desktop that feels fast, cohesive, predictable, and distinctly mine.

🖼️ screenshots

❤️ credits

created by void01n
.

feel free to fork, modify, and make it your own.

if you find something broken or have an improvement, open an issue or pull request. 🚀
