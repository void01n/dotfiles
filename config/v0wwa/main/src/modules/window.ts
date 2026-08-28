import type { ModuleCtx } from "../bar";
import { onBridgeReady } from "../types";

export function mountWindow(ctx: ModuleCtx): void {
  const titleEl = document.getElementById("winTitle");
  const classEl = document.getElementById("winClass");
  if (!titleEl || !classEl) throw new Error("window module: title/class elements missing");

  onBridgeReady(() => {
    window.v0wwa.window.onFocus(win => {
      titleEl!.textContent = win?.title || "Desktop";
      classEl!.textContent = win?.class || "";
      ctx.setState("window", { accent: "#f2f2f4", ring: true, autoRevertMs: 2200 });
    });
  });
}
