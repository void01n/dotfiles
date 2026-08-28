import type { ModuleCtx } from "../bar";
import type { Workspace } from "../types";
import { onBridgeReady } from "../types";

export function mountWorkspace(ctx: ModuleCtx): void {
  const track = document.getElementById("wsTrack");
  if (!track) throw new Error("workspace module: #wsTrack element missing");

  function render(list: Workspace[]) {
    track!.innerHTML = "";
    (list || []).forEach(ws => {
      const n = document.createElement("div");
      n.className = "ws-node" + (ws.focused ? " on" : "");
      n.title = ws.name;
      n.onclick = (e) => {
        e.stopPropagation();
        window.v0wwa.workspace.focus(ws.id);
      };
      track!.appendChild(n);
    });
  }

  onBridgeReady(() => {
    let first = true;
    window.v0wwa.workspace.onChange(list => {
      render(list);
      if (first) { first = false; return; }
      ctx.setState("workspace", { accent: "#f2f2f4", ring: true, autoRevertMs: 1400 });
    });
    render(window.v0wwa.workspace.list());
  });
}
