#!/usr/bin/env bash
set -euo pipefail

# Run this from inside the cloned dots repo, e.g.:
#   git clone https://github.com/void01n/dots.git ~/dots
#   cd ~/dots
#   ./install.sh [fish|zsh]
#
# Shell mode defaults to "fish". Pass "zsh" to install ~/.zshrc (and a
# zsh/ config dir, if present in the repo) instead of the fish config.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_MODE="${1:-fish}"

case "$SHELL_MODE" in
    fish|zsh) ;;
    *)
        echo "error: unknown shell mode '$SHELL_MODE' (expected 'fish' or 'zsh')" >&2
        exit 1
        ;;
esac

# Runtime deps actually invoked by the configs in this repo. Add to this list
# whenever a config starts calling something new (e.g. sqlite for pkg's
# --rorphs feature).
REQUIRED_PKGS=(
    alacritty            # terminal emulator (alacritty.toml)
    python3              # runs catppuccinize.py
    fastfetch             # config.fish/.zshrc: neofetch/lolfetch aliases
    fortune               # config.fish/.zshrc: loltsay
    cowsay                # config.fish/.zshrc: loltsay
    cmatrix               # config.fish/.zshrc: xcmatrix
    eza                   # config.fish/.zshrc: ls/ll/lt aliases
    neovim                 # config.fish/.zshrc: EDITOR/VISUAL, nano alias
    zoxide                 # config.fish/.zshrc: zoxide init
    sqlite                 # pkg.fish: --rorphs companion db
    nerd-fonts.jetbrains-mono  # alacritty.toml font
)

if [ "$SHELL_MODE" = "fish" ]; then
    REQUIRED_PKGS+=(fish)
else
    REQUIRED_PKGS+=(zsh)
fi

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

    # Create packages.nix as a self-contained NixOS module.
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

    # Wire packages.nix into configuration.nix if it isn't already imported.
    if grep -qF './packages.nix' "$config"; then
        echo "configuration.nix already imports packages.nix"
    else
        backup "$config"

        if grep -qE '^[[:space:]]*imports[[:space:]]*=' "$config"; then
            # Handles both styles:
            #   imports = [ ./a.nix ./b.nix ];        (single line)
            #   imports = [                            (multi line)
            #     ./a.nix
            #   ];
            # awk tracks whether we're inside the imports [...] block and
            # inserts ./packages.nix right before the closing "];" no
            # matter which line that closer is on.
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
            # No imports block exists, so create one.
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
        echo "pkg was installed, but the configuration needs attention."
        return 1
    fi
}

install_shell_config() {
    if [ "$SHELL_MODE" = "fish" ]; then
        if [ -d "$REPO_DIR/fish" ]; then
            mkdir -p "$HOME/.config/fish"
            backup "$HOME/.config/fish"
            cp -r "$REPO_DIR/fish/." "$HOME/.config/fish/"
            echo "installed: ~/.config/fish"
        else
            echo "skip (not in repo): fish/"
        fi
        return
    fi

    # zsh mode: apply .zshrc, and a zsh/ config dir if the repo has one.
    # This does not touch ~/.config/fish, so fish stays installed
    # side-by-side if it's already there; zsh just becomes what gets
    # applied/activated by this run.
    local zshrc_src=""
    if [ -f "$REPO_DIR/zsh/.zshrc" ]; then
        zshrc_src="$REPO_DIR/zsh/.zshrc"
    elif [ -f "$REPO_DIR/zsh/zshrc" ]; then
        zshrc_src="$REPO_DIR/zsh/zshrc"
    elif [ -f "$REPO_DIR/.zshrc" ]; then
        zshrc_src="$REPO_DIR/.zshrc"
    fi

    if [ -n "$zshrc_src" ]; then
        install_file "$zshrc_src" "$HOME/.zshrc"
    else
        echo "skip (not in repo): .zshrc"
    fi

    if [ -d "$REPO_DIR/zsh" ]; then
        mkdir -p "$HOME/.config/zsh"
        backup "$HOME/.config/zsh"
        cp -r "$REPO_DIR/zsh/." "$HOME/.config/zsh/"
        echo "installed: ~/.config/zsh"
    else
        echo "skip (not in repo): zsh/"
    fi

    # Make zsh the login shell if it isn't already.
    local zsh_path
    zsh_path="$(command -v zsh || true)"
    if [ -n "$zsh_path" ] && [ "${SHELL:-}" != "$zsh_path" ]; then
        if chsh -s "$zsh_path" 2>/dev/null; then
            echo "changed login shell to: $zsh_path"
        else
            echo "WARNING: could not chsh to $zsh_path (try: chsh -s $zsh_path)"
        fi
    fi
}

echo "Shell mode: $SHELL_MODE"
echo

# fish or zsh config, depending on mode
install_shell_config

# alacritty
install_file \
    "$REPO_DIR/alacritty.toml" \
    "$HOME/.config/alacritty/alacritty.toml"

# catppuccinize
install_file \
    "$REPO_DIR/catppuccinize.py" \
    "$HOME/.config/shell/catppuccinize.py"

# cosmic shortcuts
install_file \
    "$REPO_DIR/cosmic-shortcuts.ron" \
    "$HOME/.config/cosmic/com.system76.CosmicSettings.Shortcuts/v1/custom"

# NixOS declarative package manager + runtime deps
setup_nixos_pkg

# cosmic.ron and wallpaper are imported manually via cosmic-settings,
# not copied here.
echo "skip: cosmic.ron (import manually via cosmic-settings)"
echo "skip: wallpaper (import manually via cosmic-settings)"

echo
echo "Done. Log out and back in (or restart cosmic-comp) for changes to take effect."
echo
echo "pkg is ready:"
echo "  pkg install <package>"
echo "  pkg remove <package> [--rorphs]"
echo "  pkg list"
echo "  pkg import"
echo "  pkg orphan add|rm <anchor> <companion>"
