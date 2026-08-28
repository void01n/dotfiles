#!/usr/bin/env python3
"""
v0wwa b2 — multi-instance, multi-monitor host.

A GTK4 + gtk4-layer-shell + WebKitGTK bar host that loads an instance
directory (bar.html/src/dist/modules.json) and injects a live `v0wwa`
bridge object plus a `window.__v0wwa_config` manifest. Layout/order/module
config comes from modules.json; behavior (click, scroll, rendering) lives
entirely in each module's own .ts file.

Monitor handling is automatic: on launch, v0wwa enumerates all connected
outputs via GTK's display API and spawns one window per monitor, each
pinned to its own output and independently scoped (workspaces/active
window queries filtered to that output). No manual output config needed.
Set "output" explicitly in modules.json only to pin an instance to one
specific monitor instead of spawning on all of them.

Providers auto-detect the runtime environment:
  - compositor: niri, sway, or hyprland (whichever is found)
  - audio backend: wpctl or pactl
  - battery: first /sys/class/power_supply/BAT* found

Run:
  python3 v0wwa.py ~/.config/v0wwa/main
  python3 v0wwa.py ~/.config/v0wwa/second
  python3 v0wwa.py ~/.config/v0wwa/final
"""

import os, glob

def _discover_typelib_dirs():
    dirs = set()
    lib_dirs = set()
    for c in ["/usr/lib/girepository-1.0", "/usr/lib64/girepository-1.0", "/usr/lib/x86_64-linux-gnu/girepository-1.0", "/run/current-system/sw/lib/girepository-1.0"]:
        if os.path.isdir(c):
            dirs.add(c)
            lib_dirs.add(os.path.dirname(c))
    needed = {"WebKit-6.0.typelib", "Gtk4LayerShell-1.0.typelib"}
    for path in glob.glob("/nix/store/*/lib/girepository-1.0"):
        try:
            files = set(os.listdir(path))
        except OSError:
            continue
        if files & needed:
            dirs.add(path)
            lib_dirs.add(os.path.dirname(path))
    return dirs, lib_dirs

_typelib_dirs, _lib_dirs = _discover_typelib_dirs()
if _typelib_dirs:
    os.environ["GI_TYPELIB_PATH"] = ":".join(_typelib_dirs) + ((":" + os.environ["GI_TYPELIB_PATH"]) if os.environ.get("GI_TYPELIB_PATH") else "")
if _lib_dirs:
    os.environ["LD_LIBRARY_PATH"] = ":".join(_lib_dirs) + ((":" + os.environ["LD_LIBRARY_PATH"]) if os.environ.get("LD_LIBRARY_PATH") else "")

import sys

if not os.environ.get("_V0WWA_PRELOADED"):
    _so_matches = glob.glob("/nix/store/*gtk4-layer-shell*/lib/libgtk4-layer-shell.so*")
    if _so_matches:
        os.environ["LD_PRELOAD"] = _so_matches[0] + ((":" + os.environ["LD_PRELOAD"]) if os.environ.get("LD_PRELOAD") else "")
        os.environ["_V0WWA_PRELOADED"] = "1"
        os.execv(sys.executable, [sys.executable] + sys.argv)

import gi
import os
import sys
import json
import shutil
import socket
import subprocess
import threading
import atexit
import time
import traceback
from urllib.parse import quote

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, WebKit, Gtk4LayerShell as LayerShell, GLib, Gdk


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_INSTANCE_DIR = os.path.expanduser("~/.config/v0wwa/main")
POLL_INTERVAL_SEC = 1.0
XDG_RUNTIME = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

DEFAULT_MODULES_CONFIG = {
    "name": "main",
    "cycle_order": ["idle", "workspace", "window", "audio", "power"],
    "modules": {},
    "anchor": ["top", "left", "right"],
    "exclusive_zone": True,
    "margin": {},
    "width": 1920,
    "height": 36,
    # "output": "eDP-1"  # optional: pin to one monitor instead of spawning on all
}


