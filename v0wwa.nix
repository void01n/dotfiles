{ pkgs, ... }:
let
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [ pygobject3 evdev ]);
  gi_packages = with pkgs; [ gtk4 gtk4-layer-shell webkitgtk_6_0 pango.dev graphene harfbuzz gdk-pixbuf glib gsettings-desktop-schemas ];
in
{
  environment.systemPackages = [
    (pkgs.symlinkJoin {
      name = "v0wwa";
      paths = [ pythonEnv ];
      buildInputs = [ pkgs.makeWrapper ];
      postBuild = ''
        makeWrapper ${pythonEnv}/bin/python3 $out/bin/v0wwa \
          --prefix GI_TYPELIB_PATH : "${pkgs.lib.makeSearchPath "lib/girepository-1.0" gi_packages}" \
          --run 'export GI_TYPELIB_PATH="$(c=$HOME/.cache/v0wwa_pangocairo_dir; [ -f "$c" ] && cat "$c" || { f=$(find /nix/store -maxdepth 5 -name PangoCairo-1.0.typelib 2>/dev/null | head -1); if [ -n "$f" ]; then d=$(dirname "$f"); mkdir -p "$(dirname "$c")"; echo "$d" > "$c"; echo "$d"; fi; }):$GI_TYPELIB_PATH"' \
          --run 'exec "'"${pythonEnv}"'/bin/python3" "$HOME/v0wwa.py" "$HOME/.config/v0wwa/main"'
      '';
    })
    pkgs.esbuild
  ];
}
