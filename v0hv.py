#!/usr/bin/env python3
"""
v0hv -- void01n's helper for void01n's wonky widgets.

Feeds a pile of live system state into v0wwa over its unix control socket,
one channel per hook. Requires the v0wwa.py channel-passthrough patch.

Bespoke (event-driven) hooks:
  media   -- MPRIS via playerctl --follow
  notify  -- mako notifications via polled `makoctl list -j`

Generic (polled) hooks, each independently optional -- missing a dependency
just disables that one hook and prints why, everything else keeps running:
  network    -- active wifi SSID/signal via nmcli
  sysstat    -- cpu/ram/disk percent via /proc + shutil, no deps
  bluetooth  -- connected bluetooth devices via bluetoothctl
  brightness -- backlight percent via brightnessctl or /sys/class/backlight
  clipboard  -- clipboard text via wl-paste or xclip
  weather    -- current conditions via wttr.in (network only, no API key)
  diskalert  -- edge-triggered alert when / usage crosses a threshold
  custom     -- runs every executable script in ~/.config/v0hv/hooks.d/
  temp       -- thermal zone temps via /sys/class/thermal, no deps
  kblayout   -- active keyboard layout (niri/sway/hyprctl) + caps/num lock
                (lock state via /sys/class/leds, compositor-agnostic)
  uptime     -- uptime + load average via /proc, no deps

Run: python3 v0hv.py
Env:
  V0HV_WEATHER_LOC          -- location string for weather (default: IP geoloc)
  V0HV_DISKALERT_THRESHOLD  -- percent-full to alert at (default: 90)
"""
import os, sys, re, glob, json, socket, subprocess, shutil, threading, time
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

XDG_RUNTIME = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
HOOKS_DIR = os.path.join(XDG_CONFIG, "v0hv", "hooks.d")

MAKO_POLL_SEC = 0.7
NETWORK_POLL_SEC = 3.0
SYSSTAT_POLL_SEC = 2.0
BLUETOOTH_POLL_SEC = 5.0
BRIGHTNESS_POLL_SEC = 1.0
CLIPBOARD_POLL_SEC = 1.0
WEATHER_POLL_SEC = 900.0
DISKALERT_POLL_SEC = 30.0
DISKALERT_THRESHOLD = float(os.environ.get("V0HV_DISKALERT_THRESHOLD", "90"))
CUSTOM_POLL_SEC = 5.0
TEMP_POLL_SEC = 2.0
KBLAYOUT_POLL_SEC = 1.0
UPTIME_POLL_SEC = 5.0
WEATHER_LOC = os.environ.get("V0HV_WEATHER_LOC", "")


def find_sockets():
    return sorted(glob.glob(os.path.join(XDG_RUNTIME, "v0wwa-*.sock")))


