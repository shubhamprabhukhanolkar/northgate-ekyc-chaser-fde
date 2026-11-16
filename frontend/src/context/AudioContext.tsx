import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
} from "react";
import { soundEngine, SoundCue } from "../audio/sound";

const Audio = createContext({
  enabled: false,
  supported: true,
  toggle: () => {},
  play: (_cue: SoundCue) => {},
});

export function AudioProvider({ children }: { children: ReactNode }) {
  const supported = typeof window.AudioContext !== "undefined";
  const [enabled, setEnabled] = useState(
    () => supported && localStorage.getItem("northgate-audio") !== "off",
  );
  const enabledRef = useRef(enabled);

  const play = useCallback((cue: SoundCue) => {
    if (enabledRef.current && document.visibilityState === "visible")
      void soundEngine.play(cue);
  }, []);

  const toggle = useCallback(() => {
    if (!supported) return;
    const next = !enabledRef.current;
    enabledRef.current = next;
    setEnabled(next);
    localStorage.setItem("northgate-audio", next ? "on" : "off");
    if (next) void soundEngine.play("enable");
    else soundEngine.mute();
  }, [supported]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (!event.isTrusted || !(event.target instanceof Element)) return;
      const target = event.target.closest<HTMLElement>(
        "button, a[href], summary",
      );
      if (
        !target ||
        target.matches(":disabled, [aria-disabled='true']") ||
        target.closest("[data-sound='custom']")
      )
        return;
      play(target.closest("nav") ? "navigate" : "tap");
    };
    const onFeedback = (event: Event) => {
      const cue = (event as CustomEvent).detail;
      if (cue === "success" || cue === "notice") play(cue);
    };
    const onVisibility = () => {
      if (document.visibilityState !== "visible") soundEngine.mute();
    };
    document.addEventListener("click", onClick);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("northgate:audio-feedback", onFeedback);
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("northgate:audio-feedback", onFeedback);
    };
  }, [play]);

  return (
    <Audio.Provider value={{ enabled, supported, toggle, play }}>
      {children}
    </Audio.Provider>
  );
}

export const useAudio = () => useContext(Audio);
