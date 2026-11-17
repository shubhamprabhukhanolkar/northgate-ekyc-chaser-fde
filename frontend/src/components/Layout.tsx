import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Inbox,
  FileCheck2,
  Clock3,
  Workflow,
  SlidersHorizontal,
  ChartNoAxesCombined,
  Bot,
  Link2,
  Landmark,
  LogOut,
  ShieldCheck,
  Globe,
  Command,
  PanelLeftClose,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import ExperienceControls from "./ExperienceControls";
import { api } from "../api";
import { Pill, usePoll } from "./UI";
const links = [
  ["/", "Case Queue", Inbox],
  ["/workspace", "Gap Workspace", FileCheck2],
  ["/nudges", "3-Day Nudges", Clock3],
  ["/trace", "Agent Trace", Workflow],
  ["/studio", "Toner Studio", SlidersHorizontal],
  ["/finops", "FinOps & Impact", ChartNoAxesCombined],
  ["/executive", "Executive Dashboard", Landmark],
  ["/policy", "Portal Guide", Bot],
  ["/connections", "Connected Apps", Link2],
] as const;
export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [menu, setMenu] = useState(false);
  const { data: runtime } = usePoll(() => api("/runtime"));
  return (
    <div className={"shell " + (menu ? "menu-open" : "")}>
      <aside>
        <a className="brand" href="/">
          <div className="monogram">
            N<span>◈</span>
          </div>
          <div>
            <strong>
              Northgate<span className="brand-bank">Corporate Bank</span>
            </strong>
            <small>eKYC WORKSPACE</small>
          </div>
          <Pill>01</Pill>
        </a>
        <div className="nav-label">OPERATOR WORKSPACE</div>
        <nav>
          {links.map(([path, text, Icon]) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              onClick={() => setMenu(false)}
            >
              <Icon size={18} />
              <span>{text}</span>
              {path === "/workspace" && <span className="nav-dot" />}
            </NavLink>
          ))}
        </nav>
        <div className="profile">
          <div className="avatar">
            {user?.name
              .split(" ")
              .map((n) => n[0])
              .join("")}
          </div>
          <div>
            <strong>{user?.name}</strong>
            <small>{user?.role.toUpperCase()} · Northgate Demo</small>
          </div>
          <button className="icon-button" onClick={logout} title="Sign out">
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="app-body">
        <header>
          <button
            className="icon-button mobile-menu"
            title="Toggle navigation"
            onClick={() => setMenu(!menu)}
          >
            <PanelLeftClose />
          </button>
          <div className="location">
            <Globe size={15} />
            <strong>LDN</strong>
            <span> / </span> Singapore · New York
          </div>
          <div className="header-gates">
            <Pill tone="green">
              <span className="dot" />
              Received-doc lock active
            </Pill>
            <Pill tone="purple">
              <ShieldCheck size={13} />
              Human gate enforced
            </Pill>
          </div>
          <div className="header-right">
            <ExperienceControls />
            <span className="header-divider" />
            <div className="avatar small">
              {user?.role.slice(0, 2).toUpperCase()}
            </div>
          </div>
        </header>
        <main>
          {location.pathname !== "/policy" && (
            <div className="environment-bar">
              <span>
                <Command size={12} /> FIRST SOLUTION SLICE
              </span>
              <span>
                {runtime?.offline_demo
                  ? "Offline demo · deterministic fixtures"
                  : runtime?.gemini_configured
                    ? "Gemini primary · Groq standby"
                    : "API keys not configured"}{" "}
                · Synthetic outbox
              </span>
            </div>
          )}
          <div className="page-transition" key={location.pathname}>
            <Outlet />
          </div>
        </main>
        <footer>
          <span>
            <span className="dot" /> Northgate eKYC · All case data is synthetic
          </span>
          <span>RM REVIEW REQUIRED · NO AUTO-SEND</span>
        </footer>
      </div>
    </div>
  );
}
