🌌 void01n's dotfiles

a minimal, highly optimized nixos rice built around niri, ghostty, waybar, and a hybrid zsh + fish shell environment.

✦ features
window manager — niri for smooth, scrollable tiling across an infinite canvas.
terminal — ghostty for fast gpu-accelerated rendering and clean font handling.
launcher — fuzzel for a lightweight, native wayland application picker.
status bar — waybar with a custom layout, system telemetry, and power controls.
shell — zsh as the primary interactive shell, with fish handling custom package-management functions.
theming — catppuccin macchiato applied consistently across the desktop environment.
automation — an idempotent installer handles deployment, backups, package configuration, and nixos rebuilds.
✦ repository layout

the repository follows the xdg configuration structure while keeping each component isolated and easy to maintain.

.
├── config/
│   ├── fastfetch/     # system information and visual configuration
│   ├── fuzzel/        # application launcher configuration
│   ├── ghostty/       # terminal configuration and theme
│   ├── niri/          # window manager configuration and keybinds
│   └── waybar/        # status bar configuration and styling
├── fish/              # fish modules and package-management helpers
├── .zshrc             # interactive zsh configuration
├── catppuccinize.py   # theme deployment automation
└── install.sh         # nixos deployment and setup script

✦ installation

clone the repository, enter the directory, and run the installer.

git clone https://github.com/void01n/dotfiles ~/dots
cd ~/dots

chmod +x install.sh
./install.sh


the installer handles the rest automatically, including:

backing up existing configuration files
creating the required xdg directories
linking configuration files into place
configuring the package environment
updating /etc/nixos/packages.nix
rebuilding the nixos system
✦ safe deployments

the installer is designed to be safe to run on an existing system.

before replacing an existing file or directory, it creates a timestamped backup rather than deleting it.

~/.config/niri.bak.1787860861


this makes it easy to restore previous configurations or experiment without permanently losing existing tweaks.

✦ package management

the shell environment uses zsh for everyday interaction while delegating package
