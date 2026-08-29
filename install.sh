#!/usr/bin/env bash
# Complete installer tracking clean config/ folders and a root fish/ folder.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REQUIRED_PKGS=(
    ghostty
    fish
    python3
    fastfetch
    fortune
    cowsay
    cmatrix
    eza
    neovim
    zoxide
    sqlite
    nerd-fonts.jetbrains-mono
    fuzzel
    niri
    mako
    libnotify
    swaybg
    networkmanagerapplet
    zsh
    nodejs
    wireguard-tools
    wgcf
)

WGCF_DIR="$HOME/.config/wgcf"
WGCF_PROFILE="$WGCF_DIR/wgcf-profile.conf"
WGCF_ACCOUNT="$WGCF_DIR/wgcf-account.toml"

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

    if [ ! -f "$pkgfile" ]; then
        sudo tee "$pkgfile" >/dev/null <<'EOF'
{ pkgs, ... }:
{
  environment.systemPackages = with pkgs; [
  ];
}
EOF
        echo "created: $pkgfile"
    fi

    ensure_packages "$pkgfile" "${REQUIRED_PKGS[@]}"

    if ! grep -qF './packages.nix' "$config"; then
        backup "$config"
        if grep -qE '^[[:space:]]*imports[[:space:]]*=' "$config"; then
            sudo awk '
                BEGIN { in_imports = 0; done = 0 }
                {
                    if (!done && !in_imports && $0 ~ /^[[:space:]]*imports[[:space:]]*=/) { in_imports = 1 }
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
        else
            sudo tee -a "$config" >/dev/null <<'EOF'

imports = [
  ./packages.nix
];
EOF
        fi
        echo "configured: configuration.nix imports packages.nix"
    fi
}

setup_v0wwa_package() {
    if [ ! -f /etc/NIXOS ] && [ ! -f /etc/nixos/configuration.nix ]; then
        echo "skip: NixOS not detected, can't install v0wwa.nix"
        return
    fi

    local config="/etc/nixos/configuration.nix"
    sudo cp "$REPO_DIR/v0wwa.nix" /etc/nixos/v0wwa.nix
    echo "installed: /etc/nixos/v0wwa.nix"

    if grep -qF './v0wwa.nix' "$config"; then
        echo "already configured: configuration.nix imports v0wwa.nix"
        return
    fi

    backup "$config"

    if grep -qE '^[[:space:]]*imports[[:space:]]*=' "$config"; then
        sudo awk '
            BEGIN { in_imports = 0; done = 0 }
            {
                if (!done && !in_imports && $0 ~ /^[[:space:]]*imports[[:space:]]*=/) { in_imports = 1 }
                if (!done && in_imports && $0 ~ /\];/) {
                    idx = index($0, "];")
                    pre = substr($0, 1, idx - 1)
                    post = substr($0, idx)
                    print pre "./v0wwa.nix " post
                    in_imports = 0
                    done = 1
                    next
                }
                print
            }
        ' "$config" | sudo tee "$config.tmp" >/dev/null
        sudo mv "$config.tmp" "$config"
    else
        sudo tee -a "$config" >/dev/null <<'EOF'

imports = [
  ./v0wwa.nix
];
EOF
    fi

    if grep -qF './v0wwa.nix' "$config"; then
        echo "configured: configuration.nix imports v0wwa.nix"
    else
        echo "ERROR: failed to inject ./v0wwa.nix into $config -- add it manually" >&2
    fi
}

setup_wgcf_profile() {
    if ! command -v wgcf >/dev/null 2>&1; then
        echo "skip: wgcf not on PATH yet (will be available after nixos-rebuild) -- rerun to register profile"
        return
    fi

    mkdir -p "$WGCF_DIR"
    (
        cd "$WGCF_DIR"
        if [ ! -f "$WGCF_ACCOUNT" ]; then
            echo "registering new wgcf account..."
            wgcf register --accept-tos
        else
            echo "wgcf account already registered: $WGCF_ACCOUNT"
        fi

        if [ ! -f "$WGCF_PROFILE" ]; then
            echo "generating WireGuard profile..."
            wgcf generate
        else
            echo "profile already exists: $WGCF_PROFILE"
        fi
    )
}

