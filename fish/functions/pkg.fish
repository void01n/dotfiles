function _pkg_reqs --description "runtime requisites for a nixpkgs attribute name"
    set -l name $argv[1]
    set -l path (nix eval --raw "nixpkgs#$name.outPath" 2>/dev/null)
    if test -z "$path"
        return 1
    end
    nix-store --query --requisites $path 2>/dev/null \
        | string replace -r '^.*-' '' \
        | string match -rv '^(source|dev|doc|man|info|debug)$'
end

set -g _pkg_db "$HOME/.config/pkg/orphans.db"

function _pkg_db_init --description "create the companions db if it doesn't exist yet"
    mkdir -p (dirname $_pkg_db)
    sqlite3 $_pkg_db "CREATE TABLE IF NOT EXISTS companions (anchor TEXT NOT NULL, companion TEXT NOT NULL, PRIMARY KEY (anchor, companion));"
end

function _pkg_orphans --description "companions of a removed anchor, not claimed by any other surviving anchor"
    set -l removed_name $argv[1]
    set -l current $argv[2..-1]
    _pkg_db_init
    for companion in (sqlite3 $_pkg_db "SELECT companion FROM companions WHERE anchor = '$removed_name';")
        if contains -- $companion $current
            set -l claimed 0
            for anchor in (sqlite3 $_pkg_db "SELECT DISTINCT anchor FROM companions WHERE companion = '$companion';")
                if test "$anchor" != "$removed_name"; and contains -- $anchor $current
                    set claimed 1
                    break
                end
            end
            if test $claimed = 0
                echo $companion
            end
        end
    end
end

function pkg --description "declarative-feeling pkg manager for packages.nix"
    set -l pkgfile /etc/nixos/packages.nix
    set -l cmd $argv[1]
    set -l rorphs 0
    set -l names
    for a in $argv[2..-1]
        if test "$a" = "--rorphs"
            set rorphs 1
        else
            set -a names $a
        end
    end

    switch $cmd
        case install
            if test -z "$names"
                echo "usage: pkg install <name> [name...]"
                return 1
            end
            for name in $names
                set -l re (string escape --style=regex -- $name)
                if grep -qE "^\s*$re\s*\$" $pkgfile
                    echo "already installed: $name"
                    continue
                end
                echo "checking: $name"
                nix eval --raw "nixpkgs#$name.outPath" >/dev/null 2>&1
                if test $status -eq 0
                    sudo sed -i "/^\s*\];/i\\    $name" $pkgfile
                    echo "added: $name"
                else
                    echo "invalid, skipped: $name"
                end
            end

        case remove
            if test -z "$names"
                echo "usage: pkg remove <name> [name...] [--rorphs]"
                return 1
            end

            set -l current (grep -E "^\s*[a-zA-Z0-9_.-]+\s*\$" $pkgfile | string trim)
            set -l to_remove $names

            # rdeps: always prune runtime deps that only the removed names needed.
            # a dep is only pruned if no *surviving* package's closure also needs it.
            for name in $names
                for dep in (_pkg_reqs $name)
                    if contains -- $dep $current; and test "$dep" != "$name"
                        set -l claimed_elsewhere 0
                        for other in $current
                            if test "$other" != "$name"; and not contains -- $other $names
                                if contains -- $dep (_pkg_reqs $other)
                                    set claimed_elsewhere 1
                                    break
                                end
                            end
                        end
                        if test $claimed_elsewhere = 0
                            echo "  + dep of $name: $dep"
                            set -a to_remove $dep
                        end
                    end
                end
            end

            # rorphs: companion packages (e.g. hyprpaper alongside hyprland) that
            # have no actual nix dependency link, so they're tracked in a small
            # sqlite db instead. opt-in via --rorphs since it's not derivable.
            if test $rorphs = 1
                for name in $names
                    for orphan in (_pkg_orphans $name $current)
                        echo "  + orphan of $name: $orphan"
                        set -a to_remove $orphan
                    end
                end
            end

            set -l to_remove (printf '%s\n' $to_remove | sort -u)
            echo "will remove: $to_remove"
            read -P "confirm? [y/N] " -l confirm
            if test "$confirm" != y -a "$confirm" != Y
                echo "aborted"
                return 1
            end

            for name in $to_remove
                set -l re (string escape --style=regex -- $name)
                if grep -qE "^\s*$re\s*\$" $pkgfile
                    sudo sed -i "/^\s*$re\s*\$/d" $pkgfile
                    echo "removed: $name"
                else
                    echo "not found: $name"
                end
            end

        case list
            grep -E "^\s*[a-zA-Z0-9_.-]+\s*\$" $pkgfile | string trim

        case import
            for name in (nix profile list | string match -r 'Flake attribute:\s+legacyPackages\.x86_64-linux\.(.+)$' -g)
                set -l re (string escape --style=regex -- $name)
                if grep -qE "^\s*$re\s*\$" $pkgfile
                    echo "already installed: $name"
                else
                    sudo sed -i "/^\s*\];/i\\    $name" $pkgfile
                    echo "imported: $name"
                end
            end

        case orphan
            _pkg_db_init
            switch $names[1]
                case add
                    if test (count $names) -lt 3
                        echo "usage: pkg orphan add <anchor> <companion>"
                        return 1
                    end
                    sqlite3 $_pkg_db "INSERT OR IGNORE INTO companions (anchor, companion) VALUES ('$names[2]', '$names[3]');"
                    echo "linked: $names[3] -> $names[2]"
                case rm
                    if test (count $names) -lt 3
                        echo "usage: pkg orphan rm <anchor> <companion>"
                        return 1
                    end
                    sqlite3 $_pkg_db "DELETE FROM companions WHERE anchor = '$names[2]' AND companion = '$names[3]';"
                    echo "unlinked: $names[3] -> $names[2]"
                case list
                    sqlite3 -header -column $_pkg_db "SELECT anchor, companion FROM companions ORDER BY anchor;"
                case "*"
                    echo "usage: pkg orphan add|rm <anchor> <companion>"
                    echo "       pkg orphan list"
            end
            return 0

        case "*"
            echo "usage: pkg install|remove|list|import|orphan [name...] [--rorphs]"
            return 1
    end

    if test "$cmd" = install -o "$cmd" = remove -o "$cmd" = import
        if sudo nixos-rebuild switch
            set -l msg "pkg $cmd $names"
            sudo git -C /etc/nixos add -A
            if sudo git -C /etc/nixos commit -m "$msg" --allow-empty
                echo "nix committed: $msg"
                if sudo git -C /etc/nixos push
                    echo "nix pushed to origin"
                else
                    echo "nix commit ok, push failed"
                end
            else
                echo "nix: nothing to commit"
            end
        else
            echo "rebuild failed — not committing"
        end
    end
end