def push(channel, payload):
    msg = json.dumps({"channel": channel, "payload": payload}).encode()
    for sock_path in find_sockets():
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect(sock_path)
            s.sendall(msg)
            s.close()
        except OSError as e:
            print(f"[v0hv] push to {sock_path} failed: {e!r}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Bespoke event-driven hooks (unchanged behavior from the original v0hv)
# ---------------------------------------------------------------------------

def media_loop():
    if not shutil.which("playerctl"):
        print("[v0hv] playerctl not found on PATH -- media hook disabled", file=sys.stderr)
        return
    fmt = "{{status}}\t{{artist}}\t{{title}}"
    while True:
        try:
            proc = subprocess.Popen(
                ["playerctl", "metadata", "--follow", "-f", fmt],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line:
                    continue
                parts = line.split("\t")
                status = parts[0] if len(parts) > 0 else ""
                artist = parts[1] if len(parts) > 1 else ""
                title = parts[2] if len(parts) > 2 else ""
                push("media", {
                    "playing": status.lower() == "playing",
                    "artist": artist,
                    "title": title,
                })
            print("[v0hv] playerctl --follow exited, restarting in 2s", file=sys.stderr)
        except Exception as e:
            print(f"[v0hv] media_loop error: {e!r}, retrying in 2s", file=sys.stderr)
        time.sleep(2)


def _flatten_mako_notification(flat_kv_list):
    out = {}
    for i in range(0, len(flat_kv_list) - 1, 2):
        key = flat_kv_list[i]
        val = flat_kv_list[i + 1]
        out[key] = val["data"] if isinstance(val, dict) and "data" in val else val
    return out


def _extract_notifications(parsed):
    results = []
    data = parsed.get("data", parsed) if isinstance(parsed, dict) else parsed

    def walk(node):
        if isinstance(node, dict):
            if "app-name" in node or "summary" in node:
                results.append(node)
            else:
                for v in node.values():
                    walk(v)
        elif isinstance(node, list):
            if node and isinstance(node[0], str) and len(node) >= 2 and isinstance(node[1], dict):
                results.append(_flatten_mako_notification(node))
            else:
                for item in node:
                    walk(item)

    walk(data)
    return results


def mako_loop():
    if not shutil.which("makoctl"):
        print("[v0hv] makoctl not found on PATH -- notify hook disabled", file=sys.stderr)
        return
    seen_ids = set()
    warned_once = False
    while True:
        try:
            result = subprocess.run(
                ["makoctl", "list", "-j"], capture_output=True, text=True, timeout=1.5,
            )
            if result.returncode != 0:
                if not warned_once:
                    print(f"[v0hv] `makoctl list -j` failed (rc={result.returncode}): "
                          f"{result.stderr.strip()} -- your mako may predate JSON output "
                          f"(needs 1.11.0+), or the flag differs. Check `makoctl list --help`.",
                          file=sys.stderr)
                    warned_once = True
                time.sleep(MAKO_POLL_SEC)
                continue
            parsed = json.loads(result.stdout)
            notifs = _extract_notifications(parsed)
            current_ids = set()
            for n in notifs:
                nid = n.get("id")
                if nid is None:
                    continue
                current_ids.add(nid)
                if nid not in seen_ids:
                    push("notify", {
                        "app": n.get("app-name", ""),
                        "summary": n.get("summary", ""),
                        "body": n.get("body", ""),
                    })
            seen_ids = current_ids
        except json.JSONDecodeError as e:
            if not warned_once:
                print(f"[v0hv] couldn't parse `makoctl list -j` output as JSON: {e!r} "
                      f"-- paste `makoctl list -j` output back if this keeps happening.",
                      file=sys.stderr)
                warned_once = True
        except Exception as e:
            print(f"[v0hv] mako_loop error: {e!r}", file=sys.stderr)
        time.sleep(MAKO_POLL_SEC)


# ---------------------------------------------------------------------------
# Generic polled-hook framework
# ---------------------------------------------------------------------------

@dataclass
class Hook:
    name: str
    interval: float
    check: Callable[[], bool]
    fetch: Callable[[], Optional[dict]]
    unavailable_msg: str


def run_hook(hook: Hook):
    if not hook.check():
        print(f"[v0hv] {hook.unavailable_msg}", file=sys.stderr)
        return
    last = None
    warned = False
    while True:
        try:
            payload = hook.fetch()
            if payload is not None and payload != last:
                push(hook.name, payload)
                last = payload
            warned = False
        except Exception as e:
            if not warned:
                print(f"[v0hv] {hook.name} hook error: {e!r}", file=sys.stderr)
                warned = True
        time.sleep(hook.interval)


def check_always_true():
    return True


# ---- network ----------------------------------------------------------

def _parse_nmcli_wifi(output_text):
    """Parse `nmcli -t -f active,ssid,signal,security dev wifi` output.
    nmcli's -t mode escapes literal ':' inside fields as '\\:'."""
    for line in output_text.splitlines():
        fields = re.split(r"(?<!\\):", line)
        fields = [f.replace("\\:", ":") for f in fields]
        if len(fields) >= 4 and fields[0] == "yes":
            signal = int(fields[2]) if fields[2].isdigit() else None
            return {"connected": True, "ssid": fields[1], "signal": signal, "security": fields[3]}
    return {"connected": False, "ssid": None, "signal": None, "security": None}


def fetch_network():
    out = subprocess.run(
        ["nmcli", "-t", "-f", "active,ssid,signal,security", "dev", "wifi"],
        capture_output=True, text=True, timeout=2.0,
    )
    return _parse_nmcli_wifi(out.stdout)


def check_network():
    return shutil.which("nmcli") is not None


# ---- sysstat (cpu/ram/disk) -- pure /proc + shutil, no external deps -----

_cpu_prev = None


def _read_proc_stat_cpu(text):
    parts = [int(x) for x in text.splitlines()[0].split()[1:]]
    idle = parts[3] + parts[4]
    total = sum(parts)
    return total, idle


def fetch_sysstat():
    global _cpu_prev
    total, idle = _read_proc_stat_cpu(open("/proc/stat").read())
    if _cpu_prev is None:
        _cpu_prev = (total, idle)
        cpu_pct = 0.0
    else:
        ptotal, pidle = _cpu_prev
        dtotal, didle = total - ptotal, idle - pidle
        cpu_pct = round(100.0 * (dtotal - didle) / dtotal, 1) if dtotal > 0 else 0.0
        _cpu_prev = (total, idle)
    meminfo = {}
    for line in open("/proc/meminfo"):
        k, v = line.split(":", 1)
        meminfo[k.strip()] = int(v.strip().split()[0])
    mem_total = meminfo.get("MemTotal", 1)
    mem_avail = meminfo.get("MemAvailable", mem_total)
    ram_pct = round(100.0 * (mem_total - mem_avail) / mem_total, 1)
    du = shutil.disk_usage("/")
    disk_pct = round(100.0 * du.used / du.total, 1)
    return {"cpu_pct": cpu_pct, "ram_pct": ram_pct, "disk_pct": disk_pct}


# ---- bluetooth ----------------------------------------------------------

_BT_DEVICE_RE = re.compile(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)")


def _parse_bluetoothctl_devices(output_text):
    devices = []
    for line in output_text.splitlines():
        m = _BT_DEVICE_RE.match(line.strip())
        if m:
            devices.append({"mac": m.group(1), "name": m.group(2)})
    return devices


def fetch_bluetooth():
    out = subprocess.run(["bluetoothctl", "devices", "Connected"],
                          capture_output=True, text=True, timeout=2.0)
    if out.returncode == 0:
        devices = _parse_bluetoothctl_devices(out.stdout)
    else:
        # older bluetoothctl without the "devices Connected" filter subcommand
        devices = []
        for d in _parse_bluetoothctl_devices(
            subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True, timeout=2.0).stdout
        ):
            info = subprocess.run(["bluetoothctl", "info", d["mac"]],
                                   capture_output=True, text=True, timeout=1.5)
            if "Connected: yes" in info.stdout:
                devices.append(d)
    return {"devices": devices, "count": len(devices)}


def check_bluetooth():
    return shutil.which("bluetoothctl") is not None


# ---- brightness -----------------------------------------------------------

def fetch_brightness():
    if shutil.which("brightnessctl"):
        out = subprocess.run(["brightnessctl", "-m"], capture_output=True, text=True, timeout=1.5)
        line = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
        parts = line.split(",")
        if len(parts) >= 4:
            pct = parts[3].rstrip("%")
            return {"percent": int(pct) if pct.isdigit() else None, "device": parts[0]}
    base = "/sys/class/backlight"
    if os.path.isdir(base):
        devices = os.listdir(base)
        if devices:
            d = devices[0]
            cur = int(open(os.path.join(base, d, "brightness")).read().strip())
            mx = int(open(os.path.join(base, d, "max_brightness")).read().strip())
            pct = round(100.0 * cur / mx, 1) if mx else None
            return {"percent": pct, "device": d}
    return None


def check_brightness():
    return shutil.which("brightnessctl") is not None or os.path.isdir("/sys/class/backlight")


# ---- clipboard --------------------------------------------------------

def fetch_clipboard():
    text = None
    if shutil.which("wl-paste"):
        out = subprocess.run(["wl-paste", "-n"], capture_output=True, text=True, timeout=1.5)
        if out.returncode == 0:
            text = out.stdout
    elif shutil.which("xclip"):
        out = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                              capture_output=True, text=True, timeout=1.5)
        if out.returncode == 0:
            text = out.stdout
    if text is None:
        return None
    text = text.strip()
    return {"text": text[:500], "truncated": len(text) > 500}