def load_instance_config(instance_dir: str) -> dict:
    cfg = dict(DEFAULT_MODULES_CONFIG)
    cfg["name"] = os.path.basename(instance_dir.rstrip("/")) or "main"
    cfg_path = os.path.join(instance_dir, "modules.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"[v0wwa] failed to parse {cfg_path}: {e!r} -- using defaults")
    return cfg


def build_frontend(instance_dir: str):
    """Compile src/*.ts -> dist/bar.js via esbuild on every launch."""
    src_entry = os.path.join(instance_dir, "src", "bar.ts")
    dist_out = os.path.join(instance_dir, "dist", "bar.js")
    if not os.path.exists(src_entry):
        return
    os.makedirs(os.path.dirname(dist_out), exist_ok=True)
    try:
        result = subprocess.run(
            ["esbuild", src_entry, "--bundle", f"--outfile={dist_out}",
             "--target=es2020", "--format=iife"],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        print("[v0wwa] esbuild not found on PATH -- using existing dist/bar.js")
        return
    except subprocess.TimeoutExpired:
        print("[v0wwa] esbuild timed out -- using existing dist/bar.js")
        return
    if result.returncode != 0:
        print("[v0wwa] esbuild failed, falling back to existing dist/bar.js:\n" + result.stderr)
    else:
        print("[v0wwa] built dist/bar.js")


# ---------------------------------------------------------------------------
# Monitor discovery (GTK-level, compositor-agnostic)
# ---------------------------------------------------------------------------

def discover_monitors():
    """Returns a list of (connector_name, Gdk.Monitor) for every connected
    output, via GTK's own display API. On Wayland, Gdk.Monitor's connector
    name matches the compositor's own output name (e.g. niri's "eDP-1"),
    so this can be used directly to scope Providers per-output."""
    display = Gdk.Display.get_default()
    if display is None:
        return []
    monitors = display.get_monitors()
    result = []
    for i in range(monitors.get_n_items()):
        mon = monitors.get_item(i)
        name = None
        try:
            name = mon.get_connector()
        except Exception:
            pass
        if not name:
            name = f"monitor{i}"
        result.append((name, mon))
    return result


# ---------------------------------------------------------------------------
# System state providers (auto-detect compositor / audio backend / battery)
# ---------------------------------------------------------------------------

class Providers:
    def __init__(self, output=None):
        self._output = output
        self._battery_path = self._detect_battery_path()
        self._compositor = self._detect_compositor()
        self._audio_backend = self._detect_audio_backend()
        print(f"[v0wwa] compositor={self._compositor or 'none'} "
              f"audio={self._audio_backend or 'none'} "
              f"battery={self._battery_path or 'none'} "
              f"output={self._output or 'unscoped'}")

    def _detect_battery_path(self):
        candidates = sorted(glob.glob("/sys/class/power_supply/BAT*"))
        return candidates[0] if candidates else None

    def _detect_compositor(self):
        if shutil.which("niri"):
            return "niri"
        if shutil.which("swaymsg"):
            return "sway"
        if shutil.which("hyprctl"):
            return "hyprland"
        return None

    def _detect_audio_backend(self):
        if shutil.which("wpctl"):
            return "wpctl"
        if shutil.which("pactl"):
            return "pactl"
        return None

    # -- workspaces / active window -----------------------------------------

    def _niri_json(self, *args):
        out = subprocess.run(["niri", "msg", "--json", *args], capture_output=True, text=True, timeout=1.0)
        if out.returncode != 0:
            raise RuntimeError(f"niri msg failed: {out.stderr.strip()}")
        return json.loads(out.stdout)

    def _niri_ipc_action(self, action_payload: dict):
        """Send a raw Action over niri's IPC socket. Needed for actions
        (like FocusWorkspace-by-id) that the `niri msg` CLI doesn't expose
        an argument for, even though the underlying IPC protocol supports
        them (WorkspaceReferenceArg has Id/Index/Name variants; the CLI
        only parses index or name text)."""
        sock_path = os.environ.get("NIRI_SOCKET")
        if not sock_path:
            raise RuntimeError("NIRI_SOCKET env var not set")
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.0)
        try:
            s.connect(sock_path)
            msg = json.dumps({"Action": action_payload}) + "\n"
            s.sendall(msg.encode())
            resp = s.recv(4096).decode(errors="replace")
        finally:
            s.close()
        try:
            parsed = json.loads(resp)
        except Exception:
            raise RuntimeError(f"niri IPC returned non-JSON: {resp!r}")
        if isinstance(parsed, dict) and "Err" in parsed:
            raise RuntimeError(f"niri IPC error: {parsed['Err']}")
        return parsed

    def _find_focused_sway(self, node):
        if node.get("focused"):
            return node
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            found = self._find_focused_sway(child)
            if found:
                return found
        return None

    def workspaces(self):
        if self._compositor == "niri":
            data = self._niri_json("workspaces")
            if self._output:
                data = [w for w in data if w.get("output") == self._output]
            return sorted(
                [{"id": w["id"], "name": str(w.get("idx", w["id"])), "focused": w["is_active"]} for w in data],
                key=lambda w: next(x.get("idx", x["id"]) for x in data if x["id"] == w["id"]),
            )
        if self._compositor == "sway":
            out = subprocess.run(["swaymsg", "-t", "get_workspaces"], capture_output=True, text=True, timeout=1.0)
            if out.returncode != 0:
                raise RuntimeError(f"swaymsg failed: {out.stderr.strip()}")
            data = json.loads(out.stdout)
            if self._output:
                data = [w for w in data if w.get("output") == self._output]
            return [{"id": w["num"], "name": w["name"], "focused": w["focused"]} for w in data]
        if self._compositor == "hyprland":
            out = subprocess.run(["hyprctl", "-j", "workspaces"], capture_output=True, text=True, timeout=1.0)
            if out.returncode != 0:
                raise RuntimeError(f"hyprctl failed: {out.stderr.strip()}")
            active = subprocess.run(["hyprctl", "-j", "activeworkspace"], capture_output=True, text=True, timeout=1.0)
            active_id = json.loads(active.stdout).get("id") if active.returncode == 0 else None
            data = json.loads(out.stdout)
            if self._output:
                data = [w for w in data if w.get("monitor") == self._output]
            return sorted(
                [{"id": w["id"], "name": w.get("name", str(w["id"])), "focused": w["id"] == active_id} for w in data],
                key=lambda w: w["id"],
            )
        raise RuntimeError("no supported compositor found (looked for niri, sway, hyprland)")

    def active_window(self):
        if self._compositor == "niri":
            data = self._niri_json("focused-window")
            if not data:
                return None
            if self._output:
                ws_list = self._niri_json("workspaces")
                ws_by_id = {w["id"]: w for w in ws_list}
                win_ws = ws_by_id.get(data.get("workspace_id"))
                if win_ws and win_ws.get("output") != self._output:
                    return None
            return {"title": data.get("title", ""), "class": data.get("app_id", "")}
        if self._compositor == "sway":
            out = subprocess.run(["swaymsg", "-t", "get_tree"], capture_output=True, text=True, timeout=1.0)
            if out.returncode != 0:
                raise RuntimeError(f"swaymsg failed: {out.stderr.strip()}")
            node = self._find_focused_sway(json.loads(out.stdout))
            if not node:
                return None
            cls = node.get("app_id") or (node.get("window_properties") or {}).get("class", "")
            return {"title": node.get("name") or "", "class": cls}
        if self._compositor == "hyprland":
            out = subprocess.run(["hyprctl", "-j", "activewindow"], capture_output=True, text=True, timeout=1.0)
            if out.returncode != 0:
                raise RuntimeError(f"hyprctl failed: {out.stderr.strip()}")
            data = json.loads(out.stdout)
            if not data:
                return None
            if self._output and data.get("monitor") not in (None, self._output):
                return None
            return {"title": data.get("title", ""), "class": data.get("class", "")}
        raise RuntimeError("no supported compositor found (looked for niri, sway, hyprland)")

    def focus_workspace(self, ws_id):
        if self._compositor == "niri":
            self._niri_ipc_action({"FocusWorkspace": {"reference": {"Id": int(ws_id)}}})
        elif self._compositor == "sway":
            subprocess.run(["swaymsg", "workspace", "number", str(ws_id)], timeout=1.0)
        elif self._compositor == "hyprland":
            subprocess.run(["hyprctl", "dispatch", "workspace", str(ws_id)], timeout=1.0)

    def shift_workspace(self, direction):
        """Move focus to the next/prev workspace within THIS bar's own
        output, regardless of which output currently has input focus."""
        ws = self.workspaces()
        if not ws:
            return
        idx = next((i for i, w in enumerate(ws) if w["focused"]), 0)
        step = 1 if direction == "next" else -1
        new_idx = (idx + step) % len(ws)
        self.focus_workspace(ws[new_idx]["id"])

    # -- audio ----------------------------------------------------------

    def audio(self):
        if self._audio_backend == "wpctl":
            out = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True, timeout=1.0).stdout.strip()
            parts = out.split()
            vol = float(parts[1]) if len(parts) > 1 else 0.0
            muted = "[MUTED]" in out
            return {"volume": round(vol, 3), "muted": muted}
        if self._audio_backend == "pactl":
            vol_out = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], capture_output=True, text=True, timeout=1.0).stdout
            mute_out = subprocess.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], capture_output=True, text=True, timeout=1.0).stdout
            pct = 0.0
            for tok in vol_out.split():
                if tok.endswith("%"):
                    pct = float(tok.rstrip("%")) / 100.0
                    break
            return {"volume": round(pct, 3), "muted": "yes" in mute_out.lower()}
        raise RuntimeError("no supported audio backend found (looked for wpctl, pactl)")

    # -- battery ----------------------------------------------------------

    def battery(self):
        if not self._battery_path:
            return {"present": False, "percentage": 100, "charging": True}
        pct = int(open(f"{self._battery_path}/capacity").read().strip())
        status = open(f"{self._battery_path}/status").read().strip()
        return {"present": True, "percentage": pct, "charging": status == "Charging"}


