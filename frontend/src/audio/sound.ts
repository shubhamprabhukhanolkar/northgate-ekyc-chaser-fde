export type SoundCue =
  | "tap"
  | "navigate"
  | "light"
  | "dark"
  | "enable"
  | "success"
  | "notice"
  | "scan"
  | "plan"
  | "write"
  | "polish"
  | "verify"
  | "ready"
  | "reroute"
  | "flip";

// Small, original synthesized cues: no downloads, tracking, or looping audio.
const scores: Record<SoundCue, [number, number, number][]> = {
  scan: [
    [392, 0, 0.1],
    [784, 0.055, 0.13],
  ],
  plan: [
    [440, 0, 0.15],
    [554.37, 0.055, 0.19],
  ],
  write: [
    [523.25, 0, 0.085],
    [659.25, 0.045, 0.11],
    [783.99, 0.09, 0.17],
  ],
  polish: [
    [659.25, 0, 0.16],
    [987.77, 0.07, 0.23],
  ],
  verify: [
    [783.99, 0, 0.13],
    [1046.5, 0.09, 0.21],
  ],
  ready: [
    [523.25, 0, 0.28],
    [659.25, 0.07, 0.3],
    [783.99, 0.14, 0.34],
    [1046.5, 0.23, 0.42],
  ],
  reroute: [
    [587.33, 0, 0.12],
    [440, 0.075, 0.13],
    [587.33, 0.15, 0.2],
  ],
  flip: [
    [293.66, 0, 0.12],
    [440, 0.055, 0.15],
    [587.33, 0.11, 0.2],
  ],
  tap: [[560, 0, 0.065]],
  navigate: [
    [440, 0, 0.09],
    [660, 0.045, 0.12],
  ],
  light: [
    [523.25, 0, 0.16],
    [783.99, 0.07, 0.22],
    [1046.5, 0.14, 0.26],
  ],
  dark: [
    [783.99, 0, 0.16],
    [523.25, 0.065, 0.22],
    [392, 0.13, 0.26],
  ],
  enable: [
    [523.25, 0, 0.18],
    [659.25, 0.075, 0.2],
    [783.99, 0.15, 0.3],
  ],
  success: [
    [659.25, 0, 0.15],
    [783.99, 0.09, 0.18],
    [1046.5, 0.18, 0.28],
  ],
  notice: [
    [349.23, 0, 0.13],
    [329.63, 0.14, 0.17],
  ],
};

class SoundEngine {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private lastTap = 0;
  private generation = 0;

  async play(cue: SoundCue) {
    // Dense clicks should feel like one gesture, not a flurry of notifications.
    if (cue === "tap" || cue === "navigate") {
      if (performance.now() - this.lastTap < 110) return;
      this.lastTap = performance.now();
    }
    const generation = this.generation;
    try {
      if (!this.context) {
        this.context = new AudioContext();
        this.master = this.context.createGain();
        const limiter = this.context.createDynamicsCompressor();
        limiter.threshold.value = -18;
        limiter.ratio.value = 5;
        this.master.connect(limiter);
        limiter.connect(this.context.destination);
      }
      const context = this.context;
      if (context.state === "suspended") await context.resume();
      if (generation !== this.generation || context.state !== "running") return;
      const master = this.master!;
      master.gain.setValueAtTime(0.14, context.currentTime);
      for (const [frequency, offset, duration] of scores[cue]) {
        const oscillator = context.createOscillator();
        const envelope = context.createGain();
        const pan = context.createStereoPanner();
        const start = context.currentTime + offset;
        oscillator.type =
          cue === "flip" || cue === "scan" ? "triangle" : "sine";
        oscillator.frequency.setValueAtTime(frequency, start);
        oscillator.frequency.exponentialRampToValueAtTime(
          frequency * 0.99,
          start + duration,
        );
        envelope.gain.setValueAtTime(0, start);
        envelope.gain.linearRampToValueAtTime(
          cue === "flip" || cue === "scan" ? 0.12 : 0.23,
          start + 0.008,
        );
        envelope.gain.exponentialRampToValueAtTime(0.001, start + duration);
        oscillator.connect(envelope);
        pan.pan.setValueAtTime(cue === "flip" ? -0.45 : -0.12, start);
        pan.pan.linearRampToValueAtTime(
          cue === "flip" ? 0.45 : 0.12,
          start + duration,
        );
        envelope.connect(pan);
        pan.connect(master);
        oscillator.start(start);
        oscillator.stop(start + duration + 0.02);
        oscillator.onended = () => {
          oscillator.disconnect();
          envelope.disconnect();
          pan.disconnect();
        };
      }
    } catch {
      // Unsupported audio or browser playback policy never interrupts a task.
    }
  }

  mute() {
    this.generation += 1;
    if (this.context && this.master) {
      this.master.gain.cancelScheduledValues(this.context.currentTime);
      this.master.gain.setValueAtTime(0, this.context.currentTime);
    }
  }
}

export const soundEngine = new SoundEngine();

export function actionFeedback(cue: "success" | "notice") {
  window.dispatchEvent(
    new CustomEvent("northgate:audio-feedback", { detail: cue }),
  );
}
