import type { ModuleCtx } from "../bar";
import type { ControlMsg } from "../types";
import { CYCLE_ORDER } from "../types";

// Not a visual face — listens for {cmd:"cycle",dir:"back"|"forward"} sent
// via the v0wwa control socket (see niri keybind setup) and steps through
// CYCLE_ORDER accordingly.
export function mountControl(ctx: ModuleCtx): void {
  const orig = window.__v0wwa_emit;
  window.__v0wwa_emit = function (channel: string, payload: unknown) {
    if (channel === "control" && payload && (payload as ControlMsg).cmd === "cycle") {
      const msg = payload as ControlMsg;
      const dir = msg.dir === "back" ? -1 : 1;
      const idx = CYCLE_ORDER.indexOf(ctx.getCurrent());
      const next = CYCLE_ORDER[(idx + dir + CYCLE_ORDER.length) % CYCLE_ORDER.length];
      ctx.setState(next, { ring: true, force: true, autoRevertMs: next === "idle" ? null : 4000 });
      return;
    }
    orig(channel, payload);
  };
}