class ControlServer:
    def __init__(self, bridge, socket_path):
        self.bridge = bridge
        self.socket_path = socket_path
        self._stop = threading.Event()
        self._srv = None

    def _handle(self, conn):
        with conn:
            data = b""
            conn.settimeout(1.0)
            try:
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            except socket.timeout:
                pass
            if not data:
                return
            try:
                msg = json.loads(data.decode())
            except Exception:
                return
            if msg.get("cmd") == "shift_workspace":
                self.bridge.handle_inbound({
                    "action": "shift_workspace",
                    "direction": msg.get("direction", "next"),
                })
                return
            if "channel" in msg:
                self.bridge.push(msg["channel"], msg.get("payload"))
                return
            self.bridge.push("control", msg)

    def serve(self):
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.socket_path)
        srv.listen(4)
        srv.settimeout(1.0)
        self._srv = srv
        while not self._stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
        srv.close()
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

    def stop(self):
        self._stop.set()


class Bridge:
    CHANNELS = ("workspace", "window", "audio", "power", "control")

    def __init__(self, webview: WebKit.WebView, providers: Providers):
        self.webview = webview
        self.providers = providers
        self._last = {ch: None for ch in self.CHANNELS}
        self._sent_once = set()
        self._stop = threading.Event()

    def _run_js(self, js: str):
        GLib.idle_add(self._exec_js, js)

    def _exec_js(self, js: str):
        try:
            self.webview.evaluate_javascript(js, -1, None, None, None, None, None)
        except Exception:
            traceback.print_exc()
        return False

    def push(self, channel: str, payload):
        encoded = json.dumps(payload)
        js = f"window.__v0wwa_emit && window.__v0wwa_emit({json.dumps(channel)}, {encoded});"
        self._run_js(js)

    def _poll_once(self):
        try:
            ws = self.providers.workspaces()
        except Exception as e:
            print(f"[v0wwa] workspaces() failed: {e!r}")
            ws = []
        if ws != self._last["workspace"] or "workspace" not in self._sent_once:
            self._last["workspace"] = ws
            self._sent_once.add("workspace")
            self.push("workspace", ws)

        try:
            win = self.providers.active_window()
        except Exception as e:
            print(f"[v0wwa] active_window() failed: {e!r}")
            win = None
        if win != self._last["window"] or "window" not in self._sent_once:
            self._last["window"] = win
            self._sent_once.add("window")
            self.push("window", win)

        try:
            aud = self.providers.audio()
        except Exception as e:
            print(f"[v0wwa] audio() failed: {e!r}")
            aud = {"volume": 0, "muted": False}
        if aud != self._last["audio"] or "audio" not in self._sent_once:
            self._last["audio"] = aud
            self._sent_once.add("audio")
            self.push("audio", aud)

        try:
            bat = self.providers.battery()
        except Exception as e:
            print(f"[v0wwa] battery() failed: {e!r}")
            bat = {"present": False, "percentage": 100, "charging": True}
        if bat != self._last["power"] or "power" not in self._sent_once:
            self._last["power"] = bat
            self._sent_once.add("power")
            self.push("power", bat)

    def poll_loop(self):
        while not self._stop.is_set():
            try:
                self._poll_once()
            except Exception:
                traceback.print_exc()
            time.sleep(POLL_INTERVAL_SEC)

    def stop(self):
        self._stop.set()

    def force_sync(self):
        """Push current state for all channels unconditionally, bypassing
        the change-diff check. Called once the webview finishes loading,
        so the frontend always gets a real value even if the very first
        poll fired before window.__v0wwa_emit existed yet."""
        try:
            ws = self.providers.workspaces()
        except Exception as e:
            print(f"[v0wwa] workspaces() failed: {e!r}")
            ws = []
        self._last["workspace"] = ws
        self._sent_once.add("workspace")
        self.push("workspace", ws)

        try:
            win = self.providers.active_window()
        except Exception as e:
            print(f"[v0wwa] active_window() failed: {e!r}")
            win = None
        self._last["window"] = win
        self._sent_once.add("window")
        self.push("window", win)

        try:
            aud = self.providers.audio()
        except Exception as e:
            print(f"[v0wwa] audio() failed: {e!r}")
            aud = {"volume": 0, "muted": False}
        self._last["audio"] = aud
        self._sent_once.add("audio")
        self.push("audio", aud)

        try:
            bat = self.providers.battery()
        except Exception as e:
            print(f"[v0wwa] battery() failed: {e!r}")
            bat = {"present": False, "percentage": 100, "charging": True}
        self._last["power"] = bat
        self._sent_once.add("power")
        self.push("power", bat)

    def handle_inbound(self, action: dict):
        print(f"[v0wwa] inbound action: {action}")
        try:
            if action.get("action") == "focus_workspace":
                self.providers.focus_workspace(action["id"])
            elif action.get("action") == "shift_workspace":
                self.providers.shift_workspace(action.get("direction", "next"))
        except Exception:
            traceback.print_exc()


