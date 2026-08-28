export interface Workspace { id: number; name: string; focused: boolean; }
export interface WindowInfo { title: string; class: string; }
export interface AudioState { volume: number; muted: boolean; }
export interface PowerState { present: boolean; percentage: number; charging: boolean; }
export interface ControlMsg { cmd: string; dir?: "back" | "forward"; face?: string; }

export const CYCLE_ORDER = ["idle", "workspace", "window", "audio", "power"];

export interface V0wwaBridge {
  workspace: {
    list(): Workspace[];
    onChange(cb: (list: Workspace[]) => void): void;
    focus(id: number): void;
  };
  window: {
    current(): WindowInfo | null;
    onFocus(cb: (win: WindowInfo | null) => void): void;
  };
  audio: {
    state(): AudioState;
    onChange(cb: (state: AudioState) => void): void;
  };
  power: {
    battery(): PowerState;
    onChange(cb: (state: PowerState) => void): void;
  };
}

declare global {
  interface Window {
    v0wwa: V0wwaBridge;
    __v0wwa_emit: (channel: string, payload: unknown) => void;
    __v0wwa_state: Record<string, unknown>;
  }
}

// Some modules mount before the WebKit-injected bridge script has finished
// setting window.v0wwa. Poll briefly instead of failing once and giving up.
export function onBridgeReady(fn: () => void): void {
  if (window.v0wwa) { fn(); return; }
  let tries = 0;
  const id = setInterval(() => {
    tries++;
    if (window.v0wwa) {
      clearInterval(id);
      fn();
    } else if (tries > 50) {
      clearInterval(id);
      console.error("[v0wwa] window.v0wwa never became available");
    }
  }, 100);
}
