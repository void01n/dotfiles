import type { ModuleCtx } from "../bar";

export function mountIdle(_ctx: ModuleCtx): void {
  const clockEl = document.getElementById("clock");
  if (!clockEl) throw new Error("idle module: #clock element missing");

  function tick() {
    clockEl!.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  tick();
  setInterval(tick, 15000);
}
