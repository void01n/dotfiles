🌌 void01n's dotfiles

a minimal, fast, and highly customized nixos rice built around niri, ghostty, waybar, and a hybrid zsh + fish shell environment.

✨ features
🪟 window manager — niri for smooth, scrollable tiling across an infinite canvas.
🖥️ terminal — ghostty for fast GPU-accelerated rendering and clean font handling.
🚀 application launcher — fuzzel for a lightweight native Wayland application picker.
📊 status bar — waybar with custom telemetry, system information, and power controls.
🐚 shell — Zsh as the primary interactive shell, enhanced with Oh My Zsh, autosuggestions, syntax highlighting, and Git integration.
🐟 fish utilities — Fish handles package-management helpers and supporting shell functionality.
🧭 navigation — zoxide for fast, intelligent directory jumping.
🎨 theme — Catppuccin Macchiato across the desktop and shell environment.
🖥️ system information — Fastfetch with custom configuration and themed output.
📜 history — persistent, shared Zsh history with duplicate filtering and incremental saving.
🛡️ safe deployment — existing configurations are backed up before being replaced.
❄️ system — NixOS for declarative and reproducible system configuration.
📁 repository layout
.
├── config/
│   ├── fastfetch/       # 🖥️ system information
│   ├── fuzzel/          # 🚀 application launcher
│   ├── ghostty/         # 🖥️ terminal configuration
│   ├── niri/            # 🪟 window manager configuration
│   └── waybar/          # 📊 status bar and styling
├── fish/                # 🐟 fish modules and package helpers
├── .zshrc               # 🐚 interactive zsh configuration
├── catppuccinize.py     # 🎨 theme transformation utility
├── install.sh           # ⚡ nixos deployment script
├── img.png              # 🖼️ desktop screenshot
└── LICENSE

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

the setup includes:

robbyrussell as the base Oh My Zsh theme
Git integration
zsh-autosuggestions for history-based suggestions
zsh-syntax-highlighting for command feedback
zoxide for intelligent directory navigation
compinit for completion support
persistent and shared command history
duplicate-history filtering
incremental history saving

the shell also features a custom prompt inspired by Fish:

void01n@nixos: ~/dots/
>


the prompt is dynamically colorized through the custom Catppuccin utility.

📜 history

Zsh maintains a persistent history of up to 10,000 commands:

HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000

setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS
setopt APPEND_HISTORY
setopt INC_APPEND_HISTORY


autosuggestions use the shell history as their source:

ZSH_AUTOSUGGEST_STRATEGY=(history)


this keeps frequently used commands immediately available while preserving the normal Zsh workflow.

🐟 fish + package management

Zsh is used for interactive work, while Fish provides the package-management helper.

the .zshrc exposes the Fish package function through a small wrapper:

pkg() {
    fish -c 'pkg $argv' -- "$@"
}


this allows package-related functionality to remain modular inside the fish/ directory without requiring Fish to be the primary interactive shell.

🧰 aliases & utilities

the shell includes a collection of small quality-of-life aliases:

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


eza replaces the traditional ls workflow with icons, directory grouping, Git status, and tree views.

filesystem commands such as rm, cp, and mv prompt before modifying files, while mkdir -p makes nested directory creation painless.

🖥️ fastfetch

Fastfetch provides system information through a custom configuration:

alias neofetch="fastfetch --config ~/.config/fastfetch/config.jsonc"


the shell also provides a themed Fastfetch command:

lolfetch


which pipes the output through the custom Catppuccinizer.

lmao is simply a shorter alias for the same themed output:

alias lmao="lolfetch"

🎨 shell theming

Catppuccin Macchiato is used as the primary visual language throughout the desktop.

the shell uses the custom Catppuccinizer:

python3 ~/.config/shell/catppuccinize.py


the utility is used by both the prompt and Fastfetch workflow, allowing generated output to share the same palette as the rest of the desktop.

the custom prompt:

detects the current working directory
shortens $HOME to ~
displays the current user and hostname
dynamically applies generated colors
uses a two-line prompt layout
integrates with Zsh prompt expansion
🧭 navigation

zoxide is initialized directly inside Zsh:

eval "$(zoxide init zsh)"


this provides smarter directory navigation based on frequently visited locations while keeping the normal shell workflow intact.

🌐 environment

the shell also configures common user-level environment variables:

export NIXPKGS_ALLOW_UNFREE=1

export EDITOR=nvim
export VISUAL=nvim

export XDG_DATA_DIRS="$HOME/.local/share/flatpak/exports/share:$XDG_DATA_DIRS"

export PATH="$HOME/.local/bin:$PATH"


Neovim is the preferred editor, local user binaries are added to $PATH, and Flatpak exports are included in $XDG_DATA_DIRS.

❄️ NixOS integration

the environment is designed around NixOS rather than a conventional mutable Linux installation.

system-level packages are managed declaratively, while the installer handles the connection between the dotfiles and:

/etc/nixos/packages.nix


the result is a setup that can be deployed onto a fresh system without manually reconstructing the desktop environment.

🛡️ safe deployments

existing configuration files are never blindly overwritten.

if a file or directory already exists, the installer moves it to a timestamped backup:

~/.config/niri.bak.1787860861


this makes the installer safe to run repeatedly while keeping previous configurations available for recovery.

🎨 theming

the environment follows the Catppuccin Macchiato palette across:

🪟 niri
🖥️ ghostty
📊 waybar
🚀 fuzzel
🐚 Zsh
🐟 Fish
🖥️ Fastfetch

theme generation and shell-specific transformations are handled automatically through:

python3 catppuccinize.py


this keeps colors consistent without requiring manual edits across every configuration.

🧠 design philosophy

this setup is built around a few simple ideas:

🧼 minimal — keep the environment focused and avoid unnecessary software.
⚡ fast — prioritize low overhead, quick startup, and responsive tools.
🧩 modular — keep applications and shell components independently configurable.
🐚 practical — use Zsh for interactive work while retaining Fish where its scripting is useful.
❄️ declarative — let NixOS handle system-level configuration.
🎨 consistent — keep the entire environment visually unified.
🔁 repeatable — make deployments safe and reproducible.
🛠️ custom — favor small personal utilities over unnecessary frameworks.

the goal isn't to build the most complicated rice possible.

it's to build a desktop that feels fast, cohesive, predictable, and distinctly mine.

🖼️ screenshots

❤️ credits

created by void01n.

feel free to fork, modify, and make it your own.

if you find something broken or have an improvement, open an issue or pull request. 🚀