def check_clipboard():
    return shutil.which("wl-paste") is not None or shutil.which("xclip") is not None


# ---- weather (wttr.in, no API key) -------------------------------------

def _parse_wttr_json(data):
    cur = data["current_condition"][0]
    return {
        "temp_c": int(cur["temp_C"]),
        "feels_like_c": int(cur["FeelsLikeC"]),
        "desc": cur["weatherDesc"][0]["value"],
        "humidity": int(cur["humidity"]),
    }


def fetch_weather():
    url = f"https://wttr.in/{WEATHER_LOC}?format=j1"
    with urllib.request.urlopen(url, timeout=5.0) as resp:
        data = json.loads(resp.read().decode())
    return _parse_wttr_json(data)


def check_weather():
    return True  # network reachability is checked at fetch time, not here


# ---- diskalert (edge-triggered) ----------------------------------------

def fetch_diskalert():
    du = shutil.disk_usage("/")
    pct = round(100.0 * du.used / du.total, 1)
    return {"path": "/", "percent": pct, "alert": pct >= DISKALERT_THRESHOLD,
            "threshold": DISKALERT_THRESHOLD}


def check_diskalert():
    return True


# ---- custom user-script hooks ------------------------------------------

def fetch_custom():
    if not os.path.isdir(HOOKS_DIR):
        return None
    results = []
    for script in sorted(glob.glob(os.path.join(HOOKS_DIR, "*"))):
        if not os.access(script, os.X_OK):
            continue
        try:
            out = subprocess.run([script], capture_output=True, text=True, timeout=3.0)
            raw = out.stdout.strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            results.append({"hook": os.path.basename(script), "output": parsed})
        except Exception as e:
            results.append({"hook": os.path.basename(script), "error": str(e)})
    return {"results": results} if results else None


