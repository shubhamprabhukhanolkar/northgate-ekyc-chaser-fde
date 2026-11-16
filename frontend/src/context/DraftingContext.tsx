import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

export type DraftingMode = "auto" | "guided";
const Drafting = createContext({
  mode: "guided" as DraftingMode,
  setMode: (_mode: DraftingMode) => {},
  busy: false,
  registerBusy: (_owner: symbol, _active: boolean) => {},
});

export function DraftingProvider({ children }: { children: ReactNode }) {
  const [mode, updateMode] = useState<DraftingMode>(() =>
    localStorage.getItem("northgate-draft-mode") === "auto" ? "auto" : "guided",
  );
  const [owners, setOwners] = useState<Set<symbol>>(() => new Set());
  const setMode = useCallback((next: DraftingMode) => {
    localStorage.setItem("northgate-draft-mode", next);
    updateMode(next);
  }, []);
  const registerBusy = useCallback((owner: symbol, active: boolean) => {
    setOwners((previous) => {
      if (previous.has(owner) === active) return previous;
      const next = new Set(previous);
      if (active) next.add(owner);
      else next.delete(owner);
      return next;
    });
  }, []);
  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === "northgate-draft-mode")
        updateMode(event.newValue === "auto" ? "auto" : "guided");
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);
  return (
    <Drafting.Provider
      value={{ mode, setMode, busy: owners.size > 0, registerBusy }}
    >
      {children}
    </Drafting.Provider>
  );
}

export const useDrafting = () => useContext(Drafting);
