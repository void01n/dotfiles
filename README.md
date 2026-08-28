void01n's dotfiles

a minimal and highly optimized nixos rice built around niri, ghostty, waybar, and a hybrid zsh + fish shell environment.

features
window manager: niri for smooth, scrollable tiling across an infinite canvas.
terminal: ghostty for fast gpu-accelerated rendering and clean font handling.
application launcher: fuzzel for a lightweight, native wayland application picker.
status bar: waybar with custom telemetry, system information, and power controls.
shell: zsh as the primary interactive shell with fish handling custom package-management functions.
theming: catppuccin macchiato across the desktop environment.
automation: an idempotent installer for backups, configuration deployment, package setup, and nixos rebuilds.
repository layout
.
├── config/
│   ├── fastfetch/     # system information configuration
│   ├── fuzzel/        # application launcher configuration
│   ├── ghostty/       # terminal configuration
│   ├── niri/          # window manager configuration
│   └── waybar/        # status bar configuration and styling
├── fish/              # fish modules and package helpers
├── .zshrc             # interactive zsh configuration
├── catppuccinize.py   # theme deployment script
└── install.sh         # nixos deployment script

installation

clone the repository and run the installer:

git clone https://github.com/void01n/dotfiles ~/dots
cd ~/dots

chmod +x install.sh
./install.sh


the installer handles the deployment automatically, including:

backing up existing configuration files
creating required xdg directories
installing configuration files
configuring package management
updating /etc/nixos/packages.nix
rebuilding the nixos system
backups

existing files are never overwritten without first creating a backup.

backups use an absolute unix timestamp:

~/.config/niri.bak.1787860861


this makes it possible to safely experiment with the configuration while keeping previous versions available for recovery.

package management

the interactive shell runs through zsh, while package-related functionality is handled by fish.

the .zshrc exposes the fish package helper through a simple alias:

alias pkg="fish -c pkg"


this keeps the main shell configuration lightweight while allowing package-management functionality to remain modular inside the fish/ directory.

the installer also handles the required nixos package declarations and metadata configuration automatically.

design philosophy

this configuration focuses on three things:

minimalism
performance
maintainability

each component is kept modular and follows the xdg configuration structure where possible. the goal is a fast and clean wayland desktop that requires minimal manual maintenance.

credits

created by void01n.

feel free to fork the repository, customize it, or open an issue with suggestions and improvements.