def check_custom():
    return True  # harmless no-op if HOOKS_DIR is empty or missing


# ---- temp (thermal zones) ----------------------------------------------

def fetch_temp():
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return None
    best = None
    for zone in sorted(glob.glob(os.path.join(base, "thermal_zone*"))):
        try:
            ztype = open(os.path.join(zone, "type")).read().strip()
            raw = int(open(os.path.join(zone, "temp")).read().strip())
        except (OSError, ValueError):
            continue
        c = raw / 1000.0
        is_cpu = any(k in ztype.lower() for k in ("cpu", "pkg", "core"))
        if best is None:
            best = {"zone": ztype, "temp_c": round(c, 1)}
        if is_cpu:
            best = {"zone": ztype, "temp_c": round(c, 1)}
            break
    return best


def check_temp():
    return len(glob.glob("/sys/class/thermal/thermal_zone*")) > 0


# ---- keyboard layout + lock state --------------------------------------

def _read_led_state(name_substr):
    base = "/sys/class/leds"
    if not os.path.isdir(base):
        return None
    for led in os.listdir(base):
        if name_substr in led.lower():
            try:
                return int(open(os.path.join(base, led, "brightness")).read().strip()) > 0
            except (OSError, ValueError):
                continue
    return None


def _parse_niri_layout(data):
    idx = data.get("current_idx")
    names = data.get("names", [])
    if idx is not None and 0 <= idx < len(names):
        return names[idx]
    return None


def _parse_sway_layout(devices):
    for dev in devices:
        if dev.get("type") == "keyboard" and "xkb_active_layout_name" in dev:
            return dev["xkb_active_layout_name"]
    return None