# Bridge JS: onChange() replays the last-known value immediately on
# registration, so a module that mounts after the first poll already
# fired still gets current state -- no per-module manual pull required.
V0WWA_API_JS = r"""
(function() {
    const CHANNELS = ["workspace", "window", "audio", "power", "media", "notify"];
    const listeners = {};
    const received = {};
    CHANNELS.forEach(function(ch) { listeners[ch] = []; received[ch] = false; });

    window.__v0wwa_state = {
        workspace: [],
        window: null,
        audio: { volume: 0, muted: false },
        power: { present: false, percentage: 100, charging: true },
        media: null,
        notify: null,
    };

    window.__v0wwa_emit = function(channel, payload) {
        window.__v0wwa_state[channel] = payload;
        received[channel] = true;
        (listeners[channel] || []).forEach(function(cb) {
            try { cb(payload); } catch (e) { console.error("v0wwa listener error:", channel, e); }
        });
    };

    function post(action) {
        window.webkit.messageHandlers.v0wwa.postMessage(JSON.stringify(action));
    }

    function onChange(channel, cb) {
        if (typeof cb !== "function") return;
        listeners[channel].push(cb);
        if (received[channel]) {
            try { cb(window.__v0wwa_state[channel]); } catch (e) { console.error("v0wwa replay error:", channel, e); }
        }
    }

    window.v0wwa = {
        workspace: {
            list: function() { return window.__v0wwa_state.workspace; },
            onChange: function(cb) { onChange("workspace", cb); },
            focus: function(id) { post({ action: "focus_workspace", id: id }); },
            shift: function(direction) { post({ action: "shift_workspace", direction: direction }); },
        },
        window: {
            current: function() { return window.__v0wwa_state.window; },
            onFocus: function(cb) { onChange("window", cb); },
        },
        audio: {
            state: function() { return window.__v0wwa_state.audio; },
            onChange: function(cb) { onChange("audio", cb); },
        },
        power: {
            battery: function() { return window.__v0wwa_state.power; },
            onChange: function(cb) { onChange("power", cb); },
        },
        media: {
            current: function() { return window.__v0wwa_state.media; },
            onChange: function(cb) { onChange("media", cb); },
        },
        notify: {
            current: function() { return window.__v0wwa_state.notify; },
            onChange: function(cb) { onChange("notify", cb); },
        },
    };
})();
"""


