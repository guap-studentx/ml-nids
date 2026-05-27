import { Activity, Database, FileText, History, LayoutDashboard, RadioTower, ShieldCheck, Signal } from "lucide-react";
import { NavLink } from "react-router-dom";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/captures", label: "Captures", icon: Activity },
  { to: "/live-monitor", label: "Live Monitor", icon: Signal },
  { to: "/models", label: "Models", icon: Database },
  { to: "/agents", label: "Agents", icon: RadioTower },
  { to: "/history", label: "History", icon: History },
  { to: "/reports", label: "Reports", icon: FileText },
];

export default function Sidebar() {
  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-line bg-white md:min-h-screen md:w-64 md:border-b-0 md:border-r">
      <div className="flex h-16 items-center gap-3 border-b border-line px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-accent text-white">
          <ShieldCheck size={20} />
        </div>
        <div>
          <div className="text-base font-semibold text-ink">ML-NIDS</div>
          <div className="text-xs text-muted">Traffic analysis</div>
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto p-3 md:flex-col md:overflow-visible">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex h-10 min-w-max items-center gap-3 rounded-md px-3 text-sm font-medium transition ${
                  isActive ? "bg-teal-50 text-accent" : "text-muted hover:bg-panel hover:text-ink"
                }`
              }
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
