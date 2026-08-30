#!/usr/bin/env python3
import asyncio, os, subprocess, sys
import evdev
from evdev import ecodes

V0WS_PATH = os.path.expanduser("~/v0ws.py")
ctrl_held = set()
alt_held = set()
CTRL_CODES = {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL}
ALT_CODES = {ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT}

def spawn(direction):
    subprocess.run(["niri", "msg", "action", "focus-workspace-up" if direction == "prev" else "focus-workspace-down"], check=False)

def find_keyboards():
    devices = []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except (PermissionError, OSError) as e:
            print(f"v0ws-hotkeyd: cannot open {path}: {e}", file=sys.stderr)
            continue
        caps = dev.capabilities().get(ecodes.EV_KEY, [])
        if ecodes.KEY_A in caps and ecodes.KEY_RIGHT in caps:
            devices.append(dev)
    return devices

async def watch(dev):
    async for event in dev.async_read_loop():
        if event.type != ecodes.EV_KEY:
            continue
        code = event.code
        value = event.value
        if code in CTRL_CODES:
            if value == 1: ctrl_held.add(code)
            elif value == 0: ctrl_held.discard(code)
        elif code in ALT_CODES:
            if value == 1: alt_held.add(code)
            elif value == 0: alt_held.discard(code)
        elif value == 1 and ctrl_held and alt_held:
            if code == ecodes.KEY_RIGHT:
                spawn("next")
            elif code == ecodes.KEY_LEFT:
                spawn("prev")

async def main():
    devices = find_keyboards()
    if not devices:
        print("v0ws-hotkeyd: no keyboard devices found/readable -- check group membership", file=sys.stderr)
        sys.exit(1)
    print(f"v0ws-hotkeyd: watching {len(devices)} device(s): " + ", ".join(d.path for d in devices))
    await asyncio.gather(*(watch(d) for d in devices))

if __name__ == "__main__":
    asyncio.run(main())