def _parse_hyprctl_layout(data):
    kbs = data.get("keyboards", [])
    return kbs[0].get("active_keymap") if kbs else None


def fetch_kblayout():
    layout = None
    try:
        if shutil.which("niri"):
            out = subprocess.run(["niri", "msg", "--json", "keyboard-layouts"],
                                  capture_output=True, text=True, timeout=1.0)
            layout = _parse_niri_layout(json.loads(out.stdout))
        elif shutil.which("swaymsg"):
            out = subprocess.run(["swaymsg", "-t", "get_inputs"],
                                  capture_output=True, text=True, timeout=1.0)
            layout = _parse_sway_layout(json.loads(out.stdout))
        elif shutil.which("hyprctl"):
            out = subprocess.run(["hyprctl", "devices", "-j"],
                                  capture_output=True, text=True, timeout=1.0)
            layout = _parse_hyprctl_layout(json.loads(out.stdout))
    except Exception:
        layout = None
    return {
        "layout": layout,
        "caps_lock": _read_led_state("capslock"),
        "num_lock": _read_led_state("numlock"),
    }


def check_kblayout():
    return True  # degrades to nulls if no compositor/LEDs found


# ---- uptime / load average ----------------------------------------------

def fetch_uptime():
    up_sec = float(open("/proc/uptime").read().split()[0])
    load1, load5, load15 = open("/proc/loadavg").read().split()[:3]
    return {"uptime_sec": int(up_sec), "load1": float(load1),
            "load5": float(load5), "load15": float(load15)}


def check_uptime():
    return os.path.exists("/proc/uptime")


HOOKS = [
    Hook("network", NETWORK_POLL_SEC, check_network, fetch_network,
         "nmcli not found -- network hook disabled"),
    Hook("sysstat", SYSSTAT_POLL_SEC, check_always_true, fetch_sysstat,
         "sysstat hook disabled"),
    Hook("bluetooth", BLUETOOTH_POLL_SEC, check_bluetooth, fetch_bluetooth,
         "bluetoothctl not found -- bluetooth hook disabled"),
    Hook("brightness", BRIGHTNESS_POLL_SEC, check_brightness, fetch_brightness,
         "no brightnessctl or /sys/class/backlight -- brightness hook disabled"),
    Hook("clipboard", CLIPBOARD_POLL_SEC, check_clipboard, fetch_clipboard,
         "no wl-paste or xclip found -- clipboard hook disabled"),
    Hook("weather", WEATHER_POLL_SEC, check_weather, fetch_weather,
         "weather hook disabled"),
    Hook("diskalert", DISKALERT_POLL_SEC, check_diskalert, fetch_diskalert,
         "diskalert hook disabled"),
    Hook("custom", CUSTOM_POLL_SEC, check_custom, fetch_custom,
         "custom hook disabled"),
    Hook("temp", TEMP_POLL_SEC, check_temp, fetch_temp,
         "no /sys/class/thermal zones -- temp hook disabled"),
    Hook("kblayout", KBLAYOUT_POLL_SEC, check_kblayout, fetch_kblayout,
         "kblayout hook disabled"),
    Hook("uptime", UPTIME_POLL_SEC, check_uptime, fetch_uptime,
         "uptime hook disabled"),
]


def main():
    sockets = find_sockets()
    if not sockets:
        print(f"[v0hv] no v0wwa-*.sock found in {XDG_RUNTIME} -- is v0wwa running?", file=sys.stderr)
    else:
        print(f"[v0hv] found sockets: {sockets}")

    threads = [
        threading.Thread(target=media_loop, daemon=True, name="media"),
        threading.Thread(target=mako_loop, daemon=True, name="notify"),
    ]
    for hook in HOOKS:
        threads.append(threading.Thread(target=run_hook, args=(hook,), daemon=True, name=hook.name))
    for t in threads:
        t.start()
    print(f"[v0hv] started {len(threads)} hook threads: " + ", ".join(t.name for t in threads))
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
