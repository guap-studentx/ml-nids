import { Navigate, Route, Routes } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Spinner from "./components/Spinner";
import { useAuth } from "./context/AuthContext";
import { useLanguage } from "./context/LanguageContext";
import Agents from "./pages/Agents";
import CaptureDetail from "./pages/CaptureDetail";
import CaptureFlows from "./pages/CaptureFlows";
import Captures from "./pages/Captures";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import LiveMonitor from "./pages/LiveMonitor";
import Login from "./pages/Login";
import Models from "./pages/Models";
import Reports from "./pages/Reports";

function ProtectedLayout() {
  const { isAuthenticated, isReady, logout, user } = useAuth();
  const { language, setLanguage, t } = useLanguage();

  if (!isReady) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-panel">
        <Spinner label={t("Restore session")} />
      </main>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-panel md:flex">
      <Sidebar />
      <main className="min-w-0 flex-1">
        <div className="flex h-16 items-center justify-end gap-3 border-b border-line bg-white px-5">
          <label className="flex items-center gap-2 text-sm text-muted">
            <span className="hidden sm:inline">{t("Language")}</span>
            <select
              className="h-9 rounded-md border border-line bg-white px-2 text-sm font-medium text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            >
              <option value="en">EN</option>
              <option value="ru">RU</option>
            </select>
          </label>
          <div className="text-right">
            <div className="text-sm font-medium text-ink">{user.username}</div>
            <div className="text-xs text-muted">{user.role}</div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="h-9 rounded-md border border-line bg-white px-3 text-sm font-medium text-muted hover:bg-panel hover:text-ink"
          >
            {t("Logout")}
          </button>
        </div>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/captures" element={<Captures />} />
          <Route path="/captures/:captureId" element={<CaptureDetail />} />
          <Route path="/captures/:captureId/flows" element={<CaptureFlows />} />
          <Route path="/live-monitor" element={<LiveMonitor />} />
          <Route path="/models" element={<Models />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/history" element={<History />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<ProtectedLayout />} />
    </Routes>
  );
}
