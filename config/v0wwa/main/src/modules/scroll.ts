import type { ModuleCtx } from "../bar";
import { CYCLE_ORDER } from "../types";

// Scrolling on the island cycles forward/backward through faces,
// same step logic as the control-socket cycle command.
export function mountScroll(ctx: ModuleCtx): void {
  let lastFire = 0;
  const THROTTLE_MS = 220; // avoid one scroll gesture firing 5 steps at once

  ctx.island.addEventListener(
    "wheel",
    (e: WheelEvent) => {
      e.preventDefault();
      const now = Date.now();
      if (now - lastFire < THROTTLE_MS) return;
      lastFire = now;

      const dir = e.deltaY > 0 ? 1 : -1; // scroll down = forward, up = back
      const idx = CYCLE_ORDER.indexOf(ctx.getCurrent());
      const next = CYCLE_ORDER[(idx + dir + CYCLE_ORDER.length) % CYCLE_ORDER.length];
      ctx.setState(next, { ring: true, force: true, autoRevertMs: next === "idle" ? null : 4000 });
    },
    { passive: false }
  );
}
