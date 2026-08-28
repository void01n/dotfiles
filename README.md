🌌 void01n's dotfiles

a minimal, fast, and highly optimized nixos rice built around niri, ghostty, waybar, and a hybrid zsh + fish shell environment.

✨ features
🧩 component	⚙️ setup
🪟 window manager	niri — smooth, scrollable tiling on an infinite canvas
🖥️ terminal	ghostty — fast gpu-accelerated terminal with clean font rendering
🚀 launcher	fuzzel — lightweight, native wayland application launcher
📊 status bar	waybar — custom telemetry, system information, and power controls
🐚 shell	zsh + fish — minimal interactive shell with modular helpers
🎨 theme	catppuccin macchiato
❄️ system	nixos — declarative and reproducible system configuration
🛠️ deployment	automated installer with backups and rebuild support
📁 repository layout
.
├── config/
│   ├── fastfetch/       # 🖥️ system information
│   ├── fuzzel/          # 🚀 application launcher
│   ├── ghostty/         # 🖥️ terminal configuration
│   ├── niri/            # 🪟 window manager configuration
│   └── waybar/          # 📊 status bar and styling
├── fish/                 # 🐟 fish modules and package helpers
├── .zshrc                # 🐚 interactive zsh configuration
├── catppuccinize.py      # 🎨 theme deployment automation
└── install.sh            # ⚡ nixos deployment script

📥 installation

clone the repository and run the installer:

git clone https://github.com/void01n/dotfiles ~/dots
cd ~/dots

chmod +x install.sh
./install.sh


the installer handles the deployment automatically. ✨

🔧 what it does
💾 backs up existing configuration files
📂 creates required xdg directories
🔗 deploys the dotfiles
📦 configures package management
📝 updates /etc/nixos/packages.nix
🎨 applies the selected theme
❄️ rebuilds the nixos system
🛡️ safe deployments

existing configuration files are never blindly overwritten.

if a file or directory already exists, the installer moves it to a timestamped backup:

~/.config/niri.bak.1787860861


this makes the installer safe to run repeatedly while keeping your previous configuration available for recovery. 🔒

📦 package management

the interactive environment runs through zsh, while package-management functionality is handled by fish.

the .zshrc exposes the package helper through a simple alias:

alias pkg="fish -c pkg"


this keeps the primary shell configuration minimal while allowing package-related functionality to remain modular inside fish/. 🐟

the installer also handles the required nixos package declarations and metadata automatically.

🎨 theming

the desktop uses the catppuccin macchiato palette across supported applications.

theme deployment is automated through:

python3 catppuccinize.py


no need to manually update every application configuration. 🎨

🧠 design philosophy

this setup is built around a few simple ideas:

🧼 minimal — keep only what is useful
⚡ fast — prioritize low overhead and quick startup
🧩 modular — keep each application independently configurable
❄️ declarative — let nixos handle system-level configuration
🔁 repeatable — make deployments safe and reproducible

the goal is a clean wayland desktop that stays out of the way and lets the workflow take priority.

🖼️ screenshots

❤️ credits

created by void01n.

feel free to fork, modify, and make it your own.

if you find something broken or have an improvement, open an issue or pull request. 🚀
