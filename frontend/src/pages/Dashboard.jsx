import { Activity, Database, RadioTower, RefreshCw, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getDashboardSummary, getDashboardTimeseries } from "../api/dashboard";
import Badge from "../components/Badge";
import Button from "../components/Button";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

function statusTone(status) {
  if (status === "completed") return "green";
  if (status === "failed") return "red";
  if (status === "running") return "blue";
  return "amber";
}

function formatTime(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export default function Dashboard() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [timeseries, setTimeseries] = useState(null);
  const [period, setPeriod] = useState("24h");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const chartData = useMemo(
    () =>
      timeseries?.points?.map((point) => ({
        time: new Date(point.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        anomalies: point.anomalies,
      })) ?? [],
    [timeseries],
  );

  const loadDashboard = useCallback(async () => {
    setError("");
    setIsLoading(true);
    try {
      const [summaryResponse, timeseriesResponse] = await Promise.all([
        getDashboardSummary(),
        getDashboardTimeseries(period),
      ]);
      setSummary(summaryResponse);
      setTimeseries(timeseriesResponse);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  return (
    <>
      <PageHeader
        title={t("Dashboard")}
        description={t("System summary for processed sessions, anomalies, and component status.")}
        actions={
          <>
            <select
              className="h-9 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
            >
              <option value="24h">24h</option>
              <option value="72h">72h</option>
              <option value="168h">7d</option>
            </select>
            <Button onClick={loadDashboard}>
              <RefreshCw size={16} />
              {t("Refresh")}
            </Button>
          </>
        }
      />

      <section className="grid gap-5 p-5">
        {isLoading ? (
          <div className="rounded-lg border border-line bg-white p-5">
            <Spinner />
          </div>
        ) : null}
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

        {!isLoading && summary ? (
          <>
            <div className="grid gap-3 md:grid-cols-4">
              <MetricCard icon={Activity} label={t("Sessions")} value={summary.total_sessions} />
              <MetricCard icon={ShieldAlert} label={t("Anomalies 24h")} value={summary.anomalies_24h} />
              <MetricCard icon={RadioTower} label={t("Active agents")} value={summary.active_agents} />
              <MetricCard icon={Database} label={t("Active models")} value={summary.active_models} />
            </div>

            <div className="rounded-lg border border-line bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-ink">{t("Anomaly timeline")}</h2>
                <span className="text-sm text-muted">{timeseries?.period_hours ?? 24} {t("hours")}</span>
              </div>
              <div className="mt-4 h-72">
                {chartData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                      <CartesianGrid stroke="#d9dee7" strokeDasharray="3 3" />
                      <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="anomalies" stroke="#0f766e" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center text-sm text-muted">{t("No points for selected period.")}</div>
                )}
              </div>
            </div>

            <div className="overflow-hidden rounded-lg border border-line bg-white">
              <div className="border-b border-line px-4 py-3">
                <h2 className="text-base font-semibold text-ink">{t("Recent captures")}</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[860px] text-left text-sm">
                  <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
                    <tr>
                      <th className="px-4 py-3 font-semibold">{t("Name")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Mode")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Status")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Flows")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Anomalies")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Finished")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {summary.recent_captures.map((capture) => (
                      <tr
                        key={capture.id}
                        className="cursor-pointer hover:bg-panel"
                        onClick={() => navigate(`/captures/${capture.id}`)}
                      >
                        <td className="px-4 py-3 font-medium text-ink">{capture.name ?? capture.source_filename ?? capture.id}</td>
                        <td className="px-4 py-3 text-muted">{t(capture.mode)}</td>
                        <td className="px-4 py-3">
                          <Badge tone={statusTone(capture.status)}>{t(capture.status)}</Badge>
                        </td>
                        <td className="px-4 py-3 text-muted">{capture.flows_total}</td>
                        <td className="px-4 py-3 text-muted">{capture.flows_anomaly}</td>
                        <td className="px-4 py-3 text-muted">{formatTime(capture.finished_at)}</td>
                      </tr>
                    ))}
                    {summary.recent_captures.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-muted" colSpan="6">
                          {t("No capture sessions yet.")}
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : null}
      </section>
    </>
  );
}

function MetricCard({ icon, label, value }) {
  const MetricIcon = icon;

  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase text-muted">{label}</div>
        <MetricIcon className="text-accent" size={18} />
      </div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value}</div>
    </div>
  );
}
