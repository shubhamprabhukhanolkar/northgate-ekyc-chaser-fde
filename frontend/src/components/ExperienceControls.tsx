import {
  Moon,
  Sun,
  Volume2,
  VolumeX,
  WandSparkles,
  MessageSquareText,
} from "lucide-react";
import { useAudio } from "../context/AudioContext";
import { useTheme } from "../context/ThemeContext";
import { useDrafting } from "../context/DraftingContext";

export function DraftingModeToggle() {
  const { mode, setMode, busy } = useDrafting();
  return (
    <div
      className="draft-mode-switch"
      role="group"
      aria-label="Drafting style"
      title={
        busy
          ? "Drafting style can be changed when the current run finishes"
          : "Drafting style applies throughout your workspace"
      }
    >
      <button
        type="button"
        className="draft-choice-guided"
        disabled={busy}
        aria-pressed={mode === "guided"}
        onClick={() => setMode("guided")}
        title="Add your instructions before asking AI to draft"
      >
        <MessageSquareText size={13} />
        <span>Guided draft</span>
      </button>
      <button
        type="button"
        className="draft-choice-auto"
        disabled={busy}
        aria-pressed={mode === "auto"}
        onClick={() => setMode("auto")}
        title="AI prepares the draft automatically; you approve sending"
      >
        <WandSparkles size={13} />
        <span>Auto-draft</span>
      </button>
    </div>
  );
}

export function ThemeToggle() {
  const { dark, toggle } = useTheme();
  const { play } = useAudio();
  return (
    <button
      type="button"
      className={"theme-toggle " + (dark ? "is-dark" : "is-light")}
      aria-label="Toggle color theme"
      aria-pressed={!dark}
      title={
        dark
          ? "Dark mode active · switch to Light"
          : "Light mode active · switch to Dark"
      }
      data-sound="custom"
      onClick={() => {
        play(dark ? "light" : "dark");
        toggle();
      }}
    >
      <span className="theme-toggle-thumb" aria-hidden="true" />
      <span
        className={"theme-segment " + (dark ? "is-active" : "")}
        aria-hidden="true"
      >
        <Moon size={14} />
        Dark
      </span>
      <span
        className={"theme-segment " + (!dark ? "is-active" : "")}
        aria-hidden="true"
      >
        <Sun size={14} />
        Light
      </span>
    </button>
  );
}

export function AudioToggle() {
  const { enabled, supported, toggle } = useAudio();
  return (
    <button
      type="button"
      className={"audio-toggle " + (enabled ? "is-on" : "")}
      aria-label="Interface audio"
      aria-pressed={enabled}
      title={
        supported
          ? enabled
            ? "Turn interface sounds off"
            : "Turn interface sounds on · soft clicks and chimes"
          : "Interface audio is unavailable in this browser"
      }
      disabled={!supported}
      data-sound="custom"
      onClick={toggle}
    >
      <span className="audio-icon">
        {enabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
      </span>
      <span className="audio-label">
        Audio <span>{enabled ? "on" : "off"}</span>
      </span>
      <span className="audio-bars" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
    </button>
  );
}

export default function ExperienceControls({
  login = false,
  finance = false,
}: {
  login?: boolean;
  finance?: boolean;
}) {
  return (
    <div className={"experience-controls " + (login ? "login-controls" : "")}>
      {!login && !finance && <DraftingModeToggle />}
      {!login && <AudioToggle />}
      <ThemeToggle />
    </div>
  );
}
