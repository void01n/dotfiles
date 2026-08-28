# 🌌 void01n's dotfiles

> a minimal, fast, and highly optimized nixos rice built around niri, ghostty, waybar, and a hybrid zsh + fish shell environment.

![desktop preview](img.png)

## ✨ features

- 🪟 **window manager** — niri for smooth, scrollable tiling across an infinite canvas.
- 🖥️ **terminal** — ghostty for fast gpu-accelerated rendering and clean font handling.
- 🚀 **application launcher** — fuzzel for a lightweight, native wayland application picker.
- 📊 **status bar** — waybar with custom telemetry, system information, and power controls.
- 🐚 **shell** — zsh for interactive use with fish handling custom package helpers.
- 🎨 **theme** — catppuccin macchiato across the desktop environment.
- ❄️ **system** — nixos for declarative and reproducible system configuration.
- ⚡ **deployment** — automated installation with backups and nixos rebuild support.

## 📁 repository layout

```text
.
├── config/
│   ├── fastfetch/       # 🖥️ system information
│   ├── fuzzel/          # 🚀 application launcher
│   ├── ghostty/         # 🖥️ terminal configuration
│   ├── niri/            # 🪟 window manager configuration
│   └── waybar/          # 📊 status bar and styling
├── fish/                # 🐟 fish modules and package helpers
├── .zshrc               # 🐚 interactive zsh configuration
├── catppuccinize.py     # 🎨 theme deployment automation
└── install.sh           # ⚡ nixos deployment script
```

## 📥 installation

clone the repository and run the installer:

```bash
git clone https://github.com/void01n/dotfiles.git ~/dots
cd ~/dots

chmod +x install.sh
./install.sh
```

the installer handles the deployment automatically. ✨

### 🔧 what it does

- 💾 backs up existing configuration files
- 📂 creates the required xdg directories
- 🔗 deploys the dotfiles
- 📦 configures package management
- 📝 updates `/etc/nixos/packages.nix`
- 🎨 applies the selected theme
- ❄️ rebuilds the nixos system

## 🛡️ safe deployments

existing configuration files are never blindly overwritten.

if a file or directory already exists, the installer moves it to a timestamped backup:

```text
~/.config/niri.bak.1787860861
```

this makes the installer safe to run repeatedly while keeping previous configurations available for recovery.

## 📦 package management

the interactive shell runs through zsh, while package-management functionality is handled by fish.

the `.zshrc` exposes the package helper through a simple alias:

```zsh
alias pkg="fish -c pkg"
```

this keeps the primary shell configuration minimal while allowing package-related functionality to remain modular inside the `fish/` directory.

the installer also handles the required nixos package declarations and metadata automatically.

## 🎨 theming

the desktop uses the catppuccin macchiato palette across supported applications.

theme deployment is automated through:

```bash
python3 catppuccinize.py
```

this keeps the visual configuration consistent without requiring manual edits across individual applications.

## 🧠 design philosophy

this setup is built around a few simple ideas:

- 🧼 **minimal** — keep only what is useful
- ⚡ **fast** — prioritize low overhead and quick startup
- 🧩 **modular** — keep each application independently configurable
- ❄️ **declarative** — let nixos handle system-level configuration
- 🔁 **repeatable** — make deployments safe and reproducible

the goal is a clean wayland desktop that stays out of the way and lets the workflow take priority.

## 🖼️ screenshots

![desktop preview](img.png)

## ❤️ credits

created by [void01n](https://github.com/void01n).

feel free to fork, modify, and make it your own.

if you find something broken or have an improvement, open an issue or pull request. 🚀
