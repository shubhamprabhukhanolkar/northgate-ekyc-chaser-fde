import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { api, post } from "../api";
type User = { email: string; name: string; role: string };
const Auth = createContext<{
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  return (
    <Auth.Provider
      value={{
        user,
        loading,
        login: async (email, password) => {
          const data = await post("/auth/login", { email, password });
          setUser(data.user);
        },
        logout: async () => {
          await post("/auth/logout");
          setUser(null);
        },
      }}
    >
      {children}
    </Auth.Provider>
  );
}
export const useAuth = () => useContext(Auth);