install_cfwrp_function() {
    local fish_func="$HOME/.config/fish/functions/cfwrp.fish"
    mkdir -p "$(dirname "$fish_func")"
    cat > "$fish_func" <<EOF
function cfwrp
    if ip link show dev wgcf-profile >/dev/null 2>&1
        echo "⤵️ Disconnecting from Cloudflare WARP..."
        sudo wg-quick down $WGCF_PROFILE
    else
        echo "⤴️ Connecting to Cloudflare WARP..."
        sudo wg-quick up $WGCF_PROFILE
    end
end
EOF
    echo "installed: $fish_func"

    local zsh_func="$HOME/.config/shell/cfwrp.zsh"
    mkdir -p "$(dirname "$zsh_func")"
    cat > "$zsh_func" <<EOF
cfwrp() {
    if ip link show dev wgcf-profile >/dev/null 2>&1; then
        echo "⤵️ Disconnecting from Cloudflare WARP..."
        sudo wg-quick down $WGCF_PROFILE
    else
        echo "⤴️ Connecting to Cloudflare WARP..."
        sudo wg-quick up $WGCF_PROFILE
    fi
}
EOF
    echo "installed: $zsh_func"
    grep -qF "source $zsh_func" "$HOME/.zshrc" 2>/dev/null || \
        echo "source $zsh_func" >> "$HOME/.zshrc"
}

echo "Shell Profile target: Zsh with Fish backend modules"
echo

install_file "$REPO_DIR/.zshrc" "$HOME/.zshrc"

local_zsh="$(command -v zsh || true)"
if [ -n "$local_zsh" ] && [ "${SHELL:-}" != "$local_zsh" ]; then
    chsh -s "$local_zsh" 2>/dev/null || echo "Run 'chsh -s $local_zsh' manually to switch your shell."
fi

install_dir "$REPO_DIR/fish" "$HOME/.config/fish"

install_dir "$REPO_DIR/config/ghostty"   "$HOME/.config/ghostty"
install_dir "$REPO_DIR/config/fastfetch" "$HOME/.config/fastfetch"
install_dir "$REPO_DIR/config/fuzzel"    "$HOME/.config/fuzzel"
install_dir "$REPO_DIR/config/niri"      "$HOME/.config/niri"
install_dir "$REPO_DIR/config/mako"      "$HOME/.config/mako"
install_dir "$REPO_DIR/config/v0wwa"     "$HOME/.config/v0wwa"

install_file "$REPO_DIR/catppuccinize.py" "$HOME/.config/shell/catppuccinize.py"

install_file "$REPO_DIR/v0wwa.py" "$HOME/v0wwa.py"
chmod +x "$HOME/v0wwa.py"

install_file "$REPO_DIR/v0hv.py" "$HOME/v0hv.py"
chmod +x "$HOME/v0hv.py"

install_file "$REPO_DIR/v0ws-hotkeyd.py" "$HOME/v0ws-hotkeyd.py"
chmod +x "$HOME/v0ws-hotkeyd.py"

mkdir -p "$HOME/Pictures/wallpaper"
install_file "$REPO_DIR/nix-wallpaper-nineish-catppuccin-macchiato-alt.png" "$HOME/Pictures/wallpaper/nix.png"

setup_v0wwa_package
setup_nixos_pkg

install_cfwrp_function

echo
echo "Rebuilding NixOS..."
sudo nixos-rebuild switch

echo
echo "Registering wgcf profile (post-rebuild, now that wgcf is installed)..."
setup_wgcf_profile

echo
echo "Done!"