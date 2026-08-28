import type { ModuleCtx } from "../bar";
import { onBridgeReady } from "../types";

export function mountAudio(ctx: ModuleCtx): void {
  const labelEl = document.getElementById("volLabel");
  const fillEl = document.getElementById("volFill");
  if (!labelEl || !fillEl) throw new Error("audio module: label/fill elements missing");

  onBridgeReady(() => {
    let first = true;
    window.v0wwa.audio.onChange(state => {
      const pct = Math.round((state.volume || 0) * 100);
      labelEl!.textContent = state.muted ? "muted" : pct + "%";
      fillEl!.style.width = pct + "%";
      if (first) { first = false; return; }
      ctx.setState("audio", { accent: state.muted ? "#ff5257" : "#6ee7ff", ring: true, autoRevertMs: 1600 });
    });
  });
}
