import type { ModuleCtx } from "../bar";
import { onBridgeReady } from "../types";

export function mountPower(ctx: ModuleCtx): void {
  const labelEl = document.getElementById("battLabel");
  if (!labelEl) throw new Error("power module: #battLabel element missing");

  onBridgeReady(() => {
    let first = true;
    window.v0wwa.power.onChange(state => {
      labelEl!.textContent = state.percentage + "%" + (state.charging ? " ⚡" : "");
      if (first) { first = false; return; }
      const accent = state.percentage <= 20 && !state.charging ? "#ff5257" : "#4ade80";
      ctx.setState("power", { accent, ring: true, autoRevertMs: 2200 });
    });
  });
}