def on_script_message(_content_mgr, js_result, bridge: Bridge):
    try:
        raw = js_result.to_json(0) if hasattr(js_result, "to_json") else js_result.get_js_value().to_string()
        data = json.loads(raw)
    except Exception:
        traceback.print_exc()
        return
    bridge.handle_inbound(data)


def build_window(app, instance_dir: str, cfg: dict, monitor=None):
    bar_html_path = os.path.join(instance_dir, "bar.html")
    output_name = cfg.get("output")

    win = Gtk.ApplicationWindow(application=app)
    win.add_css_class("v0wwa-transparent")
    win.set_default_size(cfg.get("width", 1920), cfg.get("height", 36))

    print(f"[v0wwa:{cfg['name']}] layer-shell supported:", LayerShell.is_supported())
    LayerShell.init_for_window(win)
    LayerShell.set_layer(win, LayerShell.Layer.TOP)

    if monitor is not None:
        LayerShell.set_monitor(win, monitor)

    anchors = set(cfg.get("anchor", ["top", "left", "right"]))
    LayerShell.set_anchor(win, LayerShell.Edge.TOP, "top" in anchors)
    LayerShell.set_anchor(win, LayerShell.Edge.LEFT, "left" in anchors)
    LayerShell.set_anchor(win, LayerShell.Edge.RIGHT, "right" in anchors)
    LayerShell.set_anchor(win, LayerShell.Edge.BOTTOM, "bottom" in anchors)

    margin = cfg.get("margin", {})
    for edge_name, edge in [("top", LayerShell.Edge.TOP), ("left", LayerShell.Edge.LEFT),
                             ("right", LayerShell.Edge.RIGHT), ("bottom", LayerShell.Edge.BOTTOM)]:
        if edge_name in margin:
            LayerShell.set_margin(win, edge, margin[edge_name])

    if cfg.get("exclusive_zone", True):
        LayerShell.auto_exclusive_zone_enable(win)
    LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.ON_DEMAND)
    ns_suffix = f"-{output_name}" if output_name else ""
    LayerShell.set_namespace(win, f"v0wwa-{cfg['name']}{ns_suffix}")

    css = Gtk.CssProvider()
    css.load_from_data(b"window.v0wwa-transparent { background: transparent; }")
    Gtk.StyleContext.add_provider_for_display(win.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    content_mgr = WebKit.UserContentManager()
    content_mgr.register_script_message_handler("v0wwa")

    api_script = WebKit.UserScript.new(
        V0WWA_API_JS,
        WebKit.UserContentInjectedFrames.ALL_FRAMES,
        WebKit.UserScriptInjectionTime.START,
        None, None,
    )
    content_mgr.add_script(api_script)

    config_js = f"window.__v0wwa_config = {json.dumps(cfg)};"
    config_script = WebKit.UserScript.new(
        config_js,
        WebKit.UserContentInjectedFrames.ALL_FRAMES,
        WebKit.UserScriptInjectionTime.START,
        None, None,
    )
    content_mgr.add_script(config_script)

    webview = WebKit.WebView(user_content_manager=content_mgr)
    webview.get_settings().set_enable_developer_extras(True)
    _transparent = Gdk.RGBA(); _transparent.parse("rgba(0,0,0,0)"); webview.set_background_color(_transparent)

    providers = Providers(output=output_name)
    bridge = Bridge(webview, providers)
    content_mgr.connect("script-message-received::v0wwa", on_script_message, bridge)

    def _on_load_changed(_webview, event, _bridge=None):
        if event == WebKit.LoadEvent.FINISHED:
            bridge.force_sync()
    webview.connect("load-changed", _on_load_changed)

    if not os.path.exists(bar_html_path):
        print(f"[v0wwa:{cfg['name']}] warning: {bar_html_path} not found, loading blank page")
        webview.load_html("<body style='background:#111;color:#fff;font-family:sans-serif;"
                           "display:flex;align-items:center;padding-left:12px'>"
                           f"no bar.html at {bar_html_path}</body>", None)
    else:
        webview.load_uri("file://" + quote(bar_html_path))

    win.set_child(webview)

    poll_thread = threading.Thread(target=bridge.poll_loop, daemon=True)
    poll_thread.start()

    socket_path = f"{XDG_RUNTIME}/v0wwa-{cfg['name']}{ns_suffix}.sock"
    ctrl = ControlServer(bridge, socket_path)
    threading.Thread(target=ctrl.serve, daemon=True).start()

    def on_close(_):
        bridge.stop()
        ctrl.stop()

    key_controller = Gtk.EventControllerKey.new()
    key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

    def on_key_pressed(_controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Right:
            bridge.handle_inbound({"action": "shift_workspace", "direction": "next"})
            return True
        if keyval == Gdk.KEY_Left:
            bridge.handle_inbound({"action": "shift_workspace", "direction": "prev"})
            return True
        return False

    key_controller.connect("key-pressed", on_key_pressed)
    win.add_controller(key_controller)

    win.connect("destroy", on_close)
    win.present()
    return win


def main():
    instance_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INSTANCE_DIR
    instance_dir = os.path.abspath(os.path.expanduser(instance_dir))

    build_frontend(instance_dir)
    cfg = load_instance_config(instance_dir)

    app = Gtk.Application(application_id=f"dev.void01n.v0wwa.{cfg['name']}")

    def on_activate(a):
        hotkeyd_env = dict(os.environ)
        hotkeyd_env["PYTHONPATH"] = (
            "/nix/store/avs8b6nifyc92gwcic4wv2bcrfkwl6lb-python3.14-evdev-1.9.3/lib/python3.14/site-packages"
            + (":" + hotkeyd_env["PYTHONPATH"] if hotkeyd_env.get("PYTHONPATH") else "")
        )
        hotkeyd_path = os.path.expanduser("~/v0ws-hotkeyd.py")
        try:
            hotkeyd_proc = subprocess.Popen(
                ["python3", hotkeyd_path],
                env=hotkeyd_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[v0wwa] spawned v0ws-hotkeyd (pid {hotkeyd_proc.pid})")
            atexit.register(hotkeyd_proc.terminate)
        except Exception as e:
            print(f"[v0wwa] failed to spawn v0ws-hotkeyd: {e}")

        v0hv_path = os.path.expanduser("~/v0hv.py")
        try:
            v0hv_proc = subprocess.Popen(["python3", v0hv_path], env=dict(os.environ), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[v0wwa] spawned v0hv (pid {v0hv_proc.pid})")
            atexit.register(v0hv_proc.terminate)
        except Exception as e:
            print(f"[v0wwa] failed to spawn v0hv: {e}")

        if cfg.get("output"):
            # Explicit pin in modules.json -- single instance on that output.
            monitors = discover_monitors()
            match = next((m for name, m in monitors if name == cfg["output"]), None)
            if match is None:
                print(f"[v0wwa] warning: configured output {cfg['output']!r} not found among "
                      f"connected monitors {[n for n, _ in monitors]!r} -- launching unpinned")
            build_window(a, instance_dir, dict(cfg), monitor=match)
            return

        monitors = discover_monitors()
        if not monitors:
            print("[v0wwa] warning: no monitors detected via GTK, launching unpinned")
            build_window(a, instance_dir, dict(cfg), monitor=None)
            return

        print(f"[v0wwa] detected {len(monitors)} monitor(s): {[n for n, _ in monitors]!r}")
        for name, mon in monitors:
            inst_cfg = dict(cfg)
            inst_cfg["output"] = name
            build_window(a, instance_dir, inst_cfg, monitor=mon)

    app.connect("activate", on_activate)
    app.run(None)


if __name__ == "__main__":
    main()
