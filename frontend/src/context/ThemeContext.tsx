import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
const Theme = createContext({ dark: true, toggle: () => {} });
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [dark, setDark] = useState(
    localStorage.getItem("northgate-theme") !== "light",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("northgate-theme", dark ? "dark" : "light");
  }, [dark]);
  return (
    <Theme.Provider value={{ dark, toggle: () => setDark((v) => !v) }}>
      {children}
    </Theme.Provider>
  );
}
export const useTheme = () => useContext(Theme);
