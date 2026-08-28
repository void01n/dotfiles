#!/usr/bin/env bash
# Complete installer tracking clean config/ folders and a root fish/ folder.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# System dependencies for NixOS
REQUIRED_PKGS=(
    ghostty               # terminal emulator
    fish                  # required for fish -c commands and pkg manager aliases
    python3              # runs catppuccinize.py
    fastfetch             # system info display
    fortune               # terminal quotes
    cowsay                # speech bubble display
    cmatrix               # matrix screen effect
    eza                   # modern ls replacement
    neovim                 # text editor
    zoxide                 # smart cd command
    sqlite                 # pkg.fish metadata tracking
    nerd-fonts.jetbrains-mono  # system terminal font
    fuzzel                # wayland application launcher
    niri                  # tiling window manager
    waybar                # custom status bar
    mako                  # notification daemon
    libnotify              # provides notify-send for testing notifications
    swaybg                 # wallpaper setter for wlroots compositors
    networkmanagerapplet   # network manager applet for a systray icon
    zsh                   # primary interactive login shell
)

backup() {
    local dest="$1"
    if [ -f "$dest" ] || [ -d "$dest" ]; then
        cp -r "$dest" "$dest.bak.$(date +%s)"
        echo "backed up: $dest"
    fi
}

install_file() {
    local src="$1" dest="$2"
    if [ ! -f "$src" ]; then
        echo "skip (not in repo): $src"
        return
    fi
    mkdir -p "$(dirname "$dest")"
    backup "$dest"
    cp "$src" "$dest"
    echo "installed: $dest"
}

install_dir() {
    local src="$1" dest="$2"
    if [ ! -d "$src" ]; then
        echo "skip (not in repo): $src"
        return
    fi
    mkdir -p "$dest"
    backup "$dest"
    cp -r "$src/." "$dest/"
    echo "installed: $dest"
}

ensure_packages() {
    local pkgfile="$1"
    shift
    local pkgs=("$@")

    if [ ! -f "$pkgfile" ]; then
        echo "skip: $pkgfile not found, can't declare packages"
        return
    fi

    for name in "${pkgs[@]}"; do
        if grep -qE "^\s*${name}\s*\$" "$pkgfile"; then
            echo "already declared: $name"
            continue
        fi
        sudo sed -i "/^\s*\];/i\\    ${name}" "$pkgfile"
        echo "declared: $name"
    done
}

setup_nixos_pkg() {
    if [ ! -f /etc/NIXOS ] && [ ! -f /etc/nixos/configuration.nix ]; then
        echo "skip: NixOS not detected"
        return
    fi

    local nixos_dir="/etc/nixos"
    local pkgfile="$nixos_dir/packages.nix"
    local config="$nixos_dir/configuration.nix"

    if [ ! -f "$config" ]; then
        echo "skip: /etc/nixos/configuration.nix not found"
        return
    fi

    echo
    echo "Setting up declarative pkg..."

    if [ ! -f "$pkgfile" ]; then
        sudo tee "$pkgfile" >/dev/null <<'EOF'
{ pkgs, ... }:
{
  environment.systemPackages = with pkgs; [
  ];
}
EOF
        echo "created: $pkgfile"
    else
        echo "exists: $pkgfile"
    fi

    echo
    echo "Declaring dotfiles runtime dependencies..."
    ensure_packages "$pkgfile" "${REQUIRED_PKGS[@]}"

    if grep -qF './packages.nix' "$config"; then
        echo "configuration.nix already imports packages.nix"
    else
        backup "$config"

        if grep -qE '^[[:space:]]*imports[[:space:]]*=' "$config"; then
            sudo awk '
                BEGIN { in_imports = 0; done = 0 }
                {
                    if (!done && !in_imports && $0 ~ /^[[:space:]]*imports[[:space:]]*=/) {
                        in_imports = 1
                    }
                    if (!done && in_imports && $0 ~ /\];/) {
                        idx = index($0, "];")
                        pre = substr($0, 1, idx - 1)
                        post = substr($0, idx)
                        print pre "./packages.nix " post
                        in_imports = 0
                        done = 1
                        next
                    }
                    print
                }
            ' "$config" | sudo tee "$config.tmp" >/dev/null
            sudo mv "$config.tmp" "$config"
            echo "configured: configuration.nix imports packages.nix"
        else
            sudo tee -a "$config" >/dev/null <<'EOF'

imports = [
  ./packages.nix
];
EOF
            echo "configured: added imports block for packages.nix"
        fi
    fi

    echo
    echo "Testing NixOS configuration..."
    if sudo nixos-rebuild build; then
        echo "NixOS configuration is valid."
    else
        echo "WARNING: NixOS configuration failed to build."
        return 1
    fi
}

echo "Shell Profile target: Zsh with Fish backend modules"
echo

# 1. Install Zsh Profile (Directly from Root-level .zshrc)
install_file "$REPO_DIR/.zshrc" "$HOME/.zshrc"

# Enforce Zsh as primary interactive login shell environment
local_zsh="$(command -v zsh || true)"
if [ -n "$local_zsh" ] && [ "${SHELL:-}" != "$local_zsh" ]; then
    chsh -s "$local_zsh" 2>/dev/null || echo "Run 'chsh -s $local_zsh' manually to switch your shell."
fi

# 2. Install Fish Functions (Deploys your root fish/ directory to ~/.config/fish)
install_dir "$REPO_DIR/fish" "$HOME/.config/fish"

# 3. Install App Configurations (from the config/ directory)
install_dir "$REPO_DIR/config/ghostty"   "$HOME/.config/ghostty"
install_dir "$REPO_DIR/config/fastfetch" "$HOME/.config/fastfetch"
install_dir "$REPO_DIR/config/fuzzel"    "$HOME/.config/fuzzel"
install_dir "$REPO_DIR/config/niri"      "$HOME/.config/niri"
install_dir "$REPO_DIR/config/waybar"    "$HOME/.config/waybar"
install_dir "$REPO_DIR/config/mako"      "$HOME/.config/mako"

# 4. Python Helper Scripts
install_file "$REPO_DIR/catppuccinize.py" "$HOME/.config/shell/catppuccinize.py"

# 5. Ensure waybar helper scripts (e.g. mako-status.sh) are executable after install
if [ -d "$HOME/.config/waybar/scripts" ]; then
    chmod +x "$HOME/.config/waybar/scripts/"*.sh 2>/dev/null || true
    echo "made executable: waybar scripts"
fi

# 6. Wallpaper setup
mkdir -p "$HOME/Pictures/wallpaper"
install_file "$REPO_DIR/nix-wallpaper-nineish-catppuccin-macchiato-alt.png" "$HOME/Pictures/wallpaper/nix.png"

NIRI_CONFIG="$HOME/.config/niri/config.kdl"
if [ -f "$NIRI_CONFIG" ] && ! grep -qF 'swaybg' "$NIRI_CONFIG"; then
    echo 'spawn-at-startup "swaybg" "-i" "'"$HOME"'/Pictures/wallpaper/nix.png" "-m" "fill"' >> "$NIRI_CONFIG"
    echo "configured: swaybg autostart in niri"
else
    echo "skip: swaybg already configured or niri config missing"
fi

# 7. Declarative package generation & validation
setup_nixos_pkg

echo
echo "Done! Fish packages and configurations have been successfully linked."