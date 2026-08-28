import "./types";
import { mountIdle } from "./modules/idle";
import { mountWorkspace } from "./modules/workspace";
import { mountWindow } from "./modules/window";
import { mountAudio } from "./modules/audio";
import { mountPower } from "./modules/power";
import { mountControl } from "./modules/control";
import { mountScroll } from "./modules/scroll";

export interface Shape { width: number; height: number; radius: number; }
export interface SetStateOpts {
  accent?: string;
  ring?: boolean;
  force?: boolean;
  autoRevertMs?: number | null;
}
export interface ModuleCtx {
  island: HTMLElement;
  faces: HTMLElement[];
  setState: (name: string, opts?: SetStateOpts) => void;
  getCurrent: () => string;
}

const SHAPES: Record<string, Shape> = {
  idle:      { width: 130, height: 36, radius: 26 },
  workspace: { width: 118, height: 36, radius: 26 },
  window:    { width: 230, height: 44, radius: 24 },
  audio:     { width: 190, height: 40, radius: 22 },
  power:     { width: 140, height: 38, radius: 22 },
};

export { CYCLE_ORDER } from "./types";

function boot() {
  const island = document.getElementById("island");
  if (!island) {
    console.error("[v0wwa] #island element missing from bar.html");
    return;
  }
  const faces = Array.from(document.querySelectorAll<HTMLElement>(".face"));

  let current = "idle";
  let revertTimer: ReturnType<typeof setTimeout> | null = null;

  function setState(name: string, opts: SetStateOpts = {}) {
    const shape = SHAPES[name];
    if (!shape) {
      console.error(`[v0wwa] unknown face "${name}" — check SHAPES in bar.ts`);
      return;
    }
    if (name === current && !opts.force) return;
    current = name;

    island!.style.width = shape.width + "px";
    island!.style.height = shape.height + "px";
    island!.style.borderRadius = shape.radius + "px";
    faces.forEach(f => f.classList.toggle("active", f.dataset.face === name));
    if (opts.accent) island!.style.setProperty("--accent", opts.accent);
    if (opts.ring) {
      island!.classList.remove("ring");
      void island!.offsetWidth;
      island!.classList.add("ring");
    }
    if (revertTimer) clearTimeout(revertTimer);
    if (opts.autoRevertMs) {
      revertTimer = setTimeout(() => setState("idle"), opts.autoRevertMs);
    }
  }

  const ctx: ModuleCtx = { island, faces, setState, getCurrent: () => current };

  // Each mount() is wrapped so one broken module can't take down the rest.
  const mounts: [string, (ctx: ModuleCtx) => void][] = [
    ["idle", mountIdle],
    ["workspace", mountWorkspace],
    ["window", mountWindow],
    ["audio", mountAudio],
    ["power", mountPower],
    ["control", mountControl],
    ["scroll", mountScroll],
  ];

  for (const [name, mount] of mounts) {
    try {
      mount(ctx);
    } catch (e) {
      console.error(`[v0wwa] module "${name}" failed to mount:`, e);
    }
  }

  island.addEventListener("click", (e) => {
    if (e.target === island) setState("idle", { force: true });
  });
}

boot();
