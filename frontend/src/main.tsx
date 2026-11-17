import React from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import { AudioProvider } from "./context/AudioContext";
import { DraftingProvider } from "./context/DraftingContext";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CaseQueuePage from "./pages/CaseQueuePage";
import ChaserWorkspacePage from "./pages/ChaserWorkspacePage";
import NudgeTrackerPage from "./pages/NudgeTrackerPage";
import AgentTracePage from "./pages/TracePage";
import TonerStudioPage from "./pages/TonerStudioPage";
import FinOpsDashboardPage from "./pages/FinOpsDashboardPage";
import PortalGuidePage from "./pages/PortalGuidePage";
import ConnectionsPage from "./pages/ConnectionsPage";
import { Loading } from "./components/UI";
import "./styles.css";
function App() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Loading />;
  if (!user) return <LoginPage />;
  if (location.pathname === "/login") return <Navigate to="/" />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CaseQueuePage />} />
        <Route path="workspace" element={<ChaserWorkspacePage />} />
        <Route path="nudges" element={<NudgeTrackerPage />} />
        <Route path="trace" element={<AgentTracePage />} />
        <Route path="studio" element={<TonerStudioPage />} />
        <Route path="finops" element={<FinOpsDashboardPage />} />
        <Route path="policy" element={<PortalGuidePage />} />
        <Route path="connections" element={<ConnectionsPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <AudioProvider>
        <DraftingProvider>
          <AuthProvider>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </AuthProvider>
        </DraftingProvider>
      </AudioProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
